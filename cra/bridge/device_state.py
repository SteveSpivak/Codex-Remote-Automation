from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .crypto import random_secret


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BridgePaths:
    base_dir: Path
    device_state_path: Path
    runtime_state_path: Path
    pairing_payload_path: Path
    pairing_qr_path: Path
    wire_audit_path: Path
    bridge_audit_path: Path


def default_bridge_paths(base_dir: Path | None = None, audit_dir: Path | None = None) -> BridgePaths:
    bridge_root = base_dir or (_repo_root() / "var" / "bridge")
    audit_root = audit_dir or (_repo_root() / "var" / "audit")
    return BridgePaths(
        base_dir=bridge_root,
        device_state_path=bridge_root / "device-state.json",
        runtime_state_path=bridge_root / "bridge-state.json",
        pairing_payload_path=bridge_root / "pairing-payload.json",
        pairing_qr_path=bridge_root / "pairing-qr.txt",
        wire_audit_path=audit_root / "bridge-wire.jsonl",
        bridge_audit_path=audit_root / "bridge-events.jsonl",
    )


def _default_device_state() -> dict[str, Any]:
    return {
        "bridge_device_id": str(uuid.uuid4()),
        "bridge_secret": random_secret(),
        "created_at": _utc_now(),
        "trusted_phones": {},
    }


def save_bridge_device_state(path: Path, state: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_or_create_bridge_device_state(path: Path) -> dict[str, Any]:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Expected JSON object in {path}")
        payload.setdefault("trusted_phones", {})
        return payload

    state = _default_device_state()
    save_bridge_device_state(path, state)
    return state


def get_trusted_phone(state: dict[str, Any], phone_device_id: str) -> dict[str, Any] | None:
    trusted = state.get("trusted_phones", {})
    if not isinstance(trusted, dict):
        return None
    phone = trusted.get(phone_device_id)
    return phone if isinstance(phone, dict) else None


def remember_trusted_phone(
    state: dict[str, Any],
    *,
    phone_device_id: str,
    shared_secret: str,
    phone_label: str | None = None,
) -> dict[str, Any]:
    trusted = state.setdefault("trusted_phones", {})
    if not isinstance(trusted, dict):
        trusted = {}
        state["trusted_phones"] = trusted
    existing = trusted.get(phone_device_id, {})
    if not isinstance(existing, dict):
        existing = {}
    trusted[phone_device_id] = {
        "device_id": phone_device_id,
        "phone_label": phone_label or existing.get("phone_label") or "CRA Operator",
        "shared_secret": shared_secret,
        "paired_at": existing.get("paired_at") or _utc_now(),
        "last_seen_at": _utc_now(),
    }
    return state
