#!/usr/bin/env python3
"""
DataPower Atlas - Operation Journey Builder

Purpose
-------
Decompose DataPower service processing policies into operation-level journeys
using resolved graph evidence, then enrich the existing operation journey with
architecture-relevant dependency, file-resolution, routing/egress, certainty,
findings, provenance, and targeted resolved-artifact semantics.

Important
---------
- Existing traversal semantics are preserved.
- Relationships are never inferred from names.
- Missing artifacts remain unresolved.
- Configured backend is not automatically treated as actual egress.
- Cross-domain evidence is never borrowed automatically.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Iterable, Tuple, Optional
from xml.parsers import expat

VERSION = "base-candidate"

SERVICE_ROOT_TYPES = {
    "multi_protocol_gateway",
    "web_service_proxy",
}

PROCESSING_POLICY_TYPES = {
    "style_policy",
    "web_service_proxy_processing_policy",
}

PROCESSING_RULE_TYPES = {
    "processing_rule",
    "web_service_proxy_processing_rule",
}

TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_records(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv(path)
    if suffix == ".jsonl":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("findings", "records", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
    return []


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stable_id(parts: List[str]) -> str:
    raw = "\x1f".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def unique_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def first_nonempty(row: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def normalize_bool(value: str) -> Optional[bool]:
    norm = str(value or "").strip().strip('"\'').lower()
    if norm in TRUE_VALUES:
        return True
    if norm in FALSE_VALUES:
        return False
    return None


def normalize_resolution_status(row: Dict[str, Any]) -> str:
    raw = first_nonempty(row, "resolution_status", "status").strip()
    if raw == "resolved_exact":
        return "resolved"
    if raw.startswith("resolved"):
        return "resolved"
    if raw:
        return raw
    if first_nonempty(row, "target_file_id", "target_object_id", "resolved_path", "target_relative_path"):
        return "resolved"
    return "unresolved_target_not_found"


def evidence_pointer(row: Dict[str, Any]) -> Dict[str, str]:
    ptr = {
        "evidence_file": first_nonempty(row, "evidence_file", "source_file"),
        "source_line": first_nonempty(row, "source_line", "line_number", "start_line"),
        "property_name": first_nonempty(row, "property_name"),
        "property_path": first_nonempty(row, "property_path"),
    }
    return {k: v for k, v in ptr.items() if v}


def dedupe_dicts(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def properties_by_object(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        oid = row.get("object_id", "")
        if oid:
            result[oid].append(row)
    return result


def raw_file_reference(row: Dict[str, Any]) -> str:
    return first_nonempty(
        row,
        "raw_reference",
        "reference_value",
        "raw_value",
        "property_value",
        "target_reference",
        "target_relative_path",
    )


def file_dependency_record(row: Dict[str, Any]) -> Dict[str, Any]:
    status = normalize_resolution_status(row)
    certainty = "confirmed" if status == "resolved" else "unresolved"
    return {
        "target_file_id": first_nonempty(row, "target_file_id"),
        "target_relative_path": first_nonempty(row, "target_relative_path", "resolved_path"),
        "classification": first_nonempty(row, "target_classification", "classification"),
        "relationship_type": first_nonempty(row, "relationship_type"),
        "source_object_id": first_nonempty(row, "source_object_id"),
        "property_name": first_nonempty(row, "property_name"),
        "raw_reference": raw_file_reference(row),
        "resolution_status": status,
        "certainty": certainty,
        "evidence": evidence_pointer(row),
    }


def relationship_dependency_record(row: Dict[str, Any]) -> Dict[str, Any]:
    raw_status = first_nonempty(row, "resolution_status")
    resolved = raw_status in {"resolved_exact", "resolved"} or bool(first_nonempty(row, "target_object_id"))
    return {
        "relationship_type": first_nonempty(row, "relationship_type"),
        "source_object_id": first_nonempty(row, "source_object_id"),
        "source_object_name": first_nonempty(row, "source_object_name"),
        "source_type": first_nonempty(row, "source_type"),
        "target_object_id": first_nonempty(row, "target_object_id"),
        "target_object_name": first_nonempty(row, "target_object_name", "target_name"),
        "target_type": first_nonempty(row, "target_type", "target_type_hint"),
        "raw_reference": first_nonempty(row, "raw_reference", "property_value", "target_name"),
        "resolution_status": "resolved" if resolved else (raw_status or "unresolved_target_not_found"),
        "certainty": "confirmed" if resolved else "unresolved",
        "evidence": evidence_pointer(row),
    }


def artifact_candidate_paths(row: Dict[str, Any], artifact_root: Optional[Path]) -> List[Path]:
    values = unique_keep_order([
        first_nonempty(row, "resolved_path"),
        first_nonempty(row, "target_relative_path"),
    ])
    out: List[Path] = []
    for value in values:
        if not value:
            continue
        p = Path(value)
        if p.is_absolute():
            out.append(p)
        if artifact_root:
            out.append(artifact_root / value.lstrip("/"))
    return out


def extract_urls(text: str) -> List[str]:
    return unique_keep_order(
        re.findall(r"https?://[^\s\"'<>)}]+", text, flags=re.IGNORECASE)
    )


def extract_method_near(text: str, token: str) -> str:
    idx = text.lower().find(token.lower())
    if idx < 0:
        return ""
    window = text[max(0, idx - 700): idx + 1200]
    patterns = [
        r"\bmethod\s*[:=]\s*[\"']?(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)",
        r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, window, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return ""



def extract_runtime_destination_components(text: str, urls: List[str]) -> Dict[str, Any]:
    runtime_refs = unique_keep_order(
        re.findall(r"var://service/[A-Za-z0-9_./:-]+", text, flags=re.IGNORECASE)
    )
    if not urls or not runtime_refs:
        return {
            "destination_type": "static" if urls else "dynamic_or_runtime_computed",
            "base_targets": urls,
            "dynamic_components": [],
        }

    nearby_refs: List[str] = []
    lowered = text.lower()
    for url in urls:
        start = 0
        url_l = url.lower()
        while True:
            idx = lowered.find(url_l, start)
            if idx < 0:
                break
            window = text[max(0, idx - 500): idx + len(url) + 500]
            nearby_refs.extend(
                re.findall(r"var://service/[A-Za-z0-9_./:-]+", window, flags=re.IGNORECASE)
            )
            start = idx + len(url)

    dynamic_components = unique_keep_order(nearby_refs)
    return {
        "destination_type": "dynamic" if dynamic_components else "static",
        "base_targets": urls,
        "dynamic_components": dynamic_components,
    }


def xpath_literal_value(expression: str) -> Tuple[str, str]:
    value = expression.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        return value[1:-1].replace(quote * 2, quote), "literal"
    return value, "computed"


def split_xpath_arguments(expression: str) -> List[str]:
    arguments: List[str] = []
    start = 0
    depth = 0
    quote = ""
    index = 0
    while index < len(expression):
        char = expression[index]
        if quote:
            if char == quote:
                if index + 1 < len(expression) and expression[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
        elif char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            arguments.append(expression[start:index].strip())
            start = index + 1
        index += 1
    arguments.append(expression[start:].strip())
    return arguments


def extract_database_calls(expression: str) -> List[List[str]]:
    calls: List[List[str]] = []
    call_pattern = re.compile(r"(?<![\w.-])(?:dp:sql-execute|dp)\s*\(")
    index = 0
    quote = ""
    while index < len(expression):
        char = expression[index]
        if quote:
            if char == quote:
                if index + 1 < len(expression) and expression[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        match = call_pattern.match(expression, index)
        if not match:
            index += 1
            continue

        opening = match.end() - 1
        depth = 1
        call_quote = ""
        closing = opening + 1
        while closing < len(expression) and depth:
            current = expression[closing]
            if call_quote:
                if current == call_quote:
                    if closing + 1 < len(expression) and expression[closing + 1] == call_quote:
                        closing += 1
                    else:
                        call_quote = ""
            elif current in {"'", '"'}:
                call_quote = current
            elif current == "(":
                depth += 1
            elif current == ")":
                depth -= 1
            closing += 1
        if depth == 0:
            calls.append(split_xpath_arguments(expression[opening + 1:closing - 1]))
            index = closing
        else:
            index = match.end()
    return calls


def extract_database_semantic_facts(text: str, path: Path, file_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    owning_action = first_nonempty(file_row, "source_object_id")
    parser = expat.ParserCreate(namespace_separator="}")

    def add_fact(datasource_expression: str, statement_expression: str, syntax_form: str, source_line: int) -> None:
        datasource, datasource_type = xpath_literal_value(datasource_expression)
        statement, statement_type = xpath_literal_value(statement_expression)
        facts.append({
            "fact_type": "outbound_database_request",
            "mechanism": "datapower_sql",
            "datasource": datasource,
            "datasource_type": datasource_type,
            "statement": statement,
            "statement_type": statement_type,
            "syntax_form": syntax_form,
            "certainty": "confirmed",
            "artifact_path": str(path),
            "source_path": str(path),
            "source_line": source_line,
            "source_object_id": owning_action,
            "owning_action": owning_action,
        })

    def start_element(name: str, attributes: Dict[str, str]) -> None:
        local_name = name.rsplit("}", 1)[-1].rsplit(":", 1)[-1]
        local_attributes = {key.rsplit("}", 1)[-1].rsplit(":", 1)[-1]: value for key, value in attributes.items()}
        source_line = parser.CurrentLineNumber
        is_dp_element = local_name == "dp" or (
            local_name == "sql-execute" and name.startswith("http://www.datapower.com/extensions}")
        )
        if is_dp_element and "source" in local_attributes and "statement" in local_attributes:
            add_fact(local_attributes["source"], local_attributes["statement"], "extension_element", source_line)
        for expression in attributes.values():
            for arguments in extract_database_calls(expression):
                if len(arguments) == 2:
                    add_fact(arguments[0], arguments[1], "extension_function", source_line)

    parser.StartElementHandler = start_element
    try:
        parser.Parse(text, True)
    except expat.ExpatError:
        return []
    return facts


def extract_skip_backside_evidence(rows: List[Dict[str, str]]) -> List[Tuple[str, Optional[bool], Dict[str, Any]]]:
    """Extract only explicit skip-backside facts.

    DataPower setvar actions represent the variable name and its assigned value as
    separate properties.  The old enrichment treated any boolean-looking property
    on the same action (for example retry-count=0 or timeout=0) as the setvar value.
    This routine deliberately pairs only an explicit skip-backside marker with an
    explicit setvar value property from the same object/property set.
    """
    evidence: List[Tuple[str, Optional[bool], Dict[str, Any]]] = []

    # Direct property forms, if present in an export.
    for row in rows:
        name = str(row.get("property_name", "")).strip().lower().replace("_", "-")
        value = str(row.get("property_value", ""))
        if "skip-backside" in name:
            parsed = normalize_bool(value)
            if parsed is not None:
                evidence.append((value, parsed, evidence_pointer(row)))

    # Setvar form: variable=<skip-backside URI>, value=<assigned value>.
    marker_rows = [
        row for row in rows
        if "var://service/mpgw/skip-backside" in str(row.get("property_value", "")).lower()
        or "var://service/mpgw/skip-backside" in str(row.get("property_path", "")).lower()
    ]
    value_rows = [
        row for row in rows
        if str(row.get("property_name", "")).strip().lower().replace("_", "-")
        in {"value", "var-value", "variable-value", "setvar-value"}
    ]

    for marker in marker_rows:
        for row in value_rows:
            raw = str(row.get("property_value", ""))
            parsed = normalize_bool(raw)
            if parsed is None:
                continue
            ptr = evidence_pointer(row)
            ptr["setvar_variable"] = "var://service/mpgw/skip-backside"
            ptr["setvar_variable_evidence"] = evidence_pointer(marker)
            evidence.append((raw, parsed, ptr))

    out: List[Tuple[str, Optional[bool], Dict[str, Any]]] = []
    seen = set()
    for raw, parsed, ptr in evidence:
        key = (raw, parsed, repr(sorted(ptr.items())))
        if key not in seen:
            seen.add(key)
            out.append((raw, parsed, ptr))
    return out

def extract_semantic_facts(file_row: Dict[str, Any], artifact_root: Optional[Path]) -> List[Dict[str, Any]]:
    if normalize_resolution_status(file_row) != "resolved":
        return []

    path = next((p for p in artifact_candidate_paths(file_row, artifact_root) if p.exists() and p.is_file()), None)
    if not path:
        return []

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    classification = first_nonempty(file_row, "target_classification", "classification").lower()
    suffix = path.suffix.lower()
    facts: List[Dict[str, Any]] = []

    is_js = "gateway" in classification or "javascript" in classification or suffix == ".js"
    is_xslt = "xslt" in classification or suffix in {".xsl", ".xslt"}

    if is_js and re.search(r"\burlopen\b|require\s*\(\s*[\"']urlopen[\"']", text, flags=re.IGNORECASE):
        urls = extract_urls(text)
        destination = extract_runtime_destination_components(text, urls)
        facts.append({
            "fact_type": "outbound_http_request",
            "mechanism": "gatewayscript",
            "method": extract_method_near(text, "urlopen"),
            "targets": urls,
            "destination_type": destination["destination_type"],
            "base_targets": destination["base_targets"],
            "dynamic_components": destination["dynamic_components"],
            "certainty": "confirmed",
            "artifact_path": str(path),
            "source_object_id": first_nonempty(file_row, "source_object_id"),
        })

    if is_xslt and re.search(r"(?:dp:)?url-open|urlopen", text, flags=re.IGNORECASE):
        urls = extract_urls(text)
        facts.append({
            "fact_type": "outbound_http_request",
            "mechanism": "xslt",
            "method": "",
            "targets": urls,
            "destination_type": "static" if urls else "dynamic_or_runtime_computed",
            "certainty": "confirmed",
            "artifact_path": str(path),
            "source_object_id": first_nonempty(file_row, "source_object_id"),
        })

    if is_xslt:
        facts.extend(extract_database_semantic_facts(text, path, file_row))

    return facts


def route_control_for_sources(
    source_ids: List[str],
    props_by_object: Dict[str, List[Dict[str, str]]],
    endpoints: List[Dict[str, str]],
    semantic_facts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    skip_values: List[Tuple[str, Optional[bool], Dict[str, str]]] = []
    dynamic_evidence: List[Dict[str, str]] = []
    route_action_evidence: List[Dict[str, str]] = []

    for source_id in source_ids:
        source_props = props_by_object.get(source_id, [])
        skip_values.extend(extract_skip_backside_evidence(source_props))
        for row in source_props:
            name = str(row.get("property_name", "")).strip().lower().replace("_", "-")
            value = str(row.get("property_value", ""))
            value_norm = value.strip().lower().replace("_", "-")
            if (
                name in {"dynamic-backend", "dynamic-route", "route-url", "route"}
                or "dynamic-backend" in name
                or (name == "type" and value_norm == "dynamic-backend")
            ):
                dynamic_evidence.append({
                    "source_object_id": source_id,
                    "property_name": row.get("property_name", ""),
                    "property_value": value,
                    "evidence": evidence_pointer(row),
                })

    for e in endpoints:
        role = str(e.get("route_role", ""))
        if role == "dynamic_route_expression":
            dynamic_evidence.append({
                "source_object_id": e.get("source_object_id", ""),
                "route_role": role,
                "normalized_endpoint": e.get("normalized_endpoint", ""),
            })
        if role == "processing_action_route_candidate":
            route_action_evidence.append({
                "source_object_id": e.get("source_object_id", ""),
                "route_role": role,
                "normalized_endpoint": e.get("normalized_endpoint", ""),
            })

    skip_true = any(v is True for _, v, _ in skip_values)
    skip_false = bool(skip_values) and all(v is False for _, v, _ in skip_values if v is not None)
    skip_state: Any = True if skip_true else (False if skip_false else None)

    return {
        "skip_backside": {
            "value": skip_state,
            "certainty": "confirmed" if skip_values and skip_state is not None else "not_evidenced",
            "evidence": [
                {"raw_value": raw, **ptr}
                for raw, _, ptr in skip_values
            ],
        },
        "dynamic_route": {
            "value": bool(dynamic_evidence),
            "certainty": "confirmed" if dynamic_evidence else "not_evidenced",
            "evidence": dynamic_evidence,
        },
        "route_action": {
            "present": bool(route_action_evidence),
            "certainty": "confirmed" if route_action_evidence else "not_evidenced",
            "evidence": route_action_evidence,
        },
        "script_mediated": {
            "present": any(f.get("mechanism") == "gatewayscript" for f in semantic_facts),
            "certainty": "confirmed" if any(f.get("mechanism") == "gatewayscript" for f in semantic_facts) else "not_evidenced",
        },
        "transformation_mediated": {
            "present": any(f.get("mechanism") == "xslt" for f in semantic_facts),
            "certainty": "confirmed" if any(f.get("mechanism") == "xslt" for f in semantic_facts) else "not_evidenced",
        },
    }


def configured_backend_from_endpoints(endpoints: List[Dict[str, str]]) -> Dict[str, Any]:
    records = [
        {
            "endpoint_id": e.get("endpoint_id", ""),
            "route_role": e.get("route_role", ""),
            "normalized_endpoint": e.get("normalized_endpoint", ""),
            "source_object_id": e.get("source_object_id", ""),
        }
        for e in endpoints
        if e.get("route_role") in {"configured_default_backend", "web_service_proxy_remote_endpoint"}
    ]
    return {
        "targets": dedupe_dicts(records),
        "certainty": "confirmed" if records else "not_evidenced",
    }


def derive_backend_mode(configured_backend: Dict[str, Any], route_control: Dict[str, Any]) -> Dict[str, Any]:
    if route_control["dynamic_route"]["value"]:
        return {"value": "dynamic", "certainty": "confirmed"}
    if configured_backend.get("targets"):
        return {"value": "static", "certainty": "confirmed"}
    return {"value": "not_evidenced", "certainty": "not_evidenced"}


def derive_actual_egress(
    endpoints: List[Dict[str, str]],
    file_records: List[Dict[str, Any]],
    route_control: Dict[str, Any],
    semantic_facts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    database_facts = [f for f in semantic_facts if f.get("fact_type") == "outbound_database_request"]
    if database_facts:
        return {
            "status": "confirmed",
            "mechanism": "database",
            "targets": [
                {
                    "target": fact.get("datasource", ""),
                    "logical_datasource": fact.get("datasource", ""),
                    "target_type": "logical_datasource",
                }
                for fact in database_facts
            ],
            "reason": "resolved_artifact_contains_explicit_database_outbound_behavior",
            "certainty": "confirmed",
        }

    semantic_targets: List[Dict[str, Any]] = []
    for fact in semantic_facts:
        if fact.get("fact_type") != "outbound_http_request":
            continue
        targets = fact.get("targets") or []
        if targets:
            for target in targets:
                semantic_targets.append({
                    "target": target,
                    "mechanism": fact.get("mechanism", ""),
                    "method": fact.get("method", ""),
                    "destination_type": fact.get("destination_type", "static"),
                    "dynamic_components": fact.get("dynamic_components", []),
                })
        else:
            semantic_targets.append({
                "target": "",
                "mechanism": fact.get("mechanism", ""),
                "method": fact.get("method", ""),
                "destination_type": fact.get("destination_type", "dynamic_or_runtime_computed"),
            })

    if semantic_targets:
        return {
            "status": "confirmed",
            "mechanism": unique_keep_order(t.get("mechanism", "") for t in semantic_targets),
            "targets": semantic_targets,
            "reason": "resolved_artifact_contains_explicit_outbound_behavior",
            "certainty": "confirmed",
        }

    # Unresolved file evidence is preserved in file_resolution.unresolved, but it
    # must not by itself force actual egress to unresolved. Egress state is derived
    # only from explicit routing / backend / semantic evidence below.
    skip_backside = route_control.get("skip_backside", {}).get("value") is True
    dynamic_route = route_control.get("dynamic_route", {}).get("value") is True

    route_targets = [
        {
            "target": e.get("normalized_endpoint", ""),
            "route_role": e.get("route_role", ""),
            "source_object_id": e.get("source_object_id", ""),
        }
        for e in endpoints
        if e.get("route_role") == "processing_action_route_candidate"
    ]
    if route_targets:
        return {
            "status": "candidate",
            "mechanism": ["route_action"],
            "targets": dedupe_dicts(route_targets),
            "reason": "processing_action_route_candidate_present",
            "certainty": "candidate",
        }

    if skip_backside:
        return {
            "status": "not_evidenced",
            "mechanism": [],
            "targets": [],
            "reason": "normal_backside_bypassed_and_no_alternative_egress_evidenced",
            "certainty": "not_evidenced",
        }

    configured = [
        {
            "target": e.get("normalized_endpoint", ""),
            "route_role": e.get("route_role", ""),
            "source_object_id": e.get("source_object_id", ""),
        }
        for e in endpoints
        if e.get("route_role") in {"configured_default_backend", "web_service_proxy_remote_endpoint"}
    ]
    if configured:
        return {
            "status": "candidate",
            "mechanism": ["configured_backside"],
            "targets": dedupe_dicts(configured),
            "reason": "configured_backend_present_without_operation_execution_proof",
            "certainty": "candidate",
        }

    return {
        "status": "not_evidenced",
        "mechanism": [],
        "targets": [],
        "reason": "no_outbound_behavior_evidenced",
        "certainty": "not_evidenced",
    }


def finding_matches_operation(
    finding: Dict[str, Any],
    operation_id: str,
    service_id: str,
    source_ids: List[str],
    domain: str,
) -> bool:
    if first_nonempty(finding, "operation_id") == operation_id:
        return True
    if first_nonempty(finding, "service_id", "parent_service_id", "root_object_id") == service_id:
        return True
    object_id = first_nonempty(finding, "object_id", "source_object_id", "owner_object_id")
    if object_id and object_id in source_ids:
        return True
    # Do not attach broad domain findings unless they explicitly identify this graph.
    return False


def compact_finding(f: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "finding_id": first_nonempty(f, "finding_id", "id"),
        "classification": first_nonempty(f, "classification", "finding_type", "severity"),
        "scope": first_nonempty(f, "scope"),
        "summary": first_nonempty(f, "summary", "message", "description", "finding"),
        "certainty": first_nonempty(f, "certainty", "evidence_status") or "confirmed",
        "evidence": evidence_pointer(f),
    }


def domain_consistency(expected_domain: str, rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    observed = sorted({str(r.get("domain", "")) for r in rows if r.get("domain")})
    if expected_domain and expected_domain not in observed and observed:
        return {"status": "inconsistent", "expected": expected_domain, "observed": observed}
    if len(set(observed)) > 1:
        return {"status": "inconsistent", "expected": expected_domain, "observed": observed}
    return {"status": "consistent", "expected": expected_domain, "observed": observed}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", required=True)
    ap.add_argument("--properties", required=True)
    ap.add_argument("--relationships", required=True)
    ap.add_argument("--endpoints", required=False)
    ap.add_argument("--file-relationships", required=False)
    ap.add_argument("--unresolved-file-references", required=False, help="Optional unresolved_file_references.csv from the file resolver")
    ap.add_argument("--findings", required=False, help="Optional CSV/JSON/JSONL findings source")
    ap.add_argument("--artifact-root", required=False, help="Optional root used to inspect resolved local XSLT/GatewayScript artifacts")
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary-output", required=True)
    args = ap.parse_args()

    objects = load_csv(Path(args.objects))
    properties = load_csv(Path(args.properties))
    relationships = load_csv(Path(args.relationships))
    endpoints = load_csv(Path(args.endpoints)) if args.endpoints else []
    file_rels = load_csv(Path(args.file_relationships)) if args.file_relationships else []
    unresolved_file_refs = load_csv(Path(args.unresolved_file_references)) if args.unresolved_file_references else []
    findings = load_records(Path(args.findings)) if args.findings else []
    artifact_root = Path(args.artifact_root) if args.artifact_root else None

    object_by_id = {r["object_id"]: r for r in objects}
    props_by_object = properties_by_object(properties)

    outgoing = defaultdict(list)
    for r in relationships:
        outgoing[r["source_object_id"]].append(r)

    endpoints_by_source = defaultdict(list)
    for e in endpoints:
        endpoints_by_source[e.get("source_object_id", "")].append(e)

    files_by_source = defaultdict(list)
    for f in file_rels:
        files_by_source[f.get("source_object_id", "")].append(f)

    unresolved_files_by_source = defaultdict(list)
    for f in unresolved_file_refs:
        unresolved_files_by_source[f.get("source_object_id", "")].append(f)

    roots = [
        o for o in objects
        if o.get("canonical_type") in SERVICE_ROOT_TYPES
    ]

    operation_records: List[Dict[str, Any]] = []

    for root in roots:
        root_id = root["object_id"]

        policy_edges = [
            r for r in outgoing.get(root_id, [])
            if r.get("relationship_type") == "uses_processing_policy"
            and r.get("target_type") in PROCESSING_POLICY_TYPES
        ]

        for policy_edge in policy_edges:
            policy_id = policy_edge["target_object_id"]
            policy_rels = outgoing.get(policy_id, [])

            # Preserve the validated traversal rule: pair matching and processing
            # relationships by the same policy evidence line.
            by_evidence = defaultdict(list)
            for rel in policy_rels:
                if rel.get("property_name") == "match":
                    key = (
                        rel.get("evidence_file", ""),
                        rel.get("source_line", ""),
                        rel.get("property_path", ""),
                    )
                    by_evidence[key].append(rel)

            for key, rels in sorted(by_evidence.items(), key=lambda kv: (kv[0][0], int(kv[0][1] or 0))):
                matching = [
                    r for r in rels
                    if r.get("relationship_type") == "uses_matching_rule"
                ]
                processing = [
                    r for r in rels
                    if r.get("relationship_type") == "contains_processing_rule"
                    and r.get("target_type") in PROCESSING_RULE_TYPES
                ]

                proc_edges = processing or [None]

                for proc_edge in proc_edges:
                    proc_id = proc_edge["target_object_id"] if proc_edge else ""

                    action_edges = [
                        r for r in outgoing.get(proc_id, [])
                        if r.get("relationship_type") == "contains_processing_action"
                        and r.get("target_type") == "processing_action"
                    ] if proc_id else []

                    action_ids = unique_keep_order(r["target_object_id"] for r in action_edges)
                    action_names = unique_keep_order(r["target_object_name"] for r in action_edges)

                    dependency_sources = [root_id, policy_id, proc_id] + action_ids
                    dependency_sources = [x for x in dependency_sources if x]

                    op_endpoints: List[Dict[str, str]] = []
                    for source_id in dependency_sources:
                        op_endpoints.extend(endpoints_by_source.get(source_id, []))

                    op_resolved_files: List[Dict[str, str]] = []
                    op_unresolved_files: List[Dict[str, str]] = []
                    for source_id in dependency_sources:
                        op_resolved_files.extend(files_by_source.get(source_id, []))
                        op_unresolved_files.extend(unresolved_files_by_source.get(source_id, []))
                    # Preserve both evidence paths. Resolved relationships and unresolved
                    # references are separate resolver outputs but belong to the same Journey.
                    op_files: List[Dict[str, str]] = [*op_resolved_files, *op_unresolved_files]

                    domain = (
                        policy_edge.get("domain")
                        or next((r.get("domain") for r in rels if r.get("domain")), "")
                    )
                    environment = root.get("environment", "")

                    evidence_line = key[1]
                    operation_id = (
                        f"op:{environment}:{domain}:{stable_id([root_id, policy_id, key[0], evidence_line, proc_id])}"
                    )

                    match_names = unique_keep_order(r.get("target_object_name", "") for r in matching)
                    match_ids = unique_keep_order(r.get("target_object_id", "") for r in matching)

                    action_types = [
                        object_by_id.get(aid, {}).get("canonical_type", "processing_action")
                        for aid in action_ids
                    ]

                    # Enrichment uses the already-discovered graph. It does not alter traversal.
                    operation_relationships: List[Dict[str, Any]] = []
                    for source_id in dependency_sources:
                        operation_relationships.extend(outgoing.get(source_id, []))
                    dependency_records = [relationship_dependency_record(r) for r in operation_relationships]
                    resolved_dependencies = dedupe_dicts([
                        d for d in dependency_records if d["resolution_status"] == "resolved"
                    ])
                    unresolved_dependencies = dedupe_dicts([
                        d for d in dependency_records if d["resolution_status"] != "resolved"
                    ])

                    file_records = dedupe_dicts(file_dependency_record(f) for f in op_files)
                    resolved_files = [f for f in file_records if f["resolution_status"] == "resolved"]
                    unresolved_files = [f for f in file_records if f["resolution_status"] != "resolved"]

                    semantic_facts: List[Dict[str, Any]] = []
                    for f in op_resolved_files:
                        semantic_facts.extend(extract_semantic_facts(f, artifact_root))
                    semantic_facts = dedupe_dicts(semantic_facts)

                    route_control = route_control_for_sources(
                        dependency_sources,
                        props_by_object,
                        op_endpoints,
                        semantic_facts,
                    )
                    configured_backend = configured_backend_from_endpoints(op_endpoints)
                    backend_mode = derive_backend_mode(configured_backend, route_control)
                    actual_egress = derive_actual_egress(
                        op_endpoints,
                        file_records,
                        route_control,
                        semantic_facts,
                    )

                    relevant_findings = [
                        compact_finding(f)
                        for f in findings
                        if finding_matches_operation(f, operation_id, root_id, dependency_sources, domain)
                    ]
                    relevant_findings = dedupe_dicts(relevant_findings)

                    provenance_rows: List[Dict[str, Any]] = [policy_edge, *rels, *action_edges, *op_endpoints, *op_files]
                    source_pointers = dedupe_dicts(
                        ptr for ptr in (evidence_pointer(r) for r in provenance_rows) if ptr
                    )
                    provenance = {
                        "environment": environment,
                        "domain": domain,
                        "source_files": unique_keep_order(p.get("evidence_file", "") for p in source_pointers),
                        "source_pointers": source_pointers,
                        "domain_consistency": domain_consistency(domain, provenance_rows),
                        "builder": VERSION,
                        "generated_from": {
                            "objects": args.objects,
                            "properties": args.properties,
                            "relationships": args.relationships,
                            "endpoints": args.endpoints or "",
                            "file_relationships": args.file_relationships or "",
                            "unresolved_file_references": args.unresolved_file_references or "",
                            "findings": args.findings or "",
                        },
                    }

                    endpoint_dependencies_legacy = [
                        {
                            "endpoint_id": e.get("endpoint_id", ""),
                            "route_role": e.get("route_role", ""),
                            "normalized_endpoint": e.get("normalized_endpoint", ""),
                            "source_object_id": e.get("source_object_id", ""),
                        }
                        for e in op_endpoints
                    ]
                    file_dependencies_legacy = [
                        {
                            "target_file_id": f.get("target_file_id", ""),
                            "target_relative_path": f.get("target_relative_path", ""),
                            "classification": f.get("target_classification", ""),
                            "relationship_type": f.get("relationship_type", ""),
                            "source_object_id": f.get("source_object_id", ""),
                        }
                        for f in op_resolved_files
                    ]

                    operation_records.append({
                        # Existing fields retained for backward compatibility.
                        "operation_id": operation_id,
                        "environment": environment,
                        "domain": domain,
                        "parent_service_id": root_id,
                        "parent_service_type": root.get("canonical_type", ""),
                        "parent_service_name": root.get("object_name", ""),
                        "processing_policy_id": policy_id,
                        "processing_policy_type": policy_edge.get("target_type", ""),
                        "processing_policy_name": policy_edge.get("target_object_name", ""),
                        "match_evidence_file": key[0],
                        "match_source_line": evidence_line,
                        "matching_rule_ids": match_ids,
                        "matching_rule_names": match_names,
                        "processing_rule_id": proc_id,
                        "processing_rule_type": proc_edge.get("target_type", "") if proc_edge else "",
                        "processing_rule_name": proc_edge.get("target_object_name", "") if proc_edge else "",
                        "processing_rule_found": bool(proc_edge),
                        "action_ids": action_ids,
                        "action_names": action_names,
                        "action_types": action_types,
                        "action_count": len(action_ids),
                        "endpoint_dependencies": endpoint_dependencies_legacy,
                        "endpoint_count": len({e.get("endpoint_id", "") for e in op_endpoints if e.get("endpoint_id")}),
                        "file_dependencies": file_dependencies_legacy,
                        "file_count": len({
                            f.get("target_file_id", "") or f.get("target_relative_path", "") or raw_file_reference(f)
                            for f in op_files
                            if f.get("target_file_id") or f.get("target_relative_path") or raw_file_reference(f)
                        }),
                        # Additive architectural evidence enrichment.
                        "dependencies": {
                            "resolved": resolved_dependencies,
                            "unresolved": unresolved_dependencies,
                        },
                        "file_resolution": {
                            "resolved": resolved_files,
                            "unresolved": unresolved_files,
                        },
                        "routing": {
                            "backend_mode": backend_mode,
                            "configured_backend": configured_backend,
                            "route_control": route_control,
                            "actual_egress": actual_egress,
                            "remote_system_identity": {
                                "value": "",
                                "certainty": "not_evidenced",
                            },
                            "remote_topology": {
                                "value": "",
                                "certainty": "not_evidenced",
                            },
                        },
                        "semantic_facts": semantic_facts,
                        "known_findings": relevant_findings,
                        "evidence": {
                            "certainty": actual_egress.get("certainty", "not_evidenced"),
                            "source_pointers": source_pointers,
                        },
                        "provenance": provenance,
                        "builder_version": VERSION,
                    })

    summary = []
    for op in operation_records:
        summary.append({
            "operation_id": op["operation_id"],
            "environment": op["environment"],
            "domain": op["domain"],
            "parent_service_name": op["parent_service_name"],
            "parent_service_type": op["parent_service_type"],
            "processing_policy_name": op["processing_policy_name"],
            "matching_rule_names": "|".join(op["matching_rule_names"]),
            "processing_rule_name": op["processing_rule_name"],
            "processing_rule_found": str(op["processing_rule_found"]).lower(),
            "action_count": op["action_count"],
            "endpoint_count": op["endpoint_count"],
            "file_count": op["file_count"],
            "resolved_dependency_count": len(op["dependencies"]["resolved"]),
            "unresolved_dependency_count": len(op["dependencies"]["unresolved"]),
            "resolved_file_count": len(op["file_resolution"]["resolved"]),
            "unresolved_file_count": len(op["file_resolution"]["unresolved"]),
            "backend_mode": op["routing"]["backend_mode"]["value"],
            "actual_egress_status": op["routing"]["actual_egress"]["status"],
            "semantic_fact_count": len(op["semantic_facts"]),
            "finding_count": len(op["known_findings"]),
            "provenance_status": op["provenance"]["domain_consistency"]["status"],
            "match_source_line": op["match_source_line"],
            "builder_version": VERSION,
        })

    write_jsonl(Path(args.output), operation_records)
    fields = [
        "operation_id",
        "environment",
        "domain",
        "parent_service_name",
        "parent_service_type",
        "processing_policy_name",
        "matching_rule_names",
        "processing_rule_name",
        "processing_rule_found",
        "action_count",
        "endpoint_count",
        "file_count",
        "resolved_dependency_count",
        "unresolved_dependency_count",
        "resolved_file_count",
        "unresolved_file_count",
        "backend_mode",
        "actual_egress_status",
        "semantic_fact_count",
        "finding_count",
        "provenance_status",
        "match_source_line",
        "builder_version",
    ]
    write_csv(Path(args.summary_output), summary, fields)

    print("=" * 80)
    print("DATAPOWER OPERATION JOURNEY BUILDER")
    print("=" * 80)
    print(f"Builder version:          {VERSION}")
    print(f"Service roots scanned:    {len(roots)}")
    print(f"Operations built:         {len(operation_records)}")
    print(f"Services with operations: {len(set(o['parent_service_id'] for o in operation_records))}")
    print(f"Output:                   {args.output}")
    print(f"Summary:                  {args.summary_output}")
    print("-" * 80)

    by_service = defaultdict(int)
    for op in operation_records:
        by_service[op["parent_service_name"]] += 1
    for name, count in sorted(by_service.items(), key=lambda x: (-x[1], x[0])):
        print(f"{name:55} {count:6}")

    incomplete = sum(1 for o in operation_records if not o["processing_rule_found"])
    unresolved_egress = sum(1 for o in operation_records if o["routing"]["actual_egress"]["status"] == "unresolved")
    confirmed_egress = sum(1 for o in operation_records if o["routing"]["actual_egress"]["status"] == "confirmed")
    provenance_issues = sum(1 for o in operation_records if o["provenance"]["domain_consistency"]["status"] != "consistent")
    print("-" * 80)
    print(f"Operations missing processing rule: {incomplete}")
    print(f"Operations confirmed egress:        {confirmed_egress}")
    print(f"Operations unresolved egress:       {unresolved_egress}")
    print(f"Provenance inconsistencies:          {provenance_issues}")
    print("OPERATION JOURNEY BUILDER: PASS — VALIDATE OUTPUT SEMANTICS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
