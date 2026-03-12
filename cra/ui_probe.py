from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Dict, List


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def probe_script_path() -> Path:
    return _repo_root() / "scripts" / "cra_probe_codex_ui.applescript"


def run_probe() -> str:
    completed = subprocess.run(
        ["/usr/bin/osascript", str(probe_script_path())],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "Codex UI probe failed.")
    return completed.stdout.strip()


def parse_probe_output(raw_output: str) -> Dict[str, object]:
    buttons: List[Dict[str, str]] = []
    elements: List[Dict[str, str]] = []
    process_name = ""
    window_name = ""
    error_text = ""

    for line in raw_output.splitlines():
        if not line:
            continue
        columns = line.split("\t")
        record_type = columns[0]
        if record_type == "PROCESS" and len(columns) > 1:
            process_name = columns[1]
        elif record_type == "WINDOW" and len(columns) > 1:
            window_name = columns[1]
        elif record_type == "ERROR" and len(columns) > 1:
            error_text = columns[1]
        elif record_type == "BUTTON":
            entry: Dict[str, str] = {}
            for field in columns[1:]:
                if "=" not in field:
                    continue
                key, value = field.split("=", 1)
                entry[key] = value
            buttons.append(entry)
        elif record_type == "ELEMENT":
            entry = {}
            for field in columns[1:]:
                if "=" not in field:
                    continue
                key, value = field.split("=", 1)
                entry[key] = value
            elements.append(entry)

    return {
        "process": process_name,
        "window": window_name,
        "buttons": buttons,
        "elements": elements,
        "error": error_text,
    }


def parse_probe_output_json(raw_output: str) -> str:
    return json.dumps(parse_probe_output(raw_output), indent=2, sort_keys=True)
