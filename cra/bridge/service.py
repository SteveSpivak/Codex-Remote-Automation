from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..app_server import AppServerClient
from ..audit import append_jsonl
from ..broker import (
    audit_raw_message,
    default_broker_audit_paths,
    record_events,
)
from ..broker_service import write_json_atomic
from .device_state import BridgePaths, load_or_create_bridge_device_state, save_bridge_device_state
from .qr import write_pairing_qr_image, write_pairing_qr_stub
from .runtime import BridgeRuntime
from .secure_transport import BridgeSecureTransport
from .ws_client import WebSocketClient


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _default_relay_session_url(relay_url: str, session_id: str, role: str) -> str:
    base = relay_url.rstrip("/")
    return f"{base}/session/{session_id}?role={role}"


def build_bridge_state_payload(
    *,
    session_id: str,
    relay_url: str,
    pairing_payload: dict[str, Any],
    runtime: BridgeRuntime,
    secure_ready: bool,
    bridge_paths: BridgePaths,
    status: str,
    thread_id: str | None,
    turn_id: str | None,
    last_error: str | None = None,
) -> dict[str, Any]:
    payload = {
        "status": status,
        "session_id": session_id,
        "relay_url": relay_url,
        "secure_ready": secure_ready,
        "pairing_payload_path": str(bridge_paths.pairing_payload_path),
        "pairing_qr_path": str(bridge_paths.pairing_qr_path),
        "pairing_qr_stub_path": str(bridge_paths.pairing_qr_stub_path),
        "thread_id": thread_id,
        "turn_id": turn_id,
        "pending_approvals": runtime.snapshot_payload()["pendingApprovals"],
        "updated_at": _utc_now(),
    }
    if last_error is not None:
        payload["last_error"] = last_error
    return payload


def run_bridge_service(
    *,
    relay_url: str,
    bridge_paths: BridgePaths,
    cwd: Path,
    prompt: str | None = None,
    approval_policy: str = "unlessTrusted",
    sandbox_policy: str = "workspaceWrite",
    timeout: float | None = None,
    poll_interval: float = 0.25,
) -> dict[str, Any]:
    device_state = load_or_create_bridge_device_state(bridge_paths.device_state_path)
    session_id = str(uuid.uuid4())
    secure_transport = BridgeSecureTransport(
        session_id=session_id,
        relay_url=relay_url.rstrip("/"),
        device_state=device_state,
    )
    pairing_payload = secure_transport.create_pairing_payload()
    bridge_paths.pairing_payload_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_paths.pairing_payload_path.write_text(
        json.dumps(pairing_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_pairing_qr_image(bridge_paths.pairing_qr_path, pairing_payload)
    write_pairing_qr_stub(bridge_paths.pairing_qr_stub_path, pairing_payload)

    runtime = BridgeRuntime()
    broker_audit_paths = default_broker_audit_paths(bridge_paths.bridge_audit_path.parent)
    relay_session_url = _default_relay_session_url(relay_url, session_id, "mac")
    started_at = time.monotonic()
    thread_id: str | None = None
    turn_id: str | None = None

    write_json_atomic(
        bridge_paths.runtime_state_path,
        build_bridge_state_payload(
            session_id=session_id,
            relay_url=relay_session_url,
            pairing_payload=pairing_payload,
            runtime=runtime,
            secure_ready=False,
            bridge_paths=bridge_paths,
            status="starting",
            thread_id=thread_id,
            turn_id=turn_id,
        ),
    )

    def log_app_server_message(direction: str, message: dict[str, Any]) -> None:
        audit_raw_message(broker_audit_paths.raw_messages, direction=direction, message=message)

    with AppServerClient(cwd=cwd, message_logger=log_app_server_message) as client, WebSocketClient(relay_session_url) as relay:
        secure_transport.bind_live_send_wire_message(relay.send_text)
        append_jsonl(bridge_paths.bridge_audit_path, "bridge_started", {"session_id": session_id, "relay_url": relay_session_url})

        client.initialize()
        client.mark_initialized()
        thread_result = client.start_thread(cwd=cwd, approval_policy=approval_policy, sandbox=sandbox_policy)
        thread = thread_result.get("thread", {})
        if isinstance(thread, dict):
            thread_id = thread.get("id") if isinstance(thread.get("id"), str) else None
        if prompt and thread_id:
            turn_result = client.start_turn(
                thread_id=thread_id,
                prompt=prompt,
                cwd=cwd,
                approval_policy=approval_policy,
                sandbox_policy=sandbox_policy,
            )
            turn = turn_result.get("turn", {})
            if isinstance(turn, dict):
                turn_id = turn.get("id") if isinstance(turn.get("id"), str) else None

        def send_control_message(control_message: dict[str, Any]) -> None:
            append_jsonl(bridge_paths.wire_audit_path, "bridge_wire_outbound", control_message)
            relay.send_text(_serialize_json(control_message))
            save_bridge_device_state(bridge_paths.device_state_path, secure_transport.device_state)

        def on_application_message(payload_text: str) -> None:
            append_jsonl(bridge_paths.bridge_audit_path, "bridge_phone_message", {"payload": payload_text})
            result = runtime.handle_phone_message(payload_text)
            for codex_request in result["forward_to_codex"]:
                client._send_message(codex_request)  # noqa: SLF001 - bridge forwards opaque protocol messages.
            for codex_response in result["codex_responses"]:
                client.send_response(codex_response["id"], {"decision": codex_response["result"]["decision"]})
            if result["broker_events"]:
                record_events(result["broker_events"], audit_paths=broker_audit_paths)
            for phone_message in result["phone_messages"]:
                secure_transport.queue_outbound_application_message(_serialize_json(phone_message), relay.send_text)

        while True:
            if timeout is not None and (time.monotonic() - started_at) >= timeout:
                break

            wire_message = relay.recv_text(timeout=poll_interval)
            if wire_message:
                append_jsonl(bridge_paths.wire_audit_path, "bridge_wire_inbound", {"message": wire_message})
                secure_transport.handle_incoming_wire_message(
                    wire_message,
                    send_control_message=send_control_message,
                    on_application_message=on_application_message,
                )
                save_bridge_device_state(bridge_paths.device_state_path, secure_transport.device_state)

            app_message = client.read_message(timeout=0.01)
            if app_message is not None:
                result = runtime.handle_codex_message(app_message)
                if result["broker_events"]:
                    record_events(result["broker_events"], audit_paths=broker_audit_paths)
                for phone_update in result["phone_messages"]:
                    secure_transport.queue_outbound_application_message(_serialize_json(phone_update), relay.send_text)

            write_json_atomic(
                bridge_paths.runtime_state_path,
                build_bridge_state_payload(
                    session_id=session_id,
                    relay_url=relay_session_url,
                    pairing_payload=pairing_payload,
                    runtime=runtime,
                    secure_ready=secure_transport.is_secure_channel_ready(),
                    bridge_paths=bridge_paths,
                    status="running",
                    thread_id=thread_id,
                    turn_id=turn_id,
                ),
            )

    save_bridge_device_state(bridge_paths.device_state_path, secure_transport.device_state)
    final_state = build_bridge_state_payload(
        session_id=session_id,
        relay_url=relay_session_url,
        pairing_payload=pairing_payload,
        runtime=runtime,
        secure_ready=secure_transport.is_secure_channel_ready(),
        bridge_paths=bridge_paths,
        status="completed",
        thread_id=thread_id,
        turn_id=turn_id,
    )
    write_json_atomic(bridge_paths.runtime_state_path, final_state)
    return final_state
