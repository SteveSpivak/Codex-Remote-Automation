from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any


def pairing_uri(payload: dict[str, Any]) -> str:
    return "cra-bridge://pair?" + json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _qr_generator_script() -> Path:
    return _repo_root() / "scripts" / "cra_generate_qr.swift"


def write_pairing_qr_image(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    cache_dir = path.parent / ".swift-module-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    environment = os.environ.copy()
    environment["CLANG_MODULE_CACHE_PATH"] = str(cache_dir)
    environment["SWIFT_MODULE_CACHE_PATH"] = str(cache_dir)

    result = subprocess.run(
        ["swift", str(_qr_generator_script()), pairing_uri(payload), str(path)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Unknown QR generation failure."
        raise RuntimeError(f"Failed to generate pairing QR image: {message}")
    return path


def write_pairing_qr_stub(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "CRA Bridge Pairing",
        "",
        "Use this payload to generate a QR code or paste it into the CRA Operator app.",
        "",
        pairing_uri(payload),
        "",
        json.dumps(payload, indent=2, sort_keys=True),
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
