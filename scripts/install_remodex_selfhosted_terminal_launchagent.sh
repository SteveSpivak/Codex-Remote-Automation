#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

"${PYTHON:-python3}" -m cra.cli remodex-selfhosted-install-terminal-launch-agent "$@"
