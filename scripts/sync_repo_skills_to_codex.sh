#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="$REPO_ROOT/skills"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
TARGET_DIR="$CODEX_HOME/skills"

mkdir -p "$TARGET_DIR"

found_any=0
for skill_dir in "$SOURCE_DIR"/*; do
  if [[ ! -f "$skill_dir/SKILL.md" ]]; then
    continue
  fi

  found_any=1
  skill_name="$(basename "$skill_dir")"
  target_path="$TARGET_DIR/$skill_name"

  if [[ -e "$target_path" && ! -L "$target_path" ]]; then
    echo "conflict: $target_path exists and is not a symlink" >&2
    exit 1
  fi

  if [[ -L "$target_path" ]]; then
    current_target="$(readlink "$target_path")"
    if [[ "$current_target" == "$skill_dir" ]]; then
      echo "ok: $skill_name already linked"
      continue
    fi
    rm -f "$target_path"
  fi

  ln -s "$skill_dir" "$target_path"
  echo "linked: $skill_name -> $skill_dir"
done

if [[ "$found_any" -eq 0 ]]; then
  echo "no repo skills found under $SOURCE_DIR" >&2
  exit 1
fi

echo "done: repo skills are linked into $TARGET_DIR"
echo "restart Codex to pick up newly linked skills"
