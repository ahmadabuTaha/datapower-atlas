#!/usr/bin/env bash
set -Eeuo pipefail

# ============================================================================
# DataPower Atlas - Per-Domain Full Pipeline
# ============================================================================
#
# Usage:
#   ./tools/run_domain_pipeline.sh --domain STG
#
# Example with a domain name containing spaces:
#   ./tools/run_domain_pipeline.sh \
#     --domain "STG Replica" \
#     --environment STG \
#     --cfg "export-stg-uat/extracted/STG Replica/config/STG Replica.cfg"
#
# Optional:
#   --export-dir export-stg-uat/extracted
#   --taxonomy-dir taxonomy
#   --index-root index
#   --reports-root reports
#   --python python
#
# Notes:
# - Each domain gets its own isolated index/<DOMAIN_SLUG>/ directory.
# - The frozen file inventory tool is not modified. It scans the export root,
#   then this wrapper filters the inventory to the requested domain.
# - The script stops immediately if any stage fails.
# ============================================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

DOMAIN=""
ENVIRONMENT=""
CFG_FILE=""
EXPORT_DIR="export-stg-uat/extracted"
TAXONOMY_DIR="taxonomy"
INDEX_ROOT="index"
REPORTS_ROOT="reports"
PYTHON_BIN="${PYTHON_BIN:-python}"

usage() {
  sed -n '3,35p' "$0"
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain)
      DOMAIN="${2:?Missing value for --domain}"
      shift 2
      ;;
    --environment)
      ENVIRONMENT="${2:?Missing value for --environment}"
      shift 2
      ;;
    --cfg)
      CFG_FILE="${2:?Missing value for --cfg}"
      shift 2
      ;;
    --export-dir)
      EXPORT_DIR="${2:?Missing value for --export-dir}"
      shift 2
      ;;
    --taxonomy-dir)
      TAXONOMY_DIR="${2:?Missing value for --taxonomy-dir}"
      shift 2
      ;;
    --index-root)
      INDEX_ROOT="${2:?Missing value for --index-root}"
      shift 2
      ;;
    --reports-root)
      REPORTS_ROOT="${2:?Missing value for --reports-root}"
      shift 2
      ;;
    --python)
      PYTHON_BIN="${2:?Missing value for --python}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[FATAL] Unknown argument: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$DOMAIN" ]]; then
  echo "[FATAL] --domain is required" >&2
  usage
  exit 2
fi

# Parser environment can be different from the DataPower domain.
# If not explicitly supplied, use the domain value.
if [[ -z "$ENVIRONMENT" ]]; then
  ENVIRONMENT="$DOMAIN"
fi

# Safe directory name only; the evidence retains the real domain string.
DOMAIN_SLUG="$(
  printf '%s' "$DOMAIN" \
  | tr '[:lower:]' '[:upper:]' \
  | sed -E 's/[^A-Z0-9._-]+/_/g; s/^_+//; s/_+$//'
)"

if [[ -z "$DOMAIN_SLUG" ]]; then
  echo "[FATAL] Could not derive a directory name from domain: $DOMAIN" >&2
  exit 2
fi

DOMAIN_INDEX="${INDEX_ROOT}/${DOMAIN_SLUG}"
DOMAIN_REPORTS="${REPORTS_ROOT}/${DOMAIN_SLUG}"

mkdir -p "$DOMAIN_INDEX" "$DOMAIN_REPORTS"

RUN_LOG="${DOMAIN_REPORTS}/pipeline.log"
: > "$RUN_LOG"
exec > >(tee -a "$RUN_LOG") 2>&1

trap 'echo; echo "[FAILED] Stage failed at line $LINENO. See: $RUN_LOG"' ERR

if [[ -z "$CFG_FILE" ]]; then
  CFG_FILE="${EXPORT_DIR}/${DOMAIN}/config/${DOMAIN}.cfg"
fi

echo "============================================================================"
echo "DATAPOWER ATLAS - DOMAIN PIPELINE"
echo "============================================================================"
echo "Project root:      $ROOT_DIR"
echo "Domain:            $DOMAIN"
echo "Environment:       $ENVIRONMENT"
echo "Domain index:      $DOMAIN_INDEX"
echo "Domain reports:    $DOMAIN_REPORTS"
echo "Export root:       $EXPORT_DIR"
echo "CFG:               $CFG_FILE"
echo "Taxonomy:          $TAXONOMY_DIR"
echo "Python:            $PYTHON_BIN"
echo "============================================================================"

required_files=(
  "tools/validate_taxonomies.py"
  "tools/build_file_inventory.py"
  "tools/scan_sensitivity.py"
  "tools/parse_datapower_cfg.py"
  "tools/extract_datapower_references.py"
  "tools/resolve_datapower_relationships.py"
  "tools/extract_datapower_endpoints.py"
  "tools/resolve_datapower_file_references.py"
  "tools/build_datapower_service_journeys.py"
  "tools/build_operation_journeys.py"
  "tools/analyze_journey_quality.py"
  "$CFG_FILE"
)

for f in "${required_files[@]}"; do
  if [[ ! -f "$f" ]]; then
    echo "[FATAL] Required file not found: $f" >&2
    exit 2
  fi
done

if [[ ! -d "$EXPORT_DIR" ]]; then
  echo "[FATAL] Export directory not found: $EXPORT_DIR" >&2
  exit 2
fi

if [[ ! -d "$TAXONOMY_DIR" ]]; then
  echo "[FATAL] Taxonomy directory not found: $TAXONOMY_DIR" >&2
  exit 2
fi

stage() {
  echo
  echo "============================================================================"
  echo "$1"
  echo "============================================================================"
}

# ----------------------------------------------------------------------------
# 1. Taxonomy validation
# ----------------------------------------------------------------------------
stage "1/11 - VALIDATE TAXONOMIES"

"$PYTHON_BIN" tools/validate_taxonomies.py \
  --taxonomy-dir "$TAXONOMY_DIR"

# ----------------------------------------------------------------------------
# 2. File inventory
# ----------------------------------------------------------------------------
#
# build_file_inventory.py derives the environment/domain from the first path
# component below EXPORT_DIR. It does not currently accept a domain filter.
# Keep the frozen tool untouched: build a temporary full inventory, then filter
# exact environment/domain rows into this domain's index.
# ----------------------------------------------------------------------------
stage "2/11 - BUILD DOMAIN FILE INVENTORY"

TMP_ALL_FILES="${DOMAIN_INDEX}/.files_all_domains.tmp.csv"

"$PYTHON_BIN" tools/build_file_inventory.py \
  --exported-dir "$EXPORT_DIR" \
  --taxonomy-dir "$TAXONOMY_DIR" \
  --output "$TMP_ALL_FILES"

DOMAIN="$DOMAIN" INPUT="$TMP_ALL_FILES" OUTPUT="${DOMAIN_INDEX}/files.csv" \
"$PYTHON_BIN" - <<'PY'
import csv
import os
from pathlib import Path

domain = os.environ["DOMAIN"]
src = Path(os.environ["INPUT"])
dst = Path(os.environ["OUTPUT"])

with src.open("r", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    fields = reader.fieldnames or []
    rows = [r for r in reader if r.get("environment") == domain]

if not rows:
    raise SystemExit(
        f"[FATAL] No inventory rows found for domain/environment {domain!r}. "
        "Check --domain and --export-dir."
    )

dst.parent.mkdir(parents=True, exist_ok=True)
with dst.open("w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)

print(f"Domain inventory rows: {len(rows)}")
print(f"Domain inventory:      {dst}")
PY

rm -f "$TMP_ALL_FILES"

# ----------------------------------------------------------------------------
# 3. Sensitivity scan
# ----------------------------------------------------------------------------
stage "3/11 - SCAN SENSITIVITY"

"$PYTHON_BIN" tools/scan_sensitivity.py \
  --inventory "${DOMAIN_INDEX}/files.csv" \
  --taxonomy-dir "$TAXONOMY_DIR" \
  --findings-output "${DOMAIN_INDEX}/sensitivity_findings.csv" \
  --inventory-output "${DOMAIN_INDEX}/files_scanned.csv" \
  --sanitized-dir "${DOMAIN_INDEX}/sanitized"

# ----------------------------------------------------------------------------
# 4. CFG parser
# ----------------------------------------------------------------------------
stage "4/11 - PARSE DATAPOWER CFG"

"$PYTHON_BIN" tools/parse_datapower_cfg.py \
  --cfg "$CFG_FILE" \
  --environment "$ENVIRONMENT" \
  --taxonomy-dir "$TAXONOMY_DIR" \
  --objects-output "${DOMAIN_INDEX}/objects.csv" \
  --properties-output "${DOMAIN_INDEX}/object_properties.csv" \
  --unrecognized-output "${DOMAIN_INDEX}/unclassified_top_level.csv"

# ----------------------------------------------------------------------------
# 5. Reference extraction
# ----------------------------------------------------------------------------
stage "5/11 - EXTRACT REFERENCES"

"$PYTHON_BIN" tools/extract_datapower_references.py \
  --properties "${DOMAIN_INDEX}/object_properties.csv" \
  --cross-taxonomy "${TAXONOMY_DIR}/cross_taxonomy.yaml" \
  --reference-types "${TAXONOMY_DIR}/reference_types.yaml" \
  --output "${DOMAIN_INDEX}/references.csv" \
  --taxonomy-gaps-output "${DOMAIN_INDEX}/reference_taxonomy_gaps.csv"

# ----------------------------------------------------------------------------
# 6. Relationship resolution
# ----------------------------------------------------------------------------
stage "6/11 - RESOLVE OBJECT RELATIONSHIPS"

"$PYTHON_BIN" tools/resolve_datapower_relationships.py \
  --objects "${DOMAIN_INDEX}/objects.csv" \
  --references "${DOMAIN_INDEX}/references.csv" \
  --relationships-output "${DOMAIN_INDEX}/relationships.csv" \
  --unresolved-output "${DOMAIN_INDEX}/unresolved_relationships.csv" \
  --passthrough-output "${DOMAIN_INDEX}/non_object_references.csv"

# ----------------------------------------------------------------------------
# 7. Endpoint extraction (V1.1 includes WSP composite endpoints)
# ----------------------------------------------------------------------------
stage "7/11 - EXTRACT ENDPOINTS"

"$PYTHON_BIN" tools/extract_datapower_endpoints.py \
  --references "${DOMAIN_INDEX}/non_object_references.csv" \
  --properties "${DOMAIN_INDEX}/object_properties.csv" \
  --endpoint-types "${TAXONOMY_DIR}/endpoint_types.yaml" \
  --output "${DOMAIN_INDEX}/endpoints.csv" \
  --catalog-output "${DOMAIN_INDEX}/endpoint_catalog.csv" \
  --non-endpoint-output "${DOMAIN_INDEX}/file_references_pending.csv"

# ----------------------------------------------------------------------------
# 8. File reference resolution
# ----------------------------------------------------------------------------
stage "8/11 - RESOLVE FILE REFERENCES"

"$PYTHON_BIN" tools/resolve_datapower_file_references.py \
  --references "${DOMAIN_INDEX}/file_references_pending.csv" \
  --inventory "${DOMAIN_INDEX}/files_scanned.csv" \
  --resolved-output "${DOMAIN_INDEX}/file_relationships.csv" \
  --unresolved-output "${DOMAIN_INDEX}/unresolved_file_references.csv"

# ----------------------------------------------------------------------------
# 9. Service journeys
# ----------------------------------------------------------------------------
stage "9/11 - BUILD SERVICE JOURNEYS"

"$PYTHON_BIN" tools/build_datapower_service_journeys.py \
  --objects "${DOMAIN_INDEX}/objects.csv" \
  --properties "${DOMAIN_INDEX}/object_properties.csv" \
  --relationships "${DOMAIN_INDEX}/relationships.csv" \
  --endpoints "${DOMAIN_INDEX}/endpoints.csv" \
  --file-relationships "${DOMAIN_INDEX}/file_relationships.csv" \
  --unresolved-file-references "${DOMAIN_INDEX}/unresolved_file_references.csv" \
  --artifact-root "${EXPORT_DIR}/${DOMAIN}" \
  --output "${DOMAIN_INDEX}/service_journeys.jsonl" \
  --summary-output "${DOMAIN_INDEX}/service_journey_summary.csv"

# ----------------------------------------------------------------------------
# 10. Operation-level journeys
# ----------------------------------------------------------------------------
stage "10/11 - BUILD OPERATION JOURNEYS"

"$PYTHON_BIN" tools/build_operation_journeys.py \
  --objects "${DOMAIN_INDEX}/objects.csv" \
  --properties "${DOMAIN_INDEX}/object_properties.csv" \
  --relationships "${DOMAIN_INDEX}/relationships.csv" \
  --endpoints "${DOMAIN_INDEX}/endpoints.csv" \
  --file-relationships "${DOMAIN_INDEX}/file_relationships.csv" \
  --unresolved-file-references "${DOMAIN_INDEX}/unresolved_file_references.csv" \
  --artifact-root "${EXPORT_DIR}/${DOMAIN}" \
  --output "${DOMAIN_INDEX}/operation_journeys.jsonl" \
  --summary-output "${DOMAIN_INDEX}/operation_journey_summary.csv"

# ----------------------------------------------------------------------------
# 11. Journey quality / completeness findings
# ----------------------------------------------------------------------------
stage "11/11 - ANALYZE JOURNEY QUALITY"

"$PYTHON_BIN" tools/analyze_journey_quality.py \
  --summary "${DOMAIN_INDEX}/service_journey_summary.csv" \
  --objects "${DOMAIN_INDEX}/objects.csv" \
  --properties "${DOMAIN_INDEX}/object_properties.csv" \
  --relationships "${DOMAIN_INDEX}/relationships.csv" \
  --operation-summary "${DOMAIN_INDEX}/operation_journey_summary.csv" \
  --output "${DOMAIN_INDEX}/service_journey_findings.csv"

# ----------------------------------------------------------------------------
# Final manifest / report
# ----------------------------------------------------------------------------
stage "PIPELINE COMPLETE"

MANIFEST="${DOMAIN_REPORTS}/manifest.txt"

{
  echo "DataPower Atlas domain pipeline"
  echo "domain=${DOMAIN}"
  echo "environment=${ENVIRONMENT}"
  echo "cfg=${CFG_FILE}"
  echo "index_dir=${DOMAIN_INDEX}"
  echo
  echo "Generated outputs:"
  find "$DOMAIN_INDEX" -maxdepth 1 -type f -print | sort
} > "$MANIFEST"

echo "Domain:             $DOMAIN"
echo "Index:              $DOMAIN_INDEX"
echo "Pipeline log:       $RUN_LOG"
echo "Manifest:           $MANIFEST"
echo
echo "DATAPOWER DOMAIN PIPELINE: PASS"
