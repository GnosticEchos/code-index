#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/run_search_validation.sh [--json] [--tag suffix]
#
# Behavior:
#   - Creates a timestamped output directory under tests/reports/search_validation/
#   - Runs a focused set of validations across known workspaces/queries
#   - Writes one output file per query (JSON when --json is used, otherwise text)
#   - Always writes a matching .err file per query with run metadata and stderr
#   - Uses tuned weighting config in rust_optimized_config.json so adjustedScore is present and re-ranking is active

JSON=0
TAG=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      JSON=1
      shift
      ;;
    --tag)
      TAG="${2:-}"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [--json] [--tag suffix]"
      exit 0
      ;;
    *)
      echo "Warning: Unknown argument: $1" >&2
      shift
      ;;
  esac
done

timestamp="$(date -u +%Y%m%d_%H%M%S)"
suffix=""
if [[ -n "${TAG}" ]]; then
  suffix="_${TAG}"
fi
outdir="tests/reports/search_validation/${timestamp}${suffix}"
mkdir -p "${outdir}"
echo "Output directory: ${outdir}"

slug() {
  # Replace spaces and slashes with underscores, then strip unsupported characters
  printf "%s" "$1" | tr ' /' '_' | sed -E 's/[^0-9A-Za-z._-]+/_/g'
}

run() {
  # Arguments:
  #   1: workspace path
  #   2: query string
  #   3: min score
  #   4: max results
  #   5: tag for filename (optional); if empty, derived from query
  local ws="$1"
  local q="$2"
  local min="$3"
  local max="$4"
  local tag="${5:-}"

  local base
  if [[ -n "${tag}" ]]; then
    base="$(slug "${tag}")"
  else
    base="$(slug "${q}")"
  fi

  local ext="txt"
  if [[ ${JSON} -eq 1 ]]; then
    ext="json"
  fi

  local outfile="${outdir}/${base}.${ext}"
  local errfile="${outdir}/${base}.err"

  {
    echo "=== Workspace: ${ws}"
    echo "=== Query: ${q}"
    echo "=== Min score: ${min} | Max results: ${max}"
    echo "=== Timestamp (UTC): $(date -u -Is)"
    echo "=== JSON Mode: ${JSON}"
    echo
  } > "${errfile}"

  if [[ ${JSON} -eq 1 ]]; then
    # Place --json before the query argument per Click's option parsing
    code-index search \
      --workspace "${ws}" \
      --config rust_optimized_config.json \
      --min-score "${min}" \
      --max-results "${max}" \
      --json \
      "${q}" \
      > "${outfile}" 2>> "${errfile}" || true
  else
    code-index search \
      --workspace "${ws}" \
      --config rust_optimized_config.json \
      --min-score "${min}" \
      --max-results "${max}" \
      "${q}" \
      > "${outfile}" 2>> "${errfile}" || true
  fi

  echo "Wrote ${outfile}"
  echo "Wrote ${errfile}"
}

# ---------------------------------------
# Focused validation set (weights tuned)
# ---------------------------------------

# Kanban-frontend
run "/home/james/kanban_frontend/Kanban-frontend" "component props" "0.30" "25" "kanban_frontend_component_props"
run "/home/james/kanban_frontend/Kanban-frontend" "script setup emit" "0.30" "25" "kanban_frontend_script_setup_emit"
run "/home/james/kanban_frontend/Kanban-frontend" "template v-for" "0.30" "25" "kanban_frontend_template_vfor"

# kanban_api
run "/home/james/kanban_frontend/kanban_api" "register user function" "0.30" "25" "kanban_api_register_user_function"
run "/home/james/kanban_frontend/kanban_api" "signin auth jwt" "0.30" "25" "kanban_api_signin_auth_jwt"
run "/home/james/kanban_frontend/kanban_api" "surql function define" "0.30" "25" "kanban_api_surql_function_define"

# Kanban-backend
run "/home/james/kanban_frontend/Kanban-backend" "express router middleware" "0.30" "25" "kanban_backend_express_router_middleware"
run "/home/james/kanban_frontend/Kanban-backend" "sequelize model definition" "0.30" "25" "kanban_backend_sequelize_model_definition"
run "/home/james/kanban_frontend/Kanban-backend" "validation schema joi" "0.30" "25" "kanban_backend_validation_schema_joi"

echo "All searches completed. Results directory: ${outdir}"