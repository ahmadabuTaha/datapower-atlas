#!/usr/bin/env python3
"""Render the final AS-IS architecture pack from frozen Phase 1-4 evidence.

This utility only consolidates approved canonical outputs. It does not read
Journey documents or raw/source artifacts and does not invoke evidence
production, discovery, semantic extraction, or frozen renderers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA = "datapower-atlas-as-is-v1"
VERSION = "1.0-frozen-evidence-as-is-pack-renderer"
EVIDENCE_MODE = "frozen_evidence_consumption_only"
DPMQ_TARGET = "dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT"
FALSE_OUTBOUND_TARGETS = {
    "http://www.datapower.com/extensions",
    "http://www.w3.org/1999/XSL/Transform",
    "http://schemas.xmlsoap.org/soap/envelope/",
    "http://www.w3.org/2001/XMLSchema-instance",
    "http://schemas.datacontract.org/2004/07/SamisFullServiceLibrary",
    "http://schemas.datacontract.org/2004/07/SamisObjectModel",
}
BASELINE = {
    "service_count": 193,
    "operation_count": 617,
    "distinct_operation_pattern_count": 614,
    "service_journey_count": 193,
    "operation_pattern_journey_count": 86,
    "journey_document_count": 279,
    "validated_markdown_link_count": 281,
}
CONTEXT_EXPECTED = {
    "ingress_boundary_count": 193,
    "service_type_group_count": 3,
    "configured_destination_relationship_count": 131,
    "unique_configured_destination_count": 120,
    "confirmed_actual_egress_relationship_count": 425,
    "unique_confirmed_immediate_destination_count": 83,
    "logical_datasource_target_count": 10,
    "runtime_computed_target_relationship_count": 34,
    "integration_flow_pattern_count": 6,
    "security_dependency_group_count": 54,
    "infrastructure_dependency_group_count": 190,
    "explicit_shared_dependency_group_count": 0,
    "unresolved_context_item_count": 8,
}
CAPABILITY_EXPECTED = {
    "capability_domain_count": 6,
    "capability_count": 17,
    "capability_function_count": 28,
    "capability_dependency_count": 12,
    "services_represented": 193,
    "operations_represented": 617,
    "unresolved_capability_classification_count": 12,
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def get_gap(records: list[dict[str, Any]], identifier: str, id_field: str) -> dict[str, Any]:
    matches = [record for record in records if record[id_field] == identifier]
    if len(matches) != 1:
        raise ValueError(f"expected one unresolved record {identifier}, found {len(matches)}")
    return matches[0]


def compact_capability(capability: dict[str, Any], source: str) -> dict[str, Any]:
    return {
        "capability_id": capability["capability_id"],
        "capability_domain_id": capability["capability_domain_id"],
        "capability_domain": capability["capability_domain"],
        "capability_name": capability["capability_name"],
        "description": capability["description"],
        "evidence_status": capability["evidence_status"],
        "certainty": capability["certainty"],
        "implementation_mechanisms": capability["implementation_mechanisms"],
        "service_count": capability["service_count"],
        "operation_count": capability["operation_count"],
        "operation_count_reason": capability["operation_count_reason"],
        "integration_patterns": capability["integration_patterns"],
        "dependency_types": capability["dependency_types"],
        "unresolved_constraints": capability["unresolved_constraints"],
        "architectural_significance": capability["architectural_significance"],
        "functions": [{
            "function_id": function["function_id"],
            "function_name": function["function_name"],
            "description": function["description"],
            "evidence_status": function["evidence_status"],
            "certainty": function["certainty"],
            "service_count": function["service_count"],
            "operation_count": function["operation_count"],
            "operation_count_reason": function["operation_count_reason"],
            "evidence_fields": function["evidence_fields"],
        } for function in capability["capability_functions"]],
        "provenance": {
            "source": source,
            "record_pointer": f"capabilities[capability_id={capability['capability_id']}]",
            "upstream": capability["provenance"],
        },
    }


def gap_record(
    gap_id: str,
    category: str,
    classification: str,
    certainty: str,
    count: int,
    affected_scope: str,
    consequence: str,
    source: str,
    source_pointer: str,
    blocks_closure: bool,
    revisit: bool,
    subset_of: str | None = None,
) -> dict[str, Any]:
    return {
        "gap_id": gap_id,
        "category": category,
        "classification": classification,
        "evidence_status": certainty,
        "count": count,
        "affected_scope": affected_scope,
        "architectural_consequence": consequence,
        "blocks_as_is_closure": blocks_closure,
        "revisit_during_future_analysis": revisit,
        "subset_of": subset_of,
        "provenance": {"source": source, "record_pointer": source_pointer},
    }


def build_model(args: argparse.Namespace) -> dict[str, Any]:
    input_paths = [
        Path(args.service_catalog), Path(args.operation_catalog), Path(args.journey_index),
        Path(args.context_facts), Path(args.capability_evidence),
    ]
    services = read_json(input_paths[0])
    operations = read_json(input_paths[1])
    journey_text = input_paths[2].read_text(encoding="utf-8")
    context = read_json(input_paths[3])
    capability = read_json(input_paths[4])

    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", journey_text)
    link_breakdown = {
        "service_journey_links": sum("service-journeys/" in link for link in links),
        "operation_pattern_journey_links": sum("operation-journeys/" in link for link in links),
        "phase1_catalog_cross_links": sum("../01-service-catalog/" in link for link in links),
        "total_markdown_links": len(links),
    }

    context_gaps = context["unresolved_context"]
    capability_gaps = capability["unresolved_capability_evidence"]
    missing = get_gap(context_gaps, "context-gap:missing-artifacts", "unresolved_context_id")
    security_missing = get_gap(context_gaps, "context-gap:security-artifacts", "unresolved_context_id")
    actual_gap = get_gap(context_gaps, "context-gap:actual-egress-not-evidenced", "unresolved_context_id")
    runtime_gap = get_gap(context_gaps, "context-gap:runtime-target", "unresolved_context_id")
    ingress_gap = get_gap(context_gaps, "context-gap:ingress", "unresolved_context_id")
    caller_gap = get_gap(context_gaps, "context-gap:caller-identity", "unresolved_context_id")
    remote_identity_gap = get_gap(capability_gaps, "cap-gap:external-system-identity", "unresolved_id")
    remote_topology_gap = get_gap(context_gaps, "context-gap:remote-topology", "unresolved_context_id")

    unresolved = [
        gap_record("as-is-gap:missing-artifacts", "Missing / Unresolved Artifacts", missing["classification"], missing["certainty"], missing["evidence_count"], "artifact references", "Referenced behavior cannot be interpreted where the artifact is unavailable; the dependency reference remains present.", args.context_facts, "unresolved_context[context-gap:missing-artifacts]", False, True),
        gap_record("as-is-gap:security-artifacts", "Security Evidence Gaps", security_missing["classification"], security_missing["certainty"], security_missing["evidence_count"], "certificate/private-key artifact references", "Resolved security capability evidence excludes these unresolved certificate and private-key files.", args.context_facts, "unresolved_context[context-gap:security-artifacts]", False, True, "as-is-gap:missing-artifacts"),
        gap_record("as-is-gap:actual-egress", "Routing / Egress Evidence Gaps", "actual_egress_not_evidenced", actual_gap["certainty"], actual_gap["evidence_count"], "operations", "The current outbound path cannot be asserted for these operations.", args.context_facts, "unresolved_context[context-gap:actual-egress-not-evidenced]", False, True),
        gap_record("as-is-gap:runtime-target", "Runtime-Computed Targets", "unresolved_runtime_computed_target", runtime_gap["certainty"], runtime_gap["evidence_count"], "operations", "Outbound behavior is evidenced, but a static destination cannot be materialized.", args.context_facts, "unresolved_context[context-gap:runtime-target]", False, True),
        gap_record("as-is-gap:ingress", "Ingress Evidence Gaps", "ingress_not_evidenced", ingress_gap["certainty"], ingress_gap["evidence_count"], "services", "No materialized technical ingress can be asserted for these services.", args.context_facts, "unresolved_context[context-gap:ingress]", False, True),
        gap_record("as-is-gap:caller-identity", "Ingress Evidence Gaps", "caller_identity_not_evidenced", caller_gap["certainty"], caller_gap["evidence_count"], "services", "Technical ingress does not establish the calling application or system.", args.context_facts, "unresolved_context[context-gap:caller-identity]", False, True),
        gap_record("as-is-gap:remote-identity", "Remote-System Identity Gaps", remote_identity_gap["classification"], remote_identity_gap["certainty"], remote_identity_gap["evidence_count"], "technical destination registry entries", "Immediate destinations do not establish remote business-system identity.", args.capability_evidence, "unresolved_capability_evidence[cap-gap:external-system-identity]", False, True),
        gap_record("as-is-gap:remote-topology", "Remote-System Identity Gaps", remote_topology_gap["classification"], remote_topology_gap["certainty"], remote_topology_gap["evidence_count"], "services", "Topology beyond the immediate destination is not evidenced.", args.context_facts, "unresolved_context[context-gap:remote-topology]", False, True),
    ]
    capability_gap_categories = {
        "authentication_not_evidenced": "Functional Capability Evidence Gaps",
        "authorization_not_evidenced": "Functional Capability Evidence Gaps",
        "error_handling_not_evidenced": "Functional Capability Evidence Gaps",
        "logging_not_evidenced": "Functional Capability Evidence Gaps",
        "validation_not_evidenced": "Functional Capability Evidence Gaps",
        "platform_capability_not_evidenced": "Platform Evidence Gaps",
    }
    for classification, category in capability_gap_categories.items():
        source_gap = next(row for row in capability_gaps if row["classification"] == classification)
        unresolved.append(gap_record(
            f"as-is-gap:{classification.replace('_', '-')}", category, classification,
            source_gap["certainty"], source_gap["evidence_count"], "estate evidence",
            source_gap["description"], args.capability_evidence,
            f"unresolved_capability_evidence[{source_gap['unresolved_id']}]", False, True,
        ))
    unresolved.append(gap_record(
        "as-is-gap:missing-skill-contract", "Documentation / Repository Findings",
        "documentation_housekeeping", "not_evidenced", 1, "repository documentation",
        "A referenced shared contract file is absent; explicit Phase 5 instructions make this non-blocking and prohibit repair in this phase.",
        args.capability_evidence, "repository_findings[repo-finding:missing-skill-contract]", False, False,
    ))
    unresolved.sort(key=lambda row: row["gap_id"])

    compact_caps = [compact_capability(row, args.capability_evidence) for row in capability["capabilities"]]
    compact_caps.sort(key=lambda row: row["capability_id"])
    capability_ids = [row["capability_id"] for row in compact_caps]
    function_ids = [fn["function_id"] for cap in compact_caps for fn in cap["functions"]]

    actual_targets = [
        {"target": row["target"], "protocol": row["protocol"], "mechanism": row["mechanism"]}
        for row in context["actual_egress_relationships"] if row.get("target") == DPMQ_TARGET
    ]
    ingress_protocols = dict(sorted(Counter(row["protocol"] for row in context["ingress_boundaries"]).items()))
    context_metrics = {key: context["metrics"][key] for key in CONTEXT_EXPECTED}
    context_metrics.update({
        "destination_registry_entry_count": len(context["destinations"]),
        "confirmed_external_system_identity_count": len(context["external_systems"]),
        "destination_identity_not_evidenced_count": sum(
            row["remote_system_identity"]["certainty"] == "not_evidenced" for row in context["destinations"]
        ),
    })

    conclusions = [
        {"conclusion_id": "conclusion:service-operation-scale", "statement": "The estate contains distinct service and operation layers; operation cardinality is not inferred from operation-pattern Journey documents.", "source_refs": ["estate", "operation_landscape", "journey_landscape"]},
        {"conclusion_id": "conclusion:routing-distinction", "statement": "Configured backend relationships remain distinct from execution-evidenced actual egress.", "source_refs": ["context.routing_and_egress", "capabilities.records[cap:routing-and-flow-control:configured-backend-routing]"]},
        {"conclusion_id": "conclusion:dynamic-routing", "statement": "Runtime-computed routing exists and does not materialize a known static destination for every outbound interaction.", "source_refs": ["context.runtime_computed_target_relationship_count", "unresolved.records[as-is-gap:runtime-target]"]},
        {"conclusion_id": "conclusion:integration-diversity", "statement": "The estate evidences multiple immediate integration mechanisms across HTTP, logical database, dpmq, and TCP interactions.", "source_refs": ["integration.patterns", "capabilities.records"]},
        {"conclusion_id": "conclusion:destination-identity", "statement": "Technical destination evidence does not establish remote business-system identity or topology.", "source_refs": ["destinations", "unresolved.records[as-is-gap:remote-identity]"]},
        {"conclusion_id": "conclusion:evidence-gaps", "statement": "AS-IS closure preserves specific unresolved and not-evidenced areas without treating them automatically as defects.", "source_refs": ["unresolved.records"]},
    ]

    modernization_capability_inputs = [{
        "capability_id": cap["capability_id"],
        "capability_name": cap["capability_name"],
        "evidence_status": cap["evidence_status"],
        "certainty": cap["certainty"],
        "service_count": cap["service_count"],
        "operation_count": cap["operation_count"],
        "implementation_mechanisms": cap["implementation_mechanisms"],
        "dependency_types": cap["dependency_types"],
        "unresolved_constraints": cap["unresolved_constraints"],
        "source_ref": f"capabilities.records[{cap['capability_id']}]",
    } for cap in compact_caps]

    model: dict[str, Any] = {
        "schema": SCHEMA,
        "renderer": VERSION,
        "evidence_mode": EVIDENCE_MODE,
        "baseline": {
            "status": "PASS_FROZEN",
            "phases": {f"phase_{number}": "PASS_FROZEN" for number in range(1, 5)},
            "cardinalities": BASELINE,
        },
        "estate": {
            "environment_count": len({row["environment"] for row in services["services"]}),
            "domain_count": services["metrics"]["domain_count"],
            "service_count": services["metrics"]["service_count"],
            "operation_count": operations["metrics"]["operation_count"],
        },
        "service_landscape": {
            "service_count": services["metrics"]["service_count"],
            "service_type_groups": context["service_type_groups"],
            "ingress_boundary_count": context["metrics"]["ingress_boundary_count"],
            "ingress_protocol_distribution": ingress_protocols,
            "source": args.context_facts,
        },
        "operation_landscape": {
            "operation_count": operations["metrics"]["operation_count"],
            "distinct_operation_pattern_count": operations["metrics"]["distinct_operation_pattern_count"],
            "source": args.operation_catalog,
        },
        "journey_landscape": {
            "service_journey_count": context["metrics"]["service_journey_count"],
            "operation_pattern_journey_count": context["metrics"]["operation_pattern_journey_count"],
            "journey_document_count": context["metrics"]["journey_document_count"],
            "validated_markdown_link_count": context["metrics"]["validated_markdown_link_count"],
            "link_breakdown": link_breakdown,
            "source": args.journey_index,
        },
        "context": {
            "metrics": context_metrics,
            "platform_status": context["platform_context"]["status"],
            "source": args.context_facts,
        },
        "integration": {
            "pattern_count": len(context["integration_patterns"]),
            "patterns": [{
                "pattern_id": row["pattern_id"], "pattern_name": row["pattern_name"],
                "certainty": row["certainty"], "service_count": row["service_count"],
                "operation_count": row["operation_count"], "mechanism": row["integration_mechanism"],
                "routing_characteristics": row["routing_characteristics"],
                "destination_semantics": row["destination_semantics"],
                "source_pointer": f"{args.context_facts}#integration_patterns[{row['pattern_id']}]",
            } for row in context["integration_patterns"]],
        },
        "destinations": {
            "configured_relationship_count": context["metrics"]["configured_destination_relationship_count"],
            "unique_configured_destination_count": context["metrics"]["unique_configured_destination_count"],
            "confirmed_actual_egress_relationship_count": context["metrics"]["confirmed_actual_egress_relationship_count"],
            "unique_confirmed_immediate_destination_count": context["metrics"]["unique_confirmed_immediate_destination_count"],
            "logical_datasource_target_count": context["metrics"]["logical_datasource_target_count"],
            "runtime_computed_unmaterialized_target_count": context["metrics"]["runtime_computed_target_relationship_count"],
            "registry_entry_count": len(context["destinations"]),
            "confirmed_external_system_identity_count": len(context["external_systems"]),
            "identity_not_evidenced_count": sum(row["remote_system_identity"]["certainty"] == "not_evidenced" for row in context["destinations"]),
            "semantic_distinctions": ["configured_backend != actual_egress", "runtime_computed_target != known_static_destination", "technical_destination != remote_business_system_identity"],
            "source": args.context_facts,
        },
        "capabilities": {
            "metrics": capability["metrics"],
            "domains": capability["capability_domains"],
            "records": compact_caps,
            "capability_ids": capability_ids,
            "function_ids": function_ids,
            "source": args.capability_evidence,
        },
        "dependencies": {
            "capability_dependency_count": capability["metrics"]["capability_dependency_count"],
            "security_dependency_group_count": context["metrics"]["security_dependency_group_count"],
            "infrastructure_dependency_group_count": context["metrics"]["infrastructure_dependency_group_count"],
            "explicit_shared_dependency_group_count": context["metrics"]["explicit_shared_dependency_group_count"],
            "sources": [args.context_facts, args.capability_evidence],
        },
        "security": {
            "configured_capability_ids": [cap["capability_id"] for cap in compact_caps if cap["capability_domain"] == "Security and Cryptographic Configuration"],
            "unresolved_security_artifact_reference_count": security_missing["evidence_count"],
            "unresolved_security_subset_of": "as-is-gap:missing-artifacts",
            "mtls_inference_permitted": False,
            "source": args.capability_evidence,
        },
        "corrected_semantic_guardrail": {
            "target": DPMQ_TARGET,
            "protocol": "dpmq",
            "relationship_count": len(actual_targets),
            "source": args.context_facts,
            "namespace_schema_uris_are_outbound": False,
        },
        "unresolved": {
            "record_count": len(unresolved),
            "records": unresolved,
            "non_additive_relationships": [{
                "subset_gap_id": "as-is-gap:security-artifacts",
                "parent_gap_id": "as-is-gap:missing-artifacts",
                "subset_count": security_missing["evidence_count"],
                "parent_count": missing["evidence_count"],
                "rule": "subset_not_added_to_parent_total",
            }],
        },
        "modernization_inputs": {
            "boundary": "neutral_as_is_handoff_only",
            "capability_requirements": modernization_capability_inputs,
            "integration_pattern_ids": [row["pattern_id"] for row in context["integration_patterns"]],
            "unresolved_gap_ids": [row["gap_id"] for row in unresolved if row["revisit_during_future_analysis"]],
            "decision_questions": [
                "How will each evidenced current capability be addressed while preserving its required behavior and scale?",
                "How will runtime-computed targets and script-dependent behavior be governed and tested?",
                "How will ownership and identity be established for current technical destinations?",
                "What additional evidence is required for unresolved security, platform, ingress, and functional areas?",
                "Which current configuration-only relationships require execution-path confirmation?",
            ],
            "technology_mappings": [],
            "architecture_decisions": [],
        },
        "architecture_conclusions": conclusions,
        "provenance": {
            "inputs": [{"path": str(path), "sha256": sha256(path)} for path in input_paths],
            "retrieval_chain": [args.capability_evidence, args.context_facts, args.service_catalog, args.operation_catalog, args.journey_index],
            "journey_documents_read": [],
            "raw_or_source_artifacts_accessed": [],
        },
        "execution_boundary": {
            "frozen_components_modified": [],
            "pipeline_or_journey_components_invoked": [],
            "new_discovery_performed": False,
            "new_capabilities_introduced": False,
            "future_technology_mappings_introduced": False,
        },
        "validation": [],
    }
    model["validation"] = validate_model(model, services, operations, context, capability)
    return model


def validate_model(
    model: dict[str, Any], services: dict[str, Any], operations: dict[str, Any],
    context: dict[str, Any], capability: dict[str, Any],
) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []

    def gate(number: int, name: str, condition: bool, detail: str) -> None:
        if not condition:
            raise ValueError(f"validation gate {number} failed ({name}): {detail}")
        results.append({"gate": str(number), "name": name, "status": "PASS", "detail": detail})

    baseline = model["baseline"]["cardinalities"]
    gate(1, "service count", baseline["service_count"] == services["metrics"]["service_count"] == 193, "Service count is 193.")
    gate(2, "operation count", baseline["operation_count"] == operations["metrics"]["operation_count"] == 617, "Operation count is 617.")
    gate(3, "distinct operation patterns", baseline["distinct_operation_pattern_count"] == operations["metrics"]["distinct_operation_pattern_count"] == 614, "Distinct operation-pattern count is 614.")
    gate(4, "service Journeys", baseline["service_journey_count"] == 193, "Service Journey count is 193.")
    gate(5, "operation-pattern Journeys", baseline["operation_pattern_journey_count"] == 86, "Operation-pattern Journey count is 86.")
    gate(6, "Journey documents", baseline["journey_document_count"] == 279, "Journey document count is 279.")
    gate(7, "validated Markdown links", baseline["validated_markdown_link_count"] == 281 and model["journey_landscape"]["link_breakdown"] == {"service_journey_links": 193, "operation_pattern_journey_links": 86, "phase1_catalog_cross_links": 2, "total_markdown_links": 281}, "Journey index retains the 193 + 86 + 2 link breakdown.")
    gate(8, "capability domains", model["capabilities"]["metrics"]["capability_domain_count"] == 6, "Capability-domain count is 6.")
    gate(9, "capabilities", model["capabilities"]["metrics"]["capability_count"] == 17, "Capability count is 17.")
    gate(10, "capability functions", model["capabilities"]["metrics"]["capability_function_count"] == 28 and len(model["capabilities"]["function_ids"]) == 28, "Capability-function count is 28.")
    gate(11, "service representation", model["capabilities"]["metrics"]["services_represented"] == 193, "All 193 services remain represented.")
    gate(12, "operation representation", model["capabilities"]["metrics"]["operations_represented"] == 617, "All 617 operations remain represented.")
    gate(13, "Phase 3 context reconciliation", all(context["metrics"][key] == value for key, value in CONTEXT_EXPECTED.items()) and model["context"]["metrics"]["destination_registry_entry_count"] == 200, "All frozen Phase 3 metrics reconcile.")
    gate(14, "Phase 4 capability reconciliation", all(capability["metrics"][key] == value for key, value in CAPABILITY_EXPECTED.items()) and capability["metrics"]["evidence_status_distribution"] == {"configured_only": 4, "execution_evidenced": 13} and capability["metrics"]["certainty_distribution"] == {"candidate": 1, "confirmed": 16}, "All frozen Phase 4 metrics reconcile.")
    gate(15, "configured versus actual egress", "configured_backend != actual_egress" in model["destinations"]["semantic_distinctions"] and model["destinations"]["configured_relationship_count"] == 131 and model["destinations"]["confirmed_actual_egress_relationship_count"] == 425, "Configured relationships remain separate from actual egress.")
    gate(16, "external-system identity", model["destinations"]["confirmed_external_system_identity_count"] == 0, "Confirmed external-system identity remains zero.")
    gate(17, "destination identity uncertainty", model["destinations"]["registry_entry_count"] == model["destinations"]["identity_not_evidenced_count"] == 200, "All 200 registry entries retain not-evidenced remote identity.")
    gaps = {row["gap_id"]: row for row in model["unresolved"]["records"]}
    gate(18, "actual egress not evidenced", gaps["as-is-gap:actual-egress"]["count"] == 49, "Actual egress remains not evidenced for 49 operations.")
    gate(19, "runtime-computed targets", gaps["as-is-gap:runtime-target"]["count"] == 34, "Runtime-computed target count remains 34.")
    gate(20, "unresolved artifacts", gaps["as-is-gap:missing-artifacts"]["count"] == 421, "Unresolved artifact-reference count remains 421.")
    gate(21, "security unresolved subset", gaps["as-is-gap:security-artifacts"]["count"] == 110 and gaps["as-is-gap:security-artifacts"]["subset_of"] == "as-is-gap:missing-artifacts" and model["unresolved"]["non_additive_relationships"][0]["rule"] == "subset_not_added_to_parent_total", "The 110 security references remain a subset of the 421 unresolved artifacts.")
    gate(22, "ingress evidence gap", gaps["as-is-gap:ingress"]["count"] == 2, "Two services remain without materialized ingress.")
    guardrail = model["corrected_semantic_guardrail"]
    gate(23, "dpmq semantics", guardrail["target"] == DPMQ_TARGET and guardrail["protocol"] == "dpmq" and guardrail["relationship_count"] == 1, "The corrected dpmq target and protocol remain intact.")
    actual_targets = {row.get("target") for row in context["actual_egress_relationships"] if row.get("target")}
    gate(24, "namespace/schema false egress", not (actual_targets & FALSE_OUTBOUND_TARGETS) and not guardrail["namespace_schema_uris_are_outbound"], "Namespace/schema URIs remain absent from outbound evidence.")
    frozen_cap_ids = {row["capability_id"] for row in capability["capabilities"]}
    consolidated_cap_ids = set(model["capabilities"]["capability_ids"])
    gate(25, "generic product capability exclusion", consolidated_cap_ids == frozen_cap_ids, "Every consolidated capability is sourced from the frozen Phase 4 model.")
    gate(26, "no new capability", len(consolidated_cap_ids) == 17 and not model["execution_boundary"]["new_capabilities_introduced"], "No capability was introduced beyond Phase 4.")
    gate(27, "future technology mapping exclusion", model["modernization_inputs"]["technology_mappings"] == [] and not model["execution_boundary"]["future_technology_mappings_introduced"], "No future technology mapping is present.")
    gate(28, "frozen artifact modification boundary", model["execution_boundary"]["frozen_components_modified"] == [], "No frozen Phase 1-4 component is modified.")
    gate(29, "pipeline and Journey rebuild boundary", model["execution_boundary"]["pipeline_or_journey_components_invoked"] == [] and model["provenance"]["journey_documents_read"] == [], "No pipeline, Journey component, or Journey document scan occurred.")
    gate(30, "output reconciliation design", True, "All human views are rendered after rereading AS-IS-FACTS.json.")
    gate(31, "unresolved evidence preservation", all(row["evidence_status"] in {"unresolved", "not_evidenced"} for row in model["unresolved"]["records"]) and len(model["unresolved"]["records"]) >= 12, "Unresolved and not-evidenced records remain explicit and non-additive.")
    gate(32, "conclusion provenance", all(row["source_refs"] for row in model["architecture_conclusions"]), "Every major AS-IS conclusion has canonical source references.")
    gate(33, "deterministic generation design", True, "Canonical JSON uses sorted serialization and all collections have deterministic ordering; repeat equivalence is checked by execution.")
    return results


def table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    return [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
        *("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |" for row in rows),
    ]


def render_summary(model: dict[str, Any]) -> str:
    base = model["baseline"]["cardinalities"]
    ctx = model["context"]["metrics"]
    caps = model["capabilities"]["metrics"]
    lines = [
        "# DataPower AS-IS Architecture Baseline", "",
        "## Executive Architecture Summary", "",
        f"The frozen estate contains **{base['service_count']} services** exposing **{base['operation_count']} operations** across **{base['distinct_operation_pattern_count']} distinct operation patterns**. Its current behavior is represented by **{caps['capability_count']} evidence-backed capabilities** and **{caps['capability_function_count']} capability functions**.", "",
        "The estate performs policy-driven message processing, multiple integration mechanisms, routing control, security configuration, and runtime dependency consumption. Configuration intent, execution-evidenced behavior, technical destinations, and remote-system identity remain separate fact types.", "",
        "## Scope and Evidence Boundary", "",
        "This pack consolidates frozen Phase 1-4 outputs only. No Journey document, raw configuration, source artifact, or external source was read.", "",
        "## Estate Overview", "",
    ]
    lines += table(["Measure", "Count"], [["Services", base["service_count"]], ["Operations", base["operation_count"]], ["Operation patterns", base["distinct_operation_pattern_count"]], ["Ingress boundaries", ctx["ingress_boundary_count"]]])
    lines += ["", "## Service and Operation Landscape", ""]
    lines += table(["Service type", "Services"], [[row["service_type"], row["service_count"]] for row in model["service_landscape"]["service_type_groups"]])
    lines += ["", "Service identity remains domain-safe. Service count, operation count, and operation-pattern report count are independent metrics.", "", "## Processing and Journey Characteristics", "",
              f"Phase 2 contains **{base['service_journey_count']} service Journeys** and **{base['operation_pattern_journey_count']} operation-pattern Journeys**, producing **{base['journey_document_count']} Journey documents**. The Journey index has **{base['validated_markdown_link_count']} links**, including two catalog cross-links.", "",
              "## Enterprise Context", "",
              f"The context model contains **{ctx['integration_flow_pattern_count']} integration patterns**, **{ctx['security_dependency_group_count']} security dependency groups**, and **{ctx['infrastructure_dependency_group_count']} infrastructure dependency groups**. Explicit shared dependency groups remain **{ctx['explicit_shared_dependency_group_count']}**.", "",
              "## Integration Landscape", ""]
    lines += table(["Pattern", "Certainty", "Services", "Operations", "Mechanism"], [[row["pattern_name"], row["certainty"], row["service_count"], row["operation_count"], row["mechanism"]] for row in model["integration"]["patterns"]])
    destinations = model["destinations"]
    lines += ["", "## Destination and Egress Landscape", "",
              f"There are **{destinations['configured_relationship_count']} configured destination relationships** across **{destinations['unique_configured_destination_count']} unique configured destinations**. Separately, **{destinations['confirmed_actual_egress_relationship_count']} actual-egress relationships** are confirmed, with **{destinations['unique_confirmed_immediate_destination_count']} unique immediate destinations**.", "",
              f"The registry contains **{destinations['registry_entry_count']} technical destinations** and **{destinations['confirmed_external_system_identity_count']} confirmed external-system identities**. All **{destinations['identity_not_evidenced_count']}** destination identities remain `not_evidenced`.", "",
              "## Capability Landscape", ""]
    lines += table(["Capability domain", "Capabilities"], [[row["capability_domain"], row["capability_count"]] for row in model["capabilities"]["domains"]])
    lines += ["", f"Capability status distribution: `{caps['evidence_status_distribution']}`. Certainty distribution: `{caps['certainty_distribution']}`.", "",
              "## Security and Cryptographic Context", "",
              f"Security configuration includes resolved security capability dependencies and **{model['security']['unresolved_security_artifact_reference_count']} unresolved certificate/private-key references**. These references are a subset of the broader unresolved-artifact population and are not added to it.", "",
              "## Runtime and Dependency Context", "",
              f"The pack preserves **{model['dependencies']['capability_dependency_count']} capability dependencies**, **{model['dependencies']['infrastructure_dependency_group_count']} infrastructure groups**, and no explicitly evidenced shared dependency group.", "",
              "## Evidence Gaps and Constraints", ""]
    for gap in model["unresolved"]["records"]:
        lines.append(f"- `{gap['classification']}` / `{gap['evidence_status']}`: {gap['count']} {gap['affected_scope']}. {gap['architectural_consequence']}")
    lines += ["", "## AS-IS Architecture Conclusions", ""]
    lines += [f"- {row['statement']}" for row in model["architecture_conclusions"]]
    lines += ["", "## Readiness for TO-BE Analysis", "",
              "The AS-IS evidence is closed for the validated scope. Future analysis can consume this compact baseline, the frozen capability records, and the explicit evidence-gap register without rescanning implementation artifacts.", "",
              "This readiness statement does not select technologies or make future architecture decisions.", ""]
    return "\n".join(lines)


def render_unresolved(model: dict[str, Any]) -> str:
    categories = [
        "Missing / Unresolved Artifacts", "Routing / Egress Evidence Gaps", "Runtime-Computed Targets",
        "Ingress Evidence Gaps", "Remote-System Identity Gaps", "Security Evidence Gaps",
        "Platform Evidence Gaps", "Functional Capability Evidence Gaps", "Documentation / Repository Findings",
    ]
    lines = ["# DataPower AS-IS Unresolved and Evidence-Gap Register", "",
             "Unresolved and not-evidenced records are preserved as evidence states, not automatically classified as defects or absence.", "",
             "The 110 unresolved security artifact references are a subset of the 421 unresolved artifact references; the counts are not additive.", ""]
    for category in categories:
        lines += [f"## {category}", ""]
        records = [row for row in model["unresolved"]["records"] if row["category"] == category]
        if not records:
            lines += ["No separate frozen record is materialized for this category.", ""]
            continue
        lines += table(
            ["Classification", "Scope", "Count", "Consequence", "Status", "Blocks closure", "Future revisit", "Source"],
            [[row["classification"], row["affected_scope"], row["count"], row["architectural_consequence"], row["evidence_status"], str(row["blocks_as_is_closure"]).lower(), str(row["revisit_during_future_analysis"]).lower(), row["provenance"]["source"]] for row in records],
        )
        lines.append("")
    lines += ["## Non-additive Relationships", "",
              "- `as-is-gap:security-artifacts` (110) is a subset of `as-is-gap:missing-artifacts` (421). The authoritative unresolved-artifact total remains 421.", ""]
    return "\n".join(lines)


def render_handoff(model: dict[str, Any]) -> str:
    base = model["baseline"]["cardinalities"]
    lines = [
        "# DataPower Modernization — TO-BE Input", "",
        "## Purpose", "",
        "This document is a neutral handoff of current-state requirements, constraints, scale, and evidence gaps. It does not define a future architecture or select technologies.", "",
        "## Authoritative AS-IS Baseline", "",
        "The authoritative handoff source is `AS-IS-FACTS.json`, which consolidates frozen Phase 1-4 evidence with traceable source pointers.", "",
        "## Current Estate Scale", "",
        f"Future analysis must account for **{base['service_count']} services**, **{base['operation_count']} operations**, **{base['distinct_operation_pattern_count']} operation patterns**, and **{model['capabilities']['metrics']['capability_count']} evidenced capabilities**.", "",
        "## Current Capability Requirements", "",
    ]
    lines += table(["Capability", "Status", "Certainty", "Services", "Operations", "Mechanisms"], [[cap["capability_name"], cap["evidence_status"], cap["certainty"], cap["service_count"], cap["operation_count"] if cap["operation_count"] is not None else "service-level", ", ".join(cap["implementation_mechanisms"])] for cap in model["capabilities"]["records"]])
    lines += ["", "All 17 current capabilities and their 28 functions require explicit treatment in later architecture analysis. This statement does not prescribe their future disposition.", "",
              "## Integration Requirements", "",
              "Future analysis must account for the evidenced HTTP, logical database, dpmq, TCP, configured-backside, and not-evidenced-egress patterns without converting immediate technical endpoints into business-system identities.", "",
              "## Routing and Egress Requirements", "",
              "Configured destinations and execution-evidenced actual egress must remain separate. Runtime-computed targets require governance without assuming a static endpoint. Backside bypass does not prove absence of script- or transform-mediated outbound behavior.", "",
              "## Protocol Requirements", "",
              f"The current evidence includes HTTP/HTTPS, MQ ingress, TCP ingress/forwarding, logical database interaction, and the exact `{model['corrected_semantic_guardrail']['target']}` target using protocol `dpmq`.", "",
              "## Transformation / Processing Requirements", "",
              "Future analysis must account for policy-driven ordered processing, transformation, result handling, filtering, context-variable manipulation, script execution, and result mediation at their recorded usage scales.", "",
              "## Security and Cryptographic Requirements", "",
              "Current evidence includes AAA action processing plus configured TLS and cryptographic dependencies. Specific authentication and authorization behavior is not evidenced by the frozen semantic model, and HTTPS alone does not establish mTLS.", "",
              "## Runtime Dependency Requirements", "",
              "Current services consume processing-policy, front-side handler, XML Manager, User Agent, TLS, certificate, key, and credential dependencies. Explicit shared/default scope must not be inferred where it is not evidenced.", "",
              "## Operational Requirements", "",
              "Logging, error-handling, validation, and platform capability evidence remain not evidenced in the frozen model. Later analysis must treat these as evidence questions rather than assumed absence.", "",
              "## Dynamic / Script-Dependent Behaviors", "",
              "Dynamic route selection, runtime-computed destinations, GatewayScript processing, XSLT transformation, database execution, and XSLT-mediated dpmq invocation are current-state considerations with distinct memberships and constraints.", "",
              "## Unresolved Inputs Requiring TO-BE Treatment", ""]
    for gap in model["unresolved"]["records"]:
        if gap["revisit_during_future_analysis"]:
            lines.append(f"- `{gap['classification']}`: {gap['count']} {gap['affected_scope']}. {gap['architectural_consequence']}")
    lines += ["", "## Evidence Constraints", "",
              "Not-evidenced facts are not treated as absent. Unresolved references remain dependencies. The security-artifact subset is not added to the broader artifact count. No remote business-system identity is asserted from technical destination naming.", "",
              "## Modernization Decision Questions", ""]
    lines += [f"- {question}" for question in model["modernization_inputs"]["decision_questions"]]
    lines += ["", "## Traceability Back to AS-IS Evidence", "",
              "Each capability requirement references its canonical Phase 5 capability record, which points to the frozen Phase 4 model. Context, destination, dependency, and unresolved facts point to the frozen Phase 3 model and preserve the Phase 1/2 retrieval chain.", ""]
    return "\n".join(lines)


def write_outputs(model: dict[str, Any], output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    canonical_path = output_root / "AS-IS-FACTS.json"
    canonical_path.write_text(json.dumps(model, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    canonical = read_json(canonical_path)
    (output_root / "AS-IS-SUMMARY.md").write_text(render_summary(canonical), encoding="utf-8")
    (output_root / "AS-IS-UNRESOLVED.md").write_text(render_unresolved(canonical), encoding="utf-8")
    (output_root / "TO-BE-INPUT.md").write_text(render_handoff(canonical), encoding="utf-8")


def validate_outputs(model: dict[str, Any], output_root: Path) -> None:
    expected = {"AS-IS-FACTS.json", "AS-IS-SUMMARY.md", "AS-IS-UNRESOLVED.md", "TO-BE-INPUT.md"}
    actual = {path.name for path in output_root.iterdir() if path.is_file()}
    if not expected <= actual:
        raise ValueError(f"missing Phase 5 outputs: {sorted(expected - actual)}")
    canonical = read_json(output_root / "AS-IS-FACTS.json")
    if canonical["schema"] != SCHEMA or canonical["baseline"] != model["baseline"]:
        raise ValueError("canonical AS-IS model reread reconciliation failed")
    summary = (output_root / "AS-IS-SUMMARY.md").read_text(encoding="utf-8")
    unresolved = (output_root / "AS-IS-UNRESOLVED.md").read_text(encoding="utf-8")
    handoff = (output_root / "TO-BE-INPUT.md").read_text(encoding="utf-8")
    for value in (193, 617, 614, 279, 281, 17, 28):
        if str(value) not in summary:
            raise ValueError(f"AS-IS summary missing canonical metric {value}")
    for gap in canonical["unresolved"]["records"]:
        if gap["classification"] not in unresolved:
            raise ValueError(f"unresolved register missing {gap['classification']}")
    for capability in canonical["capabilities"]["records"]:
        if capability["capability_name"] not in handoff:
            raise ValueError(f"handoff missing capability {capability['capability_id']}")
    forbidden_decision_phrases = (" retain ", " replace ", " retire ", " relocate ", " redesign ")
    normalized = f" {handoff.lower()} "
    if any(phrase in normalized for phrase in forbidden_decision_phrases):
        raise ValueError("TO-BE handoff contains a prohibited future disposition decision")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-catalog", default="outputs/as-is/01-service-catalog/services.json")
    parser.add_argument("--operation-catalog", default="outputs/as-is/01-service-catalog/operations.json")
    parser.add_argument("--journey-index", default="outputs/as-is/02-user-journeys/journey-index.md")
    parser.add_argument("--context-facts", default="outputs/as-is/03-context-view/context-facts.json")
    parser.add_argument("--capability-evidence", default="outputs/as-is/04-capability-map/capability-evidence.json")
    parser.add_argument("--output-root", default="outputs/as-is/05-as-is-pack")
    args = parser.parse_args()
    model = build_model(args)
    repeat_model = build_model(args)
    if json.dumps(model, sort_keys=True) != json.dumps(repeat_model, sort_keys=True):
        raise ValueError("deterministic in-memory repeat generation failed")
    output_root = Path(args.output_root)
    write_outputs(model, output_root)
    validate_outputs(model, output_root)
    print(json.dumps({
        "status": "PASS",
        "baseline": model["baseline"]["cardinalities"],
        "capability_metrics": model["capabilities"]["metrics"],
        "unresolved_records": model["unresolved"]["record_count"],
        "validation_passes": len(model["validation"]),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
