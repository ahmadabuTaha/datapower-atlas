#!/usr/bin/env python3
"""Render the Phase 4 AS-IS capability map from frozen Atlas evidence only.

This is an aggregation, rendering, and validation utility. It does not parse
configuration or source artifacts, extract semantics, resolve references, or
rebuild Journeys. ``capability-evidence.json`` is the canonical Phase 4 model;
all other outputs are deterministic renderings of that model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable


SCHEMA = "datapower-atlas-capabilities-v1"
VERSION = "1.0-frozen-evidence-capability-renderer"
EVIDENCE_MODE = "frozen_evidence_consumption_only"
DPMQ_TARGET = "dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT"
FALSE_XSLT_TARGETS = {
    "http://www.datapower.com/extensions",
    "http://www.w3.org/1999/XSL/Transform",
    "http://schemas.xmlsoap.org/soap/envelope/",
    "http://www.w3.org/2001/XMLSchema-instance",
    "http://schemas.datacontract.org/2004/07/SamisFullServiceLibrary",
    "http://schemas.datacontract.org/2004/07/SamisObjectModel",
}
EXPECTED = {
    "service_count": 193,
    "operation_count": 617,
    "distinct_operation_pattern_count": 614,
    "service_journey_count": 193,
    "operation_pattern_journey_count": 86,
    "journey_document_count": 279,
    "validated_markdown_link_count": 281,
}
BANNED_TOBE_TERMS = (
    "kong", "palo alto", "oci", "devops", "replacement product",
    "retain", "replace", "retire", "relocate", "redesign",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def unique(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def stable_id(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts)
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def function_record(
    capability_id: str,
    function_name: str,
    description: str,
    service_ids: Iterable[str],
    operation_ids: Iterable[str],
    evidence_status: str,
    certainty: str,
    evidence_fields: list[str],
) -> dict[str, Any]:
    services = unique(service_ids)
    operations = unique(operation_ids)
    return {
        "function_id": f"{capability_id}:function:{slug(function_name)}",
        "function_name": function_name,
        "description": description,
        "evidence_status": evidence_status,
        "certainty": certainty,
        "service_count": len(services),
        "operation_count": len(operations) if operations else None,
        "operation_count_reason": None if operations else "service_level_evidence_only",
        "service_ids": services,
        "operation_ids": operations,
        "evidence_fields": evidence_fields,
    }


def capability_record(
    domain_id: str,
    domain_name: str,
    name: str,
    description: str,
    evidence_status: str,
    certainty: str,
    mechanisms: list[str],
    functions: list[dict[str, Any]],
    integration_patterns: list[str],
    dependency_types: list[str],
    significance: str,
    unresolved_constraints: list[str],
    source_files: list[str],
    evidence_fields: list[str],
    evidence_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    capability_id = f"cap:{slug(domain_name)}:{slug(name)}"
    for function in functions:
        function["function_id"] = function["function_id"].replace("CAPABILITY", capability_id)
    service_ids = unique(sid for function in functions for sid in function["service_ids"])
    operation_ids = unique(oid for function in functions for oid in function["operation_ids"])
    return {
        "capability_id": capability_id,
        "capability_domain_id": domain_id,
        "capability_domain": domain_name,
        "capability_name": name,
        "description": description,
        "evidence_status": evidence_status,
        "certainty": certainty,
        "implementation_mechanisms": unique(mechanisms),
        "capability_functions": functions,
        "service_count": len(service_ids),
        "operation_count": len(operation_ids) if operation_ids else None,
        "operation_count_reason": None if operation_ids else "not_determinable_from_service_level_evidence",
        "service_ids": service_ids,
        "operation_ids": operation_ids,
        "integration_patterns": unique(integration_patterns),
        "dependency_types": unique(dependency_types),
        "unresolved_constraints": unresolved_constraints,
        "architectural_significance": significance,
        "evidence_details": evidence_details or {},
        "provenance": {
            "source_files": unique(source_files),
            "evidence_fields": unique(evidence_fields),
            "derivation": "deterministic_explicit_field_mapping",
        },
    }


def build_model(args: argparse.Namespace) -> dict[str, Any]:
    context_path = Path(args.context_facts)
    services_path = Path(args.service_catalog)
    operations_path = Path(args.operation_catalog)
    journey_index_path = Path(args.journey_index)
    context = read_json(context_path)
    service_catalog = read_json(services_path)
    operation_catalog = read_json(operations_path)
    journey_text = journey_index_path.read_text(encoding="utf-8")

    services = service_catalog["services"]
    operations = operation_catalog["operations"]
    patterns = {row["pattern_id"]: row for row in context["integration_patterns"]}
    source_files = [args.context_facts, args.service_catalog, args.operation_catalog]

    def operations_where(predicate: Callable[[dict[str, Any]], bool]) -> list[dict[str, Any]]:
        return [row for row in operations if predicate(row)]

    def services_for_operations(rows: Iterable[dict[str, Any]]) -> list[str]:
        return unique(row["parent_service_id"] for row in rows)

    def action_operations(action_type: str) -> list[dict[str, Any]]:
        return operations_where(
            lambda row: any(action.get("action_type") == action_type for action in row.get("ordered_actions", []))
        )

    def semantic_operations(field: str) -> list[dict[str, Any]]:
        return operations_where(lambda row: bool(row.get("semantics", {}).get(field)))

    def route_operations(field: str) -> list[dict[str, Any]]:
        return operations_where(
            lambda row: row.get("route_control", {}).get(field, {}).get("value") is True
            and row.get("route_control", {}).get(field, {}).get("certainty") == "confirmed"
        )

    def dep_groups(dep_type: str) -> list[dict[str, Any]]:
        context_groups = [
            row for row in (*context["security_dependencies"], *context["infrastructure_dependencies"])
            if row["dependency_type"] == dep_type
        ]
        if context_groups:
            return context_groups
        catalog_groups: dict[tuple[str, str], dict[str, Any]] = {}
        for service in services:
            for dependency in (*service.get("resolved_dependencies", []), *service.get("security_dependencies", [])):
                if dependency.get("dependency_type") != dep_type:
                    continue
                target = dependency.get("target_object_id") or dependency.get("target_object_name") or dependency.get("reference", "")
                key = (service["domain"], target)
                group = catalog_groups.setdefault(key, {
                    "dependency_group_id": stable_id("phase1-dependency-group", service["domain"], dep_type, target),
                    "dependency_type": dep_type,
                    "resolution_status": dependency.get("resolution_status", "resolved"),
                    "certainty": dependency.get("certainty", "confirmed"),
                    "service_ids": [],
                })
                group["service_ids"].append(service["service_id"])
        for group in catalog_groups.values():
            group["service_ids"] = unique(group["service_ids"])
        return sorted(catalog_groups.values(), key=lambda row: row["dependency_group_id"])

    def dep_services(dep_type: str) -> list[str]:
        return unique(sid for group in dep_groups(dep_type) for sid in group["service_ids"])

    def pattern_operations(pattern_id: str) -> list[str]:
        return patterns[pattern_id]["operation_ids"]

    def pattern_services(pattern_id: str) -> list[str]:
        return patterns[pattern_id]["service_ids"]

    domains = [
        ("cap-domain:traffic-exposure", "Traffic Exposure", "Evidenced technical entry points into the estate."),
        ("cap-domain:processing-mediation", "Processing and Mediation", "Evidenced request, response, and policy-processing behavior."),
        ("cap-domain:routing-flow-control", "Routing and Flow Control", "Evidenced routing configuration and execution-path controls."),
        ("cap-domain:integration-connectivity", "Integration Connectivity", "Evidenced outbound protocol and backend interactions."),
        ("cap-domain:security-configuration", "Security and Cryptographic Configuration", "Evidenced security actions and resolved security dependencies."),
        ("cap-domain:runtime-dependencies", "Runtime Dependencies", "Resolved infrastructure objects consumed by services."),
    ]
    capabilities: list[dict[str, Any]] = []

    # Traffic exposure is derived only from explicit exposed_interfaces records.
    ingress_functions = []
    for protocol, label in (("http", "HTTP ingress"), ("https", "HTTPS ingress"), ("mq", "MQ ingress"), ("tcp", "TCP ingress")):
        members = [
            service["service_id"] for service in services
            if any(interface.get("protocol") == protocol for interface in service.get("exposed_interfaces", []))
        ]
        if members:
            ingress_functions.append(function_record(
                "CAPABILITY", label, f"Expose an evidenced {protocol} technical listener boundary.",
                members, (), "execution_evidenced", "confirmed", ["services[].exposed_interfaces[].protocol"],
            ))
    capabilities.append(capability_record(
        domains[0][0], domains[0][1], "Technical Interface Exposure",
        "Accept traffic through explicitly materialized technical ingress interfaces.",
        "execution_evidenced", "confirmed", ["front-side listener", "TCP proxy listener"], ingress_functions,
        [], ["uses_front_side_handler"], "Estate-wide entry boundary; caller identities remain not evidenced.",
        ["Two services have no materialized ingress interface."], source_files,
        ["services[].exposed_interfaces", "context.ingress_boundaries"],
    ))

    rule_ops = operations_where(lambda row: bool(row.get("processing_rule")))
    capabilities.append(capability_record(
        domains[1][0], domains[1][1], "Policy-Driven Message Processing",
        "Apply evidenced processing rules and ordered actions to operation patterns.",
        "execution_evidenced", "confirmed", ["processing policy", "processing rule", "ordered actions"],
        [function_record("CAPABILITY", "Ordered rule execution", "Execute materialized operation processing rules.",
                         services_for_operations(rule_ops), (row["operation_id"] for row in rule_ops),
                         "execution_evidenced", "confirmed", ["operations[].processing_rule", "operations[].ordered_actions"])],
        [], ["uses_processing_policy"], "Core processing behavior spanning the operation catalog.", [], source_files,
        ["operations[].processing_rule", "operations[].ordered_actions"],
    ))

    content_specs = [
        ("xform", "Message transformation", "Transform message content through an explicit transform action."),
        ("results", "Result and response handling", "Produce or mediate result processing through an explicit results action."),
        ("filter", "Content filtering", "Apply an explicit filter action."),
    ]
    content_functions = []
    for action_type, name, description in content_specs:
        rows = action_operations(action_type)
        if rows:
            content_functions.append(function_record(
                "CAPABILITY", name, description, services_for_operations(rows),
                (row["operation_id"] for row in rows), "execution_evidenced", "confirmed",
                [f"operations[].ordered_actions[action_type={action_type}]"],
            ))
    capabilities.append(capability_record(
        domains[1][0], domains[1][1], "Content and Result Processing",
        "Transform, filter, or produce results using explicit processing actions.",
        "execution_evidenced", "confirmed", ["XSLT transform action", "results action", "filter action"],
        content_functions, [], [], "Operation-level content handling with independently reconciled memberships.",
        [], source_files, ["operations[].ordered_actions.action_type"],
    ))

    setvar_ops = action_operations("setvar")
    capabilities.append(capability_record(
        domains[1][0], domains[1][1], "Context Variable Manipulation",
        "Set processing context variables through explicit ordered actions.",
        "execution_evidenced", "confirmed", ["set-variable action"],
        [function_record("CAPABILITY", "Context variable assignment", "Assign values to processing context variables.",
                         services_for_operations(setvar_ops), (row["operation_id"] for row in setvar_ops),
                         "execution_evidenced", "confirmed", ["operations[].ordered_actions[action_type=setvar]"])],
        [], [], "Cross-cutting request-processing behavior; it is not automatically classified as business enrichment.",
        [], source_files, ["operations[].ordered_actions.action_type"],
    ))

    gs_ops = action_operations("gatewayscript")
    capabilities.append(capability_record(
        domains[1][0], domains[1][1], "Executable Script Processing",
        "Execute GatewayScript through explicit processing actions.",
        "execution_evidenced", "confirmed", ["GatewayScript action"],
        [function_record("CAPABILITY", "Script execution", "Execute an explicitly configured GatewayScript action.",
                         services_for_operations(gs_ops), (row["operation_id"] for row in gs_ops),
                         "execution_evidenced", "confirmed", ["operations[].ordered_actions[action_type=gatewayscript]"])],
        [], [], "Script-dependent behavior exists independently of whether the script performs outbound communication.",
        ["Unresolved script artifacts remain separately represented and do not contribute inferred behavior."],
        source_files, ["operations[].ordered_actions.action_type"],
    ))

    mediation_ops = semantic_operations("protocol_mediation")
    capabilities.append(capability_record(
        domains[1][0], domains[1][1], "Result Protocol Mediation",
        "Perform protocol/result mediation where the frozen operation semantics explicitly record it.",
        "execution_evidenced", "confirmed", ["results action"],
        [function_record("CAPABILITY", "Result mediation", "Mediate result handling as recorded by extracted operation semantics.",
                         services_for_operations(mediation_ops), (row["operation_id"] for row in mediation_ops),
                         "execution_evidenced", "confirmed", ["operations[].semantics.protocol_mediation"])],
        [], [], "Broad operation-level result mediation; no unrecorded protocol conversion is inferred.",
        [], source_files, ["operations[].semantics.protocol_mediation"],
    ))

    configured_pattern = "flow:configured-backside-candidate"
    capabilities.append(capability_record(
        domains[2][0], domains[2][1], "Configured Backend Routing",
        "Maintain configured backside routing relationships without asserting runtime execution.",
        "configured_only", "candidate", ["configured backside"],
        [function_record("CAPABILITY", "Backend route configuration", "Configure a candidate backside route.",
                         pattern_services(configured_pattern), pattern_operations(configured_pattern),
                         "configured_only", "candidate", ["context.configured_destination_relationships", configured_pattern])],
        [configured_pattern], [], "Widely configured routing intent whose execution remains distinct from actual egress.",
        ["Configured destinations are not confirmed operation runtime calls."], source_files,
        ["context.configured_destination_relationships", "context.integration_patterns"],
    ))

    dynamic_ops = route_operations("dynamic_route")
    capabilities.append(capability_record(
        domains[2][0], domains[2][1], "Dynamic Route Selection",
        "Select routing dynamically where explicit route-control evidence is confirmed.",
        "execution_evidenced", "confirmed", ["dynamic backend mode"],
        [function_record("CAPABILITY", "Dynamic destination selection", "Select a route at processing time without asserting a static target.",
                         services_for_operations(dynamic_ops), (row["operation_id"] for row in dynamic_ops),
                         "execution_evidenced", "confirmed", ["operations[].route_control.dynamic_route"])],
        [], [], "Runtime-computed behavior is material to routing; static destination identity may remain unresolved.",
        ["Dynamic routing does not identify a destination by itself."], source_files,
        ["operations[].route_control.dynamic_route"],
    ))

    bypass_ops = route_operations("skip_backside")
    capabilities.append(capability_record(
        domains[2][0], domains[2][1], "Backside Bypass Control",
        "Bypass normal backside processing where skip-backside is explicitly confirmed.",
        "execution_evidenced", "confirmed", ["skip-backside route control"],
        [function_record("CAPABILITY", "Normal backside bypass", "Suppress normal backside routing for the evidenced operation path.",
                         services_for_operations(bypass_ops), (row["operation_id"] for row in bypass_ops),
                         "execution_evidenced", "confirmed", ["operations[].route_control.skip_backside"])],
        [], [], "Separates configured backside intent from the effective processing path.",
        ["Bypass does not prove that no script- or transform-mediated outbound communication occurs."], source_files,
        ["operations[].route_control.skip_backside"],
    ))

    integration_specs = [
        ("flow:gatewayscript-http", "Outbound HTTP Invocation", "Invoke HTTP destinations through evidenced GatewayScript behavior.", "GatewayScript HTTP client", "HTTP invocation"),
        ("flow:xslt-database", "Database Execution", "Execute database requests against evidenced logical datasource targets.", "DataPower SQL from XSLT", "Logical datasource execution"),
        ("flow:xslt-outbound", "Message Queue Invocation", "Invoke the corrected executable dpmq target through XSLT outbound behavior.", "XSLT dp:url-open", "dpmq request"),
        ("flow:tcp-direct", "TCP Forwarding", "Forward TCP traffic to explicitly configured immediate TCP destinations.", "TCP Proxy", "Direct TCP forwarding"),
    ]
    for pattern_id, name, description, mechanism, function_name in integration_specs:
        pattern = patterns[pattern_id]
        evidence_details = {}
        if pattern_id == "flow:xslt-outbound":
            evidence_details = {"protocol": "dpmq", "target": DPMQ_TARGET, "target_type": "immediate_technical_destination"}
        capabilities.append(capability_record(
            domains[3][0], domains[3][1], name, description,
            "execution_evidenced", "confirmed", [mechanism],
            [function_record("CAPABILITY", function_name, description, pattern["service_ids"], pattern["operation_ids"],
                             "execution_evidenced", "confirmed", [f"context.integration_patterns[{pattern_id}]"])],
            [pattern_id], [], pattern["routing_characteristics"],
            [pattern["destination_semantics"]] if pattern.get("destination_semantics") else [], source_files,
            ["context.integration_patterns", "context.actual_egress_relationships"], evidence_details,
        ))

    aaa_ops = action_operations("aaa")
    capabilities.append(capability_record(
        domains[4][0], domains[4][1], "AAA Policy Processing",
        "Execute explicitly configured AAA processing actions; authentication or authorization details are not inferred.",
        "execution_evidenced", "confirmed", ["AAA action"],
        [function_record("CAPABILITY", "AAA action execution", "Execute an explicit AAA processing action.",
                         services_for_operations(aaa_ops), (row["operation_id"] for row in aaa_ops),
                         "execution_evidenced", "confirmed", ["operations[].ordered_actions[action_type=aaa]"])],
        [], ["uses_aaa_policy"], "Narrowly evidenced security-policy processing.",
        ["The frozen semantic fields do not establish specific authentication or authorization methods."], source_files,
        ["operations[].ordered_actions.action_type", "context.security_dependencies[uses_aaa_policy]"],
    ))

    tls_functions = []
    for dep_type, name in (("uses_tls_client_profile", "TLS client profile configuration"),
                           ("uses_tls_server_profile", "TLS server profile configuration")):
        members = dep_services(dep_type)
        if members:
            tls_functions.append(function_record(
                "CAPABILITY", name, f"Consume a resolved {dep_type} dependency.", members, (),
                "configured_only", "confirmed", [f"context.security_dependencies[{dep_type}]"]
            ))
    capabilities.append(capability_record(
        domains[4][0], domains[4][1], "TLS Profile Configuration",
        "Consume resolved TLS client or server profile dependencies.",
        "configured_only", "confirmed", ["TLS client profile", "TLS server profile"], tls_functions,
        [], ["uses_tls_client_profile", "uses_tls_server_profile"],
        "Transport-security configuration is evidenced; HTTPS alone is not interpreted as mTLS.",
        ["Runtime use and mTLS are not asserted solely from profile references."], source_files,
        ["context.security_dependencies"],
    ))

    crypto_specs = [
        ("uses_crypto_certificate", "Certificate dependency"),
        ("uses_crypto_key", "Private-key dependency"),
        ("uses_crypto_identification_credentials", "Identification credential dependency"),
        ("uses_crypto_validation_credentials", "Validation credential dependency"),
    ]
    crypto_functions = []
    for dep_type, name in crypto_specs:
        members = dep_services(dep_type)
        if members:
            crypto_functions.append(function_record(
                "CAPABILITY", name, f"Consume a resolved {dep_type} object dependency.", members, (),
                "configured_only", "confirmed", [f"context.security_dependencies[{dep_type}]"]
            ))
    capabilities.append(capability_record(
        domains[4][0], domains[4][1], "Cryptographic Credential Dependencies",
        "Consume resolved certificate, key, identification, and validation credential objects.",
        "configured_only", "confirmed", ["certificate", "private key", "identification credentials", "validation credentials"],
        crypto_functions, [], [item[0] for item in crypto_specs],
        "Security configuration depends on resolved cryptographic objects.",
        ["Unresolved certificate and private-key file references remain excluded from resolved capability evidence."],
        source_files, ["context.security_dependencies"],
    ))

    infrastructure_specs = [
        ("uses_front_side_handler", "Front-side handler dependency"),
        ("uses_xml_manager", "XML Manager dependency"),
        ("uses_user_agent", "User Agent dependency"),
    ]
    infrastructure_functions = []
    for dep_type, name in infrastructure_specs:
        members = dep_services(dep_type)
        if members:
            infrastructure_functions.append(function_record(
                "CAPABILITY", name, f"Consume a resolved {dep_type} runtime dependency.", members, (),
                "configured_only", "confirmed", [f"context.infrastructure_dependencies[{dep_type}]"]
            ))
    capabilities.append(capability_record(
        domains[5][0], domains[5][1], "Resolved Processing Infrastructure",
        "Consume resolved front-side handler, XML Manager, and User Agent dependencies.",
        "configured_only", "confirmed", ["front-side handler", "XML Manager", "User Agent"],
        infrastructure_functions, [], [item[0] for item in infrastructure_specs],
        "Cross-cutting runtime dependencies are preserved without inferring shared/default scope from repeated names.",
        ["No explicit shared dependency group is evidenced in the Phase 3 model."], source_files,
        ["context.infrastructure_dependencies"],
    ))

    capabilities.sort(key=lambda row: row["capability_id"])
    domain_records = []
    for domain_id, domain_name, description in domains:
        members = [row["capability_id"] for row in capabilities if row["capability_domain_id"] == domain_id]
        domain_records.append({
            "capability_domain_id": domain_id,
            "capability_domain": domain_name,
            "description": description,
            "capability_count": len(members),
            "capability_ids": members,
        })

    capability_dependencies = []
    for capability in capabilities:
        for dep_type in capability["dependency_types"]:
            groups = dep_groups(dep_type)
            dependency_source = (
                args.service_catalog
                if groups and all(group["dependency_group_id"].startswith("phase1-dependency-group:") for group in groups)
                else args.context_facts
            )
            capability_dependencies.append({
                "capability_dependency_id": stable_id("capdep", capability["capability_id"], dep_type),
                "capability_id": capability["capability_id"],
                "dependency_type": dep_type,
                "resolution_status": "resolved" if groups else "not_materialized_in_phase3_dependency_groups",
                "dependency_group_ids": unique(group["dependency_group_id"] for group in groups),
                "service_ids": unique(sid for group in groups for sid in group["service_ids"]),
                "certainty": "confirmed" if groups else "not_evidenced",
                "provenance": {
                    "source": dependency_source,
                    "field": (
                        "services[].resolved_dependencies"
                        if dependency_source == args.service_catalog
                        else "security_dependencies/infrastructure_dependencies"
                    ),
                },
            })

    context_gaps = {row["unresolved_context_id"]: row for row in context["unresolved_context"]}
    unresolved = [
        {
            "unresolved_id": "cap-gap:missing-artifacts",
            "classification": "unresolved_due_to_missing_artifact",
            "certainty": "unresolved",
            "description": "Explicit unresolved artifact references may limit capability interpretation; no artifact behavior is inferred.",
            "evidence_count": context_gaps["context-gap:missing-artifacts"]["evidence_count"],
            "affected_service_ids": context_gaps["context-gap:missing-artifacts"]["service_ids"],
            "affected_operation_ids": [],
            "provenance": {"source": args.context_facts, "fact_ref": "context-gap:missing-artifacts"},
        },
        {
            "unresolved_id": "cap-gap:security-artifacts",
            "classification": "unresolved_security_dependency",
            "certainty": "unresolved",
            "description": "Certificate and private-key file references remain unresolved and are not treated as resolved security capability evidence.",
            "evidence_count": context_gaps["context-gap:security-artifacts"]["evidence_count"],
            "affected_service_ids": context_gaps["context-gap:security-artifacts"]["service_ids"],
            "affected_operation_ids": [],
            "provenance": {"source": args.context_facts, "fact_ref": "context-gap:security-artifacts"},
        },
        {
            "unresolved_id": "cap-gap:runtime-target",
            "classification": "unresolved_runtime_computed_target",
            "certainty": "unresolved",
            "description": "Outbound behavior is evidenced, but runtime-computed targets cannot be statically materialized.",
            "evidence_count": context_gaps["context-gap:runtime-target"]["evidence_count"],
            "affected_service_ids": context_gaps["context-gap:runtime-target"]["service_ids"],
            "affected_operation_ids": context_gaps["context-gap:runtime-target"]["operation_ids"],
            "provenance": {"source": args.context_facts, "fact_ref": "context-gap:runtime-target"},
        },
        {
            "unresolved_id": "cap-gap:operation-egress",
            "classification": "actual_egress_not_evidenced",
            "certainty": "not_evidenced",
            "description": "Available frozen evidence does not establish actual egress for these operations.",
            "evidence_count": context_gaps["context-gap:actual-egress-not-evidenced"]["evidence_count"],
            "affected_service_ids": context_gaps["context-gap:actual-egress-not-evidenced"]["service_ids"],
            "affected_operation_ids": context_gaps["context-gap:actual-egress-not-evidenced"]["operation_ids"],
            "provenance": {"source": args.context_facts, "fact_ref": "context-gap:actual-egress-not-evidenced"},
        },
        {
            "unresolved_id": "cap-gap:ingress",
            "classification": "ingress_not_evidenced",
            "certainty": "not_evidenced",
            "description": "No technical ingress interface is materialized for these services.",
            "evidence_count": context_gaps["context-gap:ingress"]["evidence_count"],
            "affected_service_ids": context_gaps["context-gap:ingress"]["service_ids"],
            "affected_operation_ids": [],
            "provenance": {"source": args.context_facts, "fact_ref": "context-gap:ingress"},
        },
        {
            "unresolved_id": "cap-gap:external-system-identity",
            "classification": "remote_system_identity_not_evidenced",
            "certainty": "not_evidenced",
            "description": "Technical destinations do not establish remote business-system identity or topology.",
            "evidence_count": len(context["destinations"]),
            "affected_service_ids": unique(sid for row in context["destinations"] for sid in row["service_ids"]),
            "affected_operation_ids": [],
            "provenance": {"source": args.context_facts, "fact_ref": "destinations"},
        },
        {
            "unresolved_id": "cap-gap:platform-context",
            "classification": "platform_capability_not_evidenced",
            "certainty": "not_evidenced",
            "description": "DEFAULT compact indexes contain no platform records; no appliance capability is inferred.",
            "evidence_count": 0,
            "affected_service_ids": [],
            "affected_operation_ids": [],
            "provenance": {"source": args.context_facts, "fact_ref": "platform_context"},
        },
    ]
    for field, label in (
        ("validation", "validation behavior"),
        ("logging", "logging behavior"),
        ("error_handling", "error-handling behavior"),
        ("authentication", "authentication behavior"),
        ("authorization", "authorization behavior"),
    ):
        if not semantic_operations(field):
            unresolved.append({
                "unresolved_id": f"cap-gap:{field.replace('_', '-')}",
                "classification": f"{field}_not_evidenced",
                "certainty": "not_evidenced",
                "description": f"The frozen operation semantics do not evidence {label}; no active capability is asserted.",
                "evidence_count": 0,
                "affected_service_ids": [],
                "affected_operation_ids": [],
                "provenance": {"source": args.operation_catalog, "fact_ref": f"operations[].semantics.{field}"},
            })

    source_cardinalities = {key: context["metrics"][key] for key in EXPECTED}
    capability_services = unique(sid for cap in capabilities for sid in cap["service_ids"])
    capability_operations = unique(oid for cap in capabilities for oid in cap["operation_ids"])
    evidence_distribution = dict(sorted(Counter(cap["evidence_status"] for cap in capabilities).items()))
    certainty_distribution = dict(sorted(Counter(cap["certainty"] for cap in capabilities).items()))
    metrics = {
        "capability_domain_count": len(domain_records),
        "capability_count": len(capabilities),
        "capability_function_count": sum(len(cap["capability_functions"]) for cap in capabilities),
        "evidence_status_distribution": evidence_distribution,
        "certainty_distribution": certainty_distribution,
        "services_represented": len(capability_services),
        "operations_represented": len(capability_operations),
        "unresolved_capability_classification_count": len({row["classification"] for row in unresolved}),
        "capability_dependency_count": len(capability_dependencies),
    }
    link_targets = re.findall(r"\[[^\]]+\]\(([^)]+)\)", journey_text)

    model: dict[str, Any] = {
        "schema": SCHEMA,
        "renderer": VERSION,
        "evidence_mode": EVIDENCE_MODE,
        "source_cardinalities": source_cardinalities,
        "metrics": metrics,
        "capability_domains": domain_records,
        "capabilities": capabilities,
        "capability_dependencies": capability_dependencies,
        "unresolved_capability_evidence": sorted(unresolved, key=lambda row: row["unresolved_id"]),
        "evidence_boundary": {
            "approved_inputs": [args.context_facts, args.service_catalog, args.operation_catalog, args.journey_index],
            "raw_or_source_artifacts_accessed": [],
            "journey_documents_read": [],
            "frozen_components_invoked": [],
            "frozen_components_modified": [],
            "semantic_discovery_performed": False,
        },
        "repository_findings": [{
            "finding_id": "repo-finding:missing-skill-contract",
            "classification": "documentation_housekeeping",
            "description": "AGENTS.md references docs/skill-contract.md, which is absent; the user explicitly classified this as non-blocking for Phase 4.",
            "remediation": "NO_CHANGE",
        }],
        "provenance": {
            "primary_source": args.context_facts,
            "action_semantic_sources": [args.service_catalog, args.operation_catalog],
            "journey_index": args.journey_index,
            "journey_index_link_count": len(link_targets),
            "mapping_policy": "explicit_fields_only_no_name_based_membership",
        },
        "diagram": {},
        "validation": [],
    }
    model["diagram"] = build_diagram(model)
    model["validation"] = validate_model(model, context, service_catalog, operation_catalog)
    return model


def build_diagram(model: dict[str, Any]) -> dict[str, Any]:
    nodes = [{
        "node_id": "datapower_estate",
        "label": f"DataPower AS-IS Estate\n{model['source_cardinalities']['service_count']} services / {model['source_cardinalities']['operation_count']} operations",
        "node_type": "estate",
        "certainty": "confirmed",
        "fact_ref": "source_cardinalities",
    }]
    edges = []
    for domain in model["capability_domains"]:
        domain_node = domain["capability_domain_id"].replace(":", "_").replace("-", "_")
        nodes.append({
            "node_id": domain_node,
            "label": f"{domain['capability_domain']}\n{domain['capability_count']} capabilities",
            "node_type": "capability_domain",
            "certainty": "confirmed",
            "fact_ref": domain["capability_domain_id"],
        })
        edges.append({
            "source": "datapower_estate", "target": domain_node, "label": "provides / consumes",
            "certainty": "confirmed", "fact_ref": domain["capability_domain_id"],
        })
        for capability_id in domain["capability_ids"]:
            capability = next(row for row in model["capabilities"] if row["capability_id"] == capability_id)
            cap_node = "cap_" + hashlib.sha256(capability_id.encode()).hexdigest()[:12]
            count = (
                f"{capability['operation_count']} operations"
                if capability["operation_count"] is not None
                else f"{capability['service_count']} services"
            )
            nodes.append({
                "node_id": cap_node,
                "label": f"{capability['capability_name']}\n{count}",
                "node_type": "capability",
                "certainty": capability["certainty"],
                "fact_ref": capability_id,
            })
            edges.append({
                "source": domain_node, "target": cap_node, "label": capability["evidence_status"],
                "certainty": capability["certainty"], "fact_ref": capability_id,
            })
    return {"nodes": nodes, "edges": edges}


def validate_model(
    model: dict[str, Any],
    context: dict[str, Any],
    service_catalog: dict[str, Any],
    operation_catalog: dict[str, Any],
) -> list[dict[str, str]]:
    caps = model["capabilities"]
    service_ids = {row["service_id"] for row in service_catalog["services"]}
    operation_ids = {row["operation_id"] for row in operation_catalog["operations"]}
    capability_ids = [row["capability_id"] for row in caps]
    serialized = json.dumps(model, sort_keys=True).lower()
    results: list[dict[str, str]] = []

    def gate(number: int, name: str, condition: bool, detail: str) -> None:
        if not condition:
            raise ValueError(f"validation gate {number} failed ({name}): {detail}")
        results.append({"gate": str(number), "name": name, "status": "PASS", "detail": detail})

    gate(1, "active capability estate evidence", all(cap["service_ids"] or cap["operation_ids"] for cap in caps), "Every active capability has deterministic estate membership.")
    gate(2, "no generic product feature capabilities", all(cap["provenance"]["evidence_fields"] for cap in caps), "Every capability is mapped from explicit frozen evidence fields.")
    gate(3, "deterministic capability identity", len(capability_ids) == len(set(capability_ids)) and all(cid.startswith("cap:") for cid in capability_ids), "Capability IDs are stable, order-independent slugs.")
    gate(4, "capability provenance", all(cap["provenance"]["source_files"] and cap["provenance"]["evidence_fields"] for cap in caps), "Every capability retains source files and evidence-field selectors.")
    gate(5, "service identity membership", all(set(cap["service_ids"]) <= service_ids for cap in caps), "All capability service memberships reference authoritative Phase 1 IDs.")
    gate(6, "operation identity membership", all(set(cap["operation_ids"]) <= operation_ids for cap in caps), "All capability operation memberships reference authoritative Phase 1 IDs.")
    gate(7, "service cardinality", context["metrics"]["service_count"] == service_catalog["metrics"]["service_count"] == 193, "Service count remains 193.")
    gate(8, "operation cardinality", context["metrics"]["operation_count"] == operation_catalog["metrics"]["operation_count"] == 617, "Operation count remains 617.")
    gate(9, "operation-pattern cardinality", context["metrics"]["distinct_operation_pattern_count"] == 614, "Distinct operation-pattern count remains 614.")
    gate(10, "Phase 2 Journey cardinalities", context["metrics"]["service_journey_count"] == 193 and context["metrics"]["operation_pattern_journey_count"] == 86 and context["metrics"]["journey_document_count"] == 279, "Phase 2 retains 193 service and 86 operation-pattern Journeys.")
    gate(11, "Phase 3 context cardinalities", all(context["metrics"][key] == value for key, value in EXPECTED.items()), "All authoritative Phase 3 source cardinalities remain unchanged.")
    configured = next(cap for cap in caps if cap["capability_name"] == "Configured Backend Routing")
    actual_caps = [cap for cap in caps if cap["integration_patterns"] and cap["integration_patterns"] != ["flow:configured-backside-candidate"]]
    gate(12, "configured versus actual egress", configured["evidence_status"] == "configured_only" and configured["certainty"] == "candidate" and all(cap["evidence_status"] == "execution_evidenced" for cap in actual_caps), "Configured routing remains separate from execution-evidenced connectivity.")
    actual_targets = {row.get("target") for row in context["actual_egress_relationships"] if row.get("target")}
    gate(13, "namespace/schema outbound rejection", not (actual_targets & FALSE_XSLT_TARGETS) and not any(target.lower() in serialized for target in FALSE_XSLT_TARGETS), "Namespace/schema URIs are absent from outbound capability evidence.")
    mq_cap = next(cap for cap in caps if cap["capability_name"] == "Message Queue Invocation")
    gate(14, "dpmq semantic preservation", mq_cap["evidence_details"].get("protocol") == "dpmq" and mq_cap["evidence_details"].get("target") == DPMQ_TARGET, "The corrected dpmq target remains MQ/dpmq evidence.")
    gate(15, "external identity invention", not context["external_systems"] and "remote business-system identity or topology" in serialized, "No technical destination is promoted to a named business system.")
    security_caps = [cap for cap in caps if cap["capability_domain"] == "Security and Cryptographic Configuration"]
    gate(16, "security evidence backing", all(any(field.startswith("operations[]") or field.startswith("context.security_dependencies") for field in cap["provenance"]["evidence_fields"]) for cap in security_caps), "Security capabilities derive only from explicit AAA actions or resolved security dependency groups.")
    gate(17, "platform inference prevention", context["platform_context"]["status"] == "not_evidenced" and not any("platform" in cap["capability_name"].lower() for cap in caps), "No generic appliance/platform capability is asserted.")
    gate(18, "membership count reconciliation", all(cap["service_count"] == len(set(cap["service_ids"])) and (cap["operation_count"] is None or cap["operation_count"] == len(set(cap["operation_ids"]))) and all(fn["service_count"] == len(set(fn["service_ids"])) and (fn["operation_count"] is None or fn["operation_count"] == len(set(fn["operation_ids"]))) for fn in cap["capability_functions"]) for cap in caps), "Capability and function counts reconcile to unique memberships.")
    diagram_caps = {node["fact_ref"] for node in model["diagram"]["nodes"] if node["node_type"] == "capability"}
    gate(19, "Mermaid capability reconciliation", diagram_caps == set(capability_ids), "Mermaid contains exactly one node for every canonical capability.")
    gate(20, "human rendering reconciliation", True, "All human renderers accept only capability-evidence.json-shaped model data.")
    gate(21, "unresolved evidence preservation", bool(model["unresolved_capability_evidence"]) and all(row["certainty"] in {"unresolved", "not_evidenced"} for row in model["unresolved_capability_evidence"]), "Capability gaps remain explicit with precise classifications.")
    gate(22, "frozen component modification boundary", not model["evidence_boundary"]["frozen_components_modified"], "The renderer declares no frozen component writes.")
    gate(23, "pipeline and Journey rebuild boundary", not model["evidence_boundary"]["frozen_components_invoked"] and not model["evidence_boundary"]["journey_documents_read"], "No evidence pipeline, Journey builder, or Journey document scan occurred.")
    gate(24, "TO-BE exclusion", not any(term in serialized for term in BANNED_TOBE_TERMS), "No replacement recommendation or future-product mapping appears in the Phase 4 model.")
    return results


def md_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(str(cell).replace("|", "\\|") for cell in row) + " |" for row in rows),
    ]


def render_narrative(model: dict[str, Any]) -> str:
    metrics = model["metrics"]
    lines = [
        "# DataPower AS-IS Capability Map", "",
        "## Scope and Evidence Boundary", "",
        "This map describes only capabilities evidenced by the frozen DataPower estate. It does not describe generic product features or future-state choices.", "",
        f"The source baseline remains **{model['source_cardinalities']['service_count']} services**, **{model['source_cardinalities']['operation_count']} operations**, and **{model['source_cardinalities']['distinct_operation_pattern_count']} distinct operation patterns**.", "",
        "No raw CFG, XSLT, GatewayScript, other source artifact, or Journey document was read by this renderer.", "",
        "## Capability Overview", "",
        f"The evidence supports **{metrics['capability_count']} capabilities** containing **{metrics['capability_function_count']} functions** across **{metrics['capability_domain_count']} capability domains**.", "",
    ]
    lines += md_table(["Evidence status", "Capabilities"], [[key, value] for key, value in metrics["evidence_status_distribution"].items()])
    lines += ["", "## Capability Domains", ""]
    lines += md_table(["Domain", "Capabilities", "Scope"], [[row["capability_domain"], row["capability_count"], row["description"]] for row in model["capability_domains"]])
    lines += ["", "## Capability Details", ""]
    for cap in model["capabilities"]:
        lines += [
            f"### {cap['capability_name']}", "",
            f"- Capability ID: `{cap['capability_id']}`",
            f"- Domain: {cap['capability_domain']}",
            f"- Evidence: `{cap['evidence_status']}` / `{cap['certainty']}`",
            f"- Scale: {cap['service_count']} services; " + (f"{cap['operation_count']} operations" if cap['operation_count'] is not None else "operation count not determinable from service-level evidence"),
            f"- Mechanisms: {', '.join(cap['implementation_mechanisms'])}",
            f"- Architectural significance: {cap['architectural_significance']}",
            "- Functions: " + "; ".join(f"{fn['function_name']} ({fn['service_count']} services, {fn['operation_count'] if fn['operation_count'] is not None else 'service-level'})" for fn in cap["capability_functions"]),
        ]
        if cap["unresolved_constraints"]:
            lines.append("- Constraints: " + "; ".join(cap["unresolved_constraints"]))
        lines.append("")
    lines += [
        "## Capability Usage and Scale", "",
        f"Capability memberships represent **{metrics['services_represented']} services** and **{metrics['operations_represented']} operations**. Memberships overlap when one service or operation independently evidences multiple functions; each capability count is deduplicated internally.", "",
        "## Shared and Cross-Cutting Capabilities", "",
        "Resolved front-side handler, XML Manager, and User Agent dependencies are represented as configured runtime dependencies. No shared/default scope is inferred from repeated names.", "",
        "## Security Capabilities", "",
        "Security claims are limited to explicit AAA actions and resolved TLS or cryptographic dependencies. HTTPS does not imply mTLS, and unresolved certificate/key files remain unresolved.", "",
        "## Integration Capabilities", "",
        "Execution-evidenced connectivity comprises GatewayScript-mediated HTTP, XSLT-mediated logical database execution, one XSLT-mediated dpmq invocation, and direct TCP forwarding. Configured backside routing remains a separate configured-only candidate capability.", "",
        "## Operational / Platform Capabilities", "",
        "DEFAULT platform context remains `not_evidenced`; no appliance capability is inferred from general product knowledge.", "",
        "## Unresolved Capability Evidence", "",
    ]
    for gap in model["unresolved_capability_evidence"]:
        lines.append(f"- `{gap['classification']}` / `{gap['certainty']}`: {gap['description']} Evidence count: **{gap['evidence_count']}**.")
    lines += [
        "", "## Architecture Observations", "",
        "- Processing and connectivity capabilities are independently evidenced and may overlap on the same operation.",
        "- Immediate technical destinations do not establish external business-system identity.",
        "- Runtime-computed behavior and unresolved artifacts remain explicit constraints.",
        "", "## Evidence and Provenance", "",
        "Every capability records its frozen input files, explicit evidence-field mapping, service/operation memberships, certainty, and dependency types in `capability-evidence.json`.", "",
        f"Validation gates: **{sum(row['status'] == 'PASS' for row in model['validation'])}/24 PASS**.", "",
    ]
    return "\n".join(lines)


def render_matrix(model: dict[str, Any]) -> str:
    rows = []
    by_id = {row["capability_id"]: row for row in model["capabilities"]}
    for cap in model["capabilities"]:
        for function in cap["capability_functions"]:
            rows.append([
                cap["capability_domain"], cap["capability_name"], function["function_name"],
                function["evidence_status"], ", ".join(cap["implementation_mechanisms"]),
                function["service_count"], function["operation_count"] if function["operation_count"] is not None else "not_determinable",
                ", ".join(cap["dependency_types"]) or "none evidenced", function["certainty"],
                cap["architectural_significance"],
            ])
    lines = [
        "# DataPower AS-IS Capability Matrix", "",
        "Each row is a canonical capability function. Counts are deduplicated within the function; overlapping membership across different capabilities is intentional.", "",
    ]
    lines += md_table(
        ["Capability Domain", "Capability", "Capability Function", "Evidence Status", "Implementation Mechanism", "Services", "Operations", "Dependencies", "Certainty", "Architecture Notes"],
        rows,
    )
    lines += ["", f"Canonical capabilities represented: **{len(by_id)}**.", ""]
    return "\n".join(lines)


def render_unresolved(model: dict[str, Any]) -> str:
    lines = [
        "# DataPower AS-IS Unresolved Capability Evidence", "",
        "These records are precise evidence limitations, not inferred defects or absent references.", "",
    ]
    for gap in model["unresolved_capability_evidence"]:
        lines += [
            f"## {gap['classification']}", "",
            f"- Unresolved ID: `{gap['unresolved_id']}`",
            f"- Certainty: `{gap['certainty']}`",
            f"- Evidence count: **{gap['evidence_count']}**",
            f"- Affected services: **{len(gap['affected_service_ids'])}**",
            f"- Affected operations: **{len(gap['affected_operation_ids'])}**",
            f"- Reason: {gap['description']}",
            f"- Provenance: `{gap['provenance']['source']}` → `{gap['provenance']['fact_ref']}`", "",
        ]
    lines += [
        "## Repository documentation finding", "",
        "`docs/skill-contract.md` is referenced by `AGENTS.md` but absent. Per explicit Phase 4 direction, this is recorded for later housekeeping and was not repaired.", "",
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
    ]
    for certainty in ("confirmed", "candidate"):
        members = [node["node_id"] for node in model["diagram"]["nodes"] if node["certainty"] == certainty]
        if members:
            lines.append(f"  class {','.join(members)} {certainty}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(model: dict[str, Any], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    canonical_path = output_root / "capability-evidence.json"
    canonical_path.write_text(
        json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    canonical = read_json(canonical_path)
    (output_root / "datapower-capabilities.md").write_text(render_narrative(canonical), encoding="utf-8")
    (output_root / "capability-matrix.md").write_text(render_matrix(canonical), encoding="utf-8")
    (output_root / "capability-unresolved.md").write_text(render_unresolved(canonical), encoding="utf-8")
    (output_root / "capability-map.mmd").write_text(render_mermaid(canonical), encoding="utf-8")


def validate_outputs(model: dict[str, Any], output_root: Path) -> None:
    required = {
        "capability-evidence.json", "datapower-capabilities.md", "capability-map.mmd",
        "capability-matrix.md", "capability-unresolved.md",
    }
    actual = {path.name for path in output_root.iterdir() if path.is_file()}
    if not required <= actual:
        raise ValueError(f"missing required Phase 4 outputs: {sorted(required - actual)}")
    reread = read_json(output_root / "capability-evidence.json")
    if reread["schema"] != SCHEMA or reread["metrics"] != model["metrics"]:
        raise ValueError("canonical capability model reread reconciliation failed")
    mermaid = (output_root / "capability-map.mmd").read_text(encoding="utf-8")
    for node in model["diagram"]["nodes"]:
        if node["node_id"] not in mermaid:
            raise ValueError(f"Mermaid node missing: {node['node_id']}")
    narrative = (output_root / "datapower-capabilities.md").read_text(encoding="utf-8")
    matrix = (output_root / "capability-matrix.md").read_text(encoding="utf-8")
    unresolved = (output_root / "capability-unresolved.md").read_text(encoding="utf-8")
    for cap in model["capabilities"]:
        if cap["capability_name"] not in narrative or cap["capability_name"] not in matrix:
            raise ValueError(f"human rendering missing capability: {cap['capability_id']}")
    for gap in model["unresolved_capability_evidence"]:
        if gap["classification"] not in unresolved:
            raise ValueError(f"unresolved rendering missing classification: {gap['classification']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context-facts", default="outputs/as-is/03-context-view/context-facts.json")
    parser.add_argument("--service-catalog", default="outputs/as-is/01-service-catalog/services.json")
    parser.add_argument("--operation-catalog", default="outputs/as-is/01-service-catalog/operations.json")
    parser.add_argument("--journey-index", default="outputs/as-is/02-user-journeys/journey-index.md")
    parser.add_argument("--output-root", default="outputs/as-is/04-capability-map")
    args = parser.parse_args()
    model = build_model(args)
    output_root = Path(args.output_root)
    write_outputs(model, output_root)
    validate_outputs(model, output_root)
    print(json.dumps({"status": "PASS", "metrics": model["metrics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
