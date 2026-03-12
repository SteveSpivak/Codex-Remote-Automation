from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def helper_source_path() -> Path:
    return _repo_root() / "scripts" / "enable_ax_manual_accessibility.m"


def helper_binary_path() -> Path:
    return _repo_root() / "var" / "bin" / "enable_ax_manual_accessibility"


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


def enable_manual_accessibility(
    bundle_id: str = "com.openai.codex",
    app_name: str = "Codex",
    pid: int | None = None,
    prompt_trust: bool = False,
) -> Dict[str, object]:
    helper_path = build_helper()
    command = [str(helper_path), "--bundle-id", bundle_id, "--app-name", app_name]
    if pid is not None:
        command.extend(["--pid", str(pid)])
    if prompt_trust:
        command.append("--prompt-trust")
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()

    if not stdout:
        return {
            "status": "error",
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr or "No output from AXManualAccessibility helper.",
        }

    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        payload = {
            "status": "error",
            "returncode": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }
        return payload

    payload["returncode"] = completed.returncode
    if stderr:
        payload["stderr"] = stderr
    return payload
