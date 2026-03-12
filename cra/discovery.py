from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from .models import DiscoveryFinding, DiscoveryReport
from .validation import unique_stable

HOME = Path.home()
APPLICATION_CANDIDATES = [
    Path("/Applications/Codex.app"),
    HOME / "Applications" / "Codex.app",
]
LOG_DIR = HOME / "Library" / "Logs" / "com.openai.codex"
SUPPORT_DIR = HOME / "Library" / "Application Support" / "Codex"
PREFERENCES_PATH = SUPPORT_DIR / "Preferences"
SENTRY_SCOPE_PATH = SUPPORT_DIR / "sentry" / "scope_v3.json"
LEVELDB_LOG_PATH = SUPPORT_DIR / "Local Storage" / "leveldb" / "LOG"


def _finding(name: str, path: Path, detail: str = "", confidence: str = "low") -> DiscoveryFinding:
    return DiscoveryFinding(
        name=name,
        path=path,
        exists=path.exists(),
        detail=detail,
        confidence=confidence,
    )


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_preferences(path: Path) -> Dict[str, Any]:
    with path.open("rb") as handle:
        raw_bytes = handle.read()

    try:
        return json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        import plistlib

        return plistlib.loads(raw_bytes)


def summarize_breadcrumbs(scope_payload: Dict[str, Any], limit: int = 12) -> Dict[str, List[str]]:
    breadcrumbs = scope_payload.get("scope", {}).get("breadcrumbs", [])
    ui_messages: List[str] = []
    http_urls: List[str] = []
    categories: List[str] = []

    for breadcrumb in breadcrumbs:
        category = breadcrumb.get("category")
        if category:
            categories.append(category)

        message = str(breadcrumb.get("message", "")).strip()
        if category == "ui.click" and message:
            ui_messages.append(message)

        url = breadcrumb.get("data", {}).get("url")
        if url:
            http_urls.append(str(url))

    return {
        "categories": unique_stable(categories)[-limit:],
        "ui_messages": unique_stable(ui_messages)[-limit:],
        "http_urls": unique_stable(http_urls)[-limit:],
    }


def discover_codex_environment() -> DiscoveryReport:
    findings = []
    for app_path in APPLICATION_CANDIDATES:
        findings.append(_finding("codex_app", app_path, "Electron desktop app candidate", "high"))

    findings.extend(
        [
            _finding("codex_log_dir", LOG_DIR, "Log directory exists but may be empty", "medium"),
            _finding("codex_support_dir", SUPPORT_DIR, "Electron profile directory", "high"),
            _finding("codex_preferences", PREFERENCES_PATH, "Preferences plist", "medium"),
            _finding("codex_sentry_scope", SENTRY_SCOPE_PATH, "Structured local telemetry surface", "high"),
            _finding("codex_leveldb_log", LEVELDB_LOG_PATH, "Low-level storage log", "low"),
        ]
    )

    selector_hints: List[str] = []
    http_hints: List[str] = []
    metadata: Dict[str, str] = {}
    notes: List[str] = []

    if PREFERENCES_PATH.exists():
        preferences = load_preferences(PREFERENCES_PATH)
        dictionaries = preferences.get("spellcheck", {}).get("dictionaries", [])
        metadata["spellcheck_dictionaries"] = ",".join(dictionaries)

    if SENTRY_SCOPE_PATH.exists():
        scope_payload = load_json(SENTRY_SCOPE_PATH)
        summary = summarize_breadcrumbs(scope_payload)
        selector_hints = summary["ui_messages"]
        http_hints = summary["http_urls"]
        notes.append("Sentry scope file contains UI and HTTP breadcrumbs that can support feasibility discovery.")

    if LOG_DIR.exists() and not any(LOG_DIR.iterdir()):
        notes.append("Codex log directory exists but currently has no readable log files.")

    if LEVELDB_LOG_PATH.exists():
        notes.append("Local Storage LevelDB log exists but currently looks like storage housekeeping, not human-readable app events.")

    return DiscoveryReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        findings=findings,
        selector_hints=selector_hints,
        http_hints=http_hints,
        notes=notes,
        metadata=metadata,
    )
