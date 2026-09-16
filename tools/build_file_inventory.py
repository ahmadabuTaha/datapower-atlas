from __future__ import annotations

import csv
import hashlib
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXTRACTED_DIR = PROJECT_ROOT / "extracted"
INDEX_DIR = PROJECT_ROOT / "index"
OUTPUT_FILE = INDEX_DIR / "files.csv"


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def classify_file(path: Path) -> tuple[str, str]:
    """
    Returns:
        (classification, classification_reason)

    Important:
    - No vague categories such as Other, Misc, Various, Unknown.
    - Unsupported extensions are classified explicitly.
    """

    name = path.name.lower()
    suffix = path.suffix.lower()

    # DataPower configuration
    if suffix == ".cfg":
        return (
            "datapower_cfg",
            "classified_by_cfg_extension",
        )

    # XSLT / XSL
    if suffix in {".xsl", ".xslt"}:
        return (
            "xslt_stylesheet",
            f"classified_by_{suffix.removeprefix('.')}_extension",
        )

    # GatewayScript / JavaScript
    if suffix == ".js":
        return (
            "gateway_script_javascript",
            "classified_by_js_extension",
        )

    # Web service and XML schemas
    if suffix == ".wsdl":
        return (
            "wsdl_definition",
            "classified_by_wsdl_extension",
        )

    if suffix == ".xsd":
        return (
            "xsd_schema",
            "classified_by_xsd_extension",
        )

    # XML / JSON
    if suffix == ".xml":
        return (
            "xml_document",
            "classified_by_xml_extension",
        )

    if suffix == ".json":
        return (
            "json_document",
            "classified_by_json_extension",
        )

    # MQ configuration
    if name == "mqclient.ini":
        return (
            "mq_client_ini",
            "classified_by_exact_mqclient_ini_filename",
        )

    # Generic INI configuration
    if suffix == ".ini":
        return (
            "ini_configuration",
            "classified_by_ini_extension",
        )

    # Property/config formats
    if suffix == ".properties":
        return (
            "properties_configuration",
            "classified_by_properties_extension",
        )

    if suffix in {".yaml", ".yml"}:
        return (
            "yaml_configuration",
            f"classified_by_{suffix.removeprefix('.')}_extension",
        )

    # Text
    if suffix == ".txt":
        return (
            "text_document",
            "classified_by_txt_extension",
        )

    # Certificates
    if suffix == ".pem":
        return (
            "pem_certificate_or_key_material",
            "classified_by_pem_extension",
        )

    if suffix == ".cer":
        return (
            "cer_certificate",
            "classified_by_cer_extension",
        )

    if suffix == ".crt":
        return (
            "crt_certificate",
            "classified_by_crt_extension",
        )

    if suffix == ".der":
        return (
            "der_certificate",
            "classified_by_der_extension",
        )

    # Keystores
    if suffix in {".p12", ".pfx"}:
        return (
            "pkcs12_keystore",
            f"classified_by_{suffix.removeprefix('.')}_extension",
        )

    if suffix == ".jks":
        return (
            "java_keystore",
            "classified_by_jks_extension",
        )

    # SQL
    if suffix == ".sql":
        return (
            "sql_script",
            "classified_by_sql_extension",
        )

    # Shell / command scripts
    if suffix == ".sh":
        return (
            "shell_script",
            "classified_by_sh_extension",
        )

    if suffix in {".bat", ".cmd"}:
        return (
            "windows_command_script",
            f"classified_by_{suffix.removeprefix('.')}_extension",
        )

    # Archives
    if suffix == ".zip":
        return (
            "zip_archive",
            "classified_by_zip_extension",
        )

    if suffix in {".gz", ".tgz"}:
        return (
            "gzip_archive",
            f"classified_by_{suffix.removeprefix('.')}_extension",
        )

    if suffix == ".tar":
        return (
            "tar_archive",
            "classified_by_tar_extension",
        )

    # Known binary formats
    if suffix in {".jar"}:
        return (
            "java_archive_binary",
            "classified_by_jar_extension",
        )

    if suffix in {".dll"}:
        return (
            "windows_dynamic_library_binary",
            "classified_by_dll_extension",
        )

    if suffix in {".so"}:
        return (
            "linux_shared_library_binary",
            "classified_by_so_extension",
        )

    # macOS metadata
    if name == ".ds_store":
        return (
            "macos_directory_metadata",
            "classified_by_exact_ds_store_filename",
        )

    # No extension
    if not suffix:
        return (
            "unclassified_due_to_missing_extension",
            "file_has_no_extension_and_content_has_not_yet_been_inspected",
        )

    # Explicit unsupported-extension classification
    return (
        f"unclassified_due_to_unsupported_extension_{suffix.removeprefix('.')}",
        f"extension_{suffix}_is_not_yet_present_in_classification_rules",
    )


def get_environment(file_path: Path) -> str:
    """
    Expected structure:

    extracted/
        STG/
        UAT/
        STG-Replica/
        UAT-Replica/
        default/
    """

    relative = file_path.relative_to(EXTRACTED_DIR)

    if not relative.parts:
        raise ValueError(f"Cannot determine environment for {file_path}")

    return relative.parts[0]


def build_inventory() -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []

    for path in sorted(EXTRACTED_DIR.rglob("*")):
        if not path.is_file():
            continue

        relative_path = path.relative_to(EXTRACTED_DIR)
        environment = get_environment(path)

        classification, classification_reason = classify_file(path)

        row = {
            "environment": environment,
            "relative_path": relative_path.as_posix(),
            "file_name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
            "classification": classification,
            "classification_reason": classification_reason,
        }

        rows.append(row)

    return rows


def write_csv(rows: list[dict[str, str | int]]) -> None:
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "environment",
        "relative_path",
        "file_name",
        "extension",
        "size_bytes",
        "sha256",
        "classification",
        "classification_reason",
    ]

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def print_summary(rows: list[dict[str, str | int]]) -> None:
    counts: dict[tuple[str, str], int] = {}

    for row in rows:
        key = (
            str(row["environment"]),
            str(row["classification"]),
        )

        counts[key] = counts.get(key, 0) + 1

    print()
    print(f"Inventory written to: {OUTPUT_FILE}")
    print(f"Total files indexed: {len(rows)}")
    print()
    print("Files by environment and classification:")
    print()

    for (environment, classification), count in sorted(counts.items()):
        print(
            f"{environment:<20} "
            f"{classification:<60} "
            f"{count:>6}"
        )


def main() -> None:
    if not EXTRACTED_DIR.exists():
        raise SystemExit(
            f"Extracted directory does not exist: {EXTRACTED_DIR}"
        )

    rows = build_inventory()
    write_csv(rows)
    print_summary(rows)


if __name__ == "__main__":
    main()