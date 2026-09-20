#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Tuple


RESOLVER_VERSION = "1.0-architecture-beta-exact-path"


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def strip_quotes(value: str) -> str:
    v = (value or "").strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in {'"', "'"}:
        return v[1:-1].strip()
    return v


def normalize_relative_path(value: str) -> Tuple[str, str]:
    """
    Convert DataPower file URI to inventory relative_path.

      local:///a/b.xsl   -> local/a/b.xsl
      store:///a/b.xsl   -> store/a/b.xsl
      cert:///a.pem      -> cert/a.pem
      pubcert:///a.cer   -> pubcert/a.cer

    Returns: (normalized_path, normalization_status)

    This is URI/path normalization only. It does not guess by basename.
    """
    raw = strip_quotes(value)
    if not raw:
        return "", "invalid_empty_reference"

    m = re.match(r"^([A-Za-z][A-Za-z0-9+.-]*):/{0,3}(.*)$", raw)
    if not m:
        # Relative evidence is accepted only as already-relative path.
        candidate = raw.replace("\\", "/").lstrip("/")
        if not candidate:
            return "", "invalid_empty_reference"
        return str(PurePosixPath(candidate)), "normalized_relative_path"

    scheme = m.group(1).lower()
    remainder = m.group(2).replace("\\", "/").lstrip("/")

    supported = {"local", "store", "cert", "pubcert"}
    if scheme not in supported:
        return "", f"unsupported_file_uri_scheme:{scheme}"

    if not remainder:
        return "", "invalid_missing_path"

    normalized = str(PurePosixPath(scheme) / PurePosixPath(remainder))
    return normalized, "normalized_datapower_uri"


def build_inventory_index(
    inventory: List[Dict[str, str]]
) -> Dict[Tuple[str, str], List[Dict[str, str]]]:
    index: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in inventory:
        env = (row.get("environment") or "").strip()
        rel = (row.get("relative_path") or "").replace("\\", "/").lstrip("/")
        if env and rel:
            index[(env, str(PurePosixPath(rel)))].append(row)
    return index


def resolve(
    refs: List[Dict[str, str]],
    inventory: List[Dict[str, str]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:

    index = build_inventory_index(inventory)
    resolved: List[Dict[str, Any]] = []
    unresolved: List[Dict[str, Any]] = []

    for ref in refs:
        if (ref.get("reference_family") or "") != "file_reference":
            continue

        env = (ref.get("environment") or "").strip()
        raw = ref.get("target_name") or ref.get("raw_reference") or ""
        normalized_path, norm_status = normalize_relative_path(raw)

        base = {
            "reference_id": ref.get("reference_id", ""),
            "environment": env,
            "domain": ref.get("domain", ""),
            "source_object_id": ref.get("source_object_id", ""),
            "source_type": ref.get("source_type", ""),
            "source_name": ref.get("source_name", ""),
            "property_name": ref.get("property_name", ""),
            "reference_type": ref.get("reference_type", ""),
            "relationship_type": ref.get("relationship_type_hint", ""),
            "raw_reference": ref.get("raw_reference", ""),
            "target_name": ref.get("target_name", ""),
            "normalized_relative_path": normalized_path,
            "normalization_status": norm_status,
            "source_line": ref.get("source_line", ""),
            "evidence_file": ref.get("evidence_file", ""),
            "resolver_version": RESOLVER_VERSION,
        }

        if not normalized_path:
            unresolved.append({
                **base,
                "resolution_status": "unresolved_due_to_invalid_file_reference",
                "candidate_count": 0,
                "target_file_id": "",
                "target_relative_path": "",
                "target_classification": "",
                "target_sha256": "",
                "target_sensitivity_scan_status": "",
                "target_contains_sensitive_content": "",
            })
            continue

        candidates = index.get((env, normalized_path), [])

        if len(candidates) == 0:
            unresolved.append({
                **base,
                "resolution_status": "unresolved_file_not_found",
                "candidate_count": 0,
                "target_file_id": "",
                "target_relative_path": "",
                "target_classification": "",
                "target_sha256": "",
                "target_sensitivity_scan_status": "",
                "target_contains_sensitive_content": "",
            })
            continue

        if len(candidates) > 1:
            unresolved.append({
                **base,
                "resolution_status": "unresolved_ambiguous_file",
                "candidate_count": len(candidates),
                "target_file_id": "",
                "target_relative_path": "",
                "target_classification": "",
                "target_sha256": "",
                "target_sensitivity_scan_status": "",
                "target_contains_sensitive_content": "",
            })
            continue

        target = candidates[0]
        resolved.append({
            **base,
            "resolution_status": "resolved_exact",
            "candidate_count": 1,
            "target_file_id": target.get("file_id", ""),
            "target_relative_path": target.get("relative_path", ""),
            "target_classification": target.get("classification", ""),
            "target_sha256": target.get("sha256", ""),
            "target_sensitivity_scan_status": target.get(
                "sensitivity_scan_status", ""
            ),
            "target_contains_sensitive_content": target.get(
                "contains_sensitive_content", ""
            ),
        })

    return resolved, unresolved


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Resolve DataPower file references against canonical File Inventory "
            "using exact environment + normalized relative_path matching."
        )
    )
    ap.add_argument("--references", required=True)
    ap.add_argument("--inventory", required=True)
    ap.add_argument(
        "--resolved-output",
        default="index/file_relationships.csv",
    )
    ap.add_argument(
        "--unresolved-output",
        default="index/unresolved_file_references.csv",
    )
    args = ap.parse_args()

    refs_path = Path(args.references)
    inventory_path = Path(args.inventory)

    for path in (refs_path, inventory_path):
        if not path.exists():
            print(f"[FATAL] Missing input: {path}")
            return 2

    refs = load_csv(refs_path)
    inventory = load_csv(inventory_path)

    required_inventory = {"file_id", "environment", "relative_path"}
    inventory_fields = set(inventory[0].keys()) if inventory else set()
    missing = required_inventory - inventory_fields
    if missing:
        print(
            f"[FATAL] Inventory missing required fields: {sorted(missing)}"
        )
        return 2

    resolved, unresolved = resolve(refs, inventory)

    fields = [
        "reference_id",
        "environment",
        "domain",
        "source_object_id",
        "source_type",
        "source_name",
        "property_name",
        "reference_type",
        "relationship_type",
        "raw_reference",
        "target_name",
        "normalized_relative_path",
        "normalization_status",
        "resolution_status",
        "candidate_count",
        "target_file_id",
        "target_relative_path",
        "target_classification",
        "target_sha256",
        "target_sensitivity_scan_status",
        "target_contains_sensitive_content",
        "source_line",
        "evidence_file",
        "resolver_version",
    ]

    write_csv(Path(args.resolved_output), resolved, fields)
    write_csv(Path(args.unresolved_output), unresolved, fields)

    status = Counter(
        [r["resolution_status"] for r in resolved]
        + [r["resolution_status"] for r in unresolved]
    )
    relationship_counts = Counter(
        r["relationship_type"] for r in resolved
    )
    classification_counts = Counter(
        r["target_classification"] for r in resolved
    )

    print("=" * 80)
    print("DATAPOWER FILE REFERENCE RESOLVER V1")
    print("=" * 80)
    print(f"Resolver version:             {RESOLVER_VERSION}")
    print(f"References loaded:            {len(refs)}")
    print(f"Inventory files loaded:       {len(inventory)}")
    print(f"File references processed:    {len(resolved) + len(unresolved)}")
    print(f"Resolved exact:               {len(resolved)}")
    print(f"Unresolved file references:   {len(unresolved)}")
    print("-" * 80)
    print("Resolution status:")
    for key, value in sorted(status.items()):
        print(f"  {key:40} {value}")
    print("-" * 80)
    print("Resolved relationship types:")
    for key, value in relationship_counts.most_common():
        print(f"  {key:45} {value}")
    print("-" * 80)
    print("Resolved file classifications:")
    for key, value in classification_counts.most_common():
        print(f"  {key:45} {value}")
    print("-" * 80)

    if unresolved:
        print(
            "FILE REFERENCE RESOLVER V1: PASS WITH UNRESOLVED REFERENCES"
        )
    else:
        print("FILE REFERENCE RESOLVER V1: PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
