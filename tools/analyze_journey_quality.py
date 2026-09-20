#!/usr/bin/env python3
"""
DataPower Atlas - Journey Quality Analyzer V1.1

Change from V1.0
----------------
- Correctly handles tcp_proxy direct journeys.
- A TCP Proxy with a complete direct path:
    local-address/local-port -> destination-address/destination-port
  is treated as having ingress and egress evidence even when graph
  relationship counts and endpoint_dependencies are zero.

This avoids false-positive `missing_network_edges` findings for valid
L4 forwarding services.

The analyzer remains evidence-only and does not infer missing topology.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
from typing import Dict, List, Any

VERSION = "1.1-evidence-quality-tcp-aware"


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def as_int(value: str) -> int:
    try:
        return int(value or 0)
    except (ValueError, TypeError):
        return 0


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "on"}


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})


def tcp_direct_state(journey: Dict[str, Any]) -> Dict[str, bool]:
    """
    Return evidence state for a TCP proxy direct journey.

    Supports the V1 Service Journey Builder representation where the
    direct configuration is carried in a `tcp_proxy_direct` object.
    """
    direct = journey.get("tcp_proxy_direct")
    if not isinstance(direct, dict):
        return {
            "present": False,
            "has_ingress": False,
            "has_egress": False,
            "complete": False,
        }

    local_address = str(direct.get("local_address", "")).strip()
    local_port = str(direct.get("local_port", "")).strip()
    dest_address = str(direct.get("destination_address", "")).strip()
    dest_port = str(direct.get("destination_port", "")).strip()

    has_ingress = bool(local_address and local_port)
    has_egress = bool(dest_address and dest_port)

    return {
        "present": True,
        "has_ingress": has_ingress,
        "has_egress": has_egress,
        "complete": has_ingress and has_egress,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--summary", required=True)
    ap.add_argument("--journeys", required=True)
    ap.add_argument("--objects", required=True)
    ap.add_argument("--properties", required=True)
    ap.add_argument("--relationships", required=True)
    ap.add_argument("--operation-summary", required=False)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    summary = load_csv(Path(args.summary))
    journeys = load_jsonl(Path(args.journeys))
    objects = load_csv(Path(args.objects))
    properties = load_csv(Path(args.properties))
    relationships = load_csv(Path(args.relationships))
    operations = load_csv(Path(args.operation_summary)) if args.operation_summary else []

    journey_by_root = {}
    for j in journeys:
        root_id = (
            j.get("root_object_id")
            or j.get("service_root_id")
            or j.get("root", {}).get("object_id")
            or ""
        )
        if root_id:
            journey_by_root[root_id] = j

    props_by_object = defaultdict(list)
    for p in properties:
        props_by_object[p["object_id"]].append(p)

    outgoing = defaultdict(list)
    for r in relationships:
        outgoing[r["source_object_id"]].append(r)

    operation_count = Counter(o["parent_service_name"] for o in operations)

    rows = []

    for s in summary:
        root_id = s["root_object_id"]
        root_name = s["root_name"]
        root_type = s["root_type"]

        ingress_count = as_int(s["ingress_relationships"])
        processing = as_int(s["processing_relationships"])
        security = as_int(s["security_relationships"])
        endpoint_count = as_int(s["endpoint_dependencies"])
        file_count = as_int(s["file_dependencies"])

        graph_has_ingress = ingress_count > 0
        graph_has_egress = endpoint_count > 0

        journey = journey_by_root.get(root_id, {})
        tcp_state = tcp_direct_state(journey) if root_type == "tcp_proxy" else {
            "present": False,
            "has_ingress": False,
            "has_egress": False,
            "complete": False,
        }

        effective_has_ingress = graph_has_ingress or tcp_state["has_ingress"]
        effective_has_egress = graph_has_egress or tcp_state["has_egress"]

        findings = []
        status = "complete"

        # TCP direct configuration is authoritative journey evidence for L4 proxying.
        if root_type == "tcp_proxy":
            if tcp_state["complete"]:
                status = "complete_direct_tcp_path"
            elif not effective_has_ingress and not effective_has_egress:
                status = "partial_missing_ingress_and_egress"
                findings.append((
                    "missing_tcp_direct_path",
                    "high",
                    "TCP Proxy has neither graph network evidence nor a complete direct local/destination path."
                ))
            elif not effective_has_ingress:
                status = "partial_missing_ingress"
                findings.append((
                    "missing_ingress",
                    "medium",
                    "TCP Proxy has destination evidence but no local listen address/port evidence."
                ))
            elif not effective_has_egress:
                status = "partial_missing_egress"
                findings.append((
                    "missing_egress",
                    "medium",
                    "TCP Proxy has local listen evidence but no destination address/port evidence."
                ))
        else:
            if not effective_has_ingress and not effective_has_egress:
                status = "partial_missing_ingress_and_egress"
                findings.append((
                    "missing_network_edges",
                    "high",
                    "No ingress relationship and no egress endpoint evidence in the built journey."
                ))
            elif not effective_has_ingress:
                status = "partial_missing_ingress"
                findings.append((
                    "missing_ingress",
                    "medium",
                    "No ingress relationship evidence in the built journey."
                ))
            elif not effective_has_egress and root_type in {
                "multi_protocol_gateway",
                "web_service_proxy",
            }:
                status = "partial_missing_egress"
                findings.append((
                    "missing_egress",
                    "medium",
                    "No egress endpoint evidence in the built journey."
                ))

        # Detect empty WSP endpoint rewrite policy referenced by the service.
        endpoint_rewrite_edges = [
            r for r in outgoing.get(root_id, [])
            if r.get("relationship_type") == "uses_endpoint_rewrite_policy"
        ]
        for edge in endpoint_rewrite_edges:
            target_id = edge.get("target_object_id", "")
            target_props = props_by_object.get(target_id, [])
            network_props = {
                p.get("property_name", "")
                for p in target_props
                if p.get("property_name") in {
                    "listener-rule",
                    "backend-rule",
                    "remote-endpoint-protocol",
                    "remote-endpoint-hostname",
                    "remote-endpoint-port",
                    "remote-endpoint-uri",
                }
            }
            if not network_props:
                findings.append((
                    "empty_endpoint_rewrite_policy",
                    "high",
                    f"Referenced endpoint rewrite policy '{edge.get('target_object_name','')}' exists but has no listener/backend endpoint configuration."
                ))

        # Processing concentration.
        op_count = operation_count.get(root_name, 0)
        if op_count >= 50:
            findings.append((
                "mega_processing_policy",
                "high",
                f"Service decomposes into {op_count} evidence-backed operation matches."
            ))
        elif op_count >= 20:
            findings.append((
                "high_processing_concentration",
                "medium",
                f"Service decomposes into {op_count} evidence-backed operation matches."
            ))

        if processing >= 300:
            findings.append((
                "large_processing_graph",
                "high",
                f"Service journey contains {processing} processing relationships."
            ))
        elif processing >= 100:
            findings.append((
                "large_processing_graph",
                "medium",
                f"Service journey contains {processing} processing relationships."
            ))

        # Custom XML manager explicit parser/cache values.
        xml_edges = [
            r for r in outgoing.get(root_id, [])
            if r.get("relationship_type") == "uses_xml_manager"
        ]
        for edge in xml_edges:
            xml_id = edge.get("target_object_id", "")
            xml_name = edge.get("target_object_name", "")
            if xml_name == "default":
                continue

            explicit_limits = []
            for p in props_by_object.get(xml_id, []):
                name = p.get("property_name", "")
                value = p.get("property_value", "")
                if name in {
                    "xsl cache memorysize",
                    "xsl-cache-memorysize",
                    "bytes-scanned",
                    "max-node-size",
                    "element-depth",
                    "max-prefixes",
                    "max-namespaces",
                    "max-local-names",
                }:
                    explicit_limits.append(f"{name}={value}")

            if explicit_limits:
                findings.append((
                    "custom_xml_manager_limits",
                    "medium",
                    f"Custom XML Manager '{xml_name}' has explicit parser/cache limits: "
                    + "; ".join(explicit_limits)
                ))

        if not findings:
            findings.append((
                "no_quality_gap_detected",
                "info",
                "No configured journey completeness gap detected by V1.1 rules."
            ))

        for finding_type, severity, reason in findings:
            rows.append({
                "environment": s.get("environment", ""),
                "domain": next(
                    (r.get("domain", "") for r in outgoing.get(root_id, []) if r.get("domain")),
                    ""
                ),
                "service_id": root_id,
                "service_type": root_type,
                "service_name": root_name,
                "journey_status": status,
                "graph_has_ingress": str(graph_has_ingress).lower(),
                "graph_has_egress": str(graph_has_egress).lower(),
                "tcp_direct_present": str(tcp_state["present"]).lower(),
                "tcp_direct_complete": str(tcp_state["complete"]).lower(),
                "has_ingress": str(effective_has_ingress).lower(),
                "has_processing": str(processing > 0).lower(),
                "has_security": str(security > 0).lower(),
                "has_egress": str(effective_has_egress).lower(),
                "has_file_dependencies": str(file_count > 0).lower(),
                "operation_count": op_count,
                "processing_relationships": processing,
                "finding_type": finding_type,
                "severity": severity,
                "finding_reason": reason,
                "analyzer_version": VERSION,
            })

    fields = [
        "environment",
        "domain",
        "service_id",
        "service_type",
        "service_name",
        "journey_status",
        "graph_has_ingress",
        "graph_has_egress",
        "tcp_direct_present",
        "tcp_direct_complete",
        "has_ingress",
        "has_processing",
        "has_security",
        "has_egress",
        "has_file_dependencies",
        "operation_count",
        "processing_relationships",
        "finding_type",
        "severity",
        "finding_reason",
        "analyzer_version",
    ]

    write_csv(Path(args.output), rows, fields)

    print("=" * 80)
    print("DATAPOWER JOURNEY QUALITY ANALYZER V1.1")
    print("=" * 80)
    print(f"Analyzer version:         {VERSION}")
    print(f"Services analyzed:        {len(summary)}")
    print(f"Findings emitted:         {len(rows)}")
    print(f"Output:                   {args.output}")
    print("-" * 80)

    counts = Counter(r["finding_type"] for r in rows)
    for name, count in counts.most_common():
        print(f"{name:45} {count:6}")

    tcp_roots = [s for s in summary if s.get("root_type") == "tcp_proxy"]
    tcp_complete = 0
    for s in tcp_roots:
        state = tcp_direct_state(journey_by_root.get(s["root_object_id"], {}))
        tcp_complete += 1 if state["complete"] else 0

    print("-" * 80)
    print(f"TCP Proxy roots:          {len(tcp_roots)}")
    print(f"TCP direct complete:      {tcp_complete}")
    print("JOURNEY QUALITY ANALYZER V1.1: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
