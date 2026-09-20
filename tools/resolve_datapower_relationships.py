#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple


RESOLVER_VERSION = "1.0-architecture-beta-domain-aware"


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


def infer_domain(row: Dict[str, str]) -> str:
    explicit = (row.get("domain") or "").strip()
    if explicit:
        return explicit

    source_file = (row.get("source_file") or row.get("evidence_file") or "").replace("\\", "/")
    parts = [p for p in source_file.split("/") if p]

    for i, part in enumerate(parts):
        if part == "extracted" and i + 2 < len(parts):
            if parts[i + 2] == "config":
                return parts[i + 1]

    for i, part in enumerate(parts):
        if part == "config" and i >= 1:
            return parts[i - 1]

    return ""


def unique_logical_objects(objects: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    """
    Collapse repeated occurrences to logical object identity.
    The parser already gives object_id, so repeated occurrences are not
    treated as ambiguity.
    """
    by_id: Dict[str, Dict[str, str]] = {}
    for row in objects:
        oid = (row.get("object_id") or "").strip()
        if not oid:
            continue
        by_id.setdefault(oid, row)
    return by_id


def build_object_index(
    objects_by_id: Dict[str, Dict[str, str]]
) -> Dict[Tuple[str, str, str, str], List[str]]:
    """
    Exact lookup key:
      environment + domain + canonical_type + object_name

    No fuzzy lookup.
    No fallback to name-only matching.
    """
    index: Dict[Tuple[str, str, str, str], List[str]] = defaultdict(list)

    for oid, row in objects_by_id.items():
        env = (row.get("environment") or "").strip()
        domain = infer_domain(row)
        ctype = (row.get("canonical_type") or "").strip()
        name = (row.get("object_name") or "").strip()

        index[(env, domain, ctype, name)].append(oid)

    return index


def parse_target_types(hint: str) -> List[str]:
    if not hint:
        return []
    return [x.strip() for x in hint.split("|") if x.strip()]


def resolve_object_reference(
    ref: Dict[str, str],
    object_index: Dict[Tuple[str, str, str, str], List[str]],
    objects_by_id: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:

    env = (ref.get("environment") or "").strip()
    domain = (ref.get("domain") or "").strip()
    target_name = (ref.get("target_name") or "").strip()
    target_types = parse_target_types(ref.get("target_type_hint") or "")

    base = {
        "reference_id": ref.get("reference_id", ""),
        "environment": env,
        "domain": domain,

        "source_object_id": ref.get("source_object_id", ""),
        "source_type": ref.get("source_type", ""),
        "source_name": ref.get("source_name", ""),

        "relationship_type": ref.get("relationship_type_hint", ""),
        "property_name": ref.get("property_name", ""),
        "property_path": ref.get("property_path", ""),
        "raw_reference": ref.get("raw_reference", ""),
        "target_name": target_name,
        "target_type_hint": ref.get("target_type_hint", ""),

        "source_line": ref.get("source_line", ""),
        "evidence_file": ref.get("evidence_file", ""),
        "evidence_hash": ref.get("evidence_hash", ""),
        "mapping_id": ref.get("mapping_id", ""),
        "resolution_strategy": ref.get("resolution_strategy", ""),
        "resolver_version": RESOLVER_VERSION,
    }

    if not target_name:
        return {
            **base,
            "resolution_status": "invalid_reference_value",
            "target_object_id": "",
            "target_type": "",
            "target_object_name": "",
            "candidate_count": 0,
        }

    if not domain:
        return {
            **base,
            "resolution_status": "unresolved_due_to_missing_domain",
            "target_object_id": "",
            "target_type": "",
            "target_object_name": "",
            "candidate_count": 0,
        }

    if not target_types:
        return {
            **base,
            "resolution_status": "unresolved_due_to_missing_target_type_hint",
            "target_object_id": "",
            "target_type": "",
            "target_object_name": "",
            "candidate_count": 0,
        }

    candidates: List[str] = []

    for target_type in target_types:
        key = (env, domain, target_type, target_name)
        candidates.extend(object_index.get(key, []))

    unique_candidates = sorted(set(candidates))

    if len(unique_candidates) == 0:
        return {
            **base,
            "resolution_status": "unresolved_target_not_found",
            "target_object_id": "",
            "target_type": "",
            "target_object_name": "",
            "candidate_count": 0,
        }

    if len(unique_candidates) > 1:
        return {
            **base,
            "resolution_status": "unresolved_ambiguous_target",
            "target_object_id": "",
            "target_type": "",
            "target_object_name": "",
            "candidate_count": len(unique_candidates),
        }

    target_oid = unique_candidates[0]
    target = objects_by_id[target_oid]

    return {
        **base,
        "resolution_status": "resolved_exact",
        "target_object_id": target_oid,
        "target_type": target.get("canonical_type", ""),
        "target_object_name": target.get("object_name", ""),
        "candidate_count": 1,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Resolve DataPower object references into exact same-domain "
            "relationships using objects.csv + references.csv."
        )
    )

    ap.add_argument(
        "--objects",
        required=True,
        help="objects CSV produced by CFG parser",
    )
    ap.add_argument(
        "--references",
        required=True,
        help="references CSV produced by Reference Extractor V1",
    )
    ap.add_argument(
        "--relationships-output",
        default="index/relationships.csv",
    )
    ap.add_argument(
        "--unresolved-output",
        default="index/unresolved_relationships.csv",
    )
    ap.add_argument(
        "--passthrough-output",
        default="index/non_object_references.csv",
        help="File/endpoint references preserved for later resolvers",
    )

    args = ap.parse_args()

    objects_path = Path(args.objects)
    references_path = Path(args.references)

    for path in (objects_path, references_path):
        if not path.exists():
            print(f"[FATAL] Missing input: {path}")
            return 2

    objects = load_csv(objects_path)
    references = load_csv(references_path)

    objects_by_id = unique_logical_objects(objects)
    object_index = build_object_index(objects_by_id)

    resolved_rows: List[Dict[str, Any]] = []
    unresolved_rows: List[Dict[str, Any]] = []
    passthrough_rows: List[Dict[str, Any]] = []

    for ref in references:
        family = (ref.get("reference_family") or "").strip()

        if family != "object_reference":
            passthrough_rows.append({
                "reference_id": ref.get("reference_id", ""),
                "environment": ref.get("environment", ""),
                "domain": ref.get("domain", ""),
                "reference_family": family,
                "reference_type": ref.get("reference_type", ""),
                "source_object_id": ref.get("source_object_id", ""),
                "source_type": ref.get("source_type", ""),
                "source_name": ref.get("source_name", ""),
                "property_name": ref.get("property_name", ""),
                "raw_reference": ref.get("raw_reference", ""),
                "target_name": ref.get("target_name", ""),
                "mapping_id": ref.get("mapping_id", ""),
                "relationship_type_hint": ref.get("relationship_type_hint", ""),
                "source_line": ref.get("source_line", ""),
                "evidence_file": ref.get("evidence_file", ""),
                "resolution_status": "deferred_to_specialized_resolver",
                "resolver_version": RESOLVER_VERSION,
            })
            continue

        row = resolve_object_reference(ref, object_index, objects_by_id)

        if row["resolution_status"] == "resolved_exact":
            resolved_rows.append(row)
        else:
            unresolved_rows.append(row)

    relationship_fields = [
        "reference_id",
        "environment",
        "domain",
        "source_object_id",
        "source_type",
        "source_name",
        "relationship_type",
        "target_object_id",
        "target_type",
        "target_object_name",
        "property_name",
        "property_path",
        "raw_reference",
        "target_name",
        "target_type_hint",
        "mapping_id",
        "resolution_strategy",
        "resolution_status",
        "candidate_count",
        "source_line",
        "evidence_file",
        "evidence_hash",
        "resolver_version",
    ]

    passthrough_fields = [
        "reference_id",
        "environment",
        "domain",
        "reference_family",
        "reference_type",
        "source_object_id",
        "source_type",
        "source_name",
        "property_name",
        "raw_reference",
        "target_name",
        "mapping_id",
        "relationship_type_hint",
        "source_line",
        "evidence_file",
        "resolution_status",
        "resolver_version",
    ]

    write_csv(
        Path(args.relationships_output),
        resolved_rows,
        relationship_fields,
    )

    write_csv(
        Path(args.unresolved_output),
        unresolved_rows,
        relationship_fields,
    )

    write_csv(
        Path(args.passthrough_output),
        passthrough_rows,
        passthrough_fields,
    )

    status_counts = Counter(
        [r["resolution_status"] for r in resolved_rows]
        + [r["resolution_status"] for r in unresolved_rows]
    )

    relation_counts = Counter(
        r["relationship_type"] for r in resolved_rows
    )

    domains = {
        r["domain"]
        for r in resolved_rows + unresolved_rows
        if r.get("domain")
    }

    object_refs_total = len(resolved_rows) + len(unresolved_rows)

    print("=" * 80)
    print("DATAPOWER RELATIONSHIP RESOLVER V1")
    print("=" * 80)
    print(f"Resolver version:            {RESOLVER_VERSION}")
    print(f"Objects loaded:              {len(objects)}")
    print(f"Unique logical objects:      {len(objects_by_id)}")
    print(f"References loaded:           {len(references)}")
    print(f"Object references processed: {object_refs_total}")
    print(f"Resolved relationships:      {len(resolved_rows)}")
    print(f"Unresolved object refs:      {len(unresolved_rows)}")
    print(f"Deferred non-object refs:    {len(passthrough_rows)}")
    print(f"Domains observed:            {len(domains)}")

    print("-" * 80)
    print("Resolution status:")
    for key, value in sorted(status_counts.items()):
        print(f"  {key:38} {value}")

    print("-" * 80)
    print("Resolved relationship types:")
    for key, value in relation_counts.most_common():
        print(f"  {key:45} {value}")

    print("-" * 80)

    if unresolved_rows:
        print(
            "RELATIONSHIP RESOLVER V1: PASS WITH UNRESOLVED REFERENCES "
            "(see unresolved output)"
        )
    else:
        print("RELATIONSHIP RESOLVER V1: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
