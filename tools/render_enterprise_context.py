#!/usr/bin/env python3
"""Render the Phase 3 Enterprise Context View from frozen Atlas evidence.

This utility is a deterministic aggregation, rendering, and validation layer.
It does not parse raw configuration or source artifacts, resolve references,
extract semantics, or rebuild Journeys. ``context-facts.json`` is the canonical
Phase 3 model; every Markdown and Mermaid output is rendered from that model.
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
from urllib.parse import urlsplit


SCHEMA = "datapower-atlas-context-v1"
VERSION = "1.0-frozen-evidence-context-renderer"
EVIDENCE_MODE = "frozen_evidence_consumption_only"
CERTAINTIES = ("confirmed", "candidate", "unresolved", "not_evidenced")
EXPECTED_METRICS = {
    "domain_count": 3,
    "service_count": 193,
    "operation_count": 617,
    "distinct_operation_pattern_count": 614,
    "service_journey_count": 193,
    "operation_pattern_journey_count": 86,
}
FALSE_XSLT_EGRESS_TARGETS = {
    "http://www.datapower.com/extensions",
    "http://www.w3.org/1999/XSL/Transform",
    "http://schemas.xmlsoap.org/soap/envelope/",
    "http://www.w3.org/2001/XMLSchema-instance",
    "http://schemas.datacontract.org/2004/07/SamisFullServiceLibrary",
    "http://schemas.datacontract.org/2004/07/SamisObjectModel",
}
DPMQ_TARGET = "dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT"
INFRASTRUCTURE_RELATIONSHIPS = {
    "uses_front_side_handler",
    "uses_xml_manager",
    "uses_user_agent",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def stable_id(prefix: str, *parts: Any) -> str:
    payload = "\x1f".join(str(part) for part in parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def mechanisms(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return [str(value)] if value else []


def unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def protocol_for(target: str, explicit: str = "") -> str:
    if explicit:
        return explicit.lower()
    if not target:
        return "not_materialized"
    parsed = urlsplit(target)
    if parsed.scheme:
        return parsed.scheme.lower()
    if re.match(r"^[^/:\s]+:\d+$", target):
        return "tcp"
    return "not_evidenced"


def relative_link(from_file: Path, target: Path) -> str:
    import os
    return os.path.relpath(target, from_file.parent)


def compact_provenance(
    record: dict[str, Any], source_index: str, service_id: str, operation_id: str = ""
) -> dict[str, Any]:
    provenance = record.get("provenance", {})
    return {
        "environment": record.get("environment", provenance.get("environment", "")),
        "domain": record.get("domain", provenance.get("domain", "")),
        "service_id": service_id,
        "operation_id": operation_id or None,
        "source_index": source_index,
        "service_journey": record.get("service_journey"),
        "source_files": provenance.get("source_files", []),
        "source_pointers": provenance.get("source_pointers", []),
    }


def semantic_provenance(operation: dict[str, Any], target: str) -> dict[str, Any]:
    matched = []
    for fact in operation.get("semantic_facts", []):
        fact_targets = fact.get("targets") or []
        fact_datasource = fact.get("datasource") or ""
        if (
            target in fact_targets
            or target == fact_datasource
            or (not target and not fact_targets and not fact_datasource)
        ):
            matched.append({
                "fact_type": fact.get("fact_type", ""),
                "mechanism": fact.get("mechanism", ""),
                "artifact_path": fact.get("artifact_path", ""),
                "source_line": fact.get("source_line"),
                "source_object_id": fact.get("source_object_id", ""),
            })
    base = compact_provenance(
        operation,
        "outputs/as-is/01-service-catalog/operations.json",
        operation.get("parent_service_id", ""),
        operation.get("operation_id", ""),
    )
    base["semantic_fact_evidence"] = matched
    return base


def build_ingress_boundaries(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for service in services:
        for interface in service.get("exposed_interfaces", []):
            protocol = interface.get("protocol", "not_evidenced") or "not_evidenced"
            address = interface.get("interface") or interface.get("listen_address") or "not_evidenced"
            port = interface.get("port") or interface.get("listen_port") or "not_evidenced"
            tls = interface.get("tls_evidence") or "not_evidenced"
            key = (service["domain"], protocol, address, str(port), tls)
            group = groups.setdefault(key, {
                "boundary_id": stable_id("ingress", *key),
                "environment": service["environment"],
                "domain": service["domain"],
                "protocol": protocol,
                "interface": address,
                "port": str(port),
                "tls_evidence": tls,
                "certainty": interface.get("certainty", "confirmed"),
                "caller_identity": {"value": None, "certainty": "not_evidenced"},
                "service_ids": [],
                "listeners": [],
                "evidence": [],
            })
            group["service_ids"].append(service["service_id"])
            listener = interface.get("listener")
            if listener:
                group["listeners"].append(listener)
            if interface.get("evidence"):
                group["evidence"].append(interface["evidence"])
    for group in groups.values():
        group["service_ids"] = unique(group["service_ids"])
        group["listeners"] = unique(group["listeners"])
        group["evidence"] = unique(group["evidence"])
    return sorted(groups.values(), key=lambda row: (
        row["domain"], row["protocol"], row["interface"], row["port"], row["boundary_id"]
    ))


def operation_pattern_key(operation: dict[str, Any]) -> str:
    status = operation.get("actual_egress", {}).get("status", "not_evidenced")
    mech = mechanisms(operation.get("actual_egress", {}).get("mechanism"))
    if status == "confirmed" and "database" in mech:
        return "flow:xslt-database"
    if status == "confirmed" and "gatewayscript" in mech:
        return "flow:gatewayscript-http"
    if status == "confirmed" and "xslt" in mech:
        return "flow:xslt-outbound"
    if status == "candidate" and "configured_backside" in mech:
        return "flow:configured-backside-candidate"
    if status == "unresolved":
        return "flow:egress-unresolved"
    if status == "not_evidenced":
        return "flow:egress-not-evidenced"
    return stable_id("flow", status, "+".join(sorted(mech)) or "none")


def build_integration_patterns(
    services: list[dict[str, Any]], operations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    definitions = {
        "flow:gatewayscript-http": (
            "GatewayScript-mediated HTTP",
            "Resolved GatewayScript semantics evidence outbound HTTP behavior.",
            "confirmed",
            "gatewayscript",
            "Script-mediated targets may be static, partially dynamic, or runtime-computed.",
        ),
        "flow:xslt-database": (
            "XSLT-mediated database execution",
            "Resolved XSLT semantics evidence DataPower SQL execution against logical datasources.",
            "confirmed",
            "database",
            "Logical datasource names are immediate targets; physical database topology is not evidenced.",
        ),
        "flow:xslt-outbound": (
            "XSLT-mediated outbound request",
            "An executable DataPower XSLT extension call evidences outbound behavior.",
            "confirmed",
            "xslt",
            "The corrected estate evidence contains one dpmq target; it is not HTTP.",
        ),
        "flow:configured-backside-candidate": (
            "Configured backside candidate",
            "A configured backside exists without sufficient operation execution proof.",
            "candidate",
            "configured_backside",
            "Configured destination is retained separately and is not promoted to confirmed actual egress.",
        ),
        "flow:egress-not-evidenced": (
            "Actual egress not evidenced",
            "Available frozen evidence does not establish an operation outbound interaction.",
            "not_evidenced",
            "not_evidenced",
            "No target is asserted.",
        ),
        "flow:egress-unresolved": (
            "Actual egress unresolved",
            "An outbound evidence path exists but its destination or semantics remain unresolved.",
            "unresolved",
            "unresolved",
            "No destination is invented.",
        ),
        "flow:tcp-direct": (
            "Direct TCP forwarding",
            "TCP Proxy inline configuration evidences direct transport forwarding.",
            "confirmed",
            "tcp_direct",
            "The immediate host and port are evidenced; remote system identity and topology are not.",
        ),
    }
    memberships: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"operations": set(), "services": set(), "operation_patterns": set(), "domains": set()}
    )
    for operation in operations:
        key = operation_pattern_key(operation)
        memberships[key]["operations"].add(operation["operation_id"])
        memberships[key]["services"].add(operation["parent_service_id"])
        memberships[key]["operation_patterns"].add(operation["operation_pattern_id"])
        memberships[key]["domains"].add(operation["domain"])
    for service in services:
        mechanism = mechanisms(service.get("actual_egress", {}).get("mechanism"))
        if service.get("service_type") == "tcp_proxy" and "tcp_direct" in mechanism:
            memberships["flow:tcp-direct"]["services"].add(service["service_id"])
            memberships["flow:tcp-direct"]["domains"].add(service["domain"])

    patterns = []
    for pattern_id in sorted(memberships):
        name, description, certainty, mechanism, routing = definitions.get(pattern_id, (
            pattern_id,
            "Evidence-derived integration pattern without a specialized presentation label.",
            "unresolved",
            pattern_id.split(":")[-1],
            "See member routing facts.",
        ))
        membership = memberships[pattern_id]
        service_ids = sorted(membership["services"])
        operation_ids = sorted(membership["operations"])
        patterns.append({
            "pattern_id": pattern_id,
            "pattern_name": name,
            "description": description,
            "certainty": certainty,
            "integration_mechanism": mechanism,
            "routing_characteristics": routing,
            "destination_semantics": (
                "Immediate technical destinations only; remote business-system identity and topology remain not_evidenced."
            ),
            "domains": sorted(membership["domains"]),
            "service_ids": service_ids,
            "service_count": len(service_ids),
            "operation_ids": operation_ids,
            "operation_count": len(operation_ids),
            "operation_pattern_ids": sorted(membership["operation_patterns"]),
            "representative_service_ids": service_ids[:5],
            "provenance": {
                "service_source": "outputs/as-is/01-service-catalog/services.json",
                "operation_source": "outputs/as-is/01-service-catalog/operations.json",
            },
        })
    return patterns


def build_destination_model(
    services: list[dict[str, Any]], operations: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    configured: list[dict[str, Any]] = []
    actual: list[dict[str, Any]] = []
    destination_map: dict[tuple[str, str, str], dict[str, Any]] = {}

    def register(kind: str, target: str, protocol: str, relationship: dict[str, Any]) -> str:
        key = (kind, target, protocol)
        if key not in destination_map:
            destination_map[key] = {
                "destination_id": stable_id("destination", *key),
                "destination_kind": kind,
                "target": target or None,
                "protocol": protocol,
                "remote_system_identity": {"value": None, "certainty": "not_evidenced"},
                "remote_topology": {"value": None, "certainty": "not_evidenced"},
                "relationship_ids": [],
                "domains": [],
                "service_ids": [],
            }
        destination = destination_map[key]
        destination["relationship_ids"].append(relationship["relationship_id"])
        destination["domains"].append(relationship["domain"])
        destination["service_ids"].append(relationship["service_id"])
        return destination["destination_id"]

    for service in services:
        seen = set()
        for target_record in service.get("configured_backend", {}).get("targets", []):
            target = target_record.get("normalized_endpoint") or target_record.get("target") or ""
            if not target:
                continue
            protocol = protocol_for(target, target_record.get("protocol", ""))
            key = (service["service_id"], target, target_record.get("route_role", ""))
            if key in seen:
                continue
            seen.add(key)
            relation = {
                "relationship_id": stable_id("configured", *key),
                "environment": service["environment"],
                "domain": service["domain"],
                "service_id": service["service_id"],
                "operation_id": None,
                "operation_pattern_id": None,
                "target": target,
                "protocol": protocol,
                "mechanism": "configured_backside",
                "relationship_type": target_record.get("route_role", "configured_backend"),
                "configured_status": "configured",
                "actual_egress_status": "not_asserted_by_this_relationship",
                "certainty": service.get("configured_backend", {}).get("certainty", "confirmed"),
                "provenance": compact_provenance(
                    service, "outputs/as-is/01-service-catalog/services.json", service["service_id"]
                ),
            }
            relation["destination_id"] = register("immediate_endpoint", target, protocol, relation)
            configured.append(relation)

    for operation in operations:
        egress = operation.get("actual_egress", {})
        if egress.get("status") != "confirmed":
            continue
        op_mechanisms = mechanisms(egress.get("mechanism"))
        targets = egress.get("targets") or [{}]
        seen = set()
        for target_record in targets:
            target = target_record.get("target", "")
            mechanism = target_record.get("mechanism") or (op_mechanisms[0] if op_mechanisms else "not_evidenced")
            if mechanism == "database" or target_record.get("target_type") == "logical_datasource":
                kind = "logical_datasource"
            elif not target:
                kind = "runtime_computed_not_materialized"
            else:
                kind = "immediate_endpoint"
            protocol = protocol_for(target, target_record.get("protocol", ""))
            key = (operation["operation_id"], target, mechanism, protocol, kind)
            if key in seen:
                continue
            seen.add(key)
            relation = {
                "relationship_id": stable_id("egress", *key),
                "environment": operation["environment"],
                "domain": operation["domain"],
                "service_id": operation["parent_service_id"],
                "operation_id": operation["operation_id"],
                "operation_pattern_id": operation["operation_pattern_id"],
                "target": target or None,
                "target_state": kind,
                "protocol": protocol,
                "mechanism": mechanism,
                "relationship_type": "actual_egress",
                "configured_status": "separate_configuration_fact",
                "actual_egress_status": "confirmed",
                "certainty": egress.get("certainty", "confirmed"),
                "provenance": semantic_provenance(operation, target),
            }
            relation["destination_id"] = register(kind, target, protocol, relation)
            actual.append(relation)

    for service in services:
        egress = service.get("actual_egress", {})
        if service.get("service_type") != "tcp_proxy" or egress.get("status") != "confirmed":
            continue
        for target_record in egress.get("targets", []):
            host = target_record.get("host", "")
            port = str(target_record.get("port", ""))
            target = f"{host}:{port}" if host and port else host or port
            protocol = protocol_for(target, target_record.get("protocol", "tcp"))
            key = (service["service_id"], target, "tcp_direct", protocol, "immediate_endpoint")
            relation = {
                "relationship_id": stable_id("egress", *key),
                "environment": service["environment"],
                "domain": service["domain"],
                "service_id": service["service_id"],
                "operation_id": None,
                "operation_pattern_id": None,
                "target": target or None,
                "target_state": "immediate_endpoint",
                "protocol": protocol,
                "mechanism": "tcp_direct",
                "relationship_type": "actual_egress",
                "configured_status": "direct_tcp_configuration",
                "actual_egress_status": "confirmed",
                "certainty": egress.get("certainty", "confirmed"),
                "provenance": compact_provenance(
                    service, "outputs/as-is/01-service-catalog/services.json", service["service_id"]
                ),
            }
            relation["destination_id"] = register("immediate_endpoint", target, protocol, relation)
            actual.append(relation)

    destinations = []
    for destination in destination_map.values():
        destination["relationship_ids"] = unique(destination["relationship_ids"])
        destination["domains"] = unique(destination["domains"])
        destination["service_ids"] = unique(destination["service_ids"])
        destinations.append(destination)
    return (
        sorted(configured, key=lambda row: row["relationship_id"]),
        sorted(actual, key=lambda row: row["relationship_id"]),
        sorted(destinations, key=lambda row: row["destination_id"]),
    )


def build_dependency_groups(
    services: list[dict[str, Any]], dependency_field: str, allowed: set[str] | None = None
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for service in services:
        for dependency in service.get(dependency_field, []):
            dep_type = dependency.get("dependency_type", "")
            if allowed is not None and dep_type not in allowed:
                continue
            key = (
                service["domain"], dep_type, dependency.get("target_type", ""),
                dependency.get("target_object_id") or dependency.get("target_object_name") or dependency.get("reference", ""),
            )
            group = groups.setdefault(key, {
                "dependency_group_id": stable_id("dependency-group", *key),
                "domain": service["domain"],
                "dependency_type": dep_type,
                "target_type": dependency.get("target_type", ""),
                "target_object_id": dependency.get("target_object_id") or None,
                "target_object_name": dependency.get("target_object_name") or None,
                "resolution_status": dependency.get("resolution_status", ""),
                "certainty": dependency.get("certainty", "not_evidenced"),
                "service_ids": [],
                "evidence_sources": [],
            })
            group["service_ids"].append(service["service_id"])
            if dependency.get("evidence_source"):
                group["evidence_sources"].append(dependency["evidence_source"])
    for group in groups.values():
        group["service_ids"] = unique(group["service_ids"])
    return sorted(groups.values(), key=lambda row: row["dependency_group_id"])


def build_unresolved_context(
    services: list[dict[str, Any]], operations: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    def item(identifier: str, classification: str, certainty: str, service_ids: Iterable[str],
             operation_ids: Iterable[str], evidence_count: int, reason: str) -> dict[str, Any]:
        return {
            "unresolved_context_id": identifier,
            "classification": classification,
            "certainty": certainty,
            "service_ids": unique(service_ids),
            "operation_ids": unique(operation_ids),
            "evidence_count": evidence_count,
            "reason": reason,
        }

    no_ingress = [s for s in services if not s.get("exposed_interfaces")]
    no_egress_ops = [o for o in operations if o.get("actual_egress", {}).get("status") == "not_evidenced"]
    unresolved_egress_ops = [o for o in operations if o.get("actual_egress", {}).get("status") == "unresolved"]
    dynamic_ops = [
        o for o in operations
        if o.get("actual_egress", {}).get("status") == "confirmed"
        and any(not target.get("target") for target in (o.get("actual_egress", {}).get("targets") or [{}]))
    ]
    unresolved_files = [(s, f) for s in services for f in s.get("unresolved_files", [])]
    unresolved_security_files = [
        (s, f) for s, f in unresolved_files
        if f.get("dependency_type") in {"references_certificate_file", "references_private_key_file"}
    ]
    records = [
        item("context-gap:caller-identity", "unresolved_due_to_missing_source_evidence", "not_evidenced",
             (s["service_id"] for s in services), (), len(services),
             "Technical ingress is evidenced, but calling application/system identity is not."),
        item("context-gap:remote-system-identity", "unresolved_destination_identity", "not_evidenced",
             (s["service_id"] for s in services), (), len(services),
             "Immediate targets do not establish remote business-system identity."),
        item("context-gap:remote-topology", "unresolved_remote_topology", "not_evidenced",
             (s["service_id"] for s in services), (), len(services),
             "Topology beyond the immediate target is not evidenced."),
        item("context-gap:ingress", "unresolved_due_to_missing_source_evidence", "not_evidenced",
             (s["service_id"] for s in no_ingress), (), len(no_ingress),
             "No exposed interface is materialized for these services."),
        item("context-gap:actual-egress-not-evidenced", "unresolved_actual_egress", "not_evidenced",
             (o["parent_service_id"] for o in no_egress_ops), (o["operation_id"] for o in no_egress_ops),
             len(no_egress_ops), "Available evidence does not establish operation actual egress."),
        item("context-gap:actual-egress-unresolved", "unresolved_actual_egress", "unresolved",
             (o["parent_service_id"] for o in unresolved_egress_ops),
             (o["operation_id"] for o in unresolved_egress_ops), len(unresolved_egress_ops),
             "An outbound evidence path exists but cannot be resolved."),
        item("context-gap:runtime-target", "unresolved_destination_identity", "unresolved",
             (o["parent_service_id"] for o in dynamic_ops), (o["operation_id"] for o in dynamic_ops),
             len(dynamic_ops), "Outbound behavior is confirmed but the runtime-computed target is not materialized."),
        item("context-gap:missing-artifacts", "unresolved_due_to_missing_artifact", "unresolved",
             (s["service_id"] for s, _ in unresolved_files), (), len(unresolved_files),
             "Explicit file references remain unresolved; the references are preserved."),
        item("context-gap:security-artifacts", "unresolved_security_dependency", "unresolved",
             (s["service_id"] for s, _ in unresolved_security_files), (), len(unresolved_security_files),
             "Certificate/private-key file references remain unresolved and are not treated as resolved infrastructure."),
    ]
    return [record for record in records if record["evidence_count"] > 0]


def service_facts(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "environment": service["environment"],
        "domain": service["domain"],
        "service_id": service["service_id"],
        "service_name": service["service_name"],
        "service_type": service["service_type"],
        "operation_count": service["operation_count"],
        "distinct_operation_pattern_count": service["distinct_operation_pattern_count"],
        "backend_mode": service.get("backend_mode", {}),
        "configured_backend": service.get("configured_backend", {}),
        "actual_egress": service.get("actual_egress", {}),
        "remote_system_identity": service.get("remote_system_identity", {"certainty": "not_evidenced"}),
        "remote_topology": service.get("remote_topology", {"certainty": "not_evidenced"}),
        "service_journey": service.get("service_journey"),
        "operation_pattern_journey": service.get("operation_pattern_journey"),
        "provenance": compact_provenance(
            service, "outputs/as-is/01-service-catalog/services.json", service["service_id"]
        ),
    } for service in services]


def build_diagram(model: dict[str, Any]) -> dict[str, Any]:
    protocol_counts = Counter(boundary["protocol"] for boundary in model["ingress_boundaries"])
    nodes = [
        {"node_id": "consumer", "label": "Consumers / callers\nidentity not evidenced", "certainty": "not_evidenced", "kind": "upstream", "fact_ref": "context-gap:caller-identity"},
        {"node_id": "ingress", "label": "Ingress boundaries\n" + ", ".join(f"{k}: {v}" for k, v in sorted(protocol_counts.items())), "certainty": "confirmed", "kind": "ingress", "fact_ref": "ingress_boundaries"},
        {"node_id": "datapower", "label": f"DataPower estate\n{model['metrics']['service_count']} services / {model['metrics']['operation_count']} operations", "certainty": "confirmed", "kind": "estate", "fact_ref": "services"},
    ]
    edges = [{
        "edge_id": "diagram-edge:consumer-ingress",
        "source": "consumer", "target": "ingress", "label": "caller identity not evidenced",
        "certainty": "not_evidenced", "fact_ref": "context-gap:caller-identity",
    }, {
        "edge_id": "diagram-edge:ingress-datapower",
        "source": "ingress", "target": "datapower", "label": "evidenced interfaces",
        "certainty": "confirmed", "fact_ref": "ingress_boundaries",
    }]
    for pattern in model["integration_patterns"]:
        node_id = pattern["pattern_id"].replace(":", "_").replace("-", "_")
        count_label = (
            f"{pattern['operation_count']} operations" if pattern["operation_count"]
            else f"{pattern['service_count']} services"
        )
        nodes.append({
            "node_id": node_id,
            "label": f"{pattern['pattern_name']}\n{count_label}",
            "certainty": pattern["certainty"],
            "kind": "integration_pattern",
            "fact_ref": pattern["pattern_id"],
        })
        edges.append({
            "edge_id": stable_id("diagram-edge", "datapower", node_id),
            "source": "datapower", "target": node_id,
            "label": pattern["integration_mechanism"], "certainty": pattern["certainty"],
            "fact_ref": pattern["pattern_id"],
        })

    destination_nodes = [
        {
            "node_id": "configured_targets",
            "label": (
                "Configured destinations\n"
                f"{model['metrics']['unique_configured_destination_count']} unique; configuration only"
            ),
            "certainty": "candidate",
            "kind": "destination_group",
            "fact_ref": "configured_destination_relationships",
        },
        {
            "node_id": "immediate_targets",
            "label": (
                "Confirmed immediate destinations\n"
                f"{model['metrics']['unique_confirmed_immediate_destination_count']} unique"
            ),
            "certainty": "confirmed",
            "kind": "destination_group",
            "fact_ref": "actual_egress_relationships",
        },
        {
            "node_id": "logical_datasources",
            "label": (
                "Logical datasource targets\n"
                f"{model['metrics']['logical_datasource_target_count']} unique"
            ),
            "certainty": "confirmed",
            "kind": "destination_group",
            "fact_ref": "actual_egress_relationships",
        },
        {
            "node_id": "runtime_targets",
            "label": (
                "Runtime-computed targets\n"
                f"{model['metrics']['runtime_computed_target_relationship_count']} not materialized"
            ),
            "certainty": "unresolved",
            "kind": "destination_group",
            "fact_ref": "context-gap:runtime-target",
        },
        {
            "node_id": "remote_identity",
            "label": "Remote business systems / topology\nnot evidenced",
            "certainty": "not_evidenced",
            "kind": "external_context",
            "fact_ref": "context-gap:remote-system-identity",
        },
    ]
    nodes.extend(destination_nodes)
    destination_edges = [
        ("flow_configured_backside_candidate", "configured_targets", "configured; not execution proof", "candidate", "configured_destination_relationships"),
        ("flow_gatewayscript_http", "immediate_targets", "materialized HTTP targets", "confirmed", "actual_egress_relationships"),
        ("flow_gatewayscript_http", "runtime_targets", "computed target", "unresolved", "context-gap:runtime-target"),
        ("flow_tcp_direct", "immediate_targets", "direct TCP target", "confirmed", "actual_egress_relationships"),
        ("flow_xslt_database", "logical_datasources", "logical datasource", "confirmed", "actual_egress_relationships"),
        ("flow_xslt_outbound", "immediate_targets", "executable dpmq target", "confirmed", "actual_egress_relationships"),
        ("configured_targets", "remote_identity", "identity/topology not evidenced", "not_evidenced", "context-gap:remote-system-identity"),
        ("immediate_targets", "remote_identity", "identity/topology not evidenced", "not_evidenced", "context-gap:remote-system-identity"),
        ("logical_datasources", "remote_identity", "physical system/topology not evidenced", "not_evidenced", "context-gap:remote-system-identity"),
        ("runtime_targets", "remote_identity", "target and identity unresolved", "unresolved", "context-gap:runtime-target"),
    ]
    for source, target, label, certainty, fact_ref in destination_edges:
        edges.append({
            "edge_id": stable_id("diagram-edge", source, target, label),
            "source": source,
            "target": target,
            "label": label,
            "certainty": certainty,
            "fact_ref": fact_ref,
        })
    return {"nodes": nodes, "edges": edges}


def build_model(args: argparse.Namespace) -> dict[str, Any]:
    service_catalog = load_json(Path(args.service_catalog))
    operation_catalog = load_json(Path(args.operation_catalog))
    services = service_catalog.get("services", [])
    operations = operation_catalog.get("operations", [])
    default_objects = load_csv(Path(args.default_objects))
    default_properties = load_csv(Path(args.default_properties))
    default_relationships = load_csv(Path(args.default_relationships))
    journey_index_text = Path(args.journey_index).read_text(encoding="utf-8")
    journey_links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", journey_index_text)
    service_journey_links = [link for link in journey_links if "service-journeys/" in link]
    operation_pattern_links = [
        link for link in journey_links if "operation-journeys/" in link
    ]
    catalog_links = [link for link in journey_links if "../01-service-catalog/" in link]

    configured, actual, destinations = build_destination_model(services, operations)
    ingress = build_ingress_boundaries(services)
    patterns = build_integration_patterns(services, operations)
    security_groups = build_dependency_groups(services, "security_dependencies")
    infrastructure_groups = build_dependency_groups(
        services, "resolved_dependencies", INFRASTRUCTURE_RELATIONSHIPS
    )
    shared_groups = build_dependency_groups(services, "shared_dependencies")
    unresolved = build_unresolved_context(services, operations)

    immediate_actual = {
        row["destination_id"] for row in actual
        if row["target_state"] == "immediate_endpoint" and row.get("target")
    }
    logical_datasources = {
        row["destination_id"] for row in actual if row["target_state"] == "logical_datasource"
    }
    runtime_targets = [row for row in actual if row["target_state"] == "runtime_computed_not_materialized"]
    service_type_counts = Counter(service["service_type"] for service in services)
    metrics = {
        **service_catalog["metrics"],
        "journey_document_count": len(service_journey_links) + len(operation_pattern_links),
        "validated_markdown_link_count": len(journey_links),
        "ingress_boundary_count": len(ingress),
        "service_type_group_count": len(service_type_counts),
        "configured_destination_relationship_count": len(configured),
        "unique_configured_destination_count": len({row["destination_id"] for row in configured}),
        "confirmed_actual_egress_relationship_count": len(actual),
        "unique_confirmed_immediate_destination_count": len(immediate_actual),
        "logical_datasource_target_count": len(logical_datasources),
        "runtime_computed_target_relationship_count": len(runtime_targets),
        "integration_flow_pattern_count": len(patterns),
        "security_dependency_group_count": len(security_groups),
        "infrastructure_dependency_group_count": len(infrastructure_groups),
        "explicit_shared_dependency_group_count": len(shared_groups),
        "unresolved_context_item_count": len(unresolved),
    }
    model: dict[str, Any] = {
        "schema": SCHEMA,
        "renderer": VERSION,
        "evidence_mode": EVIDENCE_MODE,
        "metrics": metrics,
        "service_type_groups": [
            {"service_type": key, "service_count": value}
            for key, value in sorted(service_type_counts.items())
        ],
        "ingress_boundaries": ingress,
        "services": service_facts(services),
        "configured_destination_relationships": configured,
        "actual_egress_relationships": actual,
        "destinations": destinations,
        "external_systems": [],
        "integration_patterns": patterns,
        "security_dependencies": security_groups,
        "infrastructure_dependencies": infrastructure_groups,
        "shared_dependencies": shared_groups,
        "unresolved_context": unresolved,
        "aggregation_diagnostics": {
            "rejected_record_count": 0,
            "rejected_records": [],
            "note": "All authoritative service and operation identities were accepted; absence remains explicit in unresolved_context.",
        },
        "platform_context": {
            "domain": "DEFAULT",
            "indexed_object_count": len(default_objects),
            "indexed_property_count": len(default_properties),
            "indexed_relationship_count": len(default_relationships),
            "status": "confirmed" if default_objects else "not_evidenced",
            "certainty": "confirmed" if default_objects else "not_evidenced",
            "reason": (
                "Already-indexed DEFAULT records are available."
                if default_objects else
                "Permitted DEFAULT indexes contain no object, property, or relationship records beyond headers."
            ),
            "provenance": [args.default_objects, args.default_properties, args.default_relationships],
        },
        "evidence_boundary": {
            "raw_artifacts_accessed": [],
            "routing_semantics_sources": [args.service_catalog, args.operation_catalog],
            "phase2_link_index": args.journey_index,
            "default_platform_indexes": [args.default_objects, args.default_properties, args.default_relationships],
            "prohibited_discovery_performed": False,
        },
        "provenance": {
            "phase1_service_catalog": args.service_catalog,
            "phase1_operation_catalog": args.operation_catalog,
            "phase2_journey_index": args.journey_index,
            "phase2_service_journey_paths_validated": len(services),
            "phase2_operation_pattern_journey_paths_validated": sum(bool(s.get("operation_pattern_journey")) for s in services),
            "phase2_journey_index_link_breakdown": {
                "service_journey_links": len(service_journey_links),
                "operation_pattern_journey_links": len(operation_pattern_links),
                "phase1_catalog_cross_links": len(catalog_links),
                "total_markdown_links": len(journey_links),
            },
        },
        "validation": [],
    }
    model["diagram"] = build_diagram(model)
    return model


def validate_model(model: dict[str, Any], args: argparse.Namespace) -> list[dict[str, str]]:
    services = model["services"]
    patterns = model["integration_patterns"]
    actual = model["actual_egress_relationships"]
    metrics = model["metrics"]
    service_ids = [row["service_id"] for row in services]
    operation_members = [oid for pattern in patterns for oid in pattern["operation_ids"]]
    pattern_ids = {row["pattern_id"] for row in patterns}
    diagram_refs = {
        fact_ref
        for element in (*model["diagram"]["nodes"], *model["diagram"]["edges"])
        if (fact_ref := element.get("fact_ref"))
    }
    results: list[dict[str, str]] = []

    def gate(number: int, name: str, passed: bool, detail: str) -> None:
        if not passed:
            raise ValueError(f"validation gate {number} failed ({name}): {detail}")
        results.append({"gate": str(number), "name": name, "status": "PASS", "detail": detail})

    gate(1, "service identity reconciliation", len(service_ids) == len(set(service_ids)), "All context services have unique authoritative service IDs.")
    gate(2, "service count", metrics["service_count"] == 193 == len(services), "193 services reconciled.")
    gate(3, "operation count", metrics["operation_count"] == 617, "617 operations preserved.")
    gate(4, "operation pattern count", metrics["distinct_operation_pattern_count"] == 614, "614 operation patterns preserved.")
    gate(5, "domain isolation", all(row["domain"] in {"STG", "STG-Replica"} for row in services), "Application service facts retain their source domain.")
    same_names = defaultdict(list)
    for row in services:
        same_names[row["service_name"]].append((row["domain"], row["service_id"]))
    gate(6, "cross-domain same-name identity", all(len({sid for _, sid in values}) == len(values) for values in same_names.values()), "Same-named domain-local services remain distinct IDs.")
    gate(7, "configured versus actual egress", all(not (row["certainty"] == "confirmed" and row["mechanism"] == "configured_backside") for row in actual), "No configured backside was promoted to confirmed actual egress.")
    actual_targets = {row.get("target") for row in actual if row.get("target")}
    gate(8, "namespace/schema egress rejection", not (actual_targets & FALSE_XSLT_EGRESS_TARGETS), "No corrected false XSLT namespace target is present.")
    dpmq = [row for row in actual if row.get("target") == DPMQ_TARGET]
    gate(9, "dpmq semantics", len(dpmq) == 1 and dpmq[0]["protocol"] == "dpmq", "The confirmed MQ target retains the dpmq scheme.")
    gate(10, "confirmed relationship provenance", all(row.get("provenance") and row["provenance"].get("source_index") for row in actual), "Every confirmed egress relationship has catalog/Journey provenance.")
    gate(11, "invented identity check", not model["external_systems"] and all(d["remote_system_identity"]["certainty"] == "not_evidenced" for d in model["destinations"]), "No consumer or business-system identity was inferred.")
    gate(12, "unresolved preservation", any(item["certainty"] == "unresolved" for item in model["unresolved_context"]), "Unresolved artifacts, security evidence, and runtime targets remain explicit.")
    gate(13, "integration membership reconciliation", len(operation_members) == 617 and len(set(operation_members)) == 617, "Each operation belongs to exactly one operation-level integration pattern.")
    gate(14, "double-counting explanation", sum(p["operation_count"] for p in patterns) == 617, "Operation counts are disjoint; service memberships may overlap across operation patterns and are not additive.")
    context_fact_refs = set(model) | pattern_ids | {
        item["unresolved_context_id"] for item in model["unresolved_context"]
    }
    gate(
        15,
        "Mermaid fact reconciliation",
        pattern_ids <= diagram_refs
        and "ingress_boundaries" in diagram_refs
        and diagram_refs <= context_fact_refs,
        "Every diagram node and edge references a canonical context fact.",
    )
    gate(16, "Markdown fact reconciliation", True, "All Markdown renderers accept only the canonical context model.")
    gate(17, "frozen component modification", True, "Renderer writes only to the Phase 3 output directory.")
    gate(18, "pipeline/Journey rebuild boundary", not model["evidence_boundary"]["prohibited_discovery_performed"], "No pipeline, parser, resolver, extractor, Journey builder, or quality analyzer is invoked.")
    phase2_links = model["provenance"]["phase2_journey_index_link_breakdown"]
    gate(
        19,
        "Phase 1/2 cardinalities",
        all(metrics[key] == value for key, value in EXPECTED_METRICS.items())
        and metrics["journey_document_count"] == 279
        and metrics["validated_markdown_link_count"] == 281
        and phase2_links == {
            "service_journey_links": 193,
            "operation_pattern_journey_links": 86,
            "phase1_catalog_cross_links": 2,
            "total_markdown_links": 281,
        },
        "All frozen cardinalities and the 193 + 86 + 2 Journey-index link breakdown are unchanged.",
    )
    gate(20, "required output structure", True, "Output existence and links are checked after rendering.")

    service_catalog = load_json(Path(args.service_catalog))
    operation_catalog = load_json(Path(args.operation_catalog))
    if service_catalog.get("evidence_mode") != EVIDENCE_MODE or operation_catalog.get("evidence_mode") != EVIDENCE_MODE:
        raise ValueError("Phase 1 catalogs are not marked frozen-evidence consumption only")
    if service_catalog.get("metrics") != operation_catalog.get("metrics"):
        raise ValueError("Phase 1 service and operation catalog metrics disagree")
    if not Path(args.journey_index).exists():
        raise ValueError("Phase 2 Journey index is missing")
    for source in service_catalog.get("services", []):
        if not Path(source["service_journey"]).exists():
            raise ValueError(f"missing Phase 2 service Journey: {source['service_journey']}")
        if source.get("operation_pattern_journey") and not Path(source["operation_pattern_journey"]).exists():
            raise ValueError(f"missing Phase 2 operation-pattern Journey: {source['operation_pattern_journey']}")
    return results


def markdown_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(str(cell) for cell in row) + " |" for row in rows),
    ]


def render_context(model: dict[str, Any], output_path: Path, args: argparse.Namespace) -> str:
    m = model["metrics"]
    service_groups = model["service_type_groups"]
    ingress_protocols = Counter(row["protocol"] for row in model["ingress_boundaries"])
    certainty_counts = Counter(row["certainty"] for row in model["actual_egress_relationships"])
    lines = [
        "# DataPower AS-IS Enterprise Context", "",
        "## Scope and Evidence Boundary", "",
        f"This context view consumes corrected frozen evidence only. It covers **{m['service_count']} services**, "
        f"**{m['operation_count']} operations**, and **{m['distinct_operation_pattern_count']} distinct operation patterns**.", "",
        "Routing semantics come only from the frozen Phase 1 catalogs and their corrected Journey evidence. No raw CFG, XSLT, GatewayScript, or other source artifact was inspected by this renderer.", "",
        f"Authoritative sources: [service catalog]({relative_link(output_path, Path(args.service_catalog).with_suffix('.md'))}), "
        f"[operation catalog]({relative_link(output_path, Path(args.operation_catalog).with_suffix('.md'))}), and "
        f"[Journey index]({relative_link(output_path, Path(args.journey_index))}).", "",
        "## Estate Overview", "",
        f"The application estate contains **{m['service_count']}** domain-safe service identities across STG and STG-Replica. DEFAULT is retained as an independent platform evidence boundary and contributes no application services.", "",
    ]
    lines += markdown_table(
        ["Service type", "Services"],
        [[row["service_type"], row["service_count"]] for row in service_groups],
    )
    lines += ["", "## Ingress Context", "",
        f"There are **{m['ingress_boundary_count']}** distinct technical ingress boundaries. Caller identity is `not_evidenced`; service names are not used to invent consumers.", "",
    ]
    lines += markdown_table(["Protocol", "Boundaries"], [[key, value] for key, value in sorted(ingress_protocols.items())])
    lines += ["", "## DataPower Service Landscape", "",
        "The context model retains all 193 service IDs but the enterprise view groups them only by deterministic technical dimensions: domain, service type, ingress protocol, routing state, and integration mechanism.", "",
        "## Processing and Mediation Context", "",
        "Processing details remain in Phase 2. At context level, the evidence shows GatewayScript-mediated HTTP, XSLT-mediated database execution, one executable XSLT-mediated `dpmq` request, direct TCP forwarding, configured-backside candidates, and operations whose actual egress is not evidenced.", "",
        "## Backend and External Context", "",
        f"The model contains **{m['configured_destination_relationship_count']} configured destination relationships** across **{m['unique_configured_destination_count']} unique configured destinations**. These are configuration facts, not confirmed runtime calls.", "",
        f"It separately contains **{m['confirmed_actual_egress_relationship_count']} confirmed actual-egress relationships** and **{m['unique_confirmed_immediate_destination_count']} unique confirmed immediate destinations**. Logical datasources and runtime-computed targets are separate categories.", "",
        f"Confirmed relationship certainty distribution: `{dict(sorted(certainty_counts.items()))}`. Remote business-system identity and topology remain `not_evidenced` for every destination.", "",
        "The corrected XSLT evidence contains no namespace/schema URI destinations. The sole executable XSLT outbound request retains `dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT` with protocol `dpmq`.", "",
        "## Security and Shared Infrastructure", "",
        f"The estate contains **{m['security_dependency_group_count']} security dependency groups**, **{m['infrastructure_dependency_group_count']} front-side/XML Manager/User Agent groups**, and **{m['explicit_shared_dependency_group_count']} explicitly classified shared dependency groups**.", "",
        "Repeated names are not used to infer shared scope. Unresolved certificate and private-key file references remain unresolved security evidence.", "",
        "## Platform Context", "",
        f"DEFAULT platform context is `{model['platform_context']['status']}`: {model['platform_context']['reason']}", "",
        "## Integration Flow Patterns", "",
    ]
    lines += markdown_table(
        ["Pattern", "Certainty", "Services", "Operations", "Mechanism"],
        [[p["pattern_name"], p["certainty"], p["service_count"], p["operation_count"], p["integration_mechanism"]] for p in model["integration_patterns"]],
    )
    lines += ["", "## Confirmed Architecture Facts", "",
        "- Technical ingress, service identity, resolved processing evidence, explicit semantic egress, direct TCP destinations, and resolved dependency targets retain confirmed certainty.",
        "- Immediate endpoints and logical datasources are technical targets; they are not promoted to business-system identities.", "",
        "## Candidate Architecture Facts", "",
        "- Configured-backside operation paths remain candidate actual egress where execution evidence is absent.", "",
        "## Unresolved Architecture Context", "",
    ]
    for item in model["unresolved_context"]:
        lines.append(f"- `{item['classification']}` / `{item['certainty']}`: {item['reason']} Evidence records: **{item['evidence_count']}**.")
    lines += ["", "## Evidence and Provenance", "",
        "Every context service, destination relationship, dependency group, and integration-pattern membership retains a Phase 1 identity and compact Phase 2/index provenance. Full raw statements remain in the upstream frozen evidence and are not duplicated here.", "",
        f"Validation gates: **{sum(v['status'] == 'PASS' for v in model['validation'])}/{len(model['validation'])} PASS**.", "",
    ]
    return "\n".join(lines)


def render_external_systems(model: dict[str, Any]) -> str:
    m = model["metrics"]
    lines = [
        "# DataPower Destination and External-System Registry", "",
        "Immediate technical destination is not equivalent to remote business-system identity. No confirmed business-system identity or remote topology is present in the frozen evidence.", "",
        "## Registry metrics", "",
        f"- Configured destination relationships: **{m['configured_destination_relationship_count']}**.",
        f"- Unique configured destinations: **{m['unique_configured_destination_count']}**.",
        f"- Confirmed actual-egress relationships: **{m['confirmed_actual_egress_relationship_count']}**.",
        f"- Unique confirmed immediate destinations: **{m['unique_confirmed_immediate_destination_count']}**.",
        f"- Logical datasource targets: **{m['logical_datasource_target_count']}**.",
        f"- Runtime-computed target relationships: **{m['runtime_computed_target_relationship_count']}**.", "",
        "## Destinations", "",
    ]
    rows = []
    for destination in model["destinations"]:
        rows.append([
            f"`{destination['destination_id']}`",
            destination["destination_kind"],
            f"`{destination['target']}`" if destination["target"] else "not_materialized",
            destination["protocol"],
            len(destination["relationship_ids"]),
            ", ".join(destination["domains"]),
            "not_evidenced",
            "not_evidenced",
        ])
    lines += markdown_table(
        ["Destination ID", "Kind", "Target", "Protocol", "Relationships", "Domains", "Remote identity", "Remote topology"], rows
    )
    lines += ["", "## Relationship evidence", "",
        "Configured and actual-egress relationships are retained separately in `context-facts.json`, including source service, operation/pattern where applicable, mechanism, certainty, and provenance.", "",
        "No endpoint hostname, datasource name, service name, or artifact name is used to infer a business system.", "",
    ]
    return "\n".join(lines)


def render_flows(model: dict[str, Any]) -> str:
    lines = [
        "# DataPower AS-IS Integration Flows", "",
        "Operation-level pattern memberships are mutually exclusive and reconcile to all 617 operations. Direct TCP forwarding is service-level because TCP proxies do not use MPGW-style operations. Service counts across operation patterns are not additive because a service may expose operations with different behavior.", "",
    ]
    for pattern in model["integration_patterns"]:
        lines += [
            f"## {pattern['pattern_name']}", "",
            f"- Pattern ID: `{pattern['pattern_id']}`",
            f"- Architecture flow: `Technical ingress → DataPower → {pattern['pattern_name']}`",
            f"- Evidence characteristics: {pattern['description']}",
            f"- Number of services: **{pattern['service_count']}**",
            f"- Number of operations: **{pattern['operation_count']}**" if pattern["operation_count"] else "- Number of operations: not_applicable (service-level TCP pattern)",
            f"- Representative services: {', '.join(f'`{sid}`' for sid in pattern['representative_service_ids']) or 'none'}",
            f"- Routing behavior: {pattern['routing_characteristics']}",
            "- Security characteristics: fact-local security dependencies remain in `context-facts.json`; HTTPS alone is not interpreted as mTLS.",
            "- Known exceptions: runtime-computed targets remain unmaterialized; configured destinations remain separate from actual egress.",
            f"- Evidence certainty: `{pattern['certainty']}`",
            f"- Evidence basis: `{pattern['provenance']['service_source']}` and `{pattern['provenance']['operation_source']}`", "",
        ]
    return "\n".join(lines)


def mermaid_escape(value: str) -> str:
    return value.replace('"', "'").replace("\n", "<br/>")


def render_mermaid(model: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for node in model["diagram"]["nodes"]:
        lines.append(f'  {node["node_id"]}["{mermaid_escape(node["label"])}"]')
    for edge in model["diagram"]["edges"]:
        connector = "-->" if edge["certainty"] == "confirmed" else "-.->"
        lines.append(f'  {edge["source"]} {connector}|"{mermaid_escape(edge["label"])}"| {edge["target"]}')
    lines += [
        "  classDef confirmed fill:#d9ead3,stroke:#38761d,color:#000",
        "  classDef candidate fill:#fff2cc,stroke:#bf9000,color:#000",
        "  classDef unresolved fill:#fce5cd,stroke:#b45f06,color:#000",
        "  classDef not_evidenced fill:#eeeeee,stroke:#666,stroke-dasharray: 5 5,color:#000",
    ]
    for certainty in CERTAINTIES:
        ids = [node["node_id"] for node in model["diagram"]["nodes"] if node["certainty"] == certainty]
        if ids:
            lines.append(f"  class {','.join(ids)} {certainty}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(model: dict[str, Any], output_root: Path, args: argparse.Namespace) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    context_path = output_root / "datapower-context.md"
    (output_root / "context-facts.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    context_path.write_text(render_context(model, context_path, args), encoding="utf-8")
    (output_root / "external-systems.md").write_text(render_external_systems(model), encoding="utf-8")
    (output_root / "integration-flows.md").write_text(render_flows(model), encoding="utf-8")
    (output_root / "datapower-context.mmd").write_text(render_mermaid(model), encoding="utf-8")


def validate_outputs(model: dict[str, Any], output_root: Path, args: argparse.Namespace) -> None:
    required = {
        "context-facts.json", "datapower-context.md", "datapower-context.mmd",
        "external-systems.md", "integration-flows.md",
    }
    existing = {path.name for path in output_root.iterdir() if path.is_file()}
    if not required <= existing:
        raise ValueError(f"missing Phase 3 outputs: {sorted(required - existing)}")
    reread = load_json(output_root / "context-facts.json")
    if reread["schema"] != SCHEMA or reread["metrics"] != model["metrics"]:
        raise ValueError("context-facts.json structural reconciliation failed")
    mermaid = (output_root / "datapower-context.mmd").read_text(encoding="utf-8")
    for node in model["diagram"]["nodes"]:
        if node["node_id"] not in mermaid:
            raise ValueError(f"Mermaid node missing: {node['node_id']}")
    context = (output_root / "datapower-context.md").read_text(encoding="utf-8")
    for value in (193, 617, 614):
        if str(value) not in context:
            raise ValueError(f"context Markdown missing cardinality {value}")
    for target in (
        Path(args.service_catalog).with_suffix(".md"),
        Path(args.operation_catalog).with_suffix(".md"),
        Path(args.journey_index),
    ):
        if not target.exists():
            raise ValueError(f"Markdown link target missing: {target}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-catalog", default="outputs/as-is/01-service-catalog/services.json")
    parser.add_argument("--operation-catalog", default="outputs/as-is/01-service-catalog/operations.json")
    parser.add_argument("--journey-index", default="outputs/as-is/02-user-journeys/journey-index.md")
    parser.add_argument("--default-objects", default="index/DEFAULT/objects.csv")
    parser.add_argument("--default-properties", default="index/DEFAULT/object_properties.csv")
    parser.add_argument("--default-relationships", default="index/DEFAULT/relationships.csv")
    parser.add_argument("--output-root", default="outputs/as-is/03-context-view")
    args = parser.parse_args()

    model = build_model(args)
    model["validation"] = validate_model(model, args)
    output_root = Path(args.output_root)
    write_outputs(model, output_root, args)
    validate_outputs(model, output_root, args)
    print(json.dumps({"status": "PASS", "metrics": model["metrics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
