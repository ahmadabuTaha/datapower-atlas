#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

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


def validate(bundle: TaxonomyBundle) -> ValidationReport:
    r = ValidationReport()

    objects = get_mapping(
        bundle.datapower_objects, "object_types", "datapower_objects"
    )
    property_rules = get_mapping(
        bundle.datapower_properties,
        "property_rules",
        "datapower_properties",
    )
    references = get_mapping(
        bundle.reference_types,
        "reference_types",
        "reference_types",
    )
    relationships = get_mapping(
        bundle.relationship_types,
        "relationship_types",
        "relationship_types",
    )
    endpoints = get_mapping(
        bundle.endpoint_types,
        "endpoint_types",
        "endpoint_types",
    )
    cross_mappings = bundle.cross_taxonomy.get("mappings", [])
    resolution_strategies = get_mapping(
        bundle.cross_taxonomy,
        "resolution_strategies",
        "cross_taxonomy",
    )
    file_types = get_mapping(
        bundle.file_types,
        "file_types",
        "file_types",
    )
    sensitivity_levels = get_mapping(
        bundle.sensitivity,
        "sensitivity_levels",
        "sensitivity",
    )

    if not isinstance(cross_mappings, list):
        r.error("cross_taxonomy.mappings must be a list")
        cross_mappings = []

    canonical_types: Dict[str, str] = {}
    for key, spec in objects.items():
        p = f"datapower_objects.object_types.{key}"
        if not isinstance(spec, dict):
            r.error(f"{p}: object definition must be a mapping")
            continue

        canonical = spec.get("canonical_type")
        if not canonical:
            r.error(f"{p}: missing canonical_type")
            continue

        if canonical in canonical_types:
            r.error(
                f"{p}: duplicate canonical_type {canonical!r}; "
                f"already used by {canonical_types[canonical]}"
            )
        else:
            canonical_types[canonical] = key

    object_types: Set[str] = set(canonical_types)

    r.metrics.update({
        "datapower_object_types": len(object_types),
        "property_source_types": len(property_rules),
        "reference_types": len(references),
        "relationship_types": len(relationships),
        "endpoint_types": len(endpoints),
        "cross_mappings": len(cross_mappings),
        "file_type_buckets": len(file_types),
        "sensitivity_levels": len(sensitivity_levels),
    })

    # ------------------------------------------------------------------
    # Object taxonomy
    # ------------------------------------------------------------------
    for key, spec in objects.items():
        if not isinstance(spec, dict):
            continue
        p = f"datapower_objects.object_types.{key}"

        canonical = spec.get("canonical_type")
        if isinstance(canonical, str) and canonical.lower() in PROHIBITED_LABELS:
            r.error(f"{p}.canonical_type: prohibited label {canonical!r}")

        kind = spec.get("recognition_kind")
        if not kind:
            r.error(f"{p}.recognition_kind: missing")

        command = spec.get("command")
        if not isinstance(command, dict):
            r.error(f"{p}.command: expected mapping")
        else:
            tokens = command.get("tokens")
            if not isinstance(tokens, list) or not tokens:
                r.error(f"{p}.command.tokens: must be non-empty list")

    # ------------------------------------------------------------------
    # Property taxonomy
    # ------------------------------------------------------------------
    valid_property_kinds = set(
        get_mapping(
            bundle.datapower_properties,
            "property_kinds",
            "datapower_properties",
        )
    )

    for source_type, props in property_rules.items():
        p = f"datapower_properties.property_rules.{source_type}"

        if source_type not in object_types:
            r.error(f"{p}: source type is not defined in datapower_objects")

        if not isinstance(props, dict):
            r.error(f"{p}: expected mapping")
            continue

        for prop_name, spec in props.items():
            pp = f"{p}.{prop_name}"
            if not isinstance(spec, dict):
                r.error(f"{pp}: expected mapping")
                continue

            kind = spec.get("property_kind")
            if kind not in valid_property_kinds:
                r.error(f"{pp}.property_kind: invalid {kind!r}")

            target = spec.get("target_type")
            if target and target not in object_types:
                r.error(f"{pp}.target_type: undefined object type {target!r}")

            for target in as_list(spec.get("target_type_set")):
                if target not in object_types:
                    r.error(
                        f"{pp}.target_type_set: undefined object type {target!r}"
                    )

            ref = spec.get("reference_type")
            if ref and ref not in references:
                r.error(f"{pp}.reference_type: undefined {ref!r}")

            rel = spec.get("relationship_type")
            if rel and rel not in relationships:
                r.error(f"{pp}.relationship_type: undefined {rel!r}")

            strategy = spec.get("resolution_strategy")
            if strategy and strategy not in resolution_strategies:
                r.error(f"{pp}.resolution_strategy: undefined {strategy!r}")

            for arg in as_list(spec.get("arguments")):
                if not isinstance(arg, dict):
                    r.error(f"{pp}.arguments: each entry must be a mapping")
                    continue
                target = arg.get("target_type")
                if target and target not in object_types:
                    r.error(
                        f"{pp}.arguments.target_type: undefined {target!r}"
                    )
                ref = arg.get("reference_type")
                if ref and ref not in references:
                    r.error(
                        f"{pp}.arguments.reference_type: undefined {ref!r}"
                    )
                rel = arg.get("relationship_type")
                if rel and rel not in relationships:
                    r.error(
                        f"{pp}.arguments.relationship_type: undefined {rel!r}"
                    )

    # ------------------------------------------------------------------
    # Reference taxonomy
    # ------------------------------------------------------------------
    families = get_mapping(
        bundle.reference_types,
        "reference_families",
        "reference_types",
    )

    for name, spec in references.items():
        p = f"reference_types.reference_types.{name}"
        if not isinstance(spec, dict):
            r.error(f"{p}: expected mapping")
            continue

        family = spec.get("family")
        if family not in families:
            r.error(f"{p}.family: undefined {family!r}")

        for ft in as_list(spec.get("expected_file_types")):
            if ft not in file_types:
                r.error(f"{p}.expected_file_types: undefined {ft!r}")

    # ------------------------------------------------------------------
    # Relationship taxonomy
    # ------------------------------------------------------------------
    rel_families = get_mapping(
        bundle.relationship_types,
        "semantic_families",
        "relationship_types",
    )

    for name, spec in relationships.items():
        p = f"relationship_types.relationship_types.{name}"
        if not isinstance(spec, dict):
            r.error(f"{p}: expected mapping")
            continue

        family = spec.get("family")
        if family not in rel_families:
            r.error(f"{p}.family: undefined {family!r}")

        for source in as_list(spec.get("allowed_sources")):
            if source not in object_types:
                r.error(f"{p}.allowed_sources: undefined {source!r}")

        for target in as_list(spec.get("allowed_targets")):
            if target not in object_types:
                r.error(f"{p}.allowed_targets: undefined {target!r}")

    # ------------------------------------------------------------------
    # Cross taxonomy
    # ------------------------------------------------------------------
    mapping_ids: Set[str] = set()

    for idx, mapping in enumerate(cross_mappings):
        p = f"cross_taxonomy.mappings[{idx}]"

        if not isinstance(mapping, dict):
            r.error(f"{p}: expected mapping")
            continue

        mapping_id = mapping.get("mapping_id")
        if not mapping_id:
            r.error(f"{p}.mapping_id: missing")
        elif mapping_id in mapping_ids:
            r.error(f"{p}.mapping_id: duplicate {mapping_id!r}")
        else:
            mapping_ids.add(mapping_id)

        source_type = mapping.get("source_type")
        property_name = mapping.get("property_name")
        property_kind = mapping.get("property_kind")
        reference_type = mapping.get("reference_type")
        relationship_type = mapping.get("relationship_type")
        resolution_strategy = mapping.get("resolution_strategy")

        if source_type not in object_types:
            r.error(f"{p}.source_type: undefined {source_type!r}")
            continue

        source_props = property_rules.get(source_type, {})
        prop_spec = source_props.get(property_name)
        if not isinstance(prop_spec, dict):
            r.error(
                f"{p}: property {property_name!r} is not defined for "
                f"source type {source_type!r}"
            )
            continue

        expected_kind = prop_spec.get("property_kind")
        if property_kind != expected_kind:
            r.error(
                f"{p}.property_kind: {property_kind!r} does not match "
                f"property taxonomy {expected_kind!r}"
            )

        if reference_type not in references:
            r.error(f"{p}.reference_type: undefined {reference_type!r}")

        if relationship_type not in relationships:
            r.error(
                f"{p}.relationship_type: undefined {relationship_type!r}"
            )

        if resolution_strategy not in resolution_strategies:
            r.error(
                f"{p}.resolution_strategy: undefined {resolution_strategy!r}"
            )

        target_type = mapping.get("target_type")
        target_type_set = as_list(mapping.get("target_type_set"))

        if target_type and target_type not in object_types:
            r.error(f"{p}.target_type: undefined {target_type!r}")

        for target in target_type_set:
            if target not in object_types:
                r.error(f"{p}.target_type_set: undefined {target!r}")

        if relationship_type in relationships:
            rel_spec = relationships[relationship_type]
            allowed_sources = set(as_list(rel_spec.get("allowed_sources")))
            allowed_targets = set(as_list(rel_spec.get("allowed_targets")))

            if allowed_sources and source_type not in allowed_sources:
                r.error(
                    f"{p}: relationship {relationship_type!r} does not allow "
                    f"source {source_type!r}"
                )

            targets_to_check = set(target_type_set)
            if target_type:
                targets_to_check.add(target_type)

            for target in targets_to_check:
                if allowed_targets and target not in allowed_targets:
                    r.error(
                        f"{p}: relationship {relationship_type!r} does not "
                        f"allow target {target!r}"
                    )

        argument_position = mapping.get("argument_position")
        if argument_position is not None:
            args = as_list(prop_spec.get("arguments"))
            matches = [
                a for a in args
                if isinstance(a, dict)
                and a.get("position") == argument_position
            ]
            if not matches:
                r.error(
                    f"{p}.argument_position: no corresponding property "
                    f"argument definition for position {argument_position}"
                )

    return r


def print_report(report: ValidationReport) -> None:
    print("=" * 76)
    print("DATAPOWER CROSS-TAXONOMY VALIDATION V2")
    print("=" * 76)

    for key, value in report.metrics.items():
        print(f"{key:36} {value}")

    print("-" * 76)

    print(f"ERRORS:   {len(report.errors)}")
    for msg in report.errors:
        print(f"  [ERROR] {msg}")

    print(f"WARNINGS: {len(report.warnings)}")
    for msg in report.warnings:
        print(f"  [WARN]  {msg}")

    print("-" * 76)
    print(
        "CROSS-TAXONOMY VALIDATION: PASS"
        if report.ok
        else "CROSS-TAXONOMY VALIDATION: FAILED"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate DataPower taxonomy V2 semantic integrity."
    )
    parser.add_argument(
        "--taxonomy-dir",
        default="taxonomy",
        help="Directory containing DataPower taxonomy YAML files",
    )
    args = parser.parse_args()

    try:
        bundle = load_taxonomies(args.taxonomy_dir)
        report = validate(bundle)
        print_report(report)
        return 0 if report.ok else 1
    except (
        DuplicateKeyError,
        FileNotFoundError,
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        print("CROSS-TAXONOMY VALIDATION: FAILED", file=sys.stderr)
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
