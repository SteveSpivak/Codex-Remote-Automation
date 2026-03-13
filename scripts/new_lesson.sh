#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <area> <slug>" >&2
  exit 2
fi

area="$1"
slug="$2"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LESSONS_ROOT="$REPO_ROOT/references/lessons"
TARGET_DIR="$LESSONS_ROOT/$area"
DATE_STAMP="$(date +%F)"
TARGET_FILE="$TARGET_DIR/$DATE_STAMP-$slug.md"

mkdir -p "$TARGET_DIR"

if [[ -e "$TARGET_FILE" ]]; then
  echo "exists: $TARGET_FILE" >&2
  exit 1
fi

cat > "$TARGET_FILE" <<EOF
# ${slug//-/ }

Date: $DATE_STAMP
Area: $area
Status: draft

## Context

## Trigger

## What Happened

## Lesson

## Evidence

## Decision

## Follow-Up

## Related Skills

EOF

echo "$TARGET_FILE"
