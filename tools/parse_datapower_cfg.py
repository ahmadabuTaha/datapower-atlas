#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from taxonomy_loader import load_taxonomies


PARSER_VERSION = "2.2-architecture-beta-lossless"


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def normalize_name(value: str) -> str:
    value = value.strip().strip('"').strip("'")
    value = re.sub(r"\s+", "_", value)
    value = re.sub(r"[^A-Za-z0-9_.:@+-]+", "_", value)
    return value.strip("_") or "unnamed"


def tokenize_cli_line(line: str) -> List[str]:
    return re.findall(r'"[^"]*"|\'[^\']*\'|\S+', line.strip())


def normalize_token(value: str) -> str:
    return value.strip().rstrip(";").lower().replace("_", "-")


def strip_token(value: str) -> str:
    return value.strip().strip('"').strip("'").rstrip(";")


def command_signature(tokens: List[str]) -> Tuple[str, ...]:
    return tuple(normalize_token(x) for x in tokens)


WRAPPER_ONLY = {
    "top;",
    "configure",
    "terminal;",
    "configure-terminal;",
    "top; configure terminal;",
}


def is_comment(line: str) -> bool:
    s = line.strip()
    return s.startswith("#") or s.startswith("//")


def is_conditional_wrapper(line: str) -> bool:
    s = line.strip()
    return s.startswith("%if%") or s.startswith("%endif%")


def load_object_document(taxonomy_dir: Path) -> Dict[str, Any]:
    bundle = load_taxonomies(taxonomy_dir)
    data = bundle.datapower_objects
    if not isinstance(data.get("object_types"), dict):
        raise ValueError("datapower_objects.yaml must contain object_types")
    return data


def build_object_grammar(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    grammar: List[Dict[str, Any]] = []

    for object_key, spec in doc["object_types"].items():
        if not isinstance(spec, dict):
            continue

        canonical_type = spec.get("canonical_type")
        command = spec.get("command")
        if not canonical_type or not isinstance(command, dict):
            continue

        command_forms: List[Dict[str, Any]] = [command]
        for alias in spec.get("command_aliases", []) or []:
            if isinstance(alias, dict):
                command_forms.append(alias)

        for form in command_forms:
            tokens = form.get("tokens")
            if not isinstance(tokens, list) or not tokens:
                continue

            grammar.append({
                "object_key": object_key,
                "canonical_type": canonical_type,
                "category": spec.get("category", ""),
                "recognition_kind": spec.get("recognition_kind", ""),
                "declaration_form": spec.get("declaration_form", "block"),
                "architecture_relevance": spec.get(
                    "architecture_relevance", "supporting"
                ),
                "command_tokens": [normalize_token(str(t)) for t in tokens],
                "name_argument": form.get(
                    "name_argument", command.get("name_argument")
                ),
                "generated_name": form.get(
                    "generated_name", command.get("generated_name")
                ),
                "required_parent_context": [
                    normalize_token(str(x))
                    for x in spec.get("required_parent_context", []) or []
                ],
                "inline_arguments": spec.get("inline_arguments", []) or [],
                "is_alias": form is not command,
            })

    # Longest command wins for compound commands.
    grammar.sort(key=lambda x: len(x["command_tokens"]), reverse=True)
    return grammar


def build_non_object_modes(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []

    for name, spec in (doc.get("non_object_configuration_modes") or {}).items():
        if not isinstance(spec, dict):
            continue
        command = spec.get("command")
        if not isinstance(command, dict):
            continue
        tokens = command.get("tokens")
        if not isinstance(tokens, list) or not tokens:
            continue
        rules.append({
            "name": name,
            "command_tokens": [normalize_token(str(t)) for t in tokens],
            "classification": spec.get("classification"),
            "create_logical_object": bool(spec.get("create_logical_object")),
            "bound_to_type": spec.get("bound_to_type"),
            "capture_as_subcontext": bool(spec.get("capture_as_subcontext")),
        })

    rules.sort(key=lambda x: len(x["command_tokens"]), reverse=True)
    return rules


def prefix_matches(tokens: List[str], prefix: List[str]) -> bool:
    if len(tokens) < len(prefix):
        return False
    return tokens[:len(prefix)] == prefix


def match_object_declaration(
    line: str,
    grammar: List[Dict[str, Any]],
    context_stack: List[str],
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    tokens_raw = tokenize_cli_line(line)
    tokens = [normalize_token(x) for x in tokens_raw]
    current_context = {normalize_token(x) for x in context_stack}

    for rule in grammar:
        cmd = rule["command_tokens"]
        if not prefix_matches(tokens, cmd):
            continue

        required = set(rule["required_parent_context"])
        if required and not required.issubset(current_context):
            continue

        if rule["recognition_kind"] == "global_singleton_configuration":
            return rule, rule.get("generated_name") or "-".join(cmd)

        pos = rule.get("name_argument")
        if not isinstance(pos, int) or len(tokens_raw) <= pos:
            continue

        return rule, strip_token(tokens_raw[pos])

    return None, None


def match_non_object_mode(
    line: str,
    modes: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    tokens = [normalize_token(x) for x in tokenize_cli_line(line)]
    for rule in modes:
        if prefix_matches(tokens, rule["command_tokens"]):
            return rule
    return None


def property_record(
    *,
    object_id: str,
    occurrence_id: str,
    environment: str,
    canonical_type: str,
    object_name: str,
    property_name: str,
    property_value: str,
    ordinal: int,
    source_file: str,
    source_line: int,
    line_scope_start: int,
    line_scope_end: int,
    subcontext: List[str],
    raw_statement: str,
) -> Dict[str, Any]:
    property_path = ".".join([*subcontext, property_name]) if subcontext else property_name
    raw_statement = raw_statement.rstrip("\n")
    return {
        "object_id": object_id,
        "occurrence_id": occurrence_id,
        "environment": environment,
        "canonical_type": canonical_type,
        "object_name": object_name,
        "property_name": property_name,
        "property_value": property_value,
        "property_path": property_path,
        "subcontext": json.dumps(
            subcontext, ensure_ascii=False, separators=(",", ":")
        ),
        "ordinal": ordinal,
        "source_file": source_file,
        "source_line": source_line,
        "line_scope_start": line_scope_start,
        "line_scope_end": line_scope_end,
        "raw_statement": raw_statement,
        "raw_statement_sha256": sha256_text(raw_statement),
        "parser_version": PARSER_VERSION,
    }


def parse_cfg(
    cfg_path: Path,
    environment: str,
    object_doc: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:

    lines = cfg_path.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines(keepends=True)

    grammar = build_object_grammar(object_doc)
    non_object_modes = build_non_object_modes(object_doc)

    objects: List[Dict[str, Any]] = []
    properties: List[Dict[str, Any]] = []
    unclassified: List[Dict[str, Any]] = []

    # Structural contexts outside logical objects, e.g. crypto.
    context_stack: List[str] = []

    current: Optional[Dict[str, Any]] = None
    current_raw_lines: List[str] = []
    current_properties: List[Dict[str, Any]] = []
    current_property_counts: Counter[str] = Counter()
    subcontext_stack: List[str] = []

    def make_ids(canonical_type: str, object_name: str,
                 start_line: int, end_line: int) -> Tuple[str, str]:
        object_id = (
            f"obj:{environment}:{canonical_type}:{normalize_name(object_name)}"
        )
        occurrence_id = (
            f"occ:{environment}:{cfg_path.name}:{start_line}:{end_line}"
        )
        return object_id, occurrence_id

    def finalize_current(
        end_line: int,
        parse_status: str = "parsed",
        parse_reason: str = "",
    ) -> None:
        nonlocal current, current_raw_lines
        nonlocal current_properties, current_property_counts, subcontext_stack

        if current is None:
            return

        object_id, occurrence_id = make_ids(
            current["canonical_type"],
            current["object_name"],
            current["start_line"],
            end_line,
        )

        # IDs/end scope are known only now, so finish the property rows here.
        for p in current_properties:
            p["object_id"] = object_id
            p["occurrence_id"] = occurrence_id
            p["line_scope_end"] = end_line
            properties.append(p)

        raw_block = "".join(current_raw_lines)

        objects.append({
            "object_id": object_id,
            "occurrence_id": occurrence_id,
            "environment": environment,
            "canonical_type": current["canonical_type"],
            "object_name": current["object_name"],
            "cli_command": current["cli_command"],
            "declaration_form": current["declaration_form"],
            "recognition_kind": current["recognition_kind"],
            "category": current["category"],
            "architecture_relevance": current["architecture_relevance"],
            "source_file": str(cfg_path),
            "source_relative_path": cfg_path.name,
            "start_line": current["start_line"],
            "end_line": end_line,
            "raw_block_sha256": sha256_text(raw_block),
            "parent_context": json.dumps(
                current["parent_context"],
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "depth": len(current["parent_context"]),
            "property_count": len(current_properties),
            "parse_status": parse_status,
            "parse_reason": parse_reason,
            "parser_version": PARSER_VERSION,
        })

        current = None
        current_raw_lines = []
        current_properties = []
        current_property_counts = Counter()
        subcontext_stack = []

    def add_current_property(
        line_number: int,
        raw: str,
        property_name: str,
        property_value: str,
        subcontext: Optional[List[str]] = None,
    ) -> None:
        assert current is not None
        ctx = list(subcontext_stack if subcontext is None else subcontext)
        key = ".".join([*ctx, property_name]) if ctx else property_name
        current_property_counts[key] += 1
        current_properties.append(
            property_record(
                object_id="",
                occurrence_id="",
                environment=environment,
                canonical_type=current["canonical_type"],
                object_name=current["object_name"],
                property_name=property_name,
                property_value=property_value,
                ordinal=current_property_counts[key],
                source_file=str(cfg_path),
                source_line=line_number,
                line_scope_start=current["start_line"],
                line_scope_end=0,
                subcontext=ctx,
                raw_statement=raw,
            )
        )

    for line_number, raw in enumerate(lines, start=1):
        s = raw.strip()

        # ---------------------------------------------------------------
        # Inside a recognized block object: preserve every statement.
        # ---------------------------------------------------------------
        if current is not None:
            current_raw_lines.append(raw)

            if not s or is_comment(raw) or is_conditional_wrapper(raw):
                continue

            # An exit closes an attached subconfiguration first; only the
            # outermost exit closes the logical object.
            if s in {"exit", "exit;"}:
                if subcontext_stack:
                    subcontext_stack.pop()
                else:
                    finalize_current(line_number)
                continue

            nested_mode = match_non_object_mode(raw, non_object_modes)
            if (
                nested_mode
                and nested_mode.get("capture_as_subcontext")
                and (
                    not nested_mode.get("bound_to_type")
                    or nested_mode["bound_to_type"] == current["canonical_type"]
                )
            ):
                tokens = tokenize_cli_line(s)
                prefix_len = len(nested_mode["command_tokens"])
                value = " ".join(tokens[prefix_len:]).rstrip(";").strip()
                # Preserve the opener itself as evidence.
                add_current_property(
                    line_number,
                    raw,
                    nested_mode["name"],
                    value,
                )
                subcontext_stack.append(nested_mode["name"])
                continue

            tokens = tokenize_cli_line(s)
            if not tokens:
                continue

            prop_name = normalize_token(tokens[0])
            prop_value = " ".join(tokens[1:]).rstrip(";").strip()
            add_current_property(
                line_number,
                raw,
                prop_name,
                prop_value,
            )
            continue

        # ---------------------------------------------------------------
        # Outside an object.
        # ---------------------------------------------------------------
        if (
            not s
            or is_comment(raw)
            or is_conditional_wrapper(raw)
            or s in WRAPPER_ONLY
        ):
            continue

        # Structural/non-object mode, e.g. crypto.
        non_object = match_non_object_mode(raw, non_object_modes)
        if (
            non_object
            and non_object.get("classification") == "structural_parent_context"
        ):
            context_stack.append(non_object["name"])
            continue

        if s in {"exit", "exit;"}:
            if context_stack:
                context_stack.pop()
            continue

        rule, object_name = match_object_declaration(
            raw, grammar, context_stack
        )

        if rule and object_name:
            tokens = tokenize_cli_line(s)
            cli_command = " ".join(rule["command_tokens"])
            declaration_form = rule["declaration_form"]

            # Inline objects are complete on the declaration line.
            if declaration_form == "inline":
                object_id, occurrence_id = make_ids(
                    rule["canonical_type"],
                    object_name,
                    line_number,
                    line_number,
                )

                inline_props: List[Dict[str, Any]] = []
                counts: Counter[str] = Counter()
                for arg in rule.get("inline_arguments", []):
                    pos = arg.get("position")
                    pname = arg.get("property_name")
                    optional = bool(arg.get("optional"))
                    if not isinstance(pos, int) or not pname:
                        continue
                    if len(tokens) <= pos:
                        if optional:
                            continue
                        continue
                    pvalue = strip_token(tokens[pos])
                    counts[pname] += 1
                    inline_props.append(
                        property_record(
                            object_id=object_id,
                            occurrence_id=occurrence_id,
                            environment=environment,
                            canonical_type=rule["canonical_type"],
                            object_name=object_name,
                            property_name=pname,
                            property_value=pvalue,
                            ordinal=counts[pname],
                            source_file=str(cfg_path),
                            source_line=line_number,
                            line_scope_start=line_number,
                            line_scope_end=line_number,
                            subcontext=[],
                            raw_statement=raw,
                        )
                    )

                properties.extend(inline_props)
                objects.append({
                    "object_id": object_id,
                    "occurrence_id": occurrence_id,
                    "environment": environment,
                    "canonical_type": rule["canonical_type"],
                    "object_name": object_name,
                    "cli_command": cli_command,
                    "declaration_form": declaration_form,
                    "recognition_kind": rule["recognition_kind"],
                    "category": rule["category"],
                    "architecture_relevance": rule["architecture_relevance"],
                    "source_file": str(cfg_path),
                    "source_relative_path": cfg_path.name,
                    "start_line": line_number,
                    "end_line": line_number,
                    "raw_block_sha256": sha256_text(raw.rstrip("\n")),
                    "parent_context": json.dumps(
                        context_stack,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                    "depth": len(context_stack),
                    "property_count": len(inline_props),
                    "parse_status": "parsed",
                    "parse_reason": "",
                    "parser_version": PARSER_VERSION,
                })
                continue

            current = {
                "canonical_type": rule["canonical_type"],
                "object_name": object_name,
                "cli_command": cli_command,
                "declaration_form": declaration_form,
                "recognition_kind": rule["recognition_kind"],
                "category": rule["category"],
                "architecture_relevance": rule["architecture_relevance"],
                "start_line": line_number,
                "parent_context": list(context_stack),
            }
            current_raw_lines = [raw]
            current_properties = []
            current_property_counts = Counter()
            subcontext_stack = []
            continue

        # This metric now means exactly what it says: a top-level statement
        # that could not be assigned to a logical object or structural context.
        tokens = tokenize_cli_line(s)
        unclassified.append({
            "environment": environment,
            "source_file": str(cfg_path),
            "line_number": line_number,
            "command": tokens[0] if tokens else "",
            "line_sha256": sha256_text(s),
            "context": json.dumps(
                context_stack, ensure_ascii=False, separators=(",", ":")
            ),
            "status": "unclassified_top_level_statement",
            "parser_version": PARSER_VERSION,
        })

    if current is not None:
        finalize_current(
            len(lines),
            parse_status="partial",
            parse_reason="unterminated_object_block",
        )

    return objects, properties, unclassified


def write_csv(
    path: Path,
    rows: List[Dict[str, Any]],
    fieldnames: List[str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Parse IBM DataPower CFG into architecture objects and "
            "losslessly-owned properties."
        )
    )
    parser.add_argument("--cfg", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--taxonomy-dir", default="taxonomy")
    parser.add_argument("--objects-output", default="index/objects.csv")
    parser.add_argument(
        "--properties-output", default="index/object_properties.csv"
    )
    parser.add_argument(
        "--unrecognized-output",
        default="index/unclassified_top_level_statements.csv",
    )
    args = parser.parse_args()

    cfg_path = Path(args.cfg).resolve()
    taxonomy_dir = Path(args.taxonomy_dir).resolve()

    if not cfg_path.exists():
        print(f"[FATAL] CFG not found: {cfg_path}")
        return 2

    object_doc = load_object_document(taxonomy_dir)
    objects, properties, unclassified = parse_cfg(
        cfg_path, args.environment, object_doc
    )

    object_fields = [
        "object_id", "occurrence_id", "environment", "canonical_type",
        "object_name", "cli_command", "declaration_form",
        "recognition_kind", "category", "architecture_relevance",
        "source_file", "source_relative_path", "start_line", "end_line",
        "raw_block_sha256", "parent_context", "depth", "property_count",
        "parse_status", "parse_reason", "parser_version",
    ]
    property_fields = [
        "object_id", "occurrence_id", "environment", "canonical_type",
        "object_name", "property_name", "property_value", "property_path",
        "subcontext", "ordinal", "source_file", "source_line",
        "line_scope_start", "line_scope_end", "raw_statement",
        "raw_statement_sha256", "parser_version",
    ]
    unclassified_fields = [
        "environment", "source_file", "line_number", "command",
        "line_sha256", "context", "status", "parser_version",
    ]

    write_csv(Path(args.objects_output), objects, object_fields)
    write_csv(Path(args.properties_output), properties, property_fields)
    write_csv(
        Path(args.unrecognized_output), unclassified, unclassified_fields
    )

    logical_counts = Counter(x["object_id"] for x in objects)
    by_type = Counter(x["canonical_type"] for x in objects)
    partial = sum(x["parse_status"] != "parsed" for x in objects)

    print("=" * 76)
    print("DATAPOWER CFG PARSER 2.2 — ARCHITECTURE BETA")
    print("=" * 76)
    print(f"Parser version:                    {PARSER_VERSION}")
    print(f"Object occurrences:                {len(objects)}")
    print(f"Unique logical objects:            {len(logical_counts)}")
    print(f"Repeated logical objects:          {sum(v > 1 for v in logical_counts.values())}")
    print(f"Properties preserved:              {len(properties)}")
    print(f"Partial/malformed blocks:          {partial}")
    print(f"Unclassified top-level statements: {len(unclassified)}")
    print("-" * 76)
    print("Object types:")
    for key, count in sorted(by_type.items()):
        print(f"  {key}: {count}")
    print("-" * 76)

    if partial:
        print("CFG PARSER 2.2: COMPLETED WITH PARSE GAPS")
        return 1

    print("CFG PARSER 2.2: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
