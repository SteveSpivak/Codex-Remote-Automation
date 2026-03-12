from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from typing import Callable, Dict

from .actuator import run_local_actuation
from .audit import append_jsonl
from .validation import build_actuation_request


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def shortcut_cli_path() -> str:
    return "/usr/bin/shortcuts"


def default_audit_path() -> Path:
    return _repo_root() / "var" / "audit" / "shortcut-entry.jsonl"


def build_shortcuts_command(
    shortcut_name: str,
    input_path: Path | None = None,
    output_path: Path | None = None,
    output_type: str | None = None,
) -> list[str]:
    command = [shortcut_cli_path(), "run", shortcut_name]
    if input_path is not None:
        command.extend(["--input-path", str(input_path)])
    if output_path is not None:
        command.extend(["--output-path", str(output_path)])
    if output_type:
        command.extend(["--output-type", output_type])
    return command


def run_shortcut(
    shortcut_name: str,
    input_path: Path | None = None,
    output_path: Path | None = None,
    output_type: str | None = None,
) -> Dict[str, object]:
    command = build_shortcuts_command(
        shortcut_name=shortcut_name,
        input_path=input_path,
        output_path=output_path,
        output_type=output_type,
    )
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    return {
        "status": "ok" if completed.returncode == 0 else "error",
        "returncode": completed.returncode,
        "command": command,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def build_ssh_command(
    decision: str,
    action_id: str,
    *,
    allow_live: bool = False,
    allow_visual: bool = False,
    selector_config: Path | None = None,
    audit_path: Path | None = None,
    python_path: str = "python3",
) -> str:
    repo_root = _repo_root()
    command = [
        python_path,
        "-m",
        "cra.cli",
        "shortcut-entry",
        "--decision",
        decision,
        "--action-id",
        action_id,
    ]
    if allow_live:
        command.append("--allow-live")
    if allow_visual:
        command.append("--allow-visual")
    if selector_config is not None:
        command.extend(["--selector-config", str(selector_config)])
    if audit_path is not None:
        command.extend(["--audit-path", str(audit_path)])
    return "cd " + shlex.quote(str(repo_root)) + " && " + shlex.join(command)


def handle_shortcut_entry(
    decision: str,
    action_id: str,
    *,
    allow_live: bool = False,
    allow_visual: bool = False,
    config_path: Path | None = None,
    audit_path: Path | None = None,
    image_output: Path | None = None,
    runner: Callable[..., Dict[str, object]] = run_local_actuation,
) -> Dict[str, object]:
    request = build_actuation_request(decision=decision, action_id=action_id)
    target_audit_path = audit_path or default_audit_path()

    append_jsonl(
        target_audit_path,
        "shortcut_request",
        {
            "decision": request.decision.value,
            "action_id": request.action_id,
            "allow_live": allow_live,
            "allow_visual": allow_visual,
        },
    )

    result = runner(
        request.decision.value,
        request.action_id,
        allow_live=allow_live,
        allow_visual=allow_visual,
        config_path=config_path,
        image_output=image_output,
    )

    append_jsonl(target_audit_path, "shortcut_result", result)
    return {
        "request": request.to_dict(),
        "result": result,
        "audit_path": str(target_audit_path),
    }
