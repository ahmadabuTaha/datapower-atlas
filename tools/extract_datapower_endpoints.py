#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import ipaddress
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import yaml


EXTRACTOR_VERSION = "1.1-architecture-beta-wsp-composite"


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    if not isinstance(doc, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return doc


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def strip_wrapping_quotes(value: str) -> str:
    value = (value or "").strip()
    if len(value) >= 2:
        if (value[0] == value[-1]) and value[0] in {'"', "'"}:
            value = value[1:-1]
    return value.strip()


def infer_domain(row: Dict[str, str]) -> str:
    explicit = (row.get("domain") or "").strip()
    if explicit:
        return explicit

    source_file = (
        row.get("evidence_file")
        or row.get("source_file")
        or ""
    ).replace("\\", "/")

    parts = [p for p in source_file.split("/") if p]

    for i, part in enumerate(parts):
        if part == "extracted" and i + 2 < len(parts):
            if parts[i + 2] == "config":
                return parts[i + 1]

    for i, part in enumerate(parts):
        if part == "config" and i >= 1:
            return parts[i - 1]

    return ""


# ---------------------------------------------------------------------------
# Endpoint taxonomy
# ---------------------------------------------------------------------------

def load_endpoint_taxonomy(path: Path) -> Dict[str, Any]:
    doc = load_yaml(path)
    endpoint_types = doc.get("endpoint_types")
    if not isinstance(endpoint_types, dict):
        raise ValueError(
            "endpoint_types.yaml must contain endpoint_types mapping"
        )
    return doc


def scheme_index(endpoint_taxonomy: Dict[str, Any]) -> Dict[str, str]:
    result: Dict[str, str] = {}

    endpoint_types = endpoint_taxonomy["endpoint_types"]
    for endpoint_type, spec in endpoint_types.items():
        if not isinstance(spec, dict):
            continue
        for scheme in spec.get("schemes", []) or []:
            result[str(scheme).lower()] = str(endpoint_type)

    return result


def endpoint_type_spec(
    endpoint_taxonomy: Dict[str, Any],
    endpoint_type: str,
) -> Dict[str, Any]:
    spec = endpoint_taxonomy["endpoint_types"].get(endpoint_type, {})
    return spec if isinstance(spec, dict) else {}


# ---------------------------------------------------------------------------
# Endpoint parsing
# ---------------------------------------------------------------------------

DYNAMIC_PREFIXES = (
    "var://",
    "context://",
)

VARIABLE_MARKERS = (
    "${",
    "$(",
    "%{",
)

DEFAULT_PORTS = {
    "http": 80,
    "https": 443,
    "ftp": 21,
    "sftp": 22,
}


def is_dynamic_expression(value: str) -> bool:
    v = value.strip().lower()

    if any(v.startswith(prefix) for prefix in DYNAMIC_PREFIXES):
        return True

    if any(marker in value for marker in VARIABLE_MARKERS):
        return True

    # DataPower runtime variable paths occasionally appear embedded in values.
    if "var://context/" in v or "var://service/" in v:
        return True

    return False


def host_kind(host: str) -> str:
    if not host:
        return ""

    candidate = host.strip("[]")

    try:
        addr = ipaddress.ip_address(candidate)
        return "ipv6" if addr.version == 6 else "ipv4"
    except ValueError:
        pass

    if candidate.lower() in {"localhost", "loopback"}:
        return "local_hostname"

    return "hostname"


def normalize_url(parts) -> str:
    scheme = (parts.scheme or "").lower()
    hostname = parts.hostname or ""

    # Preserve IPv6 bracket notation.
    rendered_host = hostname
    try:
        if hostname and ipaddress.ip_address(hostname).version == 6:
            rendered_host = f"[{hostname}]"
    except ValueError:
        pass

    netloc = rendered_host
    if parts.port is not None:
        netloc = f"{rendered_host}:{parts.port}"

    if parts.username:
        # We deliberately do not surface credentials as endpoint identity.
        # Presence can be observed through has_userinfo.
        netloc = rendered_host
        if parts.port is not None:
            netloc = f"{rendered_host}:{parts.port}"

    return urlunsplit((
        scheme,
        netloc,
        parts.path or "",
        parts.query or "",
        parts.fragment or "",
    ))


def parse_static_url(
    value: str,
    scheme_to_type: Dict[str, str],
    endpoint_taxonomy: Dict[str, Any],
) -> Dict[str, Any]:
    try:
        parts = urlsplit(value)
    except ValueError as exc:
        return {
            "parse_status": "invalid_endpoint",
            "parse_reason": f"url_parse_error:{exc.__class__.__name__}",
        }

    scheme = (parts.scheme or "").lower()

    if not scheme:
        return {
            "parse_status": "invalid_endpoint",
            "parse_reason": "missing_scheme",
        }

    endpoint_type = scheme_to_type.get(scheme)

    if not endpoint_type:
        return {
            "parse_status": "unsupported_endpoint_scheme",
            "parse_reason": f"unsupported_scheme:{scheme}",
            "scheme": scheme,
        }

    spec = endpoint_type_spec(endpoint_taxonomy, endpoint_type)

    # Non-network URI types can still be normalized, although current
    # endpoint_reference mappings normally target network resources.
    network_endpoint = spec.get("network_endpoint", True)

    host = parts.hostname or ""
    port = parts.port

    if network_endpoint and not host:
        return {
            "parse_status": "invalid_endpoint",
            "parse_reason": "network_endpoint_missing_host",
            "endpoint_type": endpoint_type,
            "scheme": scheme,
        }

    effective_port = port
    port_source = ""
    if effective_port is not None:
        port_source = "explicit"
    elif scheme in DEFAULT_PORTS:
        effective_port = DEFAULT_PORTS[scheme]
        port_source = "scheme_default"

    normalized = normalize_url(parts)

    return {
        "parse_status": "parsed_static_endpoint",
        "parse_reason": "",
        "endpoint_type": endpoint_type,
        "scheme": scheme,
        "transport": spec.get("transport", ""),
        "encrypted": spec.get("encrypted", ""),
        "network_endpoint": network_endpoint,
        "host": host,
        "host_kind": host_kind(host),
        "port": port if port is not None else "",
        "effective_port": effective_port if effective_port is not None else "",
        "port_source": port_source,
        "path": parts.path or "",
        "query": parts.query or "",
        "fragment": parts.fragment or "",
        "has_userinfo": bool(parts.username or parts.password),
        "normalized_endpoint": normalized,
    }


def parse_host_port(
    value: str,
    endpoint_taxonomy: Dict[str, Any],
) -> Dict[str, Any]:
    raw = value.strip()

    if not raw:
        return {
            "parse_status": "invalid_endpoint",
            "parse_reason": "empty_endpoint",
        }

    # [IPv6]:port
    m = re.fullmatch(r"\[([^\]]+)\]:(\d+)", raw)
    if m:
        host = m.group(1)
        port = int(m.group(2))
    else:
        # hostname:port or IPv4:port. Deliberately avoid guessing raw IPv6.
        if raw.count(":") != 1:
            return {
                "parse_status": "invalid_endpoint",
                "parse_reason": "not_host_port_form",
            }

        host, port_text = raw.rsplit(":", 1)
        host = host.strip()

        if not port_text.isdigit():
            return {
                "parse_status": "invalid_endpoint",
                "parse_reason": "invalid_port",
            }

        port = int(port_text)

    if not (1 <= port <= 65535):
        return {
            "parse_status": "invalid_endpoint",
            "parse_reason": "port_out_of_range",
        }

    endpoint_type = "host_port_endpoint"
    spec = endpoint_type_spec(endpoint_taxonomy, endpoint_type)

    return {
        "parse_status": "parsed_static_endpoint",
        "parse_reason": "",
        "endpoint_type": endpoint_type,
        "scheme": "",
        "transport": spec.get("transport", ""),
        "encrypted": spec.get("encrypted", ""),
        "network_endpoint": True,
        "host": host,
        "host_kind": host_kind(host),
        "port": port,
        "effective_port": port,
        "port_source": "explicit",
        "path": "",
        "query": "",
        "fragment": "",
        "has_userinfo": False,
        "normalized_endpoint": f"{host}:{port}",
    }


def parse_endpoint(
    raw_reference: str,
    scheme_to_type: Dict[str, str],
    endpoint_taxonomy: Dict[str, Any],
) -> Dict[str, Any]:
    value = strip_wrapping_quotes(raw_reference)

    if not value:
        return {
            "parse_status": "invalid_endpoint",
            "parse_reason": "empty_endpoint",
            "endpoint_expression": "",
        }

    if is_dynamic_expression(value):
        return {
            "parse_status": "dynamic_endpoint_expression",
            "parse_reason": "",
            "endpoint_expression": value,
            "endpoint_type": "dynamic_endpoint",
            "normalized_endpoint": "",
            "scheme": "",
            "transport": "",
            "encrypted": "",
            "network_endpoint": True,
            "host": "",
            "host_kind": "",
            "port": "",
            "effective_port": "",
            "port_source": "",
            "path": "",
            "query": "",
            "fragment": "",
            "has_userinfo": False,
        }

    # First prefer explicit URI schemes.
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value):
        result = parse_static_url(
            value,
            scheme_to_type,
            endpoint_taxonomy,
        )
        result["endpoint_expression"] = ""
        return result

    # Then exact host:port form.
    result = parse_host_port(value, endpoint_taxonomy)
    result["endpoint_expression"] = ""
    return result


# ---------------------------------------------------------------------------
# Architecture semantics
# ---------------------------------------------------------------------------

def route_role(ref: Dict[str, str], parse_status: str) -> str:
    source_type = (ref.get("source_type") or "").strip()
    property_name = (ref.get("property_name") or "").strip()

    if source_type == "multi_protocol_gateway" and property_name == "backend-url":
        return "configured_default_backend"

    if source_type == "processing_action" and property_name == "destination":
        if parse_status == "dynamic_endpoint_expression":
            return "dynamic_route_expression"
        return "processing_action_route_candidate"

    return "endpoint_dependency"


def endpoint_identity_key(
    environment: str,
    domain: str,
    parsed: Dict[str, Any],
) -> str:
    if parsed.get("parse_status") != "parsed_static_endpoint":
        return ""

    material = "|".join([
        environment,
        domain,
        str(parsed.get("endpoint_type", "")),
        str(parsed.get("normalized_endpoint", "")),
    ])
    return sha256_text(material)


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def extract_endpoints(
    refs: List[Dict[str, str]],
    endpoint_taxonomy: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:

    scheme_to_type = scheme_index(endpoint_taxonomy)

    occurrences: List[Dict[str, Any]] = []
    non_endpoint_passthrough: List[Dict[str, Any]] = []

    for ref in refs:
        family = (ref.get("reference_family") or "").strip()

        if family != "endpoint_reference":
            non_endpoint_passthrough.append(ref)
            continue

        env = (ref.get("environment") or "").strip()
        domain = infer_domain(ref)
        raw = ref.get("raw_reference", "")

        parsed = parse_endpoint(
            raw,
            scheme_to_type,
            endpoint_taxonomy,
        )

        status = parsed.get("parse_status", "invalid_endpoint")
        identity_hash = endpoint_identity_key(
            env,
            domain,
            parsed,
        )

        endpoint_id = (
            f"endpoint:{env}:{domain}:{identity_hash[:20]}"
            if identity_hash
            else ""
        )

        row = {
            "endpoint_occurrence_id": (
                f"endpoint-occ:{ref.get('reference_id','')}"
            ),
            "endpoint_id": endpoint_id,

            "environment": env,
            "domain": domain,

            "source_reference_id": ref.get("reference_id", ""),
            "source_object_id": ref.get("source_object_id", ""),
            "source_type": ref.get("source_type", ""),
            "source_name": ref.get("source_name", ""),
            "property_name": ref.get("property_name", ""),
            "mapping_id": ref.get("mapping_id", ""),
            "relationship_type_hint": ref.get(
                "relationship_type_hint", ""
            ),

            "route_role": route_role(ref, status),

            "raw_endpoint": raw,
            "endpoint_expression": parsed.get(
                "endpoint_expression", ""
            ),
            "normalized_endpoint": parsed.get(
                "normalized_endpoint", ""
            ),

            "endpoint_type": parsed.get("endpoint_type", ""),
            "scheme": parsed.get("scheme", ""),
            "transport": parsed.get("transport", ""),
            "encrypted": parsed.get("encrypted", ""),
            "network_endpoint": parsed.get("network_endpoint", ""),

            "host": parsed.get("host", ""),
            "host_kind": parsed.get("host_kind", ""),
            "port": parsed.get("port", ""),
            "effective_port": parsed.get("effective_port", ""),
            "port_source": parsed.get("port_source", ""),
            "path": parsed.get("path", ""),
            "query": parsed.get("query", ""),
            "fragment": parsed.get("fragment", ""),
            "has_userinfo": parsed.get("has_userinfo", False),

            "parse_status": status,
            "parse_reason": parsed.get("parse_reason", ""),

            "source_line": ref.get("source_line", ""),
            "evidence_file": ref.get("evidence_file", ""),
            "extractor_version": EXTRACTOR_VERSION,
        }

        occurrences.append(row)

    # Build a unique static endpoint catalog.
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in occurrences:
        if row["endpoint_id"]:
            grouped[row["endpoint_id"]].append(row)

    catalog: List[Dict[str, Any]] = []
    for endpoint_id, rows in grouped.items():
        first = rows[0]
        roles = sorted({r["route_role"] for r in rows if r["route_role"]})
        source_types = sorted({
            r["source_type"] for r in rows if r["source_type"]
        })

        catalog.append({
            "endpoint_id": endpoint_id,
            "environment": first["environment"],
            "domain": first["domain"],
            "endpoint_type": first["endpoint_type"],
            "normalized_endpoint": first["normalized_endpoint"],
            "scheme": first["scheme"],
            "transport": first["transport"],
            "encrypted": first["encrypted"],
            "host": first["host"],
            "host_kind": first["host_kind"],
            "effective_port": first["effective_port"],
            "path": first["path"],
            "reference_count": len(rows),
            "route_roles": "|".join(roles),
            "source_types": "|".join(source_types),
            "extractor_version": EXTRACTOR_VERSION,
        })

    return occurrences, catalog, non_endpoint_passthrough




def extract_wsp_composite_endpoints(
    properties: List[Dict[str, str]],
    endpoint_taxonomy: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compose WSP remote endpoint evidence from a single endpoint-rewrite
    occurrence. This does not infer values across objects or occurrences.

    Required components:
      remote-endpoint-protocol
      remote-endpoint-hostname
      remote-endpoint-port
      remote-endpoint-uri (optional for identity, preserved when present)
    """
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for row in properties:
        if row.get("canonical_type") != "web_service_proxy_endpoint_rewrite":
            continue
        occurrence_id = row.get("occurrence_id") or ""
        if occurrence_id:
            grouped[occurrence_id].append(row)

    scheme_to_type = scheme_index(endpoint_taxonomy)
    result: List[Dict[str, Any]] = []

    for occurrence_id, rows in grouped.items():
        by_name: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        for row in rows:
            by_name[row.get("property_name", "")].append(row)

        def first_value(name: str) -> str:
            values = by_name.get(name, [])
            return strip_wrapping_quotes(values[0].get("property_value", "")) if values else ""

        protocol = first_value("remote-endpoint-protocol").lower()
        host = first_value("remote-endpoint-hostname")
        port = first_value("remote-endpoint-port")
        uri = first_value("remote-endpoint-uri")

        if not protocol or not host:
            continue

        if uri and not uri.startswith("/"):
            uri = "/" + uri

        authority = host
        if port:
            authority = f"{host}:{port}"

        raw_endpoint = f"{protocol}://{authority}{uri}"
        parsed = parse_endpoint(
            raw_endpoint,
            scheme_to_type,
            endpoint_taxonomy,
        )

        first = rows[0]
        env = first.get("environment", "")
        domain = infer_domain(first)
        identity_hash = endpoint_identity_key(env, domain, parsed)
        endpoint_id = (
            f"endpoint:{env}:{domain}:{identity_hash[:20]}"
            if identity_hash else ""
        )

        source_lines = [
            int(r["source_line"])
            for r in rows
            if (r.get("source_line") or "").isdigit()
            and r.get("property_name") in {
                "remote-endpoint-protocol",
                "remote-endpoint-hostname",
                "remote-endpoint-port",
                "remote-endpoint-uri",
            }
        ]

        result.append({
            "endpoint_occurrence_id": f"endpoint-occ:wsp:{occurrence_id}",
            "endpoint_id": endpoint_id,
            "environment": env,
            "domain": domain,
            "source_reference_id": "",
            "source_object_id": first.get("object_id", ""),
            "source_type": "web_service_proxy_endpoint_rewrite",
            "source_name": first.get("object_name", ""),
            "property_name": "remote-endpoint-composite",
            "mapping_id": "wsp_endpoint_rewrite_composite",
            "relationship_type_hint": "routes_to_backend",
            "route_role": "web_service_proxy_remote_endpoint",
            "raw_endpoint": raw_endpoint,
            "endpoint_expression": parsed.get("endpoint_expression", ""),
            "normalized_endpoint": parsed.get("normalized_endpoint", ""),
            "endpoint_type": parsed.get("endpoint_type", ""),
            "scheme": parsed.get("scheme", ""),
            "transport": parsed.get("transport", ""),
            "encrypted": parsed.get("encrypted", ""),
            "network_endpoint": parsed.get("network_endpoint", ""),
            "host": parsed.get("host", ""),
            "host_kind": parsed.get("host_kind", ""),
            "port": parsed.get("port", ""),
            "effective_port": parsed.get("effective_port", ""),
            "port_source": parsed.get("port_source", ""),
            "path": parsed.get("path", ""),
            "query": parsed.get("query", ""),
            "fragment": parsed.get("fragment", ""),
            "has_userinfo": parsed.get("has_userinfo", False),
            "parse_status": parsed.get("parse_status", "invalid_endpoint"),
            "parse_reason": parsed.get("parse_reason", ""),
            "source_line": min(source_lines) if source_lines else "",
            "evidence_file": first.get("source_file", ""),
            "extractor_version": EXTRACTOR_VERSION,
        })

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Extract and normalize DataPower endpoint references produced by "
            "Reference Extractor V1."
        )
    )

    ap.add_argument(
        "--references",
        required=True,
        help=(
            "non_object_references CSV from Relationship Resolver V1 "
            "or references CSV from Reference Extractor V1"
        ),
    )
    ap.add_argument(
        "--endpoint-types",
        required=True,
        help="taxonomy/endpoint_types.yaml",
    )
    ap.add_argument(
        "--properties",
        required=False,
        help=(
            "object_properties CSV. Required to compose Web Service Proxy "
            "remote endpoints from endpoint-rewrite properties."
        ),
    )
    ap.add_argument(
        "--output",
        default="index/endpoints.csv",
        help="Endpoint occurrences with source/evidence linkage",
    )
    ap.add_argument(
        "--catalog-output",
        default="index/endpoint_catalog.csv",
        help="Unique normalized static endpoint catalog",
    )
    ap.add_argument(
        "--non-endpoint-output",
        default="index/file_references_pending.csv",
        help="Non-endpoint references preserved for later specialized resolver",
    )

    args = ap.parse_args()

    refs_path = Path(args.references)
    taxonomy_path = Path(args.endpoint_types)

    for path in (refs_path, taxonomy_path):
        if not path.exists():
            print(f"[FATAL] Missing input: {path}")
            return 2

    refs = load_csv(refs_path)
    endpoint_taxonomy = load_endpoint_taxonomy(taxonomy_path)

    occurrences, catalog, passthrough = extract_endpoints(
        refs,
        endpoint_taxonomy,
    )

    # WSP endpoint-rewrite remote endpoints are composite evidence spread
    # across multiple properties, so they are composed here from the owning
    # object occurrence rather than forced into a one-property reference.
    if args.properties:
        properties_path = Path(args.properties)
        if not properties_path.exists():
            print(f"[FATAL] Missing properties input: {properties_path}")
            return 2
        property_rows = load_csv(properties_path)
        wsp_occurrences = extract_wsp_composite_endpoints(
            property_rows,
            endpoint_taxonomy,
        )
        occurrences.extend(wsp_occurrences)

        # Rebuild the unique static endpoint catalog after adding WSP endpoints.
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in occurrences:
            if row.get("endpoint_id"):
                grouped[row["endpoint_id"]].append(row)

        catalog = []
        for endpoint_id, rows in grouped.items():
            first = rows[0]
            roles = sorted({r["route_role"] for r in rows if r["route_role"]})
            source_types = sorted({
                r["source_type"] for r in rows if r["source_type"]
            })
            catalog.append({
                "endpoint_id": endpoint_id,
                "environment": first["environment"],
                "domain": first["domain"],
                "endpoint_type": first["endpoint_type"],
                "normalized_endpoint": first["normalized_endpoint"],
                "scheme": first["scheme"],
                "transport": first["transport"],
                "encrypted": first["encrypted"],
                "host": first["host"],
                "host_kind": first["host_kind"],
                "effective_port": first["effective_port"],
                "path": first["path"],
                "reference_count": len(rows),
                "route_roles": "|".join(roles),
                "source_types": "|".join(source_types),
                "extractor_version": EXTRACTOR_VERSION,
            })

    occurrence_fields = [
        "endpoint_occurrence_id",
        "endpoint_id",
        "environment",
        "domain",
        "source_reference_id",
        "source_object_id",
        "source_type",
        "source_name",
        "property_name",
        "mapping_id",
        "relationship_type_hint",
        "route_role",
        "raw_endpoint",
        "endpoint_expression",
        "normalized_endpoint",
        "endpoint_type",
        "scheme",
        "transport",
        "encrypted",
        "network_endpoint",
        "host",
        "host_kind",
        "port",
        "effective_port",
        "port_source",
        "path",
        "query",
        "fragment",
        "has_userinfo",
        "parse_status",
        "parse_reason",
        "source_line",
        "evidence_file",
        "extractor_version",
    ]

    catalog_fields = [
        "endpoint_id",
        "environment",
        "domain",
        "endpoint_type",
        "normalized_endpoint",
        "scheme",
        "transport",
        "encrypted",
        "host",
        "host_kind",
        "effective_port",
        "path",
        "reference_count",
        "route_roles",
        "source_types",
        "extractor_version",
    ]

    # Preserve whatever columns came in for non-endpoint references.
    passthrough_fields = list(refs[0].keys()) if refs else []

    write_csv(Path(args.output), occurrences, occurrence_fields)
    write_csv(Path(args.catalog_output), catalog, catalog_fields)

    if passthrough_fields:
        write_csv(
            Path(args.non_endpoint_output),
            passthrough,
            passthrough_fields,
        )
    else:
        Path(args.non_endpoint_output).parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        Path(args.non_endpoint_output).write_text("", encoding="utf-8")

    status_counts = Counter(
        r["parse_status"] for r in occurrences
    )
    type_counts = Counter(
        r["endpoint_type"] for r in occurrences
        if r["endpoint_type"]
    )
    role_counts = Counter(
        r["route_role"] for r in occurrences
    )

    static_count = status_counts.get(
        "parsed_static_endpoint", 0
    )
    dynamic_count = status_counts.get(
        "dynamic_endpoint_expression", 0
    )
    invalid_count = sum(
        count
        for status, count in status_counts.items()
        if status not in {
            "parsed_static_endpoint",
            "dynamic_endpoint_expression",
        }
    )

    print("=" * 80)
    print("DATAPOWER ENDPOINT EXTRACTOR V1")
    print("=" * 80)
    print(f"Extractor version:             {EXTRACTOR_VERSION}")
    print(f"References loaded:             {len(refs)}")
    print(f"Endpoint references processed: {len(occurrences)}")
    print(f"Static endpoints parsed:       {static_count}")
    print(f"Dynamic endpoint expressions:  {dynamic_count}")
    print(f"Invalid/unsupported endpoints: {invalid_count}")
    print(f"Unique static endpoints:       {len(catalog)}")
    print(f"Non-endpoint refs deferred:    {len(passthrough)}")

    print("-" * 80)
    print("Endpoint types:")
    for key, value in sorted(type_counts.items()):
        print(f"  {key:40} {value}")

    print("-" * 80)
    print("Route roles:")
    for key, value in sorted(role_counts.items()):
        print(f"  {key:40} {value}")

    print("-" * 80)
    print("Parse status:")
    for key, value in sorted(status_counts.items()):
        print(f"  {key:40} {value}")

    print("-" * 80)

    if invalid_count:
        print(
            "ENDPOINT EXTRACTOR V1: PASS WITH UNPARSED ENDPOINT EVIDENCE"
        )
    else:
        print("ENDPOINT EXTRACTOR V1: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
