from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable

from .audit import append_jsonl
from .models import ApprovalKind, BrokerApprovalRequest, BrokerApprovalResponse, BrokerDecision, PendingApproval
from .validation import (
    build_broker_response,
    normalize_available_decisions,
    normalize_identifier,
    normalize_request_id,
    sanitize_text,
)

APPROVAL_METHODS = {
    "item/commandExecution/requestApproval": ApprovalKind.COMMAND_EXECUTION,
    "item/fileChange/requestApproval": ApprovalKind.FILE_CHANGE,
}

ITEM_STARTED_METHOD = "item/started"
ITEM_COMPLETED_METHOD = "item/completed"
TURN_COMPLETED_METHOD = "turn/completed"
SERVER_REQUEST_RESOLVED_METHOD = "serverRequest/resolved"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BrokerAuditPaths:
    raw_messages: Path
    approvals: Path
    decisions: Path
    resolutions: Path


def default_broker_audit_paths(base_dir: Path | None = None) -> BrokerAuditPaths:
    audit_dir = base_dir or (_repo_root() / "var" / "audit")
    return BrokerAuditPaths(
        raw_messages=audit_dir / "broker-raw.jsonl",
        approvals=audit_dir / "broker-approvals.jsonl",
        decisions=audit_dir / "broker-decisions.jsonl",
        resolutions=audit_dir / "broker-resolutions.jsonl",
    )


def audit_raw_message(path: Path, *, direction: str, message: Dict[str, Any]) -> None:
    append_jsonl(path, "app_server_message", {"direction": direction, "message": message})


def append_broker_record(path: Path, record_type: str, payload: Dict[str, Any]) -> None:
    append_jsonl(path, record_type, payload)


def load_jsonl_messages(path: Path) -> list[Dict[str, Any]]:
    messages: list[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if isinstance(payload, dict) and "record_type" in payload:
            nested = payload.get("payload", {})
            if isinstance(nested, dict) and isinstance(nested.get("message"), dict):
                messages.append(nested["message"])
                continue
        if isinstance(payload, dict):
            messages.append(payload)
    return messages


def _command_summary(params: Dict[str, Any]) -> str:
    reason = sanitize_text(str(params.get("reason") or ""), max_length=400)
    if reason:
        summary = reason
    else:
        command = sanitize_text(str(params.get("command") or "pending command"), max_length=220)
        cwd = sanitize_text(str(params.get("cwd") or ""), max_length=120)
        summary = f"Run command {command}"
        if cwd:
            summary += f" in {cwd}"

    network_context = params.get("networkApprovalContext")
    if isinstance(network_context, dict):
        host = sanitize_text(str(network_context.get("host") or ""), max_length=120)
        protocol = sanitize_text(str(network_context.get("protocol") or ""), max_length=40)
        port = network_context.get("port")
        network_parts = [part for part in [protocol, host, str(port) if port is not None else ""] if part]
        if network_parts:
            summary = f"Network approval for {' '.join(network_parts)}. {summary}"

    return sanitize_text(summary, max_length=400)


def _summarize_file_change_item(item: Dict[str, Any]) -> str:
    changes = item.get("changes")
    if not isinstance(changes, list) or not changes:
        return ""
    paths = []
    for change in changes:
        if not isinstance(change, dict):
            continue
        path = change.get("path")
        if isinstance(path, str) and path.strip():
            paths.append(sanitize_text(path, max_length=120))
    if not paths:
        return ""
    visible = ", ".join(paths[:3])
    remainder = len(paths) - min(len(paths), 3)
    if remainder > 0:
        visible += f", +{remainder} more"
    return visible


def _file_change_summary(params: Dict[str, Any], item_snapshot: Dict[str, Any] | None) -> str:
    reason = sanitize_text(str(params.get("reason") or ""), max_length=400)
    if reason:
        return reason

    grant_root = sanitize_text(str(params.get("grantRoot") or ""), max_length=180)
    change_summary = _summarize_file_change_item(item_snapshot or {})
    if change_summary and grant_root:
        return sanitize_text(f"Allow file changes to {change_summary} under {grant_root}", max_length=400)
    if change_summary:
        return sanitize_text(f"Allow file changes to {change_summary}", max_length=400)
    if grant_root:
        return sanitize_text(f"Allow file changes under {grant_root}", max_length=400)
    return "Allow file changes for the pending item"


def normalize_approval_request(
    message: Dict[str, Any],
    *,
    item_snapshot: Dict[str, Any] | None = None,
    timestamp: str | None = None,
) -> BrokerApprovalRequest:
    method = message.get("method")
    if method not in APPROVAL_METHODS:
        raise ValueError(f"Unsupported approval method: {method!r}")

    params = message.get("params")
    if not isinstance(params, dict):
        raise ValueError("Approval request params must be an object.")

    kind = APPROVAL_METHODS[method]
    if kind is ApprovalKind.COMMAND_EXECUTION:
        summary = _command_summary(params)
    else:
        summary = _file_change_summary(params, item_snapshot)

    return BrokerApprovalRequest(
        request_id=normalize_request_id(message.get("id")),
        thread_id=normalize_identifier("thread_id", params.get("threadId")),
        turn_id=normalize_identifier("turn_id", params.get("turnId")),
        item_id=normalize_identifier("item_id", params.get("itemId")),
        kind=kind,
        summary=summary,
        available_decisions=normalize_available_decisions(params.get("availableDecisions"), kind=kind),
        timestamp=timestamp or _utc_now(),
        wire_request_id=message["id"],
        approval_id=params.get("approvalId") if isinstance(params.get("approvalId"), str) else None,
        method=method,
    )


class BrokerState:
    def __init__(self) -> None:
        self.pending: dict[str, PendingApproval] = {}
        self.items_by_id: dict[str, Dict[str, Any]] = {}
        self.responded_request_ids: set[str] = set()

    def handle_message(
        self,
        message: Dict[str, Any],
        *,
        timestamp: str | None = None,
    ) -> list[Dict[str, Any]]:
        method = message.get("method")
        recorded_at = timestamp or _utc_now()
        if method in APPROVAL_METHODS:
            params = message.get("params")
            if not isinstance(params, dict):
                raise ValueError("Approval request params must be an object.")
            item_snapshot = self.items_by_id.get(normalize_identifier("item_id", params.get("itemId")))
            approval = normalize_approval_request(message, item_snapshot=item_snapshot, timestamp=recorded_at)
            self.pending[approval.request_id] = PendingApproval(
                request=approval,
                item_snapshot=item_snapshot,
                opened_at=recorded_at,
            )
            return [{"event": "approval_request", "approval": approval.to_dict()}]

        if method == ITEM_STARTED_METHOD:
            item = self._get_item(message)
            if item is not None:
                self.items_by_id[item["id"]] = item
            return []

        if method == ITEM_COMPLETED_METHOD:
            item = self._get_item(message)
            if item is not None:
                self.items_by_id[item["id"]] = item
                return self._cleanup_for_item(item, recorded_at=recorded_at)
            return []

        if method == SERVER_REQUEST_RESOLVED_METHOD:
            params = message.get("params")
            if not isinstance(params, dict):
                return []
            request_id = normalize_request_id(params.get("requestId"))
            pending = self.pending.pop(request_id, None)
            already_responded = request_id in self.responded_request_ids
            if already_responded:
                self.responded_request_ids.discard(request_id)
            return [
                {
                    "event": "resolution",
                    "request_id": request_id,
                    "thread_id": params.get("threadId"),
                    "reason": "server_request_resolved",
                    "stale": pending is None and not already_responded,
                    "timestamp": recorded_at,
                }
            ]

        if method == TURN_COMPLETED_METHOD:
            params = message.get("params")
            if isinstance(params, dict):
                turn = params.get("turn")
                if isinstance(turn, dict):
                    return [
                        {
                            "event": "turn_completed",
                            "thread_id": params.get("threadId"),
                            "turn_id": turn.get("id"),
                            "timestamp": recorded_at,
                        }
                    ]
            return []

        return []

    def send_decision(
        self,
        request_id: str,
        decision: str,
        *,
        operator_note: str | None = None,
        timestamp: str | None = None,
    ) -> BrokerApprovalResponse:
        normalized_request_id = normalize_request_id(request_id)
        pending = self.pending.pop(normalized_request_id, None)
        if pending is None:
            raise ValueError(f"request_id {normalized_request_id} is not pending.")
        response = build_broker_response(normalized_request_id, decision, operator_note=operator_note)
        pending.responded_at = timestamp or _utc_now()
        self.responded_request_ids.add(normalized_request_id)
        return response

    def has_pending(self, request_id: str) -> bool:
        return normalize_request_id(request_id) in self.pending

    def unresolved_request_ids(self) -> list[str]:
        return sorted(self.pending.keys())

    def pending_request(self, request_id: str) -> PendingApproval:
        normalized_request_id = normalize_request_id(request_id)
        pending = self.pending.get(normalized_request_id)
        if pending is None:
            raise ValueError(f"request_id {normalized_request_id} is not pending.")
        return pending

    def _get_item(self, message: Dict[str, Any]) -> Dict[str, Any] | None:
        params = message.get("params")
        if not isinstance(params, dict):
            return None
        item = params.get("item")
        if not isinstance(item, dict):
            return None
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            return None
        return item

    def _cleanup_for_item(self, item: Dict[str, Any], *, recorded_at: str) -> list[Dict[str, Any]]:
        item_id = item["id"]
        status = item.get("status")
        terminal = status != "inProgress"
        if not terminal:
            return []

        events = []
        for request_id, pending in list(self.pending.items()):
            if pending.request.item_id != item_id:
                continue
            self.pending.pop(request_id, None)
            events.append(
                {
                    "event": "resolution",
                    "request_id": request_id,
                    "item_id": item_id,
                    "thread_id": pending.request.thread_id,
                    "reason": "item_completed",
                    "stale": False,
                    "status": status,
                    "timestamp": recorded_at,
                }
            )
        return events


def record_events(
    events: Iterable[Dict[str, Any]],
    *,
    audit_paths: BrokerAuditPaths,
) -> None:
    for event in events:
        event_type = event.get("event")
        if event_type == "approval_request":
            append_broker_record(audit_paths.approvals, "broker_approval_request", event["approval"])
        elif event_type == "decision_sent":
            append_broker_record(audit_paths.decisions, "broker_decision", event)
        elif event_type == "resolution":
            append_broker_record(audit_paths.resolutions, "broker_resolution", event)


def record_decision_event(
    *,
    response: BrokerApprovalResponse,
    pending: PendingApproval,
    timestamp: str | None = None,
) -> Dict[str, Any]:
    return {
        "event": "decision_sent",
        "request_id": response.request_id,
        "decision": response.decision.value,
        "operator_note": response.operator_note,
        "kind": pending.request.kind.value,
        "thread_id": pending.request.thread_id,
        "turn_id": pending.request.turn_id,
        "item_id": pending.request.item_id,
        "timestamp": timestamp or _utc_now(),
    }


def replay_messages(
    messages: Iterable[Dict[str, Any]],
    *,
    auto_decision: str | None = None,
    audit_paths: BrokerAuditPaths | None = None,
) -> Dict[str, Any]:
    state = BrokerState()
    events: list[Dict[str, Any]] = []
    for message in messages:
        if audit_paths is not None:
            audit_raw_message(audit_paths.raw_messages, direction="inbound", message=message)

        emitted = state.handle_message(message)
        if emitted and audit_paths is not None:
            record_events(emitted, audit_paths=audit_paths)
        events.extend(emitted)

        if auto_decision:
            approval_events = [event for event in emitted if event.get("event") == "approval_request"]
            for event in approval_events:
                pending = state.pending_request(event["approval"]["request_id"])
                response = state.send_decision(event["approval"]["request_id"], auto_decision)
                decision_event = record_decision_event(response=response, pending=pending)
                events.append(decision_event)
                if audit_paths is not None:
                    audit_raw_message(
                        audit_paths.raw_messages,
                        direction="outbound",
                        message={"id": pending.request.wire_request_id, "result": {"decision": response.decision.value}},
                    )
                    append_broker_record(audit_paths.decisions, "broker_decision", decision_event)

    return {
        "status": "ok",
        "events": events,
        "pending_request_ids": state.unresolved_request_ids(),
    }


def summarize_broker_audit(audit_paths: BrokerAuditPaths) -> Dict[str, Any]:
    approvals_seen: dict[str, Dict[str, Any]] = {}
    decisions_sent: set[str] = set()
    resolved_request_ids: set[str] = set()
    stale_requests: set[str] = set()
    resolution_count = 0

    if audit_paths.approvals.exists():
        for line in audit_paths.approvals.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            record = payload.get("payload", {})
            request_id = record.get("request_id")
            if isinstance(request_id, str):
                approvals_seen[request_id] = record

    if audit_paths.decisions.exists():
        for line in audit_paths.decisions.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            record = payload.get("payload", {})
            request_id = record.get("request_id")
            if isinstance(request_id, str):
                decisions_sent.add(request_id)

    if audit_paths.resolutions.exists():
        for line in audit_paths.resolutions.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            record = payload.get("payload", {})
            resolution_count += 1
            request_id = record.get("request_id")
            if isinstance(request_id, str):
                resolved_request_ids.add(request_id)
                if record.get("stale") is True:
                    stale_requests.add(request_id)

    unresolved_request_ids = sorted(set(approvals_seen) - decisions_sent - resolved_request_ids)
    return {
        "status": "ok",
        "approvals_seen": len(approvals_seen),
        "decisions_sent": len(decisions_sent),
        "resolutions_seen": resolution_count,
        "stale_requests": sorted(stale_requests),
        "unresolved_request_ids": unresolved_request_ids,
    }
