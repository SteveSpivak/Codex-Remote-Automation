from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def helper_source_path() -> Path:
    return _repo_root() / "scripts" / "dump_ax_tree.m"


def helper_binary_path() -> Path:
    return _repo_root() / "var" / "bin" / "dump_ax_tree"


def build_helper() -> Path:
    binary_path = helper_binary_path()
    source_path = helper_source_path()
    binary_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "/usr/bin/clang",
            "-fobjc-arc",
            "-framework",
            "AppKit",
            "-framework",
            "ApplicationServices",
            "-framework",
            "Foundation",
            str(source_path),
            "-o",
            str(binary_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return binary_path


def dump_ax_tree(pid: int, max_depth: int = 4, max_children: int = 20) -> Dict[str, object]:
    helper_path = build_helper()
    completed = subprocess.run(
        [str(helper_path), "--pid", str(pid), "--max-depth", str(max_depth), "--max-children", str(max_children)],
        check=False,
        capture_output=True,
        text=True,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    payload = json.loads(stdout) if stdout else {"status": "error", "note": "No output from AX tree helper."}
    payload["returncode"] = completed.returncode
    if stderr:
        payload["stderr"] = stderr
    return payload
