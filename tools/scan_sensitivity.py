#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from taxonomy_loader import get_mapping, load_taxonomies


TEXT_LIKE_CLASSIFICATIONS = {
    "datapower_cfg",
    "xslt_stylesheet",
    "gateway_script_javascript",
    "wsdl_definition",
    "xsd_schema",
    "xml_document",
    "json_document",
    "mq_client_ini",
    "ini_configuration",
    "plain_text_artifact",
}


SECRET_LEVELS = {
    "credential_value",
    "private_key_material",
    "personal_or_identity_data",
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def bool_from_csv(value: str) -> bool:
    return str(value).strip().lower() == "true"


def load_csv(path: Path) -> Tuple[List[Dict[str, str]], List[str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return rows, list(reader.fieldnames or [])


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out: Dict[str, Any] = {}
            for k in fieldnames:
                v = row.get(k, "")
                if isinstance(v, list):
                    v = json.dumps(v, ensure_ascii=False, separators=(",", ":"))
                elif isinstance(v, bool):
                    v = "true" if v else "false"
                elif v is None:
                    v = ""
                out[k] = v
            writer.writerow(out)


def build_signal_patterns(
    sensitivity_taxonomy: Dict[str, Any],
) -> List[Tuple[str, str, re.Pattern]]:
    signals = get_mapping(
        sensitivity_taxonomy,
        "content_signals",
        "sensitivity",
    )

    patterns: List[Tuple[str, str, re.Pattern]] = []

    for signal_name, spec in signals.items():
        suggested = spec.get("suggested_sensitivity")
        for raw_value in spec.get("values", []) or []:
            pattern = re.compile(re.escape(str(raw_value)), re.IGNORECASE)
            patterns.append((signal_name, suggested, pattern))

    return patterns


def detect_property_assignment(line: str) -> Optional[Tuple[str, str]]:
    """
    Best-effort detection for common CFG/XML/JSON/INI/XSL forms.

    This scanner intentionally does not replace proper language parsers.
    It is a conservative pre-indexing safety layer.
    """
    patterns = [
        re.compile(
            r'^\s*["\']?([A-Za-z0-9_.:-]+)["\']?\s*[:=]\s*["\']?(.+?)["\']?\s*[,;]?\s*$'
        ),
        re.compile(r'^\s*([A-Za-z0-9_.:-]+)\s+(.+?)\s*$'),
        re.compile(r'<([A-Za-z0-9_.:-]+)>(.*?)</\1>', re.IGNORECASE),
        re.compile(
            r'<xsl:variable[^>]+name=["\']([^"\']+)["\'][^>]+select=["\'](.*?)["\']',
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        match = pattern.search(line)
        if match:
            return match.group(1).strip(), match.group(2).strip()

    return None


# def looks_like_secret_literal(value: str) -> bool:
#     if not value:
#         return False
#
#     cleaned = value.strip().strip("\"'")
#
#     if cleaned.lower() in {
#         "",
#         "[redacted]",
#         "true",
#         "false",
#         "enabled",
#         "disabled",
#         "none",
#         "null",
#     }:
#         return False
#
#     return len(cleaned) >= 3

def looks_like_secret_literal(value: str, property_name: str = "") -> bool:
    if not value:
        return False

    cleaned = value.strip().strip("\"'")
    lowered = cleaned.lower()
    prop = property_name.lower()

    non_secret_literals = {
        "",
        "[redacted]",
        "true",
        "false",
        "enabled",
        "disabled",
        "none",
        "null",
        "yes",
        "no",
        "on",
        "off",
        "basic",
        "bearer",
        "digest",
    }

    if lowered in non_secret_literals:
        return False

    if prop in {"authorization", "proxy-authorization"}:
        if lowered in {"basic", "bearer", "digest"}:
            return False

    if prop in {"token", "authorization", "proxy-authorization"}:
        if len(cleaned) < 6:
            return False

    return len(cleaned) >= 3


def add_finding(
    findings: List[Dict[str, Any]],
    file_row: Dict[str, str],
    line_number: int,
    finding_type: str,
    sensitivity_level: str,
    property_name: str,
    signal_name: str,
    raw_value: Optional[str],
    redacted: bool,
) -> None:
    findings.append(
        {
            "file_id": file_row["file_id"],
            "environment": file_row["environment"],
            "relative_path": file_row["relative_path"],
            "line_number": line_number,
            "finding_type": finding_type,
            "sensitivity_level": sensitivity_level,
            "property_name": property_name,
            "signal_name": signal_name,
            "value_length": len(raw_value) if raw_value is not None else 0,
            "value_sha256": sha256_text(raw_value) if raw_value is not None else "",
            "redacted": redacted,
        }
    )


def scan_file(
    path: Path,
    file_row: Dict[str, str],
    sensitivity_taxonomy: Dict[str, Any],
    signal_patterns: List[Tuple[str, str, re.Pattern]],
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    findings: List[Dict[str, Any]] = []

    redaction_cfg = get_mapping(sensitivity_taxonomy, "redaction", "sensitivity")
    replacement = redaction_cfg.get("replacement_token", "[REDACTED]")

    prop_policies = get_mapping(
        sensitivity_taxonomy,
        "property_policies",
        "sensitivity",
    )

    always_redact = {
        str(x).lower()
        for x in prop_policies.get("always_redact_exact_names", []) or []
    }

    preserve_refs = {
        str(x).lower()
        for x in prop_policies.get("preserve_reference_names", []) or []
    }

    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception:
        return [], None

    sanitized_lines: List[str] = []

    private_key_begin = re.compile(
        r"-----BEGIN (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----",
        re.IGNORECASE,
    )
    private_key_end = re.compile(
        r"-----END (?:RSA |EC |ENCRYPTED )?PRIVATE KEY-----",
        re.IGNORECASE,
    )

    auth_header = re.compile(
        r"(?i)\b(Authorization|Proxy-Authorization|X-API-Key|Api-Key)\b"
        r"\s*[:=]\s*(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
    )

    in_private_key_block = False
    private_key_buffer: List[str] = []
    private_key_start_line: Optional[int] = None

    for line_no, line in enumerate(lines, start=1):
        # Never copy private key body into sanitized output.
        if in_private_key_block:
            private_key_buffer.append(line)

            if private_key_end.search(line):
                raw_block = "".join(private_key_buffer)

                add_finding(
                    findings=findings,
                    file_row=file_row,
                    line_number=private_key_start_line or line_no,
                    finding_type="private_key_material",
                    sensitivity_level="private_key_material",
                    property_name="",
                    signal_name="private_key_markers",
                    raw_value=raw_block,
                    redacted=True,
                )

                sanitized_lines.append(replacement + "\n")
                in_private_key_block = False
                private_key_buffer = []
                private_key_start_line = None

            continue

        if private_key_begin.search(line):
            in_private_key_block = True
            private_key_start_line = line_no
            private_key_buffer = [line]

            if private_key_end.search(line):
                add_finding(
                    findings=findings,
                    file_row=file_row,
                    line_number=line_no,
                    finding_type="private_key_material",
                    sensitivity_level="private_key_material",
                    property_name="",
                    signal_name="private_key_markers",
                    raw_value=line,
                    redacted=True,
                )
                sanitized_lines.append(replacement + "\n")
                in_private_key_block = False
                private_key_buffer = []
                private_key_start_line = None

            continue

        sanitized = line

        # Authorization/API-key style values.
        auth_match = auth_header.search(sanitized)
        if auth_match:
            raw_value = auth_match.group(2).strip().strip("\"'")

            add_finding(
                findings=findings,
                file_row=file_row,
                line_number=line_no,
                finding_type="authorization_header",
                sensitivity_level="credential_value",
                property_name=auth_match.group(1),
                signal_name="authentication_headers",
                raw_value=raw_value,
                redacted=True,
            )

            sanitized = (
                sanitized[: auth_match.start(2)]
                + replacement
                + sanitized[auth_match.end(2) :]
            )

        # Explicit property/value handling.
        assignment = detect_property_assignment(line)

        if assignment:
            prop_name, prop_value = assignment
            prop_key = prop_name.lower()

            if (prop_key in always_redact
            and looks_like_secret_literal(prop_value, prop_name)
):
                raw_value = prop_value.strip().strip("\"'")

                add_finding(
                    findings=findings,
                    file_row=file_row,
                    line_number=line_no,
                    finding_type="credential_literal",
                    sensitivity_level="credential_value",
                    property_name=prop_name,
                    signal_name="always_redact_exact_names",
                    raw_value=raw_value,
                    redacted=True,
                )

                sanitized = sanitized.replace(prop_value, replacement, 1)

            elif prop_key in preserve_refs:
                # Alias/reference names are intentionally retained.
                pass

        # Public certificate marker is relevant sensitivity evidence,
        # but not a secret.
        for signal_name, suggested, pattern in signal_patterns:
            if suggested != "certificate_public_material":
                continue

            if pattern.search(line):
                add_finding(
                    findings=findings,
                    file_row=file_row,
                    line_number=line_no,
                    finding_type="certificate_public_material",
                    sensitivity_level="certificate_public_material",
                    property_name="",
                    signal_name=signal_name,
                    raw_value=None,
                    redacted=False,
                )

        sanitized_lines.append(sanitized)

    # Unterminated private key block: fail closed by redacting through EOF.
    if in_private_key_block and private_key_buffer:
        raw_block = "".join(private_key_buffer)

        add_finding(
            findings=findings,
            file_row=file_row,
            line_number=private_key_start_line or 0,
            finding_type="private_key_material",
            sensitivity_level="private_key_material",
            property_name="",
            signal_name="private_key_markers_unterminated",
            raw_value=raw_block,
            redacted=True,
        )

        sanitized_lines.append(replacement + "\n")

    return findings, "".join(sanitized_lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan indexed DataPower files for sensitive content."
    )

    parser.add_argument(
        "--inventory",
        default="index/files_stg.csv",
        help="Input file inventory CSV",
    )

    parser.add_argument(
        "--taxonomy-dir",
        default="taxonomy",
        help="Taxonomy directory",
    )

    parser.add_argument(
        "--findings-output",
        default="index/sensitivity_findings.csv",
        help="Sensitivity findings CSV",
    )

    parser.add_argument(
        "--inventory-output",
        default="index/files_stg_scanned.csv",
        help="Enriched inventory CSV",
    )

    parser.add_argument(
        "--sanitized-dir",
        default="index/sanitized",
        help="Sanitized file output directory",
    )

    args = parser.parse_args()

    inventory_path = Path(args.inventory).resolve()
    taxonomy_dir = Path(args.taxonomy_dir).resolve()
    findings_output = Path(args.findings_output).resolve()
    inventory_output = Path(args.inventory_output).resolve()
    sanitized_dir = Path(args.sanitized_dir).resolve()

    if not inventory_path.exists():
        print(f"[FATAL] Inventory does not exist: {inventory_path}")
        return 2

    bundle = load_taxonomies(taxonomy_dir)
    sensitivity_taxonomy = bundle.sensitivity
    signal_patterns = build_signal_patterns(sensitivity_taxonomy)

    rows, fieldnames = load_csv(inventory_path)

    findings_all: List[Dict[str, Any]] = []
    scanned_rows: List[Dict[str, Any]] = []

    scanned_count = 0
    skipped_count = 0
    failed_count = 0
    files_with_findings = 0

    for row in rows:
        out = dict(row)

        requires_scan = bool_from_csv(
            row.get("requires_content_sensitivity_scan", "false")
        )
        classification = row.get("classification", "")

        if not requires_scan or classification not in TEXT_LIKE_CLASSIFICATIONS:
            skipped_count += 1
            scanned_rows.append(out)
            continue

        abs_path = Path(row["absolute_path"])

        if not abs_path.exists():
            out["sensitivity_scan_status"] = "failed"
            out["contains_sensitive_content"] = ""
            out["sanitized_content_available"] = "false"
            failed_count += 1
            scanned_rows.append(out)
            continue

        file_findings, sanitized_content = scan_file(
            abs_path,
            row,
            sensitivity_taxonomy,
            signal_patterns,
        )

        scanned_count += 1

        unique_levels = sorted(
            {
                f["sensitivity_level"]
                for f in file_findings
                if f.get("sensitivity_level")
            }
        )

        secret_count = sum(
            1
            for f in file_findings
            if f.get("sensitivity_level") in SECRET_LEVELS
        )

        contains_sensitive = secret_count > 0

        out["sensitivity_scan_status"] = (
            "completed_with_findings" if file_findings else "completed"
        )
        out["contains_sensitive_content"] = (
            "true" if contains_sensitive else "false"
        )
        out["detected_secret_count"] = str(secret_count)
        out["detected_sensitivity_types"] = json.dumps(
            unique_levels,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        out["sensitivity_scan_timestamp"] = now_iso()

        if file_findings:
            files_with_findings += 1

        if file_findings and sanitized_content is not None:
            relative = Path(row["environment"]) / row["relative_path"]
            target = sanitized_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(sanitized_content, encoding="utf-8")
            out["sanitized_content_available"] = "true"
        else:
            out["sanitized_content_available"] = "false"

        findings_all.extend(file_findings)
        scanned_rows.append(out)

    finding_fields = [
        "file_id",
        "environment",
        "relative_path",
        "line_number",
        "finding_type",
        "sensitivity_level",
        "property_name",
        "signal_name",
        "value_length",
        "value_sha256",
        "redacted",
    ]

    write_csv(findings_output, findings_all, finding_fields)
    write_csv(inventory_output, scanned_rows, fieldnames)

    print("=" * 72)
    print("DATAPOWER SENSITIVITY SCAN")
    print("=" * 72)
    print(f"Inventory:             {inventory_path}")
    print(f"Taxonomy:              {taxonomy_dir}")
    print(f"Findings output:       {findings_output}")
    print(f"Scanned inventory:     {inventory_output}")
    print(f"Sanitized directory:   {sanitized_dir}")
    print("-" * 72)
    print(f"Files scanned:         {scanned_count}")
    print(f"Files skipped:         {skipped_count}")
    print(f"Files failed:          {failed_count}")
    print(f"Files with findings:   {files_with_findings}")
    print(f"Total findings:        {len(findings_all)}")
    print("-" * 72)

    if failed_count:
        print("SENSITIVITY SCAN: COMPLETED WITH FAILURES")
        return 1

    print("SENSITIVITY SCAN: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
