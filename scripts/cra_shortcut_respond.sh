#!/bin/bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: cra_shortcut_respond.sh <request_id> <decision> [operator_note]" >&2
  exit 1
fi

REQUEST_ID="$1"
DECISION="$2"
shift 2

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="${CRA_RUNTIME_DIR:-$REPO_ROOT/var/run}"

cd "$REPO_ROOT"

if [[ $# -gt 0 ]]; then
  NOTE="$*"
  exec python3 -m cra.cli broker-respond \
    --runtime-dir "$RUNTIME_DIR" \
    --request-id "$REQUEST_ID" \
    --decision "$DECISION" \
    --operator-note "$NOTE"
fi

exec python3 -m cra.cli broker-respond \
  --runtime-dir "$RUNTIME_DIR" \
  --request-id "$REQUEST_ID" \
  --decision "$DECISION"
