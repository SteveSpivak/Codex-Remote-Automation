from __future__ import annotations

import os
import json
import subprocess
from pathlib import Path
from typing import Dict

from .models import ActuationRequest
from .validation import build_actuation_request
from .vision import run_visual_actuation


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def actuator_script_path() -> Path:
    return _repo_root() / "scripts" / "cra_actuate.applescript"


def selector_map_path() -> Path:
    return _repo_root() / "config" / "codex-selectors.json"


def load_selector_entry(decision: str, config_path: Path | None = None) -> Dict[str, object]:
    target_path = config_path or selector_map_path()
    with target_path.open("r", encoding="utf-8") as handle:
        selectors = json.load(handle)
    selector_entry = selectors.get(decision, {})
    if not selector_entry:
        raise ValueError(f"No selector entry configured for decision={decision!r} in {target_path}.")
    selector_entry["_config_path"] = str(target_path)
    return selector_entry


def _is_placeholder(value: str) -> bool:
    return value.startswith("REPLACE_WITH_")


def _run_ax_actuation(decision: str, action_id: str, selector_description: str) -> Dict[str, str]:
    environment = os.environ.copy()
    command = ["/usr/bin/osascript", str(actuator_script_path()), "live", decision, action_id, selector_description]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    return {
        "status": "ok" if completed.returncode == 0 else "error",
        "returncode": str(completed.returncode),
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
        "method": "accessibility",
        "selector": selector_description,
    }


def run_local_actuation(
    decision: str,
    action_id: str,
    allow_live: bool = False,
    allow_visual: bool = False,
    config_path: Path | None = None,
    image_output: Path | None = None,
) -> Dict[str, object]:
    request: ActuationRequest = build_actuation_request(decision=decision, action_id=action_id)
    mode = "live" if allow_live else "dry-run"
    if not allow_live:
        return {
            "status": "ok",
            "returncode": "0",
            "stdout": f"status=dry-run decision={request.decision.value} action_id={request.action_id}",
            "stderr": "",
            "decision": request.decision.value,
            "action_id": request.action_id,
            "mode": mode,
        }

    selector_entry = load_selector_entry(request.decision.value, config_path=config_path)
    attempts: list[Dict[str, object]] = []

    selector_description = str(selector_entry.get("ax_description", "")).strip()
    if selector_description and not _is_placeholder(selector_description):
        ax_result = _run_ax_actuation(request.decision.value, request.action_id, selector_description)
        attempts.append(ax_result)
        if ax_result["status"] == "ok":
            ax_result.update(
                {
                    "decision": request.decision.value,
                    "action_id": request.action_id,
                    "mode": mode,
                    "attempts": attempts,
                }
            )
            return ax_result

    if allow_visual:
        visual_result = run_visual_actuation(
            request.decision.value,
            selector_entry,
            image_output=image_output,
        )
        attempts.append(visual_result)
        if visual_result.get("status") == "ok":
            visual_result.update(
                {
                    "decision": request.decision.value,
                    "action_id": request.action_id,
                    "mode": mode,
                    "attempts": attempts,
                }
            )
            return visual_result

    reason = "No live selector succeeded."
    if selector_description and _is_placeholder(selector_description):
        reason = "Selector config still contains placeholder AXDescription values."
    elif not selector_description and not allow_visual:
        reason = "No AXDescription configured and OCR fallback was not enabled."

    return {
        "status": "error",
        "returncode": "1",
        "stdout": "",
        "stderr": reason,
        "decision": request.decision.value,
        "action_id": request.action_id,
        "mode": mode,
        "attempts": attempts,
    }
