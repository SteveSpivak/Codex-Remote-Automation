from __future__ import annotations

import re
import uuid
from typing import Iterable

from .models import (
    ActuationRequest,
    ApprovalEvent,
    ApprovalKind,
    BrokerApprovalResponse,
    BrokerDecision,
    Decision,
    RiskLevel,
)

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


def normalize_request_id(value: object) -> str:
    if isinstance(value, (str, int)):
        normalized = str(value).strip()
        if normalized:
            return normalized
    raise ValueError("request_id must be a non-empty string or integer.")


def normalize_identifier(field_name: str, value: object) -> str:
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            return normalized
    raise ValueError(f"{field_name} must be a non-empty string.")


def normalize_approval_kind(value: str) -> ApprovalKind:
    try:
        return ApprovalKind(value)
    except ValueError as exc:
        raise ValueError("kind must be one of: command_execution, file_change.") from exc


def normalize_broker_decision(value: str) -> BrokerDecision:
    try:
        return BrokerDecision(value)
    except ValueError as exc:
        raise ValueError("decision must be one of: accept, acceptForSession, decline, cancel.") from exc


def default_available_decisions(kind: ApprovalKind) -> list[BrokerDecision]:
    if kind in {ApprovalKind.COMMAND_EXECUTION, ApprovalKind.FILE_CHANGE}:
        return [
            BrokerDecision.ACCEPT,
            BrokerDecision.ACCEPT_FOR_SESSION,
            BrokerDecision.DECLINE,
            BrokerDecision.CANCEL,
        ]
    raise ValueError(f"Unsupported approval kind: {kind}")


def normalize_available_decisions(
    values: Iterable[object] | None,
    *,
    kind: ApprovalKind,
) -> list[BrokerDecision]:
    if values is None:
        return default_available_decisions(kind)

    normalized: list[BrokerDecision] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            continue
        try:
            decision = normalize_broker_decision(value)
        except ValueError:
            continue
        if decision.value in seen:
            continue
        seen.add(decision.value)
        normalized.append(decision)

    return normalized or default_available_decisions(kind)


def build_broker_response(request_id: str, decision: str) -> BrokerApprovalResponse:
    normalized_request_id = normalize_request_id(request_id)
    normalized_decision = normalize_broker_decision(decision)
    return BrokerApprovalResponse(request_id=normalized_request_id, decision=normalized_decision)


def unique_stable(values: Iterable[str]) -> list[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
