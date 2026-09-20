#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

from taxonomy_loader import get_mapping, load_taxonomies

RUNTIME_DEFAULTS = {
    "sensitivity_scan_status": "not_scanned",
    "contains_sensitive_content": None,
    "detected_secret_count": 0,
    "detected_sensitivity_types": [],
    "sanitized_content_available": False,
    "sensitivity_scan_timestamp": None,
}


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def derive_environment(relative_to_exported: Path) -> str:
    if not relative_to_exported.parts:
        return "unclassified_due_to_missing_environment_path"
    return relative_to_exported.parts[0]


def build_rule_indexes(file_types: Dict[str, Any], case_sensitive_extensions: bool,
                       case_sensitive_filenames: bool) -> Tuple[Dict[str, str], Dict[str, str]]:
    ext_index: Dict[str, str] = {}
    filename_index: Dict[str, str] = {}
    for file_type, spec in file_types.items():
        for ext in spec.get("extensions", []) or []:
            key = ext if case_sensitive_extensions else ext.lower()
            if key in ext_index and ext_index[key] != file_type:
                raise ValueError(f"Duplicate extension rule {ext!r}: {ext_index[key]!r} and {file_type!r}")
            ext_index[key] = file_type
        for filename in spec.get("exact_filenames", []) or []:
            key = filename if case_sensitive_filenames else filename.lower()
            if key in filename_index and filename_index[key] != file_type:
                raise ValueError(f"Duplicate exact filename rule {filename!r}: {filename_index[key]!r} and {file_type!r}")
            filename_index[key] = file_type
    return ext_index, filename_index


def classify_file(path: Path, unclassified_types: Dict[str, Any], classification_rules: Dict[str, Any],
                  ext_index: Dict[str, str], filename_index: Dict[str, str]) -> Tuple[str, str, str, str]:
    cs_ext = classification_rules.get("case_sensitive_extensions", False)
    cs_name = classification_rules.get("case_sensitive_filenames", False)
    filename_key = path.name if cs_name else path.name.lower()
    ext = path.suffix if cs_ext else path.suffix.lower()

    if filename_key in filename_index:
        ft = filename_index[filename_key]
        return ft, "classified", f"Exact filename matched taxonomy rule for {ft}", f"exact_filename:{path.name}"

    if ext:
        if ext in ext_index:
            ft = ext_index[ext]
            return ft, "classified", f"Extension {path.suffix!r} matched taxonomy rule for {ft}", f"extension:{path.suffix}"
        fallback = "unclassified_due_to_unsupported_extension"
        if fallback not in unclassified_types:
            raise KeyError(f"Missing required unclassified file type {fallback!r}")
        return fallback, fallback, f"Extension {path.suffix!r} has no taxonomy classification rule", f"unsupported_extension:{path.suffix}"

    fallback = "unclassified_due_to_missing_extension"
    if fallback not in unclassified_types:
        raise KeyError(f"Missing required unclassified file type {fallback!r}")
    return fallback, fallback, "File has no extension and no exact filename classification matched", "missing_extension"


def merge_effective_flags(defaults: Dict[str, Any], agent_mode: Dict[str, Any], file_type_flags: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    for key, value in (agent_mode or {}).items():
        if key in defaults:
            merged[key] = value
    merged.update(file_type_flags or {})
    return merged


def make_file_id(environment: str, relative_path_inside_environment: str) -> str:
    return f"file:{environment}:{relative_path_inside_environment}"


def json_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def build_inventory(exported_dir: Path, taxonomy_dir: Path, output_csv: Path) -> int:
    bundle = load_taxonomies(taxonomy_dir)
    file_taxonomy = bundle.file_types
    classification_rules = get_mapping(file_taxonomy, "classification_rules", "file_types")
    standard_flags = get_mapping(get_mapping(file_taxonomy, "standard_flags", "file_types"), "defaults", "file_types.standard_flags")
    agent_modes = get_mapping(file_taxonomy, "agent_indexing_modes", "file_types")
    file_types = get_mapping(file_taxonomy, "file_types", "file_types")
    unclassified_types = get_mapping(file_taxonomy, "unclassified_file_types", "file_types")

    ext_index, filename_index = build_rule_indexes(
        file_types,
        classification_rules.get("case_sensitive_extensions", False),
        classification_rules.get("case_sensitive_filenames", False),
    )

    required_fields = list(file_taxonomy.get("classification_output", {}).get("required_fields", []))
    if not required_fields:
        raise ValueError("file_types.classification_output.required_fields is empty or missing")

    extra_fields = ["raw_content_policy", "absolute_path"]
    fieldnames = required_fields + [f for f in extra_fields if f not in required_fields]
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    row_count = classified_count = unclassified_count = 0

    with output_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()

        for path in iter_files(exported_dir):
            rel_exported = path.relative_to(exported_dir)
            environment = derive_environment(rel_exported)
            rel_inside_env = Path(*rel_exported.parts[1:]) if len(rel_exported.parts) > 1 else Path(path.name)

            classification, status, reason, rule = classify_file(
                path, unclassified_types, classification_rules, ext_index, filename_index
            )

            if classification in file_types:
                spec = file_types[classification]
                classified_count += 1
            else:
                spec = unclassified_types[classification]
                unclassified_count += 1

            agent_indexing = spec.get("agent_indexing", "metadata_only")
            if agent_indexing not in agent_modes:
                raise KeyError(f"{classification}: undefined agent_indexing mode {agent_indexing!r}")

            agent_mode = agent_modes[agent_indexing]
            effective_flags = merge_effective_flags(standard_flags, agent_mode, spec.get("flags", {}) or {})

            row: Dict[str, Any] = {
                "file_id": make_file_id(environment, rel_inside_env.as_posix()),
                "environment": environment,
                "relative_path": rel_inside_env.as_posix(),
                "file_name": path.name,
                "extension": path.suffix,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "classification": classification,
                "classification_status": status,
                "classification_reason": reason,
                "classification_rule": rule,
                "agent_indexing": agent_indexing,
                "raw_content_policy": agent_mode.get("raw_content_policy", ""),
                "absolute_path": str(path.resolve()),
            }
            row.update(effective_flags)
            row.update(RUNTIME_DEFAULTS)

            missing = [f for f in required_fields if f not in row]
            if missing:
                raise ValueError(f"{classification}: output row is missing required fields: {missing}")

            writer.writerow({k: json_cell(row.get(k)) for k in fieldnames})
            row_count += 1

    print("=" * 72)
    print("DATAPOWER FILE INVENTORY")
    print("=" * 72)
    print(f"Exported directory:   {exported_dir}")
    print(f"Taxonomy directory:   {taxonomy_dir}")
    print(f"Output:               {output_csv}")
    print("-" * 72)
    print(f"Files indexed:        {row_count}")
    print(f"Classified files:     {classified_count}")
    print(f"Unclassified files:   {unclassified_count}")
    print("-" * 72)
    print("FILE INVENTORY BUILD: PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical DataPower file inventory from exported archives.")
    parser.add_argument("--exported-dir", default="export-stg-uat", help="Root directory containing extracted DataPower domains (default: exported)")
    parser.add_argument("--taxonomy-dir", default="taxonomy", help="Taxonomy directory (default: taxonomy)")
    parser.add_argument("--output", default="index/files.csv", help="Output CSV path (default: index/files.csv)")
    args = parser.parse_args()

    exported_dir = Path(args.exported_dir).resolve()
    taxonomy_dir = Path(args.taxonomy_dir).resolve()
    output_csv = Path(args.output).resolve()

    if not exported_dir.exists() or not exported_dir.is_dir():
        print(f"FILE INVENTORY BUILD: FAILED\n[FATAL] Exported directory invalid: {exported_dir}", file=sys.stderr)
        return 2

    try:
        return build_inventory(exported_dir, taxonomy_dir, output_csv)
    except Exception as exc:
        print("FILE INVENTORY BUILD: FAILED", file=sys.stderr)
        print(f"[FATAL] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
