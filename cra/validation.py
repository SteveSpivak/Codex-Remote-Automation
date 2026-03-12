from __future__ import annotations

import re
import uuid
from typing import Iterable

from .models import ActuationRequest, ApprovalEvent, Decision, RiskLevel

UUID_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$"
)


def sanitize_text(value: str, max_length: int = 280) -> str:
    cleaned = "".join(ch if ch.isprintable() and ch not in {'"', "\\"} else " " for ch in value)
    collapsed = " ".join(cleaned.split())
    return collapsed[:max_length].strip()


def validate_uuid(value: str) -> str:
    if not UUID_RE.match(value):
        raise ValueError("action_id must be a UUID string.")
    parsed = uuid.UUID(value)
    return str(parsed)


def normalize_risk_level(value: str) -> RiskLevel:
    try:
        return RiskLevel(value.lower())
    except ValueError as exc:
        raise ValueError("risk_level must be one of: low, medium, high.") from exc


def normalize_decision(value: str) -> Decision:
    try:
        return Decision(value.lower())
    except ValueError as exc:
        raise ValueError("decision must be one of: approve, deny.") from exc


def build_approval_event(context: str, risk_level: str, action_id: str | None = None) -> ApprovalEvent:
    sanitized_context = sanitize_text(context)
    event_risk = normalize_risk_level(risk_level)
    event_id = validate_uuid(action_id) if action_id else str(uuid.uuid4())
    return ApprovalEvent.now(action_id=event_id, context=sanitized_context, risk_level=event_risk)


def build_actuation_request(decision: str, action_id: str) -> ActuationRequest:
    normalized_decision = normalize_decision(decision)
    normalized_action_id = validate_uuid(action_id)
    return ActuationRequest(action_id=normalized_action_id, decision=normalized_decision)


def unique_stable(values: Iterable[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
