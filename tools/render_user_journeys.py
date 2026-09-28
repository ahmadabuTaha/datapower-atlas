#!/usr/bin/env python3
"""Render compact, journey-first architecture reports from Atlas evidence bundles.

This is an additive reporting layer.  It does not traverse raw configuration or
alter the validated service/operation builders.  Materially equivalent
operations are grouped by evidence-backed behavior; full dependency and
provenance records remain in the source JSONL bundles named by each report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


VERSION = "1.1-catalog-linked-evidence-renderer"
CERTAINTIES = {"confirmed", "candidate", "unresolved", "not_evidenced"}
MATERIAL_ACTION_PROPERTIES = {
    "type", "transform", "stylesheet", "url", "route-url", "dest-url", "variable",
    "value", "condition", "error-mode",
}
STRUCTURAL_RELATIONSHIPS = {
    "uses_processing_policy", "uses_matching_rule", "contains_processing_rule",
    "contains_processing_action", "uses_front_side_handler",
}
SECURITY_RELATIONSHIPS = {
    "uses_tls_client_profile", "uses_tls_server_profile", "uses_aaa_policy",
    "uses_crypto_identification_credentials", "uses_crypto_validation_credentials",
    "uses_crypto_certificate", "uses_crypto_key",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def quote(value: Any) -> str:
    text = str(value if value not in (None, "") else "not_evidenced")
    return f"`{text.replace('`', '\N{MODIFIER LETTER GRAVE ACCENT}')}`"


def unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def service_slug(service: dict[str, Any]) -> str:
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", service["root"]["name"]).strip("-") or "service"
    digest = hashlib.sha1(service["root"]["object_id"].encode("utf-8")).hexdigest()[:8]
    return f"{name}-{digest}.md"


def properties_index(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        result[row.get("object_id", "")].append(row)
    return result


def property_values(props: dict[str, list[dict[str, str]]], oid: str, name: str) -> list[str]:
    return [r.get("property_value", "") for r in props.get(oid, []) if r.get("property_name") == name]


def first_property(props: dict[str, list[dict[str, str]]], oid: str, *names: str) -> str:
    for name in names:
        values = property_values(props, oid, name)
        if values:
            return values[0]
    return ""


def object_pointer(props: dict[str, list[dict[str, str]]], oid: str) -> str:
    rows = props.get(oid, [])
    if not rows:
        return "not_evidenced"
    row = rows[0]
    source = row.get("source_file", "")
    line = row.get("line_scope_start", "") or row.get("source_line", "")
    return f"{source}:{line}" if line else source or "not_evidenced"


def normalized_certainty(value: Any) -> str:
    value = str(value or "not_evidenced")
    return value if value in CERTAINTIES else "not_evidenced"


def finding_record(row: dict[str, str]) -> dict[str, str]:
    return {
        "finding_type": row.get("finding_type", ""),
        "severity": row.get("severity", ""),
        "reason": row.get("finding_reason", ""),
        "analyzer_version": row.get("analyzer_version", ""),
    }


def action_records(operation: dict[str, Any], props: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    records = []
    file_rows = operation.get("file_resolution", {}).get("resolved", []) + operation.get("file_resolution", {}).get("unresolved", [])
    for position, oid in enumerate(operation.get("action_ids", []), start=1):
        action_props = props.get(oid, [])
        details = [
            (r.get("property_name", ""), r.get("property_value", ""))
            for r in action_props if r.get("property_name") in MATERIAL_ACTION_PROPERTIES
        ]
        records.append({
            "position": position,
            "action_id": oid,
            "name": (operation.get("action_names", []) + [""] * position)[position - 1],
            "type": first_property(props, oid, "type") or "unresolved",
            "details": details,
            "files": [f for f in file_rows if f.get("source_object_id") == oid],
            "evidence": object_pointer(props, oid),
        })
    return records


def match_shape(operation: dict[str, Any], props: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    rows: list[tuple[str, str]] = []
    for oid in operation.get("matching_rule_ids", []):
        for row in props.get(oid, []):
            if row.get("property_name") in {"urlmatch", "method", "http-method", "expression", "match-type"}:
                rows.append((row.get("property_name", ""), row.get("property_value", "")))
    method = next((v for k, v in rows if k in {"method", "http-method"}), "")
    paths = unique(v.strip('"') for k, v in rows if k == "urlmatch")
    return {"method": method, "paths": paths, "evidence": rows}


def material_dependencies(operation: dict[str, Any]) -> list[dict[str, Any]]:
    dependencies = operation.get("dependencies", {})
    rows = dependencies.get("resolved", []) + dependencies.get("unresolved", [])
    return [d for d in rows if d.get("relationship_type") not in STRUCTURAL_RELATIONSHIPS]


def operation_signature(operation: dict[str, Any], props: dict[str, list[dict[str, str]]]) -> str:
    actions = action_records(operation, props)
    action_shape = [{
        "type": action["type"],
        "details": action["details"],
        "files": [{
            "raw_reference": row.get("raw_reference", ""),
            "relationship_type": row.get("relationship_type", ""),
            "resolution_status": row.get("resolution_status", ""),
            "target_relative_path": row.get("target_relative_path", ""),
            "classification": row.get("classification", ""),
            "certainty": row.get("certainty", ""),
        } for row in action["files"]],
    } for action in actions]
    rule_type = first_property(props, operation.get("processing_rule_id", ""), "type")
    deps = material_dependencies(operation)
    security = [{
        "relationship_type": row.get("relationship_type", ""),
        "raw_reference": row.get("raw_reference", ""),
        "target_type": row.get("target_type", ""),
        "target_object_name": row.get("target_object_name", ""),
        "resolution_status": row.get("resolution_status", ""),
        "certainty": row.get("certainty", ""),
    } for row in deps if row.get("relationship_type") in SECURITY_RELATIONSHIPS]
    routing = operation.get("routing", {})
    control = routing.get("route_control", {})
    routing_shape = {
        "backend_mode": routing.get("backend_mode", {}),
        "configured_backend": routing.get("configured_backend", {}),
        "route_control": {
            key: {field: value for field, value in state.items() if field != "evidence"}
            for key, state in control.items()
        },
        "actual_egress": routing.get("actual_egress", {}),
    }
    payload = {
        "direction": rule_type,
        "actions": action_shape,
        "file_resolution": {
            state: [{
                "raw_reference": row.get("raw_reference", ""),
                "relationship_type": row.get("relationship_type", ""),
                "resolution_status": row.get("resolution_status", ""),
                "target_relative_path": row.get("target_relative_path", ""),
                "classification": row.get("classification", ""),
                "certainty": row.get("certainty", ""),
            } for row in operation.get("file_resolution", {}).get(state, [])]
            for state in ("resolved", "unresolved")
        },
        "security": security,
        "routing": routing_shape,
        "semantic_facts": operation.get("semantic_facts", []),
    }
    return compact_json(payload)


def operation_groups(operations: list[dict[str, Any]], props: dict[str, list[dict[str, str]]]) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for operation in operations:
        groups.setdefault(operation_signature(operation, props), []).append(operation)
    return list(groups.values())


def catalog_operation_groups(
    operations: list[dict[str, Any]], pattern_by_operation: dict[str, str],
) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for operation in operations:
        operation_id = operation.get("operation_id", "")
        if operation_id not in pattern_by_operation:
            raise ValueError(f"operation missing from authoritative catalog: {operation_id}")
        groups.setdefault(pattern_by_operation[operation_id], []).append(operation)
    return list(groups.values())


def ingress_records(service: dict[str, Any], props: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    if service["root"]["type"] == "tcp_proxy":
        return service.get("tcp_proxy_direct", {}).get("ingress", [])
    result = []
    for edge in service.get("ingress", {}).get("relationships", []):
        oid = edge.get("target_object_id", "")
        target_type = edge.get("target_type", "")
        protocol = "https" if "https" in target_type else "http" if "http" in target_type else "mq" if "mq" in target_type else "unresolved"
        result.append({
            "listener": edge.get("target_object_name", ""),
            "interface": first_property(props, oid, "local-address"),
            "port": first_property(props, oid, "port", "local-port"),
            "protocol": protocol,
            "tls_evidence": "handler_type" if protocol == "https" else "not_evidenced",
            "certainty": "confirmed",
            "evidence": f"{edge.get('evidence_file', '')}:{edge.get('source_line', '')}",
        })
    return result


def semantic_summary(operation: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {k: [] for k in (
        "validation", "transformation", "security", "authentication", "authorization",
        "routing", "enrichment", "logging", "error_handling", "protocol_mediation",
        "script_based_behavior",
    )}
    for action in actions:
        action_type = action["type"].lower()
        if action_type in {"validate", "schema-validate"}: result["validation"].append(action_type)
        if action_type in {"xform", "transform", "xformpi"}: result["transformation"].append(action_type)
        if action_type in {"aaa", "authenticate", "authorize"}: result["security"].append(action_type)
        if action_type in {"authenticate"}: result["authentication"].append(action_type)
        if action_type in {"authorize"}: result["authorization"].append(action_type)
        if action_type in {"route", "route-set", "set-route"}: result["routing"].append(action_type)
        if action_type in {"fetch", "sql", "slm"}: result["enrichment"].append(action_type)
        if action_type in {"log", "event-sink"}: result["logging"].append(action_type)
        if action_type in {"on-error", "error"}: result["error_handling"].append(action_type)
        if action_type in {"convert-http", "convert-query-params", "results"}: result["protocol_mediation"].append(action_type)
        if action_type in {"gatewayscript"}: result["script_based_behavior"].append(action_type)
    for fact in operation.get("semantic_facts", []):
        fact_type = fact.get("fact_type", "")
        mechanism = fact.get("mechanism", "")
        label = f"{fact_type} via {mechanism}".strip()
        if fact_type.startswith("outbound_"): result["routing"].append(label)
        if mechanism == "gatewayscript": result["script_based_behavior"].append(label)
        if mechanism == "xslt": result["transformation"].append(label)
    return {key: unique(values) for key, values in result.items()}


def render_dependency_lines(file_resolution: dict[str, Any]) -> list[str]:
    lines = []
    for state in ("resolved", "unresolved"):
        for row in file_resolution.get(state, []):
            target = row.get("target_relative_path") or row.get("target_file_id") or "not_evidenced"
            evidence = row.get("evidence", {})
            pointer = f"{evidence.get('evidence_file', '')}:{evidence.get('source_line', '')}".strip(":")
            lines.append(
                f"- {quote(row.get('raw_reference'))} — {quote(row.get('relationship_type'))}; "
                f"status {quote(row.get('resolution_status'))}; artifact {quote(target)}; evidence {quote(pointer)}."
            )
    return lines or ["- No explicit file dependency record is materialized for this scope."]


def render_service(
    service: dict[str, Any], operations: list[dict[str, Any]], groups: list[list[dict[str, Any]]],
    props: dict[str, list[dict[str, str]]], findings: list[dict[str, str]], source_dir: Path,
    catalog_service: dict[str, Any], pattern_by_operation: dict[str, str],
) -> str:
    root = service["root"]
    routing = service.get("routing", {})
    ingress = ingress_records(service, props)
    policies = unique(o.get("processing_policy_name", "") for o in operations)
    egress = routing.get("actual_egress", {})
    configured = routing.get("configured_backend", {})
    lines = [
        f"# {service.get('domain', '')} / {root.get('name', '')}", "",
        "## Identity", "",
        f"- Environment: {quote(service.get('environment'))}.",
        f"- Domain: {quote(service.get('domain'))}.",
        f"- Service: {quote(root.get('name'))} ({quote(root.get('type'))}).",
        f"- Service ID: {quote(root.get('object_id'))}.",
        f"- Authoritative catalog record: [service catalog](../../../01-service-catalog/services.md); machine record in [services.json](../../../01-service-catalog/services.json).",
        f"- Catalog operation count: {quote(catalog_service.get('operation_count'))}; distinct operation-pattern count: {quote(catalog_service.get('distinct_operation_pattern_count'))}.",
        f"- Bundle overall certainty (fact-local certainty remains authoritative): {quote(service.get('evidence', {}).get('overall_certainty'))}.", "",
        "## Entry", "",
    ]
    if ingress:
        for row in ingress:
            lines.append(f"- {compact_json(row)}")
    else:
        lines.append("- Entry evidence: `not_evidenced`.")
    lines += ["", "## Processing and operation exposure", "",
        f"- Processing policies: {', '.join(quote(x) for x in policies) or '`not_evidenced`'}.",
        f"- Operation/request-pattern records: {quote(len(operations))}.",
        f"- Material architectural patterns: {quote(len(groups))}.",
    ]
    if operations:
        for number, group in enumerate(groups, start=1):
            sample = group[0]
            matches = [match_shape(operation, props) for operation in group]
            methods = unique(match["method"] for match in matches)
            paths = unique(path for match in matches for path in match["paths"])
            rule_type = first_property(props, sample.get("processing_rule_id", ""), "type") or "not_evidenced"
            actions = action_records(sample, props)
            semantics = semantic_summary(sample, actions)
            evidenced_semantics = [f"{key}={','.join(values)}" for key, values in semantics.items() if values]
            pattern_id = pattern_by_operation[sample.get("operation_id", "")]
            lines.append(
                f"- Pattern {number} ({quote(pattern_id)}): {len(group)} operation(s); matches {quote(', '.join(unique(name for operation in group for name in operation.get('matching_rule_names', []))))}; "
                f"methods {quote(', '.join(methods))}; paths {quote(', '.join(paths))}; direction {quote(rule_type)}; "
                f"rules {quote(', '.join(operation.get('processing_rule_name', '') for operation in group))}; "
                f"ordered action types {quote(', '.join(action['type'] for action in actions))}; semantics {quote('; '.join(evidenced_semantics))}; "
                f"egress {quote(sample.get('routing', {}).get('actual_egress', {}).get('status'))}."
            )
    elif root.get("type") == "tcp_proxy":
        lines.append("- TCP Proxy uses its direct Layer-4 path; MPGW-style operations are not applicable.")
    else:
        lines.append("- No operation record is materialized for this service.")
    lines += ["", "## Dependencies and semantics", "",
        f"- Resolved object dependencies: {quote(len(service.get('dependencies', {}).get('resolved', [])))}.",
        f"- Unresolved object dependencies: {quote(len(service.get('dependencies', {}).get('unresolved', [])))}.",
        f"- Resolved file references: {quote(len(service.get('file_resolution', {}).get('resolved', [])))}.",
        f"- Unresolved file references: {quote(len(service.get('file_resolution', {}).get('unresolved', [])))}.",
    ]
    lines.extend(render_dependency_lines(service.get("file_resolution", {})))
    lines += ["", "## Routing", "",
        f"- Configured backend mode: {quote(routing.get('backend_mode', {}).get('value'))} ({quote(routing.get('backend_mode', {}).get('certainty'))}).",
        f"- Configured backend targets: {quote(compact_json(configured.get('targets', [])))} ({quote(configured.get('certainty'))}).",
        f"- Route control: {quote(compact_json(routing.get('route_control', {})))}.",
        f"- Actual egress status: {quote(egress.get('status'))}.",
        f"- Actual egress mechanism: {quote(compact_json(egress.get('mechanism', [])))}.",
        f"- Actual egress targets: {quote(compact_json(egress.get('targets', [])))}.",
        f"- Actual egress reason: {quote(egress.get('reason'))}.",
        "- Configured backend evidence is kept separate from actual evidenced egress.", "",
        "## Findings", "",
    ]
    relevant = [finding_record(f) for f in findings if f.get("service_id") == root.get("object_id")]
    lines.extend([f"- {compact_json(f)}" for f in relevant] or ["- No journey-quality finding is materialized for this service."])
    if egress.get("status") == "confirmed" and any(f.get("finding_type") == "missing_egress" for f in relevant):
        lines.append(
            "- Scope note: `missing_egress` identifies absent graph/configured-endpoint evidence; "
            "independent resolved-artifact semantics confirm the actual egress shown above."
        )
    provenance = service.get("provenance", {})
    lines += ["", "## Provenance", "",
        f"- Service bundle: {quote(str(source_dir / 'service_journeys.jsonl'))}.",
        f"- Operation bundle: {quote(str(source_dir / 'operation_journeys.jsonl'))}.",
        "- Catalog baseline: `outputs/as-is/01-service-catalog/services.json` and `operations.json`.",
        f"- Builder: {quote(provenance.get('builder'))}; renderer: {quote(VERSION)}.",
        f"- Domain consistency: {quote(provenance.get('domain_consistency', {}).get('status'))}.",
        f"- Raw source files: {', '.join(quote(x) for x in provenance.get('source_files', [])) or '`not_evidenced`'}.",
        "- Full dependency records, evidence pointers, and hashes remain in the named JSONL evidence bundles.", "",
    ]
    return "\n".join(lines)


def render_operation_patterns(
    service: dict[str, Any], groups: list[list[dict[str, Any]]], props: dict[str, list[dict[str, str]]],
    source_dir: Path, pattern_by_operation: dict[str, str],
) -> str:
    root = service["root"]
    lines = [f"# Materially distinct operation journeys — {service.get('domain')} / {root.get('name')}", "",
        f"The operation records group into {len(groups)} evidence-backed architectural paths. Full operation records remain in {quote(str(source_dir / 'operation_journeys.jsonl'))}.",
        "Authoritative operation identities and pattern membership are in the [operation catalog](../../../01-service-catalog/operations.md) and [operations.json](../../../01-service-catalog/operations.json).", ""]
    for number, group in enumerate(groups, start=1):
        sample = group[0]
        matches = [match_shape(operation, props) for operation in group]
        methods = unique(match["method"] for match in matches)
        paths = unique(path for match in matches for path in match["paths"])
        actions = action_records(sample, props)
        routing = sample.get("routing", {})
        egress = routing.get("actual_egress", {})
        direction = first_property(props, sample.get("processing_rule_id", ""), "type") or "not_evidenced"
        pattern_id = pattern_by_operation[sample.get("operation_id", "")]
        lines += [f"## Pattern {number} — {len(group)} operation(s)", "",
            "### Identity and processing", "",
            f"- Pattern ID: {quote(pattern_id)}.",
            f"- Operation IDs: {', '.join(quote(o.get('operation_id')) for o in group)}.",
            f"- Methods: {quote(', '.join(methods))}; path/request patterns: {quote(', '.join(paths))}.",
            f"- Processing policy: {quote(sample.get('processing_policy_name'))}.",
            f"- Matches: {quote(', '.join(unique(name for operation in group for name in operation.get('matching_rule_names', []))))}.",
            f"- Direction: {quote(direction)}.",
            f"- Processing rules represented: {', '.join(quote(o.get('processing_rule_name')) for o in group)}.", "",
            "### Ordered actions", "",
        ]
        if actions:
            for action in actions:
                lines.append(
                    f"{action['position']}. {quote(action['type'])} — {quote(action['name'])}; "
                    f"properties {quote(compact_json(action['details']))}; evidence {quote(action['evidence'])}."
                )
        else:
            lines.append("- No processing action is materialized for this pattern.")
        semantics = semantic_summary(sample, actions)
        lines += ["", "### Semantics", ""]
        for category, values in semantics.items():
            lines.append(f"- {category.replace('_', ' ').title()}: {quote(', '.join(values)) if values else '`not_evidenced`'}.")
        lines += ["", "### Dependencies", ""]
        lines.extend(render_dependency_lines(sample.get("file_resolution", {})))
        lines += ["", "### Routing and certainty", "",
            f"- Configured backend mode: {quote(routing.get('backend_mode', {}).get('value'))} ({quote(routing.get('backend_mode', {}).get('certainty'))}).",
            f"- Configured backend targets: {quote(compact_json(routing.get('configured_backend', {}).get('targets', [])))}.",
            f"- Route control: {quote(compact_json(routing.get('route_control', {})))}.",
            f"- Actual egress: status {quote(egress.get('status'))}; mechanism {quote(compact_json(egress.get('mechanism', [])))}; targets {quote(compact_json(egress.get('targets', [])))}.",
            f"- Evidence certainty: {quote(normalized_certainty(sample.get('evidence', {}).get('certainty')))}.",
            f"- Source pointer count: {quote(len(sample.get('evidence', {}).get('source_pointers', [])))}.", "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-root", default="index")
    parser.add_argument("--output-root", default="outputs/as-is/02-user-journeys")
    parser.add_argument("--service-catalog", default="outputs/as-is/01-service-catalog/services.json")
    parser.add_argument("--operation-catalog", default="outputs/as-is/01-service-catalog/operations.json")
    parser.add_argument("--domains", nargs="+", required=True)
    args = parser.parse_args()

    index_root = Path(args.index_root)
    output_root = Path(args.output_root)
    service_catalog = load_json(Path(args.service_catalog))
    operation_catalog = load_json(Path(args.operation_catalog))
    service_catalog_by_id = {row["service_id"]: row for row in service_catalog.get("services", [])}
    catalog_operations = operation_catalog.get("operations", [])
    pattern_by_operation = {row["operation_id"]: row["operation_pattern_id"] for row in catalog_operations}
    catalog_metrics = service_catalog.get("metrics", {})
    if service_catalog.get("evidence_mode") != "frozen_evidence_consumption_only":
        raise SystemExit("Phase 1 service catalog is not marked frozen-evidence consumption only")
    if operation_catalog.get("metrics") != catalog_metrics:
        raise SystemExit("Phase 1 service and operation catalog metrics disagree")
    service_entries: list[tuple[dict[str, Any], str, int, int]] = []
    operation_entries: list[tuple[dict[str, Any], str, int, int]] = []

    for domain_slug in args.domains:
        source_dir = index_root / domain_slug
        services = load_jsonl(source_dir / "service_journeys.jsonl")
        operations = load_jsonl(source_dir / "operation_journeys.jsonl")
        findings = load_csv(source_dir / "service_journey_findings.csv")
        props = properties_index(load_csv(source_dir / "object_properties.csv"))
        ops_by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for operation in operations:
            ops_by_service[operation.get("parent_service_id", "")].append(operation)

        for service in services:
            root_id = service["root"]["object_id"]
            if root_id not in service_catalog_by_id:
                raise SystemExit(f"service missing from authoritative Phase 1 catalog: {root_id}")
            service_ops = ops_by_service.get(root_id, [])
            groups = catalog_operation_groups(service_ops, pattern_by_operation)
            catalog_service = service_catalog_by_id[root_id]
            if len(service_ops) != catalog_service.get("operation_count"):
                raise SystemExit(f"operation count mismatch for {root_id}")
            if len(groups) != catalog_service.get("distinct_operation_pattern_count"):
                raise SystemExit(f"operation-pattern count mismatch for {root_id}")
            filename = service_slug(service)
            domain = service.get("domain") or domain_slug
            service_path = output_root / "service-journeys" / domain / filename
            service_path.parent.mkdir(parents=True, exist_ok=True)
            service_path.write_text(
                render_service(
                    service, service_ops, groups, props, findings, source_dir,
                    catalog_service, pattern_by_operation,
                ),
                encoding="utf-8",
            )
            service_entries.append((service, str(service_path.relative_to(output_root)), len(service_ops), len(groups)))

            if len(groups) > 1:
                operation_path = output_root / "operation-journeys" / domain / filename
                operation_path.parent.mkdir(parents=True, exist_ok=True)
                operation_path.write_text(
                    render_operation_patterns(service, groups, props, source_dir, pattern_by_operation),
                    encoding="utf-8",
                )
                operation_entries.append((service, str(operation_path.relative_to(output_root)), len(service_ops), len(groups)))

    service_entries.sort(key=lambda x: (x[0].get("domain", ""), x[0]["root"]["type"], x[0]["root"]["name"]))
    operation_entries.sort(key=lambda x: (x[0].get("domain", ""), x[0]["root"]["name"]))
    if len(service_entries) != catalog_metrics.get("service_journey_count"):
        raise SystemExit("rendered service-Journey count disagrees with authoritative catalog")
    if len(operation_entries) != catalog_metrics.get("operation_pattern_journey_count"):
        raise SystemExit("rendered operation-pattern Journey count disagrees with authoritative catalog")
    lines = ["# AS-IS Journey Index", "",
        f"- Renderer: **{VERSION}**",
        "- Evidence mode: **frozen evidence consumption only**",
        f"- `operation_count`: **{catalog_metrics.get('operation_count')}**",
        f"- `distinct_operation_pattern_count`: **{catalog_metrics.get('distinct_operation_pattern_count')}**",
        f"- `service_journey_count`: **{len(service_entries)}**",
        f"- `operation_pattern_journey_count`: **{len(operation_entries)}**",
        "- Operation count is sourced from the authoritative Phase 1 catalog and is never inferred from operation-pattern reports.",
        "- Operation patterns share a document only when processing, dependencies, routing, semantics, security, egress, and error behavior are materially equivalent.",
        "- Catalogs: [services](../01-service-catalog/services.md) · [operations](../01-service-catalog/operations.md)", "",
        "## Service journeys", "", "| Domain | Service | Type | Operations | Patterns | Journey |", "|---|---|---|---:|---:|---|",
    ]
    for service, path, op_count, pattern_count in service_entries:
        root = service["root"]
        lines.append(f"| {service.get('domain')} | `{root['name']}` | {root['type']} | {op_count} | {pattern_count} | [{Path(path).name}]({path}) |")
    lines += ["", "## Materially distinct operation journeys", "", "| Domain | Service | Operations | Patterns | Journey |", "|---|---|---:|---:|---|"]
    for service, path, op_count, pattern_count in operation_entries:
        root = service["root"]
        lines.append(f"| {service.get('domain')} | `{root['name']}` | {op_count} | {pattern_count} | [{Path(path).name}]({path}) |")
    lines.append("")
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "journey-index.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Rendered {len(service_entries)} services and {len(operation_entries)} distinct-operation reports to {output_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
