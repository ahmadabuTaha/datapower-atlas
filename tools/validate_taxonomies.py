#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple

from taxonomy_loader import (
    DuplicateKeyError,
    TaxonomyBundle,
    as_list,
    get_mapping,
    load_taxonomies,
)


PROHIBITED_LABELS = {
    "unknown",
    "other",
    "others",
    "misc",
    "miscellaneous",
    "various",
    "many",
    "different",
    "generic",
}

FILE_SCAN_REQUIRED = {
    "datapower_cfg",
    "xslt_stylesheet",
    "gateway_script_javascript",
    "wsdl_definition",
    "xsd_schema",
    "xml_document",
    "json_document",
    "mq_client_ini",
    "ini_configuration",
}


@dataclass
class ValidationReport:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metrics: Dict[str, int] = field(default_factory=dict)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    @property
    def ok(self) -> bool:
        return not self.errors


def _effective_flags(defaults: Dict[str, Any], *overrides: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(defaults)
    for override in overrides:
        result.update(override or {})
    return result


def _find_prohibited_labels(value: Any, path: str = "") -> Iterable[str]:
    if isinstance(value, dict):
        for k, v in value.items():
            key_norm = str(k).strip().lower()
            if key_norm in PROHIBITED_LABELS:
                yield f"{path}.{k}" if path else str(k)
            yield from _find_prohibited_labels(v, f"{path}.{k}" if path else str(k))
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from _find_prohibited_labels(item, f"{path}[{i}]")
    elif isinstance(value, str):
        if value.strip().lower() in PROHIBITED_LABELS:
            yield path


def validate(bundle: TaxonomyBundle) -> ValidationReport:
    r = ValidationReport()

    objects = get_mapping(bundle.datapower_objects, "object_types", "datapower_objects")
    categories = get_mapping(bundle.datapower_objects, "categories", "datapower_objects")
    indexing_policies = get_mapping(bundle.datapower_objects, "indexing_policies", "datapower_objects")
    sensitivity_levels = get_mapping(bundle.sensitivity, "sensitivity_levels", "sensitivity")
    references = get_mapping(bundle.reference_types, "reference_types", "reference_types")
    relationships = get_mapping(bundle.relationship_types, "relationships", "relationship_types")
    file_types = get_mapping(bundle.file_types, "file_types", "file_types")
    agent_modes = get_mapping(bundle.file_types, "agent_indexing_modes", "file_types")
    file_defaults = get_mapping(
        get_mapping(bundle.file_types, "standard_flags", "file_types"),
        "defaults",
        "file_types.standard_flags",
    )

    r.metrics.update({
        "datapower_object_types": len(objects),
        "relationship_types": len(relationships),
        "reference_types": len(references),
        "sensitivity_levels": len(sensitivity_levels),
        "file_type_buckets": len(file_types),
    })

    # --------------------------------------------------------
    # DataPower object cross references
    # --------------------------------------------------------
    canonical_seen: Dict[str, str] = {}

    for object_key, spec in objects.items():
        p = f"datapower_objects.object_types.{object_key}"
        if not isinstance(spec, dict):
            r.error(f"{p}: object definition must be a mapping")
            continue

        canonical = spec.get("canonical_type")
        if not canonical:
            r.error(f"{p}: missing canonical_type")
        elif canonical in canonical_seen:
            r.error(
                f"{p}: duplicate canonical_type {canonical!r}; "
                f"already used by {canonical_seen[canonical]}"
            )
        else:
            canonical_seen[canonical] = object_key

        category = spec.get("category")
        if category not in categories:
            r.error(f"{p}.category: undefined category {category!r}")

        sensitivity = spec.get("sensitivity")
        if sensitivity not in sensitivity_levels:
            r.error(f"{p}.sensitivity: undefined sensitivity level {sensitivity!r}")

        indexing = spec.get("indexing_policy")
        if indexing not in indexing_policies:
            r.error(f"{p}.indexing_policy: undefined indexing policy {indexing!r}")

        for rel in as_list(spec.get("expected_relationships")):
            if rel not in relationships:
                r.error(f"{p}.expected_relationships: undefined relationship {rel!r}")

        for ref in as_list(spec.get("expected_references")):
            if ref not in references:
                r.error(f"{p}.expected_references: undefined reference type {ref!r}")

    # --------------------------------------------------------
    # Reference taxonomy
    # --------------------------------------------------------
    for ref_name, spec in references.items():
        p = f"reference_types.reference_types.{ref_name}"
        if not isinstance(spec, dict):
            r.error(f"{p}: reference definition must be a mapping")
            continue

        hint = spec.get("sensitivity_hint")
        if hint is not None and hint not in sensitivity_levels:
            r.error(f"{p}.sensitivity_hint: undefined sensitivity level {hint!r}")

        target = spec.get("target_kind")
        if not target:
            r.error(f"{p}.target_kind: missing target kind")
        elif target not in file_types and target not in objects:
            # Some target kinds intentionally represent runtime/semantic nodes.
            # These remain warnings until a dedicated semantic-kind registry exists.
            r.warn(
                f"{p}.target_kind: {target!r} is not a file type or DataPower object type; "
                "treat as semantic/runtime kind until semantic-kind registry is added"
            )

        if spec.get("evidence_required") is not True:
            r.error(f"{p}.evidence_required: must be true")

    # --------------------------------------------------------
    # Relationship taxonomy
    # --------------------------------------------------------
    # known_semantic_kinds: Set[str] = set(objects) | set(file_types) | {
    #     "datapower_object",
    #     "datapower_service",
    #     "service",
    #     "processing_action",
    #     "source_artifact",
    #     "file_inventory_entry",
    #     "backend_endpoint",
    #     "service_endpoint",
    #     "database_endpoint",
    #     "endpoint",
    #     "hostname",
    #     "ip_address",
    #     "url_pattern",
    #     "logging_sink",
    #     "backend_member",
    #     "protocol_handler",
    #     "security_policy",
    #     "taxonomy_constrained_at_runtime",
    # }
    known_semantic_kinds: Set[str] = (
        set(objects)
        | set(file_types)
        | set(references)
        | {
            "datapower_object",
            "datapower_service",
            "service",
            "processing_action",
            "source_artifact",
            "file_inventory_entry",
            "backend_endpoint",
            "service_endpoint",
            "database_endpoint",
            "endpoint",
            "hostname",
            "ip_address",
            "url_pattern",
            "logging_sink",
            "backend_member",
            "protocol_handler",
            "security_policy",
            "taxonomy_constrained_at_runtime",
        }
    )

    for rel_name, spec in relationships.items():
        p = f"relationship_types.relationships.{rel_name}"
        if not isinstance(spec, dict):
            r.error(f"{p}: relationship definition must be a mapping")
            continue

        if spec.get("directed") is not True:
            r.error(f"{p}.directed: expected true")

        if spec.get("evidence_required") is not True:
            r.error(f"{p}.evidence_required: expected true")

        if not spec.get("category"):
            r.error(f"{p}.category: missing relationship category")

        for side in ("source_kinds", "target_kinds"):
            values = as_list(spec.get(side))
            if not values:
                r.error(f"{p}.{side}: must not be empty")
            for kind in values:
                if kind not in known_semantic_kinds:
                    r.warn(
                        f"{p}.{side}: semantic kind {kind!r} is not centrally registered"
                    )

    # Explicit semantic checks discovered from current object taxonomy.
    required_source_compatibility = {
        "uses_crypto_certificate": {
            "crypto_identification_credentials",
            "crypto_validation_credentials",
        },
        "uses_crypto_key": {
            "crypto_identification_credentials",
        },
    }

    for rel, required_sources in required_source_compatibility.items():
        if rel not in relationships:
            continue
        actual = set(as_list(relationships[rel].get("source_kinds")))
        missing = sorted(required_sources - actual)
        if missing:
            r.error(
                f"relationship_types.relationships.{rel}.source_kinds: "
                f"missing source kinds required by datapower_objects: {missing}"
            )

    # --------------------------------------------------------
    # File taxonomy
    # --------------------------------------------------------
    required_pre_scan_flags = {
        "requires_content_sensitivity_scan": True,
        "may_contain_secret_value": True,
        "require_redaction_if_detected": True,
        "allow_raw_content_in_search_index_before_scan": False,
        "allow_raw_content_in_agent_context_before_scan": False,
        "allow_raw_content_in_reports_before_scan": False,
    }

    sanitized_flags = {
        "allow_sanitized_content_in_search_index",
        "allow_sanitized_content_in_agent_context",
        "allow_sanitized_content_in_reports",
    }

    for flag in required_pre_scan_flags:
        if flag not in file_defaults:
            r.error(f"file_types.standard_flags.defaults: missing flag {flag!r}")
    for flag in sanitized_flags:
        if flag not in file_defaults:
            r.error(f"file_types.standard_flags.defaults: missing flag {flag!r}")

    for file_type, spec in file_types.items():
        p = f"file_types.file_types.{file_type}"
        mode = spec.get("agent_indexing")
        if mode not in agent_modes:
            r.error(f"{p}.agent_indexing: undefined mode {mode!r}")

        flags = spec.get("flags") or {}
        unknown_flags = sorted(set(flags) - set(file_defaults))
        if unknown_flags:
            r.error(
                f"{p}.flags: flags are not declared in standard_flags.defaults: {unknown_flags}"
            )

        effective = _effective_flags(
            file_defaults,
            agent_modes.get(mode, {}) if isinstance(agent_modes.get(mode), dict) else {},
            flags,
        )

        if file_type in FILE_SCAN_REQUIRED:
            for flag, expected in required_pre_scan_flags.items():
                if effective.get(flag) != expected:
                    r.error(
                        f"{p}: effective {flag}={effective.get(flag)!r}, expected {expected!r}"
                    )

    # --------------------------------------------------------
    # File-output contract runtime fields
    # --------------------------------------------------------
    required_runtime_fields = {
        "sensitivity_scan_status",
        "contains_sensitive_content",
        "detected_secret_count",
        "detected_sensitivity_types",
        "sanitized_content_available",
        "sensitivity_scan_timestamp",
    }

    file_output = (
        bundle.file_types.get("classification_output", {}).get("required_fields", [])
    )
    missing_runtime = sorted(required_runtime_fields - set(file_output))
    if missing_runtime:
        r.error(
            "file_types.classification_output.required_fields: "
            f"missing runtime sensitivity fields {missing_runtime}"
        )

    # --------------------------------------------------------
    # Prohibited classification labels
    # Do not treat validation-policy lists themselves as usage.
    # --------------------------------------------------------
    for name, doc in (
        ("datapower_objects", bundle.datapower_objects),
        ("file_types", bundle.file_types),
        ("sensitivity", bundle.sensitivity),
    ):
        # We intentionally do not fail just because prohibited labels are
        # listed under a validation policy. Scan object/file classification
        # values explicitly instead.
        pass

    for object_key, spec in objects.items():
        for key in ("canonical_type", "category", "sensitivity", "indexing_policy"):
            value = spec.get(key)
            if isinstance(value, str) and value.lower() in PROHIBITED_LABELS:
                r.error(
                    f"datapower_objects.object_types.{object_key}.{key}: "
                    f"prohibited generic classification {value!r}"
                )

    for file_key in file_types:
        if file_key.lower() in PROHIBITED_LABELS:
            r.error(
                f"file_types.file_types.{file_key}: prohibited generic classification label"
            )

    return r


def print_report(report: ValidationReport) -> None:
    print("=" * 72)
    print("DATAPOWER TAXONOMY VALIDATION")
    print("=" * 72)

    for key, value in report.metrics.items():
        print(f"{key:34} {value}")

    print("-" * 72)

    if report.errors:
        print(f"ERRORS:   {len(report.errors)}")
        for msg in report.errors:
            print(f"  [ERROR] {msg}")
    else:
        print("ERRORS:   0")

    if report.warnings:
        print(f"WARNINGS: {len(report.warnings)}")
        for msg in report.warnings:
            print(f"  [WARN]  {msg}")
    else:
        print("WARNINGS: 0")

    print("-" * 72)

    if report.ok:
        print("CROSS-TAXONOMY VALIDATION: PASS")
    else:
        print("CROSS-TAXONOMY VALIDATION: FAILED")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate DataPower modernization taxonomy files."
    )
    parser.add_argument(
        "--taxonomy-dir",
        default="taxonomy",
        help="Directory containing the five taxonomy YAML files (default: taxonomy)",
    )
    args = parser.parse_args()

    try:
        bundle = load_taxonomies(args.taxonomy_dir)
        report = validate(bundle)
        print_report(report)
        return 0 if report.ok else 1

    except (DuplicateKeyError, FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        print("CROSS-TAXONOMY VALIDATION: FAILED", file=sys.stderr)
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
