from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def pairing_uri(payload: dict[str, Any]) -> str:
    return "cra-bridge://pair?" + json.dumps(payload, separators=(",", ":"), sort_keys=True)


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
