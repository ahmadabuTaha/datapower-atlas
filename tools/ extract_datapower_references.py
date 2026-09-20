#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml


EXTRACTOR_VERSION = "1.0-architecture-beta-domain-aware"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def tokenize_cli_value(value: str) -> List[str]:
    """
    Tokenize a DataPower property value while preserving quoted values as one
    token. Quotes are stripped from returned tokens.
    """
    tokens = re.findall(r'"[^"]*"|\'[^\']*\'|\S+', value or "")
    return [t.strip().strip('"').strip("'") for t in tokens]


def load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping: {path}")
    return data


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def normalize_dp_uri(value: str) -> str:
    return (value or "").strip().strip('"').strip("'")


def infer_domain(row: Dict[str, str]) -> str:
    """
    Domain precedence:
      1) explicit domain column, if future parser emits it
      2) infer from source_file:
           .../extracted/<DOMAIN>/config/...
      3) infer from source_file:
           .../<DOMAIN>/config/...
      4) empty -> caller marks missing context

    This is deterministic path evidence; it does NOT infer a domain from names.
    """
    explicit = (row.get("domain") or "").strip()
    if explicit:
        return explicit

    source_file = (row.get("source_file") or "").replace("\\", "/")
    parts = [p for p in source_file.split("/") if p]

    # Strongest known project layout:
    # export-.../extracted/STG/config/STG.cfg
    for i, part in enumerate(parts):
        if part == "extracted" and i + 2 < len(parts):
            if parts[i + 2] == "config":
                return parts[i + 1]

    # Generic DataPower export layout fallback:
    # .../<DOMAIN>/config/<file>.cfg
    for i, part in enumerate(parts):
        if part == "config" and i >= 1:
            return parts[i - 1]

    return ""


# ---------------------------------------------------------------------------
# Taxonomy loading / validation
# ---------------------------------------------------------------------------

def load_cross_mappings(cross_taxonomy_path: Path) -> List[Dict[str, Any]]:
    doc = load_yaml(cross_taxonomy_path)
    mappings = doc.get("mappings")
    if not isinstance(mappings, list):
        raise ValueError("cross_taxonomy.yaml must contain a mappings list")

    result: List[Dict[str, Any]] = []
    seen_ids = set()

    for idx, mapping in enumerate(mappings):
        if not isinstance(mapping, dict):
            raise ValueError(f"mappings[{idx}] must be a mapping")

        required = [
            "mapping_id",
            "source_type",
            "property_name",
            "property_kind",
            "reference_type",
            "relationship_type",
            "resolution_strategy",
        ]
        missing = [x for x in required if not mapping.get(x)]
        if missing:
            raise ValueError(
                f"mappings[{idx}] missing required keys: {', '.join(missing)}"
            )

        mid = str(mapping["mapping_id"])
        if mid in seen_ids:
            raise ValueError(f"Duplicate mapping_id: {mid}")
        seen_ids.add(mid)

        if not mapping.get("target_type") and not mapping.get("target_type_set"):
            # File and endpoint references intentionally have no object type.
            if mapping.get("property_kind") in {
                "object_reference",
                "compound_reference",
            }:
                raise ValueError(
                    f"{mid}: object/compound reference requires target_type "
                    "or target_type_set"
                )

        result.append(mapping)

    return result


def load_reference_types(reference_types_path: Path) -> Dict[str, Dict[str, Any]]:
    doc = load_yaml(reference_types_path)
    refs = doc.get("reference_types")
    if not isinstance(refs, dict):
        raise ValueError(
            "reference_types.yaml must contain reference_types mapping"
        )
    return refs


# ---------------------------------------------------------------------------
# Reference value extraction
# ---------------------------------------------------------------------------

def target_type_hint(mapping: Dict[str, Any]) -> str:
    if mapping.get("target_type"):
        return str(mapping["target_type"])

    allowed = mapping.get("target_type_set")
    if isinstance(allowed, list):
        return "|".join(str(x) for x in allowed)

    return ""


def extract_reference_value(
    mapping: Dict[str, Any],
    property_value: str,
) -> Tuple[str, str]:
    """
    Returns:
      raw_reference_value, target_name

    Important:
    - No target lookup happens here.
    - No object-name guessing happens here.
    - Compound references use the argument_position defined by taxonomy.
    """
    raw = (property_value or "").strip()
    kind = mapping.get("property_kind")

    if kind == "compound_reference":
        position = mapping.get("argument_position")
        if not isinstance(position, int) or position < 1:
            return raw, ""

        tokens = tokenize_cli_value(raw)
        idx = position - 1
        if idx >= len(tokens):
            return raw, ""

        return raw, tokens[idx]

    if kind == "object_reference":
        tokens = tokenize_cli_value(raw)
        return raw, tokens[0] if tokens else ""

    if kind == "file_reference":
        # Keep the DataPower URI intact. Resolution to inventory happens later.
        return raw, normalize_dp_uri(raw)

    if kind == "endpoint":
        # Endpoint parsing is a later stage. Preserve exact evidence here.
        return raw, raw

    # Future-safe behavior. A taxonomy gap must be visible, not guessed.
    return raw, ""


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def build_mapping_index(
    mappings: List[Dict[str, Any]],
) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)

    for mapping in mappings:
        key = (
            str(mapping["source_type"]),
            str(mapping["property_name"]),
        )
        index[key].append(mapping)

    return index


def extract_references(
    properties: List[Dict[str, str]],
    mappings: List[Dict[str, Any]],
    reference_types: Dict[str, Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:

    mapping_index = build_mapping_index(mappings)

    references: List[Dict[str, Any]] = []
    taxonomy_gaps: List[Dict[str, Any]] = []

    sequence = 0

    for prop in properties:
        source_type = (prop.get("canonical_type") or "").strip()
        property_name = (prop.get("property_name") or "").strip()

        applicable = mapping_index.get((source_type, property_name), [])
        if not applicable:
            continue

        source_domain = infer_domain(prop)

        for mapping in applicable:
            sequence += 1

            reference_type = str(mapping["reference_type"])
            ref_spec = reference_types.get(reference_type)

            if not isinstance(ref_spec, dict):
                taxonomy_gaps.append({
                    "gap_type": "undefined_reference_type",
                    "mapping_id": mapping["mapping_id"],
                    "source_type": source_type,
                    "property_name": property_name,
                    "reference_type": reference_type,
                    "source_file": prop.get("source_file", ""),
                    "source_line": prop.get("source_line", ""),
                })
                continue

            raw_reference, target_name = extract_reference_value(
                mapping,
                prop.get("property_value", ""),
            )

            if not raw_reference:
                status = "invalid_reference_value"
            elif (
                mapping.get("resolution_strategy", "").startswith("same_domain")
                and not source_domain
            ):
                status = "unresolved_due_to_missing_context"
            else:
                status = "pending"

            evidence_hash = (
                prop.get("raw_statement_sha256")
                or sha256_text(prop.get("raw_statement", raw_reference))
            )

            references.append({
                "reference_id": (
                    f"ref:{prop.get('environment','')}:"
                    f"{source_domain or 'domain-missing'}:{sequence}"
                ),
                "environment": prop.get("environment", ""),
                "domain": source_domain,

                "source_object_id": prop.get("object_id", ""),
                "source_occurrence_id": prop.get("occurrence_id", ""),
                "source_type": source_type,
                "source_name": prop.get("object_name", ""),

                "property_name": property_name,
                "property_path": (
                    prop.get("property_path") or property_name
                ),
                "property_ordinal": prop.get("ordinal", ""),

                "raw_reference": raw_reference,
                "reference_type": reference_type,
                "reference_family": ref_spec.get("family", ""),
                "target_identity_kind": ref_spec.get(
                    "target_identity_kind", ""
                ),

                "target_name": target_name,
                "target_type_hint": target_type_hint(mapping),

                "mapping_id": mapping["mapping_id"],
                "property_kind": mapping["property_kind"],
                "semantic_role": mapping.get("semantic_role", ""),
                "relationship_type_hint": mapping["relationship_type"],
                "resolution_strategy": mapping["resolution_strategy"],

                "source_line": prop.get("source_line", ""),
                "evidence_file": prop.get("source_file", ""),
                "evidence_hash": evidence_hash,

                "resolution_status": status,
                "extractor_version": EXTRACTOR_VERSION,
            })

    return references, taxonomy_gaps


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Extract DataPower references from parsed object properties using "
            "cross_taxonomy.yaml. This stage does NOT resolve relationships."
        )
    )

    ap.add_argument(
        "--properties",
        required=True,
        help="object_properties CSV produced by CFG parser",
    )
    ap.add_argument(
        "--cross-taxonomy",
        required=True,
        help="taxonomy/cross_taxonomy.yaml",
    )
    ap.add_argument(
        "--reference-types",
        required=True,
        help="taxonomy/reference_types.yaml",
    )
    ap.add_argument(
        "--output",
        default="index/references.csv",
    )
    ap.add_argument(
        "--taxonomy-gaps-output",
        default="index/reference_taxonomy_gaps.csv",
    )

    args = ap.parse_args()

    properties_path = Path(args.properties)
    cross_path = Path(args.cross_taxonomy)
    refs_path = Path(args.reference_types)

    for path in (properties_path, cross_path, refs_path):
        if not path.exists():
            print(f"[FATAL] Missing input: {path}")
            return 2

    properties = load_csv(properties_path)
    mappings = load_cross_mappings(cross_path)
    reference_types = load_reference_types(refs_path)

    references, taxonomy_gaps = extract_references(
        properties,
        mappings,
        reference_types,
    )

    fields = [
        "reference_id",
        "environment",
        "domain",
        "source_object_id",
        "source_occurrence_id",
        "source_type",
        "source_name",
        "property_name",
        "property_path",
        "property_ordinal",
        "raw_reference",
        "reference_type",
        "reference_family",
        "target_identity_kind",
        "target_name",
        "target_type_hint",
        "mapping_id",
        "property_kind",
        "semantic_role",
        "relationship_type_hint",
        "resolution_strategy",
        "source_line",
        "evidence_file",
        "evidence_hash",
        "resolution_status",
        "extractor_version",
    ]

    gap_fields = [
        "gap_type",
        "mapping_id",
        "source_type",
        "property_name",
        "reference_type",
        "source_file",
        "source_line",
    ]

    write_csv(Path(args.output), references, fields)
    write_csv(Path(args.taxonomy_gaps_output), taxonomy_gaps, gap_fields)

    by_family = Counter(r["reference_family"] for r in references)
    by_status = Counter(r["resolution_status"] for r in references)
    by_mapping = Counter(r["mapping_id"] for r in references)
    domains = {r["domain"] for r in references if r["domain"]}

    print("=" * 80)
    print("DATAPOWER REFERENCE EXTRACTOR V1")
    print("=" * 80)
    print(f"Extractor version:           {EXTRACTOR_VERSION}")
    print(f"Properties scanned:          {len(properties)}")
    print(f"Cross mappings loaded:       {len(mappings)}")
    print(f"References extracted:        {len(references)}")
    print(f"Domains observed:            {len(domains)}")
    print(f"Taxonomy gaps:               {len(taxonomy_gaps)}")

    print("-" * 80)
    print("Reference families:")
    for key, value in sorted(by_family.items()):
        print(f"  {key:35} {value}")

    print("-" * 80)
    print("Initial resolution status:")
    for key, value in sorted(by_status.items()):
        print(f"  {key:35} {value}")

    print("-" * 80)
    print("Top mappings:")
    for key, value in by_mapping.most_common(20):
        print(f"  {key:45} {value}")

    print("-" * 80)

    if taxonomy_gaps:
        print("REFERENCE EXTRACTOR V1: FAILED — TAXONOMY GAPS")
        return 1

    print("REFERENCE EXTRACTOR V1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
