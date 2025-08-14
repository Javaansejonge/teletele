#!/usr/bin/env bash
# scripts/harness-mobile.sh
# Minimal mobile runner for "AI Pentest Harness (Taxonomy-Driven)"
set -euo pipefail

# --- defaults ---
MODE="passive"                 # passive | active | samples
TARGET=""
MAX_PAGES="80"
TIMEOUT="12"
PLAN="plans/active_plan.yaml"
SAMPLES=""
OUT_BASE="out_mobile"
DRY_RUN=0
QUIET_PIP=1
VENV_DIR=".venv-mobile"

usage() {
  cat <<'USAGE'
Usage:
  harness-mobile.sh --target https://target.tld [--mode passive|active|samples]
                    [--max-pages 80] [--timeout 12]
                    [--plan plans/active_plan.yaml] [--samples samples.json]
                    [--out out_mobile] [--dry-run]

Examples:
  # Passive healthcheck (README default)
  harness-mobile.sh --target https://target.tld

  # Active light (needs edited plan)
  harness-mobile.sh --mode active --target https://target.tld --plan plans/active_plan.yaml

  # Offline output safety analysis (samples)
  harness-mobile.sh --mode samples --target https://target.tld --samples samples.json

Notes:
  - Creates/uses Python venv at .venv-mobile (separate vom Projektvenv).
  - Copies example plan if PLAN fehlt und plans/active_plan.example.yaml existiert.
  - Outputs landen in OUT_BASE/<timestamp> (z.B. out_mobile/2025-08-15_12-34-56).
USAGE
}

# --- arg parse ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    -m|--mode) MODE="${2:-}"; shift 2;;
    -t|--target) TARGET="${2:-}"; shift 2;;
    --max-pages) MAX_PAGES="${2:-}"; shift 2;;
    --timeout) TIMEOUT="${2:-}"; shift 2;;
    --plan) PLAN="${2:-}"; shift 2;;
    --samples) SAMPLES="${2:-}"; shift 2;;
    -o|--out) OUT_BASE="${2:-}"; shift 2;;
    --dry-run) DRY_RUN=1; shift;;
    -h|--help) usage; exit 0;;
    *) echo "Unknown arg: $1"; usage; exit 1;;
  esac
done

# --- validate ---
case "$MODE" in
  passive|active|samples) ;;
  *) echo "Invalid --mode: $MODE"; usage; exit 1;;
esac
if [[ -z "${TARGET}" ]]; then
  echo "Missing --target"; usage; exit 1
fi
if [[ "$MODE" == "samples" && -z "${SAMPLES}" ]]; then
  echo "Mode 'samples' requires --samples <file>"; usage; exit 1
fi

timestamp() { date +"%Y-%m-%d_%H-%M-%S"; }
OUTDIR="${OUT_BASE}/$(timestamp)"
mkdir -p "$OUTDIR"

# --- env detection ---
PYBIN="$(command -v python3 || true)"
if [[ -z "$PYBIN" ]]; then
  echo "python3 not found. Install Python 3 first (e.g., 'pkg install python' on Termux)."
  exit 1
fi

# --- venv setup ---
if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating venv at $VENV_DIR ..."
  "$PYBIN" -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "${VENV_DIR}/bin/activate"

# --- requirements install (quiet on mobile) ---
if [[ -f "requirements.txt" ]]; then
  echo "Installing requirements..."
  if [[ "$QUIET_PIP" -eq 1 ]]; then
    pip install -r requirements.txt --disable-pip-version-check -q
  else
    pip install -r requirements.txt --disable-pip-version-check
  fi
else
  echo "WARNING: requirements.txt not found. Continuing anyway."
fi

# --- plan helper (active) ---
ensure_plan() {
  local p="$1"
  if [[ -f "$p" ]]; then
    return 0
  fi
  local ex="plans/active_plan.example.yaml"
  if [[ -f "$ex" ]]; then
    echo "Plan '$p' not found. Copying example '$ex'..."
    mkdir -p "$(dirname "$p")"
    cp "$ex" "$p"
    echo "EDIT your tokens/endpoints inside: $p"
  else
    echo "ERROR: '$p' not found and no example '$ex' available."
    exit 1
  fi
}

# --- build command ---
CMD=( python harness.py "$TARGET" )
case "$MODE" in
  passive)
    CMD+=( --max-pages "$MAX_PAGES" --timeout "$TIMEOUT" --outdir "$OUTDIR" )
    ;;
  active)
    ensure_plan "$PLAN"
    CMD+=( --plan "$PLAN" --run-active --outdir "$OUTDIR" )
    ;;
  samples)
    CMD+=( --samples "$SAMPLES" --outdir "$OUTDIR" )
    ;;
esac

echo "Mode    : $MODE"
echo "Target  : $TARGET"
[[ "$MODE" == "passive" ]] && echo "Crawl   : max-pages=$MAX_PAGES timeout=$TIMEOUT"
[[ "$MODE" == "active"  ]] && echo "Plan    : $PLAN (will run active probes)"
[[ "$MODE" == "samples" ]] && echo "Samples : $SAMPLES"
echo "Outdir  : $OUTDIR"
echo "Command : ${CMD[*]}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "[DRY-RUN] Not executing."
  exit 0
fi

# --- run ---
set +e
"${CMD[@]}"
RC=$?
set -e

# --- summarize ---
echo
echo "=== Summary ==="
if [[ -f "${OUTDIR}/report.md" ]]; then
  echo "Report MD : ${OUTDIR}/report.md"
fi
if [[ -f "${OUTDIR}/report.json" ]]; then
  echo "Report JSON: ${OUTDIR}/report.json"
fi
[[ -f "${OUTDIR}/targets-checklist.md" ]] && echo "Checklist : ${OUTDIR}/targets-checklist.md"

if command -v zip >/dev/null 2>&1; then
  ZIP_PATH="${OUTDIR}.zip"
  (cd "$(dirname "$OUTDIR")" && zip -qr "$(basename "$ZIP_PATH")" "$(basename "$OUTDIR")")
  echo "Archive   : ${ZIP_PATH}"
fi

if [[ "$RC" -eq 0 ]]; then
  echo "Status    : ✅ OK"
else
  echo "Status    : ❌ Exit $RC"
fi

exit "$RC"
