from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from .app_server import AppServerClient
from .audit import append_jsonl
from .broker import (
    BrokerAuditPaths,
    BrokerState,
    audit_raw_message,
    default_broker_audit_paths,
    record_decision_event,
    record_events,
)
from .imessage import compose_approval_message, find_response_messages, message_key, poll_imessages, send_imessage
from .validation import build_broker_response


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class BrokerRuntimePaths:
    runtime_dir: Path
    state_path: Path
    response_queue_path: Path
    audit_paths: BrokerAuditPaths


def default_broker_runtime_paths(
    runtime_dir: Path | None = None,
    audit_dir: Path | None = None,
) -> BrokerRuntimePaths:
    runtime_root = runtime_dir or (_repo_root() / "var" / "run")
    return BrokerRuntimePaths(
        runtime_dir=runtime_root,
        state_path=runtime_root / "broker-state.json",
        response_queue_path=runtime_root / "broker-responses.jsonl",
        audit_paths=default_broker_audit_paths(audit_dir),
    )


def write_json_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp_path.replace(path)
    return path


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def initialize_response_queue(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")
    return path


def append_response_request(path: Path, payload: dict[str, Any]) -> Path:
    append_jsonl(path, "broker_response_request", payload)
    return path


def load_response_requests(path: Path, *, start_index: int = 0) -> tuple[list[dict[str, Any]], int]:
    if not path.exists():
        return [], start_index

    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    payloads: list[dict[str, Any]] = []
    for line in lines[start_index:]:
        record = json.loads(line)
        payload = record.get("payload", {})
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads, len(lines)


def _pending_approvals(state: BrokerState) -> list[dict[str, Any]]:
    return [pending.request.to_dict() for _, pending in sorted(state.pending.items())]


def build_runtime_state_payload(
    *,
    status: str,
    state: BrokerState,
    runtime_paths: BrokerRuntimePaths,
    approval_required: bool,
    turn_completed: bool,
    thread_id: str | None = None,
    turn_id: str | None = None,
    initialize_result: dict[str, Any] | None = None,
    last_error: str | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "thread_id": thread_id,
        "turn_id": turn_id,
        "approval_required": approval_required,
        "turn_completed": turn_completed,
        "pending_count": len(state.pending),
        "pending_approvals": _pending_approvals(state),
        "response_queue_path": str(runtime_paths.response_queue_path),
        "audit_paths": {
            key: str(value)
            for key, value in asdict(runtime_paths.audit_paths).items()
        },
        "updated_at": _utc_now(),
    }
    if initialize_result is not None:
        payload["initialize_result"] = initialize_result
    if last_error is not None:
        payload["last_error"] = last_error
    return payload


def read_runtime_state(path: Path) -> dict[str, Any]:
    return read_json_file(path)


def pending_request_ids_from_runtime_state(path: Path) -> list[str]:
    state = read_runtime_state(path)
    pending = state.get("pending_approvals", [])
    if not isinstance(pending, list):
        return []
    request_ids = []
    for approval in pending:
        if isinstance(approval, dict) and isinstance(approval.get("request_id"), str):
            request_ids.append(approval["request_id"])
    return request_ids


def queued_request_ids(path: Path) -> set[str]:
    queued: set[str] = set()
    for payload in load_response_requests(path)[0]:
        request_id = payload.get("request_id")
        if isinstance(request_id, str):
            queued.add(request_id)
    return queued


def enqueue_broker_response(
    *,
    request_id: str,
    decision: str,
    operator_note: str | None = None,
    runtime_paths: BrokerRuntimePaths,
) -> dict[str, Any]:
    response = build_broker_response(request_id, decision, operator_note=operator_note)
    state = read_runtime_state(runtime_paths.state_path)
    status = state.get("status")
    if status not in {"starting", "running", "approval_pending"}:
        raise ValueError(f"broker service is not accepting responses in status={status!r}.")

    pending_ids = set(pending_request_ids_from_runtime_state(runtime_paths.state_path))
    if response.request_id not in pending_ids:
        raise ValueError(f"request_id {response.request_id} is not currently pending.")

    if response.request_id in queued_request_ids(runtime_paths.response_queue_path):
        raise ValueError(f"request_id {response.request_id} already has a queued decision.")

    append_response_request(
        runtime_paths.response_queue_path,
        {
            "request_id": response.request_id,
            "decision": response.decision.value,
            "operator_note": response.operator_note,
            "queued_at": _utc_now(),
        },
    )
    return {
        "status": "queued",
        "response": response.to_dict(),
        "queue_path": str(runtime_paths.response_queue_path),
    }


def _determine_runtime_status(*, turn_completed: bool, pending_count: int, timed_out: bool) -> str:
    if turn_completed:
        return "completed"
    if timed_out:
        return "timeout"
    if pending_count:
        return "approval_pending"
    return "running"


def run_broker_service(
    *,
    prompt: str,
    cwd: Path,
    runtime_paths: BrokerRuntimePaths,
    approval_policy: str = "unlessTrusted",
    sandbox_policy: str = "workspaceWrite",
    timeout: float | None = None,
    poll_interval: float = 0.5,
    imessage_handle: str | None = None,
    imessage_poll_limit: int = 10,
    imessage_db_path: Path | None = None,
    client_factory: Callable[..., AppServerClient] | None = None,
) -> dict[str, Any]:
    runtime_paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    initialize_response_queue(runtime_paths.response_queue_path)
    state = BrokerState()
    approval_required = False
    turn_completed = False
    thread_id: str | None = None
    turn_id: str | None = None
    initialize_result: dict[str, Any] | None = None
    response_cursor = 0
    timed_out = False
    notified_request_ids: set[str] = set()
    seen_imessage_keys: set[str] = set()

    write_json_atomic(
        runtime_paths.state_path,
        build_runtime_state_payload(
            status="starting",
            state=state,
            runtime_paths=runtime_paths,
            approval_required=approval_required,
            turn_completed=turn_completed,
        ),
    )

    def log_message(direction: str, message: dict[str, Any]) -> None:
        audit_raw_message(runtime_paths.audit_paths.raw_messages, direction=direction, message=message)

    client_factory = client_factory or (lambda **kwargs: AppServerClient(**kwargs))
    started_at = time.monotonic()

    try:
        with client_factory(cwd=cwd, message_logger=log_message) as client:
            initialize_result = client.initialize()
            client.mark_initialized()

            thread_result = client.start_thread(
                cwd=cwd,
                approval_policy=approval_policy,
                sandbox=sandbox_policy,
            )
            thread = thread_result.get("thread", {})
            thread_id = thread.get("id") if isinstance(thread, dict) else None
            if not isinstance(thread_id, str) or not thread_id:
                raise RuntimeError(f"thread/start did not return a thread id: {thread_result!r}")

            turn_result = client.start_turn(
                thread_id=thread_id,
                prompt=prompt,
                cwd=cwd,
                approval_policy=approval_policy,
                sandbox_policy=sandbox_policy,
            )
            turn = turn_result.get("turn", {})
            turn_id = turn.get("id") if isinstance(turn, dict) else None

            write_json_atomic(
                runtime_paths.state_path,
                build_runtime_state_payload(
                    status="running",
                    state=state,
                    runtime_paths=runtime_paths,
                    approval_required=approval_required,
                    turn_completed=turn_completed,
                    thread_id=thread_id,
                    turn_id=turn_id,
                    initialize_result=initialize_result if isinstance(initialize_result, dict) else None,
                ),
            )

            while True:
                if timeout is not None and (time.monotonic() - started_at) >= timeout:
                    timed_out = True
                    break

                changed = False
                queued_responses, response_cursor = load_response_requests(
                    runtime_paths.response_queue_path,
                    start_index=response_cursor,
                )
                for queued in queued_responses:
                    queued_request_id = queued.get("request_id")
                    queued_decision = queued.get("decision")
                    queued_note = queued.get("operator_note")
                    if not isinstance(queued_request_id, str) or not isinstance(queued_decision, str):
                        continue
                    try:
                        pending = state.pending_request(queued_request_id)
                        response = state.send_decision(
                            queued_request_id,
                            queued_decision,
                            operator_note=queued_note if isinstance(queued_note, str) else None,
                        )
                    except ValueError as exc:
                        resolution = {
                            "event": "resolution",
                            "request_id": str(queued_request_id),
                            "thread_id": thread_id,
                            "reason": "response_rejected",
                            "stale": True,
                            "error": str(exc),
                            "timestamp": _utc_now(),
                        }
                        record_events([resolution], audit_paths=runtime_paths.audit_paths)
                        changed = True
                        continue

                    client.send_response(
                        pending.request.wire_request_id,
                        {"decision": response.decision.value},
                    )
                    audit_raw_message(
                        runtime_paths.audit_paths.raw_messages,
                        direction="outbound",
                        message={"id": pending.request.wire_request_id, "result": {"decision": response.decision.value}},
                    )
                    record_events(
                        [record_decision_event(response=response, pending=pending)],
                        audit_paths=runtime_paths.audit_paths,
                    )
                    changed = True

                emitted: list[dict[str, Any]] = []
                message = client.read_message(timeout=poll_interval)
                if message is not None:
                    emitted = state.handle_message(message)
                    if emitted:
                        record_events(emitted, audit_paths=runtime_paths.audit_paths)
                        if any(event.get("event") == "approval_request" for event in emitted):
                            approval_required = True
                        if any(event.get("event") == "turn_completed" for event in emitted):
                            turn_completed = True
                        changed = True

                if imessage_handle:
                    approval_events = [event for event in emitted if event.get("event") == "approval_request"]
                    for event in approval_events:
                        approval = event.get("approval", {})
                        request_id = approval.get("request_id")
                        if not isinstance(request_id, str) or request_id in notified_request_ids:
                            continue
                        pending = state.pending_request(request_id)
                        send_imessage(imessage_handle, compose_approval_message(pending.request))
                        notified_request_ids.add(request_id)

                if imessage_handle:
                    polled = poll_imessages(
                        imessage_handle,
                        limit=imessage_poll_limit,
                        db_path=imessage_db_path,
                    )
                    if polled.get("status") == "ok":
                        parsed_responses = []
                        for message in polled.get("messages", []):
                            if not isinstance(message, dict):
                                continue
                            key = message_key(message)
                            if key in seen_imessage_keys:
                                continue
                            seen_imessage_keys.add(key)
                            parsed_responses.extend(find_response_messages([message]))

                        for parsed in parsed_responses:
                            try:
                                pending = state.pending_request(parsed["request_id"])
                                response = state.send_decision(parsed["request_id"], parsed["decision"])
                            except ValueError:
                                continue
                            client.send_response(
                                pending.request.wire_request_id,
                                {"decision": response.decision.value},
                            )
                            audit_raw_message(
                                runtime_paths.audit_paths.raw_messages,
                                direction="outbound",
                                message={"id": pending.request.wire_request_id, "result": {"decision": response.decision.value}},
                            )
                            record_events(
                                [record_decision_event(response=response, pending=pending)],
                                audit_paths=runtime_paths.audit_paths,
                            )
                            changed = True

                if changed:
                    write_json_atomic(
                        runtime_paths.state_path,
                        build_runtime_state_payload(
                            status=_determine_runtime_status(
                                turn_completed=turn_completed,
                                pending_count=len(state.pending),
                                timed_out=False,
                            ),
                            state=state,
                            runtime_paths=runtime_paths,
                            approval_required=approval_required,
                            turn_completed=turn_completed,
                            thread_id=thread_id,
                            turn_id=turn_id,
                            initialize_result=initialize_result if isinstance(initialize_result, dict) else None,
                        ),
                    )

                if turn_completed and not state.pending:
                    break

    except Exception as exc:
        write_json_atomic(
            runtime_paths.state_path,
            build_runtime_state_payload(
                status="error",
                state=state,
                runtime_paths=runtime_paths,
                approval_required=approval_required,
                turn_completed=turn_completed,
                thread_id=thread_id,
                turn_id=turn_id,
                initialize_result=initialize_result if isinstance(initialize_result, dict) else None,
                last_error=str(exc),
            ),
        )
        raise

    final_status = _determine_runtime_status(
        turn_completed=turn_completed,
        pending_count=len(state.pending),
        timed_out=timed_out,
    )
    final_payload = build_runtime_state_payload(
        status=final_status,
        state=state,
        runtime_paths=runtime_paths,
        approval_required=approval_required,
        turn_completed=turn_completed,
        thread_id=thread_id,
        turn_id=turn_id,
        initialize_result=initialize_result if isinstance(initialize_result, dict) else None,
    )
    write_json_atomic(runtime_paths.state_path, final_payload)
    return final_payload
