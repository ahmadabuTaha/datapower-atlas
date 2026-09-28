#!/usr/bin/env python3
"""Render Phase 1 service and operation catalogs from frozen Atlas evidence.

This consumer never invokes parsers, resolvers, pipelines, or Journey builders.
Operation counts come exclusively from operation evidence records. Distinct
behavior-pattern counts are computed independently and never substituted for
operation counts or operation-pattern report counts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import render_user_journeys as journeys


VERSION = "1.0-frozen-evidence-consumer"


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def target_values(configured_backend: dict[str, Any]) -> list[str]:
    values = []
    for target in configured_backend.get("targets", []):
        value = target.get("normalized_endpoint") or target.get("target")
        if value and value not in values:
            values.append(value)
    return values


def operation_pattern_id(service_id: str, signature: str) -> str:
    digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:16]
    return f"operation-pattern:{service_id}:{digest}"


def source_pointer(row: dict[str, Any]) -> dict[str, str]:
    evidence = row.get("evidence", {})
    return {
        key: str(value)
        for key, value in {
            "source": evidence.get("evidence_file", ""),
            "line": evidence.get("source_line", ""),
            "property": evidence.get("property_name", ""),
        }.items()
        if value not in (None, "")
    }


def dependency_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference": row.get("raw_reference", ""),
        "dependency_type": row.get("relationship_type", ""),
        "resolution_status": row.get("resolution_status", ""),
        "certainty": row.get("certainty", ""),
        "source_object_id": row.get("source_object_id", ""),
        "target_object_id": row.get("target_object_id", ""),
        "target_object_name": row.get("target_object_name", ""),
        "target_type": row.get("target_type", ""),
        "evidence_source": source_pointer(row),
    }


def file_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference": row.get("raw_reference", ""),
        "dependency_type": row.get("relationship_type", ""),
        "resolution_status": row.get("resolution_status", ""),
        "resolved_artifact": row.get("target_relative_path", "") or None,
        "artifact_classification": row.get("classification", "") or None,
        "certainty": row.get("certainty", ""),
        "owner_object_id": row.get("source_object_id", ""),
        "evidence_source": source_pointer(row),
    }


def compact_finding(row: dict[str, str]) -> dict[str, str]:
    return {
        "finding_type": row.get("finding_type", ""),
        "severity": row.get("severity", ""),
        "reason": row.get("finding_reason", ""),
        "analyzer_version": row.get("analyzer_version", ""),
    }


def action_record(action: dict[str, Any]) -> dict[str, Any]:
    return {
        "position": action["position"],
        "action_id": action["action_id"],
        "action_name": action["name"],
        "action_type": action["type"],
        "material_properties": [
            {"property": name, "value": value} for name, value in action["details"]
        ],
        "evidence_source": action["evidence"],
    }


def service_catalog_record(
    service: dict[str, Any],
    operations: list[dict[str, Any]],
    props: dict[str, list[dict[str, str]]],
    quality_findings: list[dict[str, str]],
    pattern_ids: dict[str, str],
    output_root: Path,
) -> dict[str, Any]:
    root = service["root"]
    groups = journeys.operation_groups(operations, props)
    routing = service.get("routing", {})
    operation_ids = [operation.get("operation_id", "") for operation in operations]
    signatures = [journeys.operation_signature(group[0], props) for group in groups]
    slug = journeys.service_slug(service)
    domain = service.get("domain", "")
    service_journey_path = output_root.parent / "02-user-journeys" / "service-journeys" / domain / slug
    operation_journey_path = output_root.parent / "02-user-journeys" / "operation-journeys" / domain / slug
    dependencies = service.get("dependencies", {})
    resolved_dependencies = [dependency_record(row) for row in dependencies.get("resolved", [])]
    unresolved_dependencies = [dependency_record(row) for row in dependencies.get("unresolved", [])]
    file_resolution = service.get("file_resolution", {})
    security_dependencies = [
        row for row in resolved_dependencies + unresolved_dependencies
        if row["dependency_type"] in journeys.SECURITY_RELATIONSHIPS
    ]
    findings = [
        compact_finding(row) for row in quality_findings
        if row.get("service_id") == root.get("object_id")
    ]
    return {
        "environment": service.get("environment", ""),
        "domain": domain,
        "service_id": root.get("object_id", ""),
        "service_type": root.get("type", ""),
        "service_name": root.get("name", ""),
        "exposed_interfaces": journeys.ingress_records(service, props),
        "processing_policies": journeys.unique(operation.get("processing_policy_name", "") for operation in operations),
        "operation_count": len(operations),
        "operation_ids": operation_ids,
        "distinct_operation_pattern_count": len(groups),
        "operation_pattern_ids": [pattern_ids[f"{root.get('object_id', '')}\x00{signature}"] for signature in signatures],
        "service_journey_count": 1,
        "operation_pattern_journey_count": 1 if len(groups) > 1 and operation_journey_path.exists() else 0,
        "service_journey": str(service_journey_path),
        "operation_pattern_journey": str(operation_journey_path) if len(groups) > 1 and operation_journey_path.exists() else None,
        "backend_mode": routing.get("backend_mode", {}),
        "configured_backend": routing.get("configured_backend", {}),
        "route_control": routing.get("route_control", {}),
        "actual_egress": routing.get("actual_egress", {}),
        "remote_system_identity": routing.get("remote_system_identity", {}),
        "remote_topology": routing.get("remote_topology", {}),
        "resolved_dependencies": resolved_dependencies,
        "unresolved_dependencies": unresolved_dependencies,
        "resolved_files": [file_record(row) for row in file_resolution.get("resolved", [])],
        "unresolved_files": [file_record(row) for row in file_resolution.get("unresolved", [])],
        "security_dependencies": security_dependencies,
        "shared_dependencies": service.get("shared_dependencies", []),
        "semantic_facts": service.get("semantic_facts", []),
        "findings": findings,
        "evidence_certainty": {
            "ingress": service.get("ingress", {}).get("certainty", "not_evidenced"),
            "processing": service.get("processing", {}).get("certainty", "not_evidenced"),
            "configured_backend": routing.get("configured_backend", {}).get("certainty", "not_evidenced"),
            "actual_egress": routing.get("actual_egress", {}).get("certainty", "not_evidenced"),
            "overall": service.get("evidence", {}).get("overall_certainty", "not_evidenced"),
        },
        "provenance": service.get("provenance", {}),
    }


def operation_catalog_record(
    operation: dict[str, Any],
    props: dict[str, list[dict[str, str]]],
    pattern_id: str,
    pattern_member_count: int,
) -> dict[str, Any]:
    match = journeys.match_shape(operation, props)
    actions = journeys.action_records(operation, props)
    routing = operation.get("routing", {})
    dependencies = operation.get("dependencies", {})
    resolved_dependencies = [dependency_record(row) for row in dependencies.get("resolved", [])]
    unresolved_dependencies = [dependency_record(row) for row in dependencies.get("unresolved", [])]
    files = operation.get("file_resolution", {})
    processing_rule_id = operation.get("processing_rule_id", "")
    return {
        "environment": operation.get("environment", ""),
        "domain": operation.get("domain", ""),
        "operation_id": operation.get("operation_id", ""),
        "operation_pattern_id": pattern_id,
        "operation_pattern_member_count": pattern_member_count,
        "parent_service_id": operation.get("parent_service_id", ""),
        "parent_service_name": operation.get("parent_service_name", ""),
        "parent_service_type": operation.get("parent_service_type", ""),
        "method": match["method"] or None,
        "paths": match["paths"],
        "processing_policy": {
            "id": operation.get("processing_policy_id", ""),
            "name": operation.get("processing_policy_name", ""),
            "type": operation.get("processing_policy_type", ""),
        },
        "matching_rules": [
            {"id": oid, "name": name}
            for oid, name in zip(operation.get("matching_rule_ids", []), operation.get("matching_rule_names", []))
        ],
        "processing_rule": {
            "id": processing_rule_id,
            "name": operation.get("processing_rule_name", ""),
            "type": operation.get("processing_rule_type", ""),
            "direction": journeys.first_property(props, processing_rule_id, "type") or None,
            "resolved": bool(operation.get("processing_rule_found")),
        },
        "ordered_actions": [action_record(action) for action in actions],
        "semantics": journeys.semantic_summary(operation, actions),
        "backend_mode": routing.get("backend_mode", {}),
        "configured_backend": routing.get("configured_backend", {}),
        "route_control": routing.get("route_control", {}),
        "actual_egress": routing.get("actual_egress", {}),
        "resolved_dependencies": resolved_dependencies,
        "unresolved_dependencies": unresolved_dependencies,
        "resolved_files": [file_record(row) for row in files.get("resolved", [])],
        "unresolved_files": [file_record(row) for row in files.get("unresolved", [])],
        "semantic_facts": operation.get("semantic_facts", []),
        "known_findings": operation.get("known_findings", []),
        "evidence_certainty": operation.get("evidence", {}).get("certainty", "not_evidenced"),
        "provenance": operation.get("provenance", {}),
    }


def markdown_value(values: list[str]) -> str:
    return "<br>".join(f"`{value}`" for value in values) if values else "not_evidenced"


def render_services_markdown(metrics: dict[str, int], domains: list[dict[str, Any]], services: list[dict[str, Any]]) -> str:
    lines = [
        "# DataPower Service Catalog", "",
        "Normalized service inventory generated only from the frozen Atlas evidence bundles.", "",
        "## Independent metrics", "",
        f"- `operation_count`: **{metrics['operation_count']}** evidence-backed operation records.",
        f"- `distinct_operation_pattern_count`: **{metrics['distinct_operation_pattern_count']}** distinct material behavior signatures.",
        f"- `service_journey_count`: **{metrics['service_journey_count']}** service-level Journey documents.",
        f"- `operation_pattern_journey_count`: **{metrics['operation_pattern_journey_count']}** focused multi-pattern Journey documents.",
        "- Operation count is not derived from operation-pattern reports.", "",
        "## Domain coverage", "",
        "| Domain | Services | Operations | Distinct patterns | Service journeys | Pattern journeys |", "|---|---:|---:|---:|---:|---:|",
    ]
    for domain in domains:
        lines.append(
            f"| {domain['domain']} | {domain['service_count']} | {domain['operation_count']} | "
            f"{domain['distinct_operation_pattern_count']} | {domain['service_journey_count']} | "
            f"{domain['operation_pattern_journey_count']} |"
        )
    lines += ["", "## Services", "",
        "| Domain | Type | Service | Operations | Distinct patterns | Backend mode | Actual egress | Service journey | Pattern journey |",
        "|---|---|---|---:|---:|---|---|---|---|",
    ]
    for service in services:
        actual = service["actual_egress"]
        service_link = service["service_journey"].replace("outputs/as-is/", "../")
        pattern_link = (
            f"[patterns]({service['operation_pattern_journey'].replace('outputs/as-is/', '../')})"
            if service["operation_pattern_journey"] else "not_applicable"
        )
        lines.append(
            f"| {service['domain']} | {service['service_type']} | `{service['service_name']}` | "
            f"{service['operation_count']} | {service['distinct_operation_pattern_count']} | "
            f"{service['backend_mode'].get('value', 'not_evidenced')} | "
            f"{actual.get('status', 'not_evidenced')} ({','.join(actual.get('mechanism', [])) or 'none'}) | "
            f"[service]({service_link}) | "
            f"{pattern_link} |"
        )
    lines += ["", "Full dependency, file-resolution, certainty, and provenance records are retained in `services.json`.", ""]
    return "\n".join(lines)


def render_operations_markdown(metrics: dict[str, int], operations: list[dict[str, Any]]) -> str:
    lines = [
        "# DataPower Operation Catalog", "",
        f"- `operation_count`: **{metrics['operation_count']}**.",
        f"- `distinct_operation_pattern_count`: **{metrics['distinct_operation_pattern_count']}**.",
        f"- `operation_pattern_journey_count`: **{metrics['operation_pattern_journey_count']}**.",
        "- Every row below is an operation evidence record; patterns are cross-references, not substitutes for operations.", "",
        "| Domain | Service | Operation | Pattern | Method | Path | Policy | Rule / direction | Actions | Actual egress | Certainty |",
        "|---|---|---|---|---|---|---|---|---:|---|---|",
    ]
    for operation in operations:
        rule = operation["processing_rule"]
        egress = operation["actual_egress"]
        lines.append(
            f"| {operation['domain']} | `{operation['parent_service_name']}` | `{operation['operation_id']}` | "
            f"`{operation['operation_pattern_id']}` | {operation['method'] or 'not_evidenced'} | "
            f"{markdown_value(operation['paths'])} | `{operation['processing_policy']['name']}` | "
            f"`{rule['name']}` / {rule['direction'] or 'not_evidenced'} | {len(operation['ordered_actions'])} | "
            f"{egress.get('status', 'not_evidenced')} ({','.join(egress.get('mechanism', [])) or 'none'}) | "
            f"{operation['evidence_certainty']} |"
        )
    lines += ["", "Full ordered actions, semantics, dependencies, routing state, certainty, and provenance are retained in `operations.json`.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index-root", default="index")
    parser.add_argument("--journey-root", default="outputs/as-is/02-user-journeys")
    parser.add_argument("--output-root", default="outputs/as-is/01-service-catalog")
    parser.add_argument("--domains", nargs="+", required=True)
    args = parser.parse_args()

    index_root = Path(args.index_root)
    journey_root = Path(args.journey_root)
    output_root = Path(args.output_root)
    all_services: list[dict[str, Any]] = []
    all_operations: list[dict[str, Any]] = []
    domain_metrics: list[dict[str, Any]] = []

    for domain_slug in args.domains:
        domain_index = index_root / domain_slug
        services = journeys.load_jsonl(domain_index / "service_journeys.jsonl")
        operations = journeys.load_jsonl(domain_index / "operation_journeys.jsonl")
        properties = journeys.properties_index(journeys.load_csv(domain_index / "object_properties.csv"))
        findings = journeys.load_csv(domain_index / "service_journey_findings.csv")
        operations_by_service: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for operation in operations:
            operations_by_service[operation.get("parent_service_id", "")].append(operation)

        pattern_ids: dict[str, str] = {}
        operation_patterns: dict[str, tuple[str, int]] = {}
        distinct_pattern_count = 0
        pattern_journey_count = 0
        for service in services:
            service_id = service["root"]["object_id"]
            service_operations = operations_by_service.get(service_id, [])
            groups = journeys.operation_groups(service_operations, properties)
            distinct_pattern_count += len(groups)
            if len(groups) > 1:
                pattern_journey_count += 1
            for group in groups:
                signature = journeys.operation_signature(group[0], properties)
                pattern_id = operation_pattern_id(service_id, signature)
                pattern_ids[f"{service_id}\x00{signature}"] = pattern_id
                for operation in group:
                    operation_patterns[operation["operation_id"]] = (pattern_id, len(group))

        for service in services:
            service_id = service["root"]["object_id"]
            all_services.append(service_catalog_record(
                service,
                operations_by_service.get(service_id, []),
                properties,
                findings,
                pattern_ids,
                output_root,
            ))
        for operation in operations:
            pattern_id, member_count = operation_patterns[operation["operation_id"]]
            all_operations.append(operation_catalog_record(operation, properties, pattern_id, member_count))

        actual_domain = services[0].get("domain", domain_slug) if services else domain_slug
        domain_metrics.append({
            "domain": actual_domain,
            "service_count": len(services),
            "operation_count": len(operations),
            "distinct_operation_pattern_count": distinct_pattern_count,
            "service_journey_count": len(services),
            "operation_pattern_journey_count": pattern_journey_count,
            "evidence_sources": {
                "service_journeys": str(domain_index / "service_journeys.jsonl"),
                "operation_journeys": str(domain_index / "operation_journeys.jsonl"),
            },
        })

    all_services.sort(key=lambda row: (row["domain"], row["service_type"], row["service_name"], row["service_id"]))
    all_operations.sort(key=lambda row: (row["domain"], row["parent_service_id"], row["operation_id"]))
    metrics = {
        "domain_count": len(domain_metrics),
        "service_count": len(all_services),
        "operation_count": len(all_operations),
        "distinct_operation_pattern_count": sum(row["distinct_operation_pattern_count"] for row in domain_metrics),
        "service_journey_count": sum(row["service_journey_count"] for row in domain_metrics),
        "operation_pattern_journey_count": sum(row["operation_pattern_journey_count"] for row in domain_metrics),
    }
    available_reports = list((journey_root / "operation-journeys").rglob("*.md"))
    if len(available_reports) != metrics["operation_pattern_journey_count"]:
        raise SystemExit(
            "operation-pattern Journey count does not match frozen rendered reports: "
            f"catalog={metrics['operation_pattern_journey_count']} reports={len(available_reports)}"
        )

    service_document = {
        "schema": "datapower-atlas-service-catalog-v2",
        "renderer": VERSION,
        "evidence_mode": "frozen_evidence_consumption_only",
        "metrics": metrics,
        "domains": domain_metrics,
        "services": all_services,
    }
    operation_document = {
        "schema": "datapower-atlas-operation-catalog-v2",
        "renderer": VERSION,
        "evidence_mode": "frozen_evidence_consumption_only",
        "metrics": metrics,
        "operations": all_operations,
    }
    write_json(output_root / "services.json", service_document)
    write_json(output_root / "operations.json", operation_document)
    (output_root / "services.md").write_text(render_services_markdown(metrics, domain_metrics, all_services), encoding="utf-8")
    (output_root / "operations.md").write_text(render_operations_markdown(metrics, all_operations), encoding="utf-8")
    print(json.dumps(metrics, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
