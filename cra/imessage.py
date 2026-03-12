from __future__ import annotations

import json
import re
import sqlite3
import subprocess
from pathlib import Path
from typing import Any, Callable

from .models import BrokerApprovalRequest
from .validation import build_broker_response

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def send_script_path() -> Path:
    return _repo_root() / "scripts" / "cra_send_imessage.applescript"


def chat_db_path() -> Path:
    return Path.home() / "Library" / "Messages" / "chat.db"


def _extract_text_from_attributed_body(value: Any) -> str:
    if value is None:
        return ""

    blob = bytes(value) if isinstance(value, memoryview) else value
    if not isinstance(blob, (bytes, bytearray)):
        return ""

    decoded = bytes(blob).decode("utf-8", errors="ignore").replace("\x00", " ")
    candidates = re.findall(r"[A-Za-z0-9][A-Za-z0-9 .,:;@/_#?&=+!$%'\-()\n\r]{2,500}", decoded)
    if not candidates:
        return ""
    return max((candidate.strip() for candidate in candidates), key=len, default="")


def _coerce_message_text(text: Any, attributed_body: Any) -> str:
    if isinstance(text, str) and text.strip():
        return text.strip()
    return _extract_text_from_attributed_body(attributed_body)


def compose_approval_message(approval: BrokerApprovalRequest) -> str:
    decisions = ", ".join(decision.value for decision in approval.available_decisions)
    return (
        "CRA approval request\n"
        f"request_id: {approval.request_id}\n"
        f"kind: {approval.kind.value}\n"
        f"summary: {approval.summary}\n"
        f"decisions: {decisions}\n"
        "Reply with one of these formats:\n"
        f"decline {approval.request_id}\n"
        f"accept {approval.request_id}\n"
        f"acceptForSession {approval.request_id}\n"
        f"cancel {approval.request_id}"
    )


def parse_response_message(text: str) -> dict[str, str] | None:
    normalized = text.strip()
    if not normalized:
        return None

    try:
        payload = json.loads(normalized)
    except json.JSONDecodeError:
        payload = None

    if isinstance(payload, dict):
        request_id = payload.get("request_id")
        decision = payload.get("decision")
        if isinstance(request_id, str) and isinstance(decision, str):
            response = build_broker_response(request_id, decision)
            return response.to_dict()

    lowered = normalized.replace("\n", " ").strip()
    parts = lowered.split()
    if len(parts) >= 2:
        first, second = parts[0], parts[1]
        try:
            response = build_broker_response(second, first)
            return response.to_dict()
        except ValueError:
            pass
        try:
            response = build_broker_response(first, second)
            return response.to_dict()
        except ValueError:
            pass

    return None


def send_imessage(
    handle: str,
    message_text: str,
    *,
    runner: Runner = subprocess.run,
) -> dict[str, Any]:
    command = ["/usr/bin/osascript", str(send_script_path()), handle, message_text]
    completed = runner(command, check=False, capture_output=True, text=True)
    return {
        "status": "ok" if completed.returncode == 0 else "error",
        "returncode": completed.returncode,
        "command": command,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def poll_imessages(
    handle: str,
    *,
    limit: int = 10,
    db_path: Path | None = None,
) -> dict[str, Any]:
    target_db = db_path or chat_db_path()
    query = """
        SELECT
            COALESCE(message.guid, CAST(message.ROWID AS TEXT)) AS message_id,
            message.text AS text,
            message.attributedBody AS attributed_body,
            message.is_from_me AS is_from_me,
            datetime(message.date / 1000000000 + strftime('%s','2001-01-01'), 'unixepoch', 'localtime') AS timestamp_text
        FROM message
        JOIN handle ON handle.ROWID = message.handle_id
        WHERE handle.id = ?
        ORDER BY message.date DESC
        LIMIT ?
    """

    try:
        connection = sqlite3.connect(f"file:{target_db}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        return {
            "status": "error",
            "db_path": str(target_db),
            "error": str(exc),
            "hint": "Grant Full Disk Access to the Codex host process if macOS denies access to chat.db.",
            "messages": [],
        }

    try:
        cursor = connection.execute(query, (handle, limit))
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        connection.close()
        return {
            "status": "error",
            "db_path": str(target_db),
            "error": str(exc),
            "hint": "Grant Full Disk Access to the Codex host process if macOS denies access to chat.db.",
            "messages": [],
        }

    connection.close()
    messages = [
        {
            "message_id": str(row[0]),
            "text": _coerce_message_text(row[1], row[2]),
            "is_from_me": bool(row[3]),
            "timestamp_text": row[4],
        }
        for row in rows
    ]
    return {
        "status": "ok",
        "db_path": str(target_db),
        "messages": messages,
    }


def message_key(message: dict[str, Any]) -> str:
    message_id = message.get("message_id")
    if isinstance(message_id, str) and message_id:
        return message_id
    timestamp = str(message.get("timestamp_text") or "")
    text = str(message.get("text") or "")
    return f"{timestamp}|{text}"


def find_response_messages(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    responses: list[dict[str, str]] = []
    seen: set[str] = set()
    for message in messages:
        if bool(message.get("is_from_me")):
            continue
        text = message.get("text")
        if not isinstance(text, str):
            continue
        parsed = parse_response_message(text)
        if not parsed:
            continue
        key = f"{parsed['request_id']}|{parsed['decision']}"
        if key in seen:
            continue
        seen.add(key)
        responses.append(parsed)
    return responses
