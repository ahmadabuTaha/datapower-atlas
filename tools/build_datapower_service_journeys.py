#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


BUILDER_VERSION = "1.0-architecture-beta-evidence-only"

ROOT_TYPES = {
    "multi_protocol_gateway",
    "tcp_proxy",
    "web_service_proxy",
    "xml_firewall",
}

PROCESSING_RELATIONSHIPS = {
    "uses_processing_policy",
    "contains_processing_rule",
    "contains_processing_action",
    "uses_matching_rule",
}

SECURITY_RELATIONSHIPS = {
    "uses_tls_client_profile",
    "uses_tls_server_profile",
    "uses_aaa_policy",
    "uses_crypto_identification_credentials",
    "uses_crypto_validation_credentials",
    "uses_crypto_certificate",
    "uses_crypto_key",
}

INGRESS_RELATIONSHIPS = {
    "uses_front_side_handler",
}

SUPPORT_RELATIONSHIPS = {
    "uses_xml_manager",
    "uses_user_agent",
}


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


def unique_objects(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    result: Dict[str, Dict[str, str]] = {}
    for row in rows:
        oid = row.get("object_id", "")
        if oid:
            result.setdefault(oid, row)
    return result


def properties_by_object(
    rows: List[Dict[str, str]]
) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("object_id"):
            result[row["object_id"]].append(row)
    return result


def simple_property_map(
    rows: List[Dict[str, str]]
) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        result[row.get("property_name", "")].append(
            row.get("property_value", "")
        )
    return result


def build_graph(
    relationships: List[Dict[str, str]]
) -> Dict[str, List[Dict[str, str]]]:
    graph: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in relationships:
        if row.get("resolution_status") == "resolved_exact":
            graph[row.get("source_object_id", "")].append(row)
    return graph


def traverse(
    root_id: str,
    graph: Dict[str, List[Dict[str, str]]],
    max_depth: int,
) -> Tuple[Set[str], List[Dict[str, str]]]:
    nodes = {root_id}
    edges: List[Dict[str, str]] = []
    q = deque([(root_id, 0)])

    while q:
        oid, depth = q.popleft()
        if depth >= max_depth:
            continue

        for edge in graph.get(oid, []):
            edges.append(edge)
            tid = edge.get("target_object_id", "")
            if tid and tid not in nodes:
                nodes.add(tid)
                q.append((tid, depth + 1))

    return nodes, edges


def endpoint_index(
    endpoints: List[Dict[str, str]]
) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in endpoints:
        result[row.get("source_object_id", "")].append(row)
    return result


def file_index(
    files: List[Dict[str, str]]
) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in files:
        if row.get("resolution_status") == "resolved_exact":
            result[row.get("source_object_id", "")].append(row)
    return result


def object_stub(
    oid: str,
    objects: Dict[str, Dict[str, str]],
) -> Dict[str, str]:
    row = objects.get(oid, {})
    return {
        "object_id": oid,
        "type": row.get("canonical_type", ""),
        "name": row.get("object_name", ""),
    }


def build_tcp_proxy_direct_journey(
    root: Dict[str, str],
    prop_rows: List[Dict[str, str]],
) -> Dict[str, Any]:
    props = simple_property_map(prop_rows)

    def first(name: str) -> str:
        values = props.get(name, [])
        return values[0] if values else ""

    return {
        "ingress": [{
            "evidence_kind": "tcp_proxy_inline_configuration",
            "protocol": "tcp",
            "listen_address": first("local-address"),
            "listen_port": first("local-port"),
        }],
        "egress": [{
            "evidence_kind": "tcp_proxy_inline_configuration",
            "protocol": "tcp",
            "host": first("destination-address"),
            "port": first("destination-port"),
            "route_role": "configured_tcp_destination",
        }],
        "tcp_proxy_properties": {
            "timeout": first("timeout"),
            "priority": first("priority"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build evidence-only DataPower service journeys from resolved "
            "objects, relationships, endpoints and file dependencies."
        )
    )
    ap.add_argument("--objects", required=True)
    ap.add_argument("--properties", required=True)
    ap.add_argument("--relationships", required=True)
    ap.add_argument("--endpoints", required=True)
    ap.add_argument("--file-relationships", required=True)
    ap.add_argument("--output", default="index/service_journeys.jsonl")
    ap.add_argument(
        "--summary-output",
        default="index/service_journey_summary.csv",
    )
    ap.add_argument("--max-depth", type=int, default=8)
    args = ap.parse_args()

    paths = {
        "objects": Path(args.objects),
        "properties": Path(args.properties),
        "relationships": Path(args.relationships),
        "endpoints": Path(args.endpoints),
        "files": Path(args.file_relationships),
    }
    for name, path in paths.items():
        if not path.exists():
            print(f"[FATAL] Missing {name}: {path}")
            return 2

    objects_rows = load_csv(paths["objects"])
    props_rows = load_csv(paths["properties"])
    relationship_rows = load_csv(paths["relationships"])
    endpoint_rows = load_csv(paths["endpoints"])
    file_rows = load_csv(paths["files"])

    objects = unique_objects(objects_rows)
    props = properties_by_object(props_rows)
    graph = build_graph(relationship_rows)
    endpoints = endpoint_index(endpoint_rows)
    files = file_index(file_rows)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    summaries: List[Dict[str, Any]] = []
    root_counts = Counter()

    with output.open("w", encoding="utf-8") as fh:
        for root_id, root in sorted(objects.items()):
            root_type = root.get("canonical_type", "")
            if root_type not in ROOT_TYPES:
                continue

            node_ids, edges = traverse(
                root_id, graph, max(1, args.max_depth)
            )
            root_counts[root_type] += 1

            ingress_edges = [
                e for e in edges
                if e.get("relationship_type") in INGRESS_RELATIONSHIPS
            ]
            processing_edges = [
                e for e in edges
                if e.get("relationship_type") in PROCESSING_RELATIONSHIPS
            ]
            security_edges = [
                e for e in edges
                if e.get("relationship_type") in SECURITY_RELATIONSHIPS
            ]
            support_edges = [
                e for e in edges
                if e.get("relationship_type") in SUPPORT_RELATIONSHIPS
            ]

            reachable_endpoints: List[Dict[str, str]] = []
            reachable_files: List[Dict[str, str]] = []

            for oid in node_ids:
                reachable_endpoints.extend(endpoints.get(oid, []))
                reachable_files.extend(files.get(oid, []))

            journey: Dict[str, Any] = {
                "builder_version": BUILDER_VERSION,
                "environment": root.get("environment", ""),
                "domain": (
                    json.loads(root.get("parent_context", "[]"))[0]
                    if root.get("parent_context", "").startswith("[")
                    and json.loads(root.get("parent_context", "[]"))
                    else root.get("environment", "")
                ),
                "root": object_stub(root_id, objects),
                "graph": {
                    "node_count": len(node_ids),
                    "edge_count": len(edges),
                    "nodes": [
                        object_stub(oid, objects)
                        for oid in sorted(node_ids)
                    ],
                    "edges": edges,
                },
                "ingress": {
                    "relationships": ingress_edges,
                },
                "processing": {
                    "relationships": processing_edges,
                },
                "security": {
                    "relationships": security_edges,
                },
                "supporting_configuration": {
                    "relationships": support_edges,
                },
                "egress": {
                    "endpoints": reachable_endpoints,
                },
                "file_dependencies": reachable_files,
                "evidence_policy": (
                    "Only explicit parsed properties, resolved relationships, "
                    "resolved file references and extracted endpoints are used. "
                    "No caller/system identity is inferred from object names."
                ),
            }

            if root_type == "tcp_proxy":
                journey["tcp_proxy_direct"] = build_tcp_proxy_direct_journey(
                    root, props.get(root_id, [])
                )

            fh.write(json.dumps(journey, ensure_ascii=False) + "\n")

            summaries.append({
                "environment": root.get("environment", ""),
                "root_object_id": root_id,
                "root_type": root_type,
                "root_name": root.get("object_name", ""),
                "graph_nodes": len(node_ids),
                "graph_edges": len(edges),
                "ingress_relationships": len(ingress_edges),
                "processing_relationships": len(processing_edges),
                "security_relationships": len(security_edges),
                "endpoint_dependencies": len(reachable_endpoints),
                "file_dependencies": len(reachable_files),
                "builder_version": BUILDER_VERSION,
            })

    fields = [
        "environment",
        "root_object_id",
        "root_type",
        "root_name",
        "graph_nodes",
        "graph_edges",
        "ingress_relationships",
        "processing_relationships",
        "security_relationships",
        "endpoint_dependencies",
        "file_dependencies",
        "builder_version",
    ]
    write_csv(Path(args.summary_output), summaries, fields)

    print("=" * 80)
    print("DATAPOWER SERVICE JOURNEY BUILDER V1")
    print("=" * 80)
    print(f"Builder version:            {BUILDER_VERSION}")
    print(f"Service roots built:        {len(summaries)}")
    print(f"Journey output:             {output}")
    print(f"Summary output:             {args.summary_output}")
    print("-" * 80)
    print("Root types:")
    for key, value in sorted(root_counts.items()):
        print(f"  {key:40} {value}")
    print("-" * 80)
    print("SERVICE JOURNEY BUILDER V1: BUILT — VALIDATE BEFORE FREEZE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
