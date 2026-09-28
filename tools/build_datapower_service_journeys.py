#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional, Iterable
from xml.parsers import expat


BUILDER_VERSION = "base-candidate"

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

TRUE_VALUES = {"1", "true", "yes", "on", "enabled"}
FALSE_VALUES = {"0", "false", "no", "off", "disabled"}


def load_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_records(path: Optional[Path]) -> List[Dict[str, Any]]:
    if not path or not path.exists():
        return []
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return load_csv(path)
    if suffix == ".jsonl":
        rows: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("findings", "records", "items"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
    return []


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


def properties_by_object(rows: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("object_id"):
            result[row["object_id"]].append(row)
    return result


def simple_property_map(rows: List[Dict[str, str]]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        result[row.get("property_name", "")].append(row.get("property_value", ""))
    return result


def build_graph(relationships: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Preserve the validated traversal behavior: resolved_exact edges only."""
    graph: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in relationships:
        if row.get("resolution_status") == "resolved_exact":
            graph[row.get("source_object_id", "")].append(row)
    return graph


def relationship_index(relationships: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in relationships:
        source = row.get("source_object_id", "")
        if source:
            result[source].append(row)
    return result


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


def endpoint_index(endpoints: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in endpoints:
        result[row.get("source_object_id", "")].append(row)
    return result


def file_index(files: List[Dict[str, str]], resolved_only: bool) -> Dict[str, List[Dict[str, str]]]:
    result: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in files:
        if resolved_only and row.get("resolution_status") != "resolved_exact":
            continue
        source = row.get("source_object_id", "")
        if source:
            result[source].append(row)
    return result


def object_stub(oid: str, objects: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    row = objects.get(oid, {})
    return {
        "object_id": oid,
        "type": row.get("canonical_type", ""),
        "name": row.get("object_name", ""),
    }


def first_nonempty(row: Dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


def unique_keep_order(values: Iterable[str]) -> List[str]:
    seen = set()
    out: List[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            out.append(value)
    return out


def dedupe_dicts(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for row in rows:
        key = json.dumps(row, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            out.append(row)
    return out


def normalize_bool(value: str) -> Optional[bool]:
    norm = str(value or "").strip().strip('"\'').lower()
    if norm in TRUE_VALUES:
        return True
    if norm in FALSE_VALUES:
        return False
    return None


def evidence_pointer(row: Dict[str, Any]) -> Dict[str, str]:
    ptr = {
        "evidence_file": first_nonempty(row, "evidence_file", "source_file"),
        "source_line": first_nonempty(row, "source_line", "line_number", "start_line"),
        "property_name": first_nonempty(row, "property_name"),
        "property_path": first_nonempty(row, "property_path"),
    }
    return {k: v for k, v in ptr.items() if v}


def normalize_resolution_status(row: Dict[str, Any]) -> str:
    raw = first_nonempty(row, "resolution_status", "status").strip()
    if raw == "resolved_exact" or raw.startswith("resolved"):
        return "resolved"
    if raw:
        return raw
    if first_nonempty(row, "target_file_id", "target_object_id", "resolved_path", "target_relative_path"):
        return "resolved"
    return "unresolved_target_not_found"


def relationship_dependency_record(row: Dict[str, Any]) -> Dict[str, Any]:
    raw_status = first_nonempty(row, "resolution_status")
    resolved = raw_status in {"resolved_exact", "resolved"} or bool(first_nonempty(row, "target_object_id"))
    return {
        "relationship_type": first_nonempty(row, "relationship_type"),
        "source_object_id": first_nonempty(row, "source_object_id"),
        "source_object_name": first_nonempty(row, "source_object_name"),
        "source_type": first_nonempty(row, "source_type"),
        "target_object_id": first_nonempty(row, "target_object_id"),
        "target_object_name": first_nonempty(row, "target_object_name", "target_name"),
        "target_type": first_nonempty(row, "target_type", "target_type_hint"),
        "raw_reference": first_nonempty(row, "raw_reference", "property_value", "target_name"),
        "resolution_status": "resolved" if resolved else (raw_status or "unresolved_target_not_found"),
        "certainty": "confirmed" if resolved else "unresolved",
        "evidence": evidence_pointer(row),
    }


def raw_file_reference(row: Dict[str, Any]) -> str:
    return first_nonempty(
        row,
        "raw_reference",
        "reference_value",
        "raw_value",
        "property_value",
        "target_reference",
        "target_relative_path",
    )


def file_dependency_record(row: Dict[str, Any]) -> Dict[str, Any]:
    status = normalize_resolution_status(row)
    return {
        "target_file_id": first_nonempty(row, "target_file_id"),
        "target_relative_path": first_nonempty(row, "target_relative_path", "resolved_path"),
        "classification": first_nonempty(row, "target_classification", "classification"),
        "relationship_type": first_nonempty(row, "relationship_type"),
        "source_object_id": first_nonempty(row, "source_object_id"),
        "property_name": first_nonempty(row, "property_name"),
        "raw_reference": raw_file_reference(row),
        "resolution_status": status,
        "certainty": "confirmed" if status == "resolved" else "unresolved",
        "evidence": evidence_pointer(row),
    }


def artifact_candidate_paths(row: Dict[str, Any], artifact_root: Optional[Path]) -> List[Path]:
    values = unique_keep_order([
        first_nonempty(row, "resolved_path"),
        first_nonempty(row, "target_relative_path"),
    ])
    out: List[Path] = []
    for value in values:
        if not value:
            continue
        p = Path(value)
        if p.is_absolute():
            out.append(p)
        if artifact_root:
            out.append(artifact_root / value.lstrip("/"))
    return out


def extract_urls(text: str) -> List[str]:
    return unique_keep_order(re.findall(r"https?://[^\s\"'<>)}]+", text, flags=re.IGNORECASE))


def extract_method_near(text: str, token: str) -> str:
    idx = text.lower().find(token.lower())
    if idx < 0:
        return ""
    window = text[max(0, idx - 700): idx + 1200]
    patterns = [
        r"\bmethod\s*[:=]\s*[\"']?(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)",
        r"\b(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b",
    ]
    for pattern in patterns:
        m = re.search(pattern, window, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()
    return ""



def extract_runtime_destination_components(text: str, urls: List[str]) -> Dict[str, Any]:
    runtime_refs = unique_keep_order(
        re.findall(r"var://service/[A-Za-z0-9_./:-]+", text, flags=re.IGNORECASE)
    )
    if not urls or not runtime_refs:
        return {
            "destination_type": "static" if urls else "dynamic_or_runtime_computed",
            "base_targets": urls,
            "dynamic_components": [],
        }

    nearby_refs: List[str] = []
    lowered = text.lower()
    for url in urls:
        start = 0
        url_l = url.lower()
        while True:
            idx = lowered.find(url_l, start)
            if idx < 0:
                break
            window = text[max(0, idx - 500): idx + len(url) + 500]
            nearby_refs.extend(
                re.findall(r"var://service/[A-Za-z0-9_./:-]+", window, flags=re.IGNORECASE)
            )
            start = idx + len(url)

    dynamic_components = unique_keep_order(nearby_refs)
    return {
        "destination_type": "dynamic" if dynamic_components else "static",
        "base_targets": urls,
        "dynamic_components": dynamic_components,
    }


def xpath_literal_value(expression: str) -> Tuple[str, str]:
    value = expression.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        quote = value[0]
        return value[1:-1].replace(quote * 2, quote), "literal"
    return value, "computed"


def split_xpath_arguments(expression: str) -> List[str]:
    arguments: List[str] = []
    start = 0
    depth = 0
    quote = ""
    index = 0
    while index < len(expression):
        char = expression[index]
        if quote:
            if char == quote:
                if index + 1 < len(expression) and expression[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
        elif char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            arguments.append(expression[start:index].strip())
            start = index + 1
        index += 1
    arguments.append(expression[start:].strip())
    return arguments


def extract_database_calls(expression: str) -> List[List[str]]:
    calls: List[List[str]] = []
    call_pattern = re.compile(r"(?<![\w.-])(?:dp:sql-execute|dp)\s*\(")
    index = 0
    quote = ""
    while index < len(expression):
        char = expression[index]
        if quote:
            if char == quote:
                if index + 1 < len(expression) and expression[index + 1] == quote:
                    index += 1
                else:
                    quote = ""
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            index += 1
            continue
        match = call_pattern.match(expression, index)
        if not match:
            index += 1
            continue

        opening = match.end() - 1
        depth = 1
        call_quote = ""
        closing = opening + 1
        while closing < len(expression) and depth:
            current = expression[closing]
            if call_quote:
                if current == call_quote:
                    if closing + 1 < len(expression) and expression[closing + 1] == call_quote:
                        closing += 1
                    else:
                        call_quote = ""
            elif current in {"'", '"'}:
                call_quote = current
            elif current == "(":
                depth += 1
            elif current == ")":
                depth -= 1
            closing += 1
        if depth == 0:
            calls.append(split_xpath_arguments(expression[opening + 1:closing - 1]))
            index = closing
        else:
            index = match.end()
    return calls


def extract_database_semantic_facts(text: str, path: Path, file_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    facts: List[Dict[str, Any]] = []
    owning_action = first_nonempty(file_row, "source_object_id")
    parser = expat.ParserCreate(namespace_separator="}")

    def add_fact(datasource_expression: str, statement_expression: str, syntax_form: str, source_line: int) -> None:
        datasource, datasource_type = xpath_literal_value(datasource_expression)
        statement, statement_type = xpath_literal_value(statement_expression)
        facts.append({
            "fact_type": "outbound_database_request",
            "mechanism": "datapower_sql",
            "datasource": datasource,
            "datasource_type": datasource_type,
            "statement": statement,
            "statement_type": statement_type,
            "syntax_form": syntax_form,
            "certainty": "confirmed",
            "artifact_path": str(path),
            "source_path": str(path),
            "source_line": source_line,
            "source_object_id": owning_action,
            "owning_action": owning_action,
        })

    def start_element(name: str, attributes: Dict[str, str]) -> None:
        local_name = name.rsplit("}", 1)[-1].rsplit(":", 1)[-1]
        local_attributes = {key.rsplit("}", 1)[-1].rsplit(":", 1)[-1]: value for key, value in attributes.items()}
        source_line = parser.CurrentLineNumber
        is_dp_element = local_name == "dp" or (
            local_name == "sql-execute" and name.startswith("http://www.datapower.com/extensions}")
        )
        if is_dp_element and "source" in local_attributes and "statement" in local_attributes:
            add_fact(local_attributes["source"], local_attributes["statement"], "extension_element", source_line)
        for expression in attributes.values():
            for arguments in extract_database_calls(expression):
                if len(arguments) == 2:
                    add_fact(arguments[0], arguments[1], "extension_function", source_line)

    parser.StartElementHandler = start_element
    try:
        parser.Parse(text, True)
    except expat.ExpatError:
        return []
    return facts


def extract_xslt_outbound_semantic_facts(
    text: str, path: Path, file_row: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Extract executable DataPower XSLT outbound calls and their targets.

    URI-shaped strings elsewhere in a stylesheet (including namespace and
    schema identifiers) are not outbound evidence. Only a url-open extension
    element in the DataPower namespace establishes an outbound call.
    """
    facts: List[Dict[str, Any]] = []
    variables: Dict[str, str] = {}
    owning_action = first_nonempty(file_row, "source_object_id")
    parser = expat.ParserCreate(namespace_separator="}")
    datapower_url_open = "http://www.datapower.com/extensions}url-open"
    xslt_variable = "http://www.w3.org/1999/XSL/Transform}variable"

    def resolve_target(expression: str) -> Tuple[str, str, List[str]]:
        raw = expression.strip()
        inner = raw[1:-1].strip() if raw.startswith("{") and raw.endswith("}") else raw
        if inner.startswith("$") and re.fullmatch(r"\$[A-Za-z_][\w.-]*", inner):
            variable_name = inner[1:]
            variable_expression = variables.get(variable_name, "")
            value, value_type = xpath_literal_value(variable_expression)
            if value_type == "literal":
                return value, "static", [inner]
            return "", "dynamic_or_runtime_computed", [inner]
        value, value_type = xpath_literal_value(inner)
        if value_type == "literal":
            return value, "static", []
        if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value):
            return value, "static", []
        dynamic_components = unique_keep_order(re.findall(r"\$[A-Za-z_][\w.-]*", inner))
        return "", "dynamic_or_runtime_computed", dynamic_components

    def start_element(name: str, attributes: Dict[str, str]) -> None:
        local_attributes = {
            key.rsplit("}", 1)[-1].rsplit(":", 1)[-1]: value
            for key, value in attributes.items()
        }
        if name == xslt_variable:
            variable_name = local_attributes.get("name", "")
            select = local_attributes.get("select", "")
            if variable_name and select:
                variables[variable_name] = select
            return
        if name != datapower_url_open:
            return

        target_expression = local_attributes.get("target", "")
        target, destination_type, dynamic_components = resolve_target(target_expression)
        scheme_match = re.match(r"^([A-Za-z][A-Za-z0-9+.-]*):", target)
        protocol = scheme_match.group(1).lower() if scheme_match else "dynamic"
        facts.append({
            "fact_type": "outbound_http_request" if protocol in {"http", "https"} else "outbound_request",
            "mechanism": "xslt",
            "method": "",
            "protocol": protocol,
            "targets": [target] if target else [],
            "target_expression": target_expression,
            "destination_type": destination_type,
            "dynamic_components": dynamic_components,
            "certainty": "confirmed",
            "artifact_path": str(path),
            "source_path": str(path),
            "source_line": parser.CurrentLineNumber,
            "source_object_id": owning_action,
        })

    parser.StartElementHandler = start_element
    try:
        parser.Parse(text, True)
    except expat.ExpatError:
        return []
    return facts


def extract_skip_backside_evidence(rows: List[Dict[str, str]]) -> List[Tuple[str, Optional[bool], Dict[str, Any]]]:
    """Extract only explicit skip-backside facts.

    DataPower setvar actions represent the variable name and its assigned value as
    separate properties.  The old enrichment treated any boolean-looking property
    on the same action (for example retry-count=0 or timeout=0) as the setvar value.
    This routine deliberately pairs only an explicit skip-backside marker with an
    explicit setvar value property from the same object/property set.
    """
    evidence: List[Tuple[str, Optional[bool], Dict[str, Any]]] = []

    # Direct property forms, if present in an export.
    for row in rows:
        name = str(row.get("property_name", "")).strip().lower().replace("_", "-")
        value = str(row.get("property_value", ""))
        if "skip-backside" in name:
            parsed = normalize_bool(value)
            if parsed is not None:
                evidence.append((value, parsed, evidence_pointer(row)))

    # Setvar form: variable=<skip-backside URI>, value=<assigned value>.
    marker_rows = [
        row for row in rows
        if "var://service/mpgw/skip-backside" in str(row.get("property_value", "")).lower()
        or "var://service/mpgw/skip-backside" in str(row.get("property_path", "")).lower()
    ]
    value_rows = [
        row for row in rows
        if str(row.get("property_name", "")).strip().lower().replace("_", "-")
        in {"value", "var-value", "variable-value", "setvar-value"}
    ]

    for marker in marker_rows:
        for row in value_rows:
            raw = str(row.get("property_value", ""))
            parsed = normalize_bool(raw)
            if parsed is None:
                continue
            ptr = evidence_pointer(row)
            ptr["setvar_variable"] = "var://service/mpgw/skip-backside"
            ptr["setvar_variable_evidence"] = evidence_pointer(marker)
            evidence.append((raw, parsed, ptr))

    out: List[Tuple[str, Optional[bool], Dict[str, Any]]] = []
    seen = set()
    for raw, parsed, ptr in evidence:
        key = (raw, parsed, repr(sorted(ptr.items())))
        if key not in seen:
            seen.add(key)
            out.append((raw, parsed, ptr))
    return out

def extract_semantic_facts(file_row: Dict[str, Any], artifact_root: Optional[Path]) -> List[Dict[str, Any]]:
    if normalize_resolution_status(file_row) != "resolved":
        return []
    path = next((p for p in artifact_candidate_paths(file_row, artifact_root) if p.exists() and p.is_file()), None)
    if not path:
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    classification = first_nonempty(file_row, "target_classification", "classification").lower()
    suffix = path.suffix.lower()
    facts: List[Dict[str, Any]] = []
    is_js = "gateway" in classification or "javascript" in classification or suffix == ".js"
    is_xslt = "xslt" in classification or suffix in {".xsl", ".xslt"}

    if is_js and re.search(r"\burlopen\b|require\s*\(\s*[\"']urlopen[\"']", text, flags=re.IGNORECASE):
        urls = extract_urls(text)
        destination = extract_runtime_destination_components(text, urls)
        facts.append({
            "fact_type": "outbound_http_request",
            "mechanism": "gatewayscript",
            "method": extract_method_near(text, "urlopen"),
            "targets": urls,
            "destination_type": destination["destination_type"],
            "base_targets": destination["base_targets"],
            "dynamic_components": destination["dynamic_components"],
            "certainty": "confirmed",
            "artifact_path": str(path),
            "source_object_id": first_nonempty(file_row, "source_object_id"),
        })

    if is_xslt:
        facts.extend(extract_xslt_outbound_semantic_facts(text, path, file_row))
        facts.extend(extract_database_semantic_facts(text, path, file_row))

    return facts


def route_control_for_nodes(
    node_ids: Iterable[str],
    props_by_object_map: Dict[str, List[Dict[str, str]]],
    endpoints: List[Dict[str, str]],
    semantic_facts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    skip_values: List[Tuple[str, Optional[bool], Dict[str, str]]] = []
    dynamic_evidence: List[Dict[str, str]] = []
    route_action_evidence: List[Dict[str, str]] = []

    for oid in node_ids:
        source_props = props_by_object_map.get(oid, [])
        skip_values.extend(extract_skip_backside_evidence(source_props))
        for row in source_props:
            name = str(row.get("property_name", "")).strip().lower().replace("_", "-")
            value = str(row.get("property_value", ""))
            value_norm = value.strip().lower().replace("_", "-")
            if (
                name in {"dynamic-backend", "dynamic-route", "route-url", "route"}
                or "dynamic-backend" in name
                or (name == "type" and value_norm == "dynamic-backend")
            ):
                dynamic_evidence.append({
                    "source_object_id": oid,
                    "property_name": row.get("property_name", ""),
                    "property_value": value,
                    "evidence": evidence_pointer(row),
                })

    for e in endpoints:
        role = str(e.get("route_role", ""))
        if role == "dynamic_route_expression":
            dynamic_evidence.append({
                "source_object_id": e.get("source_object_id", ""),
                "route_role": role,
                "normalized_endpoint": e.get("normalized_endpoint", ""),
            })
        if role == "processing_action_route_candidate":
            route_action_evidence.append({
                "source_object_id": e.get("source_object_id", ""),
                "route_role": role,
                "normalized_endpoint": e.get("normalized_endpoint", ""),
            })

    skip_true = any(v is True for _, v, _ in skip_values)
    skip_false = bool(skip_values) and all(v is False for _, v, _ in skip_values if v is not None)
    skip_state: Any = True if skip_true else (False if skip_false else None)

    return {
        "skip_backside": {
            "value": skip_state,
            "certainty": "confirmed" if skip_values and skip_state is not None else "not_evidenced",
            "evidence": [{"raw_value": raw, **ptr} for raw, _, ptr in skip_values],
        },
        "dynamic_route": {
            "value": bool(dynamic_evidence),
            "certainty": "confirmed" if dynamic_evidence else "not_evidenced",
            "evidence": dynamic_evidence,
        },
        "route_action": {
            "present": bool(route_action_evidence),
            "certainty": "confirmed" if route_action_evidence else "not_evidenced",
            "evidence": route_action_evidence,
        },
        "script_mediated": {
            "present": any(f.get("mechanism") == "gatewayscript" for f in semantic_facts),
            "certainty": "confirmed" if any(f.get("mechanism") == "gatewayscript" for f in semantic_facts) else "not_evidenced",
        },
        "transformation_mediated": {
            "present": any(f.get("mechanism") == "xslt" for f in semantic_facts),
            "certainty": "confirmed" if any(f.get("mechanism") == "xslt" for f in semantic_facts) else "not_evidenced",
        },
    }


def configured_backend_from_endpoints(endpoints: List[Dict[str, str]]) -> Dict[str, Any]:
    records = [
        {
            "endpoint_id": e.get("endpoint_id", ""),
            "route_role": e.get("route_role", ""),
            "normalized_endpoint": e.get("normalized_endpoint", ""),
            "source_object_id": e.get("source_object_id", ""),
        }
        for e in endpoints
        if e.get("route_role") in {"configured_default_backend", "web_service_proxy_remote_endpoint"}
    ]
    return {"targets": dedupe_dicts(records), "certainty": "confirmed" if records else "not_evidenced"}


def derive_backend_mode(root_type: str, configured_backend: Dict[str, Any], route_control: Dict[str, Any]) -> Dict[str, Any]:
    if root_type == "tcp_proxy":
        return {"value": "direct", "certainty": "confirmed"}
    if route_control["dynamic_route"]["value"]:
        return {"value": "dynamic", "certainty": "confirmed"}
    if configured_backend.get("targets"):
        return {"value": "static", "certainty": "confirmed"}
    return {"value": "not_evidenced", "certainty": "not_evidenced"}


def derive_actual_egress(
    root_type: str,
    tcp_direct: Optional[Dict[str, Any]],
    endpoints: List[Dict[str, str]],
    file_records: List[Dict[str, Any]],
    route_control: Dict[str, Any],
    semantic_facts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if root_type == "tcp_proxy" and tcp_direct:
        targets = tcp_direct.get("egress", [])
        if targets and any(t.get("host") or t.get("port") for t in targets):
            return {
                "status": "confirmed",
                "mechanism": ["tcp_direct"],
                "targets": targets,
                "reason": "tcp_proxy_inline_destination",
                "certainty": "confirmed",
            }

    database_facts = [f for f in semantic_facts if f.get("fact_type") == "outbound_database_request"]
    if database_facts:
        return {
            "status": "confirmed",
            "mechanism": "database",
            "targets": [
                {
                    "target": fact.get("datasource", ""),
                    "logical_datasource": fact.get("datasource", ""),
                    "target_type": "logical_datasource",
                }
                for fact in database_facts
            ],
            "reason": "resolved_artifact_contains_explicit_database_outbound_behavior",
            "certainty": "confirmed",
        }

    semantic_targets: List[Dict[str, Any]] = []
    for fact in semantic_facts:
        if fact.get("fact_type") not in {"outbound_http_request", "outbound_request"}:
            continue
        targets = fact.get("targets") or []
        if targets:
            for target in targets:
                semantic_targets.append({
                    "target": target,
                    "mechanism": fact.get("mechanism", ""),
                    "method": fact.get("method", ""),
                    "destination_type": fact.get("destination_type", "static"),
                    "dynamic_components": fact.get("dynamic_components", []),
                    **({"protocol": fact["protocol"]} if fact.get("protocol") else {}),
                })
        else:
            semantic_targets.append({
                "target": "",
                "mechanism": fact.get("mechanism", ""),
                "method": fact.get("method", ""),
                "destination_type": fact.get("destination_type", "dynamic_or_runtime_computed"),
                **({"protocol": fact["protocol"]} if fact.get("protocol") else {}),
            })
    if semantic_targets:
        return {
            "status": "confirmed",
            "mechanism": unique_keep_order(t.get("mechanism", "") for t in semantic_targets),
            "targets": semantic_targets,
            "reason": "resolved_artifact_contains_explicit_outbound_behavior",
            "certainty": "confirmed",
        }

    route_targets = [
        {
            "target": e.get("normalized_endpoint", ""),
            "route_role": e.get("route_role", ""),
            "source_object_id": e.get("source_object_id", ""),
        }
        for e in endpoints
        if e.get("route_role") == "processing_action_route_candidate"
    ]
    if route_targets:
        return {
            "status": "candidate",
            "mechanism": ["route_action"],
            "targets": dedupe_dicts(route_targets),
            "reason": "processing_action_route_candidate_present",
            "certainty": "candidate",
        }

    # File-resolution gaps and gateway-level dynamic-backend configuration are
    # preserved as evidence, but neither is operation/service execution proof.
    # They therefore do not decide actual egress on their own.
    skip_backside = route_control.get("skip_backside", {}).get("value") is True

    if skip_backside:
        return {
            "status": "not_evidenced",
            "mechanism": [],
            "targets": [],
            "reason": "normal_backside_bypassed_and_no_alternative_egress_evidenced",
            "certainty": "not_evidenced",
        }

    configured = [
        {
            "target": e.get("normalized_endpoint", ""),
            "route_role": e.get("route_role", ""),
            "source_object_id": e.get("source_object_id", ""),
        }
        for e in endpoints
        if e.get("route_role") in {"configured_default_backend", "web_service_proxy_remote_endpoint"}
    ]
    if configured:
        return {
            "status": "candidate",
            "mechanism": ["configured_backside"],
            "targets": dedupe_dicts(configured),
            "reason": "configured_backend_present_without_operation_execution_proof",
            "certainty": "candidate",
        }

    return {
        "status": "not_evidenced",
        "mechanism": [],
        "targets": [],
        "reason": "no_outbound_behavior_evidenced",
        "certainty": "not_evidenced",
    }


def build_tcp_proxy_direct_journey(root: Dict[str, str], prop_rows: List[Dict[str, str]]) -> Dict[str, Any]:
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


def finding_matches_service(finding: Dict[str, Any], root_id: str, node_ids: Set[str]) -> bool:
    if first_nonempty(finding, "service_id", "parent_service_id", "root_object_id") == root_id:
        return True
    oid = first_nonempty(finding, "object_id", "source_object_id", "owner_object_id")
    if oid and oid in node_ids:
        return True
    return False


def compact_finding(f: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "finding_id": first_nonempty(f, "finding_id", "id"),
        "classification": first_nonempty(f, "classification", "finding_type", "severity"),
        "scope": first_nonempty(f, "scope"),
        "summary": first_nonempty(f, "summary", "message", "description", "finding"),
        "certainty": first_nonempty(f, "certainty", "evidence_status") or "confirmed",
        "evidence": evidence_pointer(f),
    }


def domain_from_evidence(root: Dict[str, str], rows: Iterable[Dict[str, Any]]) -> str:
    """Resolve DataPower domain from explicit downstream evidence before fallbacks.

    Object IDs are environment-scoped (obj:{environment}:...), so environment and
    domain must remain separate. When graph/reference evidence carries one unique
    domain, that domain is authoritative for the materialized Service Journey.
    """
    observed = unique_keep_order(str(r.get("domain", "")) for r in rows if r.get("domain"))
    if len(observed) == 1:
        return observed[0]

    explicit = root.get("domain", "")
    if explicit:
        return explicit

    raw = root.get("parent_context", "")
    if raw.startswith("["):
        try:
            ctx = json.loads(raw)
            if ctx:
                return str(ctx[0])
        except (json.JSONDecodeError, TypeError):
            pass
    return root.get("environment", "")


def domain_consistency(expected_domain: str, rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    observed = sorted({str(r.get("domain", "")) for r in rows if r.get("domain")})
    if expected_domain and observed and expected_domain not in observed:
        return {"status": "inconsistent", "expected": expected_domain, "observed": observed}
    if len(set(observed)) > 1:
        return {"status": "inconsistent", "expected": expected_domain, "observed": observed}
    return {"status": "consistent", "expected": expected_domain, "observed": observed}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Build evidence-backed DataPower service journeys from resolved "
            "objects, relationships, endpoints and file dependencies, while "
            "preserving existing traversal behavior and enriching the final journey."
        )
    )
    ap.add_argument("--objects", required=True)
    ap.add_argument("--properties", required=True)
    ap.add_argument("--relationships", required=True)
    ap.add_argument("--endpoints", required=True)
    ap.add_argument("--file-relationships", required=True)
    ap.add_argument("--unresolved-file-references", required=False, help="Optional unresolved_file_references.csv from the file resolver")
    ap.add_argument("--findings", required=False, help="Optional CSV/JSON/JSONL findings source")
    ap.add_argument("--artifact-root", required=False, help="Optional root used to inspect resolved local XSLT/GatewayScript artifacts")
    ap.add_argument("--output", default="index/service_journeys.jsonl")
    ap.add_argument("--summary-output", default="index/service_journey_summary.csv")
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
    unresolved_file_rows = load_csv(Path(args.unresolved_file_references)) if args.unresolved_file_references else []
    findings = load_records(Path(args.findings)) if args.findings else []
    artifact_root = Path(args.artifact_root) if args.artifact_root else None

    objects = unique_objects(objects_rows)
    props = properties_by_object(props_rows)
    graph = build_graph(relationship_rows)
    all_relationships = relationship_index(relationship_rows)
    endpoints = endpoint_index(endpoint_rows)
    files_resolved = file_index(file_rows, resolved_only=True)
    files_all = file_index([*file_rows, *unresolved_file_rows], resolved_only=False)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    summaries: List[Dict[str, Any]] = []
    root_counts = Counter()

    with output.open("w", encoding="utf-8") as fh:
        for root_id, root in sorted(objects.items()):
            root_type = root.get("canonical_type", "")
            if root_type not in ROOT_TYPES:
                continue

            # Validated traversal remains unchanged.
            node_ids, edges = traverse(root_id, graph, max(1, args.max_depth))
            root_counts[root_type] += 1

            ingress_edges = [e for e in edges if e.get("relationship_type") in INGRESS_RELATIONSHIPS]
            processing_edges = [e for e in edges if e.get("relationship_type") in PROCESSING_RELATIONSHIPS]
            security_edges = [e for e in edges if e.get("relationship_type") in SECURITY_RELATIONSHIPS]
            support_edges = [e for e in edges if e.get("relationship_type") in SUPPORT_RELATIONSHIPS]

            reachable_endpoints: List[Dict[str, str]] = []
            reachable_files_legacy: List[Dict[str, str]] = []
            reachable_files_all: List[Dict[str, str]] = []
            graph_relationships_all: List[Dict[str, str]] = []

            for oid in node_ids:
                reachable_endpoints.extend(endpoints.get(oid, []))
                reachable_files_legacy.extend(files_resolved.get(oid, []))
                reachable_files_all.extend(files_all.get(oid, []))
                graph_relationships_all.extend(all_relationships.get(oid, []))

            # Additive enrichment from existing evidence.
            dependency_records = [relationship_dependency_record(r) for r in graph_relationships_all]
            resolved_dependencies = dedupe_dicts([d for d in dependency_records if d["resolution_status"] == "resolved"])
            unresolved_dependencies = dedupe_dicts([d for d in dependency_records if d["resolution_status"] != "resolved"])

            file_records = dedupe_dicts(file_dependency_record(f) for f in reachable_files_all)
            resolved_file_records = [f for f in file_records if f["resolution_status"] == "resolved"]
            unresolved_file_records = [f for f in file_records if f["resolution_status"] != "resolved"]

            semantic_facts: List[Dict[str, Any]] = []
            for f in reachable_files_legacy:
                semantic_facts.extend(extract_semantic_facts(f, artifact_root))
            semantic_facts = dedupe_dicts(semantic_facts)

            route_control = route_control_for_nodes(node_ids, props, reachable_endpoints, semantic_facts)
            configured_backend = configured_backend_from_endpoints(reachable_endpoints)
            backend_mode = derive_backend_mode(root_type, configured_backend, route_control)

            tcp_direct = None
            if root_type == "tcp_proxy":
                tcp_direct = build_tcp_proxy_direct_journey(root, props.get(root_id, []))

            actual_egress = derive_actual_egress(
                root_type,
                tcp_direct,
                reachable_endpoints,
                file_records,
                route_control,
                semantic_facts,
            )

            provenance_rows: List[Dict[str, Any]] = [*edges, *graph_relationships_all, *reachable_endpoints, *reachable_files_all]
            domain = domain_from_evidence(root, provenance_rows)
            relevant_findings = dedupe_dicts(
                compact_finding(f) for f in findings if finding_matches_service(f, root_id, node_ids)
            )

            source_pointers = dedupe_dicts(ptr for ptr in (evidence_pointer(r) for r in provenance_rows) if ptr)
            provenance = {
                "environment": root.get("environment", ""),
                "domain": domain,
                "source_files": unique_keep_order(p.get("evidence_file", "") for p in source_pointers),
                "source_pointers": source_pointers,
                "domain_consistency": domain_consistency(domain, provenance_rows),
                "builder": BUILDER_VERSION,
                "generated_from": {
                    "objects": args.objects,
                    "properties": args.properties,
                    "relationships": args.relationships,
                    "endpoints": args.endpoints,
                    "file_relationships": args.file_relationships,
                    "unresolved_file_references": args.unresolved_file_references or "",
                    "findings": args.findings or "",
                },
            }

            journey: Dict[str, Any] = {
                # Existing fields retained.
                "builder_version": BUILDER_VERSION,
                "environment": root.get("environment", ""),
                "domain": domain,
                "root": object_stub(root_id, objects),
                "graph": {
                    "node_count": len(node_ids),
                    "edge_count": len(edges),
                    "nodes": [object_stub(oid, objects) for oid in sorted(node_ids)],
                    "edges": edges,
                },
                "ingress": {
                    "relationships": ingress_edges,
                    "certainty": "confirmed" if ingress_edges or (tcp_direct and tcp_direct.get("ingress")) else "not_evidenced",
                },
                "processing": {
                    "relationships": processing_edges,
                    "certainty": "confirmed" if processing_edges else "not_evidenced",
                },
                "security": {
                    "relationships": security_edges,
                    "certainty": "confirmed" if security_edges else "not_evidenced",
                },
                "supporting_configuration": {
                    "relationships": support_edges,
                },
                "egress": {
                    "endpoints": reachable_endpoints,
                },
                # Keep legacy resolved file list unchanged for compatibility.
                "file_dependencies": reachable_files_legacy,
                # Additive enriched evidence.
                "dependencies": {
                    "resolved": resolved_dependencies,
                    "unresolved": unresolved_dependencies,
                },
                "file_resolution": {
                    "resolved": resolved_file_records,
                    "unresolved": unresolved_file_records,
                },
                "routing": {
                    "backend_mode": backend_mode,
                    "configured_backend": configured_backend,
                    "route_control": route_control,
                    "actual_egress": actual_egress,
                    "remote_system_identity": {
                        "value": "",
                        "certainty": "not_evidenced",
                    },
                    "remote_topology": {
                        "value": "",
                        "certainty": "not_evidenced",
                    },
                },
                "semantic_facts": semantic_facts,
                "known_findings": relevant_findings,
                "evidence": {
                    "overall_certainty": actual_egress.get("certainty", "not_evidenced"),
                    "source_pointers": source_pointers,
                },
                "provenance": provenance,
                "evidence_policy": (
                    "Only explicit parsed properties, resolved/unresolved relationships, "
                    "file references, extracted endpoints, relevant known findings, and "
                    "targeted resolved-artifact semantics are used. No caller/system identity "
                    "is inferred from object names and no cross-domain evidence is borrowed."
                ),
            }

            if tcp_direct is not None:
                journey["tcp_proxy_direct"] = tcp_direct

            fh.write(json.dumps(journey, ensure_ascii=False) + "\n")

            summaries.append({
                "environment": root.get("environment", ""),
                "domain": domain,
                "root_object_id": root_id,
                "root_type": root_type,
                "root_name": root.get("object_name", ""),
                "graph_nodes": len(node_ids),
                "graph_edges": len(edges),
                "ingress_relationships": len(ingress_edges),
                "processing_relationships": len(processing_edges),
                "security_relationships": len(security_edges),
                "endpoint_dependencies": len(reachable_endpoints),
                "file_dependencies": len(reachable_files_legacy),
                "resolved_dependency_count": len(resolved_dependencies),
                "unresolved_dependency_count": len(unresolved_dependencies),
                "resolved_file_count": len(resolved_file_records),
                "unresolved_file_count": len(unresolved_file_records),
                "backend_mode": backend_mode["value"],
                "actual_egress_status": actual_egress["status"],
                "semantic_fact_count": len(semantic_facts),
                "finding_count": len(relevant_findings),
                "provenance_status": provenance["domain_consistency"]["status"],
                "builder_version": BUILDER_VERSION,
            })

    fields = [
        "environment",
        "domain",
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
        "resolved_dependency_count",
        "unresolved_dependency_count",
        "resolved_file_count",
        "unresolved_file_count",
        "backend_mode",
        "actual_egress_status",
        "semantic_fact_count",
        "finding_count",
        "provenance_status",
        "builder_version",
    ]
    write_csv(Path(args.summary_output), summaries, fields)

    print("=" * 80)
    print("DATAPOWER SERVICE JOURNEY BUILDER")
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
    print(f"Services with unresolved egress: {sum(1 for s in summaries if s['actual_egress_status'] == 'unresolved')}")
    print(f"Services with confirmed egress:  {sum(1 for s in summaries if s['actual_egress_status'] == 'confirmed')}")
    print(f"Provenance inconsistencies:       {sum(1 for s in summaries if s['provenance_status'] != 'consistent')}")
    print("SERVICE JOURNEY BUILDER: BUILT — VALIDATE BEFORE FREEZE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
