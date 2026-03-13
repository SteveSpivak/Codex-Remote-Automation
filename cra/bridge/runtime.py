from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from ..broker import BrokerState, record_decision_event
from ..models import PendingApproval


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class BridgeRuntime:
    def __init__(self, broker_state: BrokerState | None = None) -> None:
        self.broker_state = broker_state or BrokerState()
        self.codex_handshake_state = "cold"
        self.forwarded_initialize_request_ids: set[str] = set()

    def snapshot_payload(self) -> dict[str, Any]:
        pending = [pending.request.to_dict() for _, pending in sorted(self.broker_state.pending.items())]
        return {
            "pendingApprovals": pending,
            "pendingCount": len(pending),
            "updatedAt": _utc_now(),
        }

    def pending_snapshot_notification(self) -> dict[str, Any]:
        return {
            "method": "bridge/pendingApprovalsUpdated",
            "params": self.snapshot_payload(),
        }

    def handle_codex_message(self, message: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        self._track_codex_handshake_state(message)
        broker_events = self.broker_state.handle_message(message)
        if not broker_events:
            return {"phone_messages": [], "broker_events": []}
        return {
            "phone_messages": [self.pending_snapshot_notification()],
            "broker_events": broker_events,
        }

    def handle_phone_message(self, raw_message: str) -> dict[str, Any]:
        try:
            parsed = json.loads(raw_message)
        except json.JSONDecodeError:
            return {"phone_messages": [], "forward_to_codex": [], "codex_responses": [], "broker_events": []}

        if not isinstance(parsed, dict):
            return {"phone_messages": [], "forward_to_codex": [], "codex_responses": [], "broker_events": []}

        method = str(parsed.get("method") or "").strip()
        request_id = parsed.get("id")
        phone_messages: list[dict[str, Any]] = []
        forward_to_codex: list[dict[str, Any]] = []
        codex_responses: list[dict[str, Any]] = []
        broker_events: list[dict[str, Any]] = []

        if method == "initialize" and request_id is not None:
            if self.codex_handshake_state == "warm":
                phone_messages.append(
                    {
                        "id": request_id,
                        "result": {
                            "bridgeManaged": True,
                            "pendingCount": len(self.broker_state.pending),
                        },
                    }
                )
            else:
                self.forwarded_initialize_request_ids.add(str(request_id))
                forward_to_codex.append(parsed)
            return {
                "phone_messages": phone_messages,
                "forward_to_codex": forward_to_codex,
                "codex_responses": codex_responses,
                "broker_events": broker_events,
            }

        if method == "initialized":
            if self.codex_handshake_state != "warm":
                forward_to_codex.append(parsed)
            return {
                "phone_messages": phone_messages,
                "forward_to_codex": forward_to_codex,
                "codex_responses": codex_responses,
                "broker_events": broker_events,
            }

        if method == "bridge/getPendingApprovals" and request_id is not None:
            phone_messages.append({"id": request_id, "result": self.snapshot_payload()})
            return {
                "phone_messages": phone_messages,
                "forward_to_codex": forward_to_codex,
                "codex_responses": codex_responses,
                "broker_events": broker_events,
            }

        if method == "bridge/respondApproval" and request_id is not None:
            params = parsed.get("params", {})
            if not isinstance(params, dict):
                phone_messages.append(
                    {
                        "id": request_id,
                        "error": {"code": -32000, "message": "bridge/respondApproval requires params."},
                    }
                )
                return {
                    "phone_messages": phone_messages,
                    "forward_to_codex": forward_to_codex,
                    "codex_responses": codex_responses,
                    "broker_events": broker_events,
                }

            approval_request_id = str(params.get("requestId") or "")
            decision = str(params.get("decision") or "")
            operator_note = params.get("operatorNote")
            try:
                pending: PendingApproval = self.broker_state.pending_request(approval_request_id)
                response = self.broker_state.send_decision(
                    approval_request_id,
                    decision,
                    operator_note=operator_note if isinstance(operator_note, str) else None,
                )
            except ValueError as exc:
                phone_messages.append(
                    {"id": request_id, "error": {"code": -32000, "message": str(exc)}}
                )
                return {
                    "phone_messages": phone_messages,
                    "forward_to_codex": forward_to_codex,
                    "codex_responses": codex_responses,
                    "broker_events": broker_events,
                }

            broker_events.append(record_decision_event(response=response, pending=pending))
            codex_responses.append(
                {
                    "id": pending.request.wire_request_id,
                    "result": {"decision": response.decision.value},
                    "operator_note": response.operator_note,
                    "request_id": response.request_id,
                }
            )
            phone_messages.append(
                {
                    "id": request_id,
                    "result": {
                        "accepted": True,
                        "request_id": response.request_id,
                        "decision": response.decision.value,
                    },
                }
            )
            phone_messages.append(self.pending_snapshot_notification())
            return {
                "phone_messages": phone_messages,
                "forward_to_codex": forward_to_codex,
                "codex_responses": codex_responses,
                "broker_events": broker_events,
            }

        if request_id is not None:
            phone_messages.append(
                {
                    "id": request_id,
                    "error": {"code": -32000, "message": f"Unknown bridge method: {method or 'unknown'}"},
                }
            )
        return {
            "phone_messages": phone_messages,
            "forward_to_codex": forward_to_codex,
            "codex_responses": codex_responses,
            "broker_events": broker_events,
        }

    def _track_codex_handshake_state(self, message: dict[str, Any]) -> None:
        response_id = message.get("id")
        if response_id is None:
            return
        response_key = str(response_id)
        if response_key not in self.forwarded_initialize_request_ids:
            return
        if message.get("result") is not None:
            self.codex_handshake_state = "warm"
            self.forwarded_initialize_request_ids.discard(response_key)
            return
        error = message.get("error")
        error_message = ""
        if isinstance(error, dict):
            error_message = str(error.get("message") or "").lower()
        if "already initialized" in error_message:
            self.codex_handshake_state = "warm"
            self.forwarded_initialize_request_ids.discard(response_key)
