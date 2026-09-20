#!/usr/bin/env python3
"""
DataPower Atlas - Operation Journey Builder V1

Purpose
-------
Decompose large DataPower service processing policies into operation-level
journeys using only resolved graph evidence.

Evidence model
--------------
Service Root
  -> uses_processing_policy -> style_policy / web_service_proxy_processing_policy
Policy
  -> uses_matching_rule
  -> contains_processing_rule
Processing Rule
  -> contains_processing_action -> processing_action

For style-policy `match` statements, matching-rule and processing-rule
relationships are paired by the same evidence line. This avoids name guessing.

The tool never infers relationships from object names.

Outputs
-------
1) JSONL: detailed operation journey records.
2) CSV: compact operation summary.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Any, Iterable, Tuple

VERSION = "1.0-evidence-only"

SERVICE_ROOT_TYPES = {
    "multi_protocol_gateway",
    "web_service_proxy",
}

PROCESSING_POLICY_TYPES = {
    "style_policy",
    "web_service_proxy_processing_policy",
}

PROCESSING_RULE_TYPES = {
    "processing_rule",
    "web_service_proxy_processing_rule",
}


def load_csv(path: Path) -> List[Dict[str, str]]:
    if not path or not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stable_id(parts: List[str]) -> str:
    raw = "\x1f".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:20]


def unique_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for v in values:
        if v and v not in seen:
            seen.add(v)
            result.append(v)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", required=True)
    ap.add_argument("--properties", required=True)
    ap.add_argument("--relationships", required=True)
    ap.add_argument("--endpoints", required=False)
    ap.add_argument("--file-relationships", required=False)
    ap.add_argument("--output", required=True)
    ap.add_argument("--summary-output", required=True)
    args = ap.parse_args()

    objects = load_csv(Path(args.objects))
    properties = load_csv(Path(args.properties))
    relationships = load_csv(Path(args.relationships))
    endpoints = load_csv(Path(args.endpoints)) if args.endpoints else []
    file_rels = load_csv(Path(args.file_relationships)) if args.file_relationships else []

    object_by_id = {r["object_id"]: r for r in objects}

    outgoing = defaultdict(list)
    for r in relationships:
        outgoing[r["source_object_id"]].append(r)

    endpoints_by_source = defaultdict(list)
    for e in endpoints:
        endpoints_by_source[e.get("source_object_id", "")].append(e)

    files_by_source = defaultdict(list)
    for f in file_rels:
        files_by_source[f.get("source_object_id", "")].append(f)

    roots = [
        o for o in objects
        if o.get("canonical_type") in SERVICE_ROOT_TYPES
    ]

    operation_records: List[Dict[str, Any]] = []

    for root in roots:
        root_id = root["object_id"]

        policy_edges = [
            r for r in outgoing.get(root_id, [])
            if r.get("relationship_type") == "uses_processing_policy"
            and r.get("target_type") in PROCESSING_POLICY_TYPES
        ]

        for policy_edge in policy_edges:
            policy_id = policy_edge["target_object_id"]
            policy_obj = object_by_id.get(policy_id, {})
            policy_rels = outgoing.get(policy_id, [])

            # Pair matching rule and processing rule by exact policy evidence line.
            by_evidence = defaultdict(list)
            for rel in policy_rels:
                if rel.get("property_name") == "match":
                    key = (
                        rel.get("evidence_file", ""),
                        rel.get("source_line", ""),
                        rel.get("property_path", ""),
                    )
                    by_evidence[key].append(rel)

            for key, rels in sorted(by_evidence.items(), key=lambda kv: (kv[0][0], int(kv[0][1] or 0))):
                matching = [
                    r for r in rels
                    if r.get("relationship_type") == "uses_matching_rule"
                ]
                processing = [
                    r for r in rels
                    if r.get("relationship_type") == "contains_processing_rule"
                    and r.get("target_type") in PROCESSING_RULE_TYPES
                ]

                # A match line without a processing rule is preserved as an incomplete operation.
                proc_edges = processing or [None]

                for proc_edge in proc_edges:
                    proc_id = proc_edge["target_object_id"] if proc_edge else ""
                    proc_obj = object_by_id.get(proc_id, {}) if proc_id else {}

                    action_edges = [
                        r for r in outgoing.get(proc_id, [])
                        if r.get("relationship_type") == "contains_processing_action"
                        and r.get("target_type") == "processing_action"
                    ] if proc_id else []

                    action_ids = unique_keep_order(r["target_object_id"] for r in action_edges)
                    action_names = unique_keep_order(r["target_object_name"] for r in action_edges)

                    dependency_sources = [root_id, policy_id, proc_id] + action_ids
                    dependency_sources = [x for x in dependency_sources if x]

                    op_endpoints = []
                    for source_id in dependency_sources:
                        op_endpoints.extend(endpoints_by_source.get(source_id, []))

                    op_files = []
                    for source_id in dependency_sources:
                        op_files.extend(files_by_source.get(source_id, []))

                    domain = (
                        policy_edge.get("domain")
                        or next((r.get("domain") for r in rels if r.get("domain")), "")
                    )
                    environment = root.get("environment", "")

                    evidence_line = key[1]
                    operation_id = (
                        f"op:{environment}:{domain}:{stable_id([root_id, policy_id, key[0], evidence_line, proc_id])}"
                    )

                    match_names = unique_keep_order(r.get("target_object_name", "") for r in matching)
                    match_ids = unique_keep_order(r.get("target_object_id", "") for r in matching)

                    action_types = []
                    for aid in action_ids:
                        # action subtype is represented by its properties, so preserve generic type here.
                        action_types.append(object_by_id.get(aid, {}).get("canonical_type", "processing_action"))

                    operation_records.append({
                        "operation_id": operation_id,
                        "environment": environment,
                        "domain": domain,
                        "parent_service_id": root_id,
                        "parent_service_type": root.get("canonical_type", ""),
                        "parent_service_name": root.get("object_name", ""),
                        "processing_policy_id": policy_id,
                        "processing_policy_type": policy_edge.get("target_type", ""),
                        "processing_policy_name": policy_edge.get("target_object_name", ""),
                        "match_evidence_file": key[0],
                        "match_source_line": evidence_line,
                        "matching_rule_ids": match_ids,
                        "matching_rule_names": match_names,
                        "processing_rule_id": proc_id,
                        "processing_rule_type": proc_edge.get("target_type", "") if proc_edge else "",
                        "processing_rule_name": proc_edge.get("target_object_name", "") if proc_edge else "",
                        "processing_rule_found": bool(proc_edge),
                        "action_ids": action_ids,
                        "action_names": action_names,
                        "action_count": len(action_ids),
                        "endpoint_dependencies": [
                            {
                                "endpoint_id": e.get("endpoint_id", ""),
                                "route_role": e.get("route_role", ""),
                                "normalized_endpoint": e.get("normalized_endpoint", ""),
                                "source_object_id": e.get("source_object_id", ""),
                            }
                            for e in op_endpoints
                        ],
                        "endpoint_count": len({e.get("endpoint_id", "") for e in op_endpoints if e.get("endpoint_id")}),
                        "file_dependencies": [
                            {
                                "target_file_id": f.get("target_file_id", ""),
                                "target_relative_path": f.get("target_relative_path", ""),
                                "classification": f.get("target_classification", ""),
                                "relationship_type": f.get("relationship_type", ""),
                                "source_object_id": f.get("source_object_id", ""),
                            }
                            for f in op_files
                        ],
                        "file_count": len({
                            f.get("target_file_id", "") or f.get("target_relative_path", "")
                            for f in op_files
                            if f.get("target_file_id") or f.get("target_relative_path")
                        }),
                        "builder_version": VERSION,
                    })

    summary = []
    for op in operation_records:
        summary.append({
            "operation_id": op["operation_id"],
            "environment": op["environment"],
            "domain": op["domain"],
            "parent_service_name": op["parent_service_name"],
            "parent_service_type": op["parent_service_type"],
            "processing_policy_name": op["processing_policy_name"],
            "matching_rule_names": "|".join(op["matching_rule_names"]),
            "processing_rule_name": op["processing_rule_name"],
            "processing_rule_found": str(op["processing_rule_found"]).lower(),
            "action_count": op["action_count"],
            "endpoint_count": op["endpoint_count"],
            "file_count": op["file_count"],
            "match_source_line": op["match_source_line"],
            "builder_version": VERSION,
        })

    write_jsonl(Path(args.output), operation_records)
    fields = [
        "operation_id",
        "environment",
        "domain",
        "parent_service_name",
        "parent_service_type",
        "processing_policy_name",
        "matching_rule_names",
        "processing_rule_name",
        "processing_rule_found",
        "action_count",
        "endpoint_count",
        "file_count",
        "match_source_line",
        "builder_version",
    ]
    write_csv(Path(args.summary_output), summary, fields)

    print("=" * 80)
    print("DATAPOWER OPERATION JOURNEY BUILDER V1")
    print("=" * 80)
    print(f"Builder version:          {VERSION}")
    print(f"Service roots scanned:    {len(roots)}")
    print(f"Operations built:         {len(operation_records)}")
    print(f"Services with operations: {len(set(o['parent_service_id'] for o in operation_records))}")
    print(f"Output:                   {args.output}")
    print(f"Summary:                  {args.summary_output}")
    print("-" * 80)

    by_service = defaultdict(int)
    for op in operation_records:
        by_service[op["parent_service_name"]] += 1
    for name, count in sorted(by_service.items(), key=lambda x: (-x[1], x[0])):
        print(f"{name:55} {count:6}")

    incomplete = sum(1 for o in operation_records if not o["processing_rule_found"])
    print("-" * 80)
    print(f"Operations missing processing rule: {incomplete}")
    print("OPERATION JOURNEY BUILDER V1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
