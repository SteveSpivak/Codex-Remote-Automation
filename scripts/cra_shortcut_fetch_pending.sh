#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RUNTIME_DIR="${CRA_RUNTIME_DIR:-$REPO_ROOT/var/run}"

cd "$REPO_ROOT"

if [[ $# -ge 1 && -n "${1:-}" ]]; then
  exec python3 -m cra.cli broker-shortcut-payload --runtime-dir "$RUNTIME_DIR" --request-id "$1"
fi

exec python3 -m cra.cli broker-shortcut-payload --runtime-dir "$RUNTIME_DIR"
