from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

from .ax_tree import dump_ax_tree
from .accessibility import enable_manual_accessibility
from .actuator import run_local_actuation
from .app_server import AppServerClient
from .audit import append_jsonl
from .bridge import default_bridge_paths, load_or_create_bridge_device_state, run_bridge_service
from .bridge.qr import pairing_uri, write_pairing_qr_stub
from .bridge.secure_transport import BridgeSecureTransport
from .broker import (
    BrokerState,
    audit_raw_message,
    default_broker_audit_paths,
    load_jsonl_messages,
    record_decision_event,
    record_events,
    replay_messages,
    summarize_broker_audit,
)
from .broker_service import (
    default_broker_runtime_paths,
    enqueue_broker_response,
    read_runtime_state,
    run_broker_service,
)
from .discovery import SENTRY_SCOPE_PATH, discover_codex_environment
from .imessage import parse_response_message, poll_imessages, send_imessage
from .shortcuts import (
    build_shortcut_approval_payload,
    build_broker_response_ssh_command,
    build_ssh_command,
    handle_shortcut_entry,
    run_shortcut,
)
from .ui_probe import parse_probe_output, run_probe
from .validation import build_actuation_request, build_approval_event
from .vision import capture_codex_window_ocr, find_text_target
from .watcher import run_watch, summarize_scope_file


def _json_print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def main() -> int:
    parser = argparse.ArgumentParser(description="Codex Remote Automation CLI scaffold.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("discover", help="Inspect the local Codex installation and candidate event surfaces.")

    summarize_parser = subparsers.add_parser("summarize-sentry", help="Summarize the local Codex Sentry scope breadcrumbs.")
    summarize_parser.add_argument("--path", default=str(SENTRY_SCOPE_PATH), help="Override the Sentry scope path.")

    payload_parser = subparsers.add_parser("build-payload", help="Build a sanitized approval payload.")
    payload_parser.add_argument("--context", required=True)
    payload_parser.add_argument("--risk-level", required=True)
    payload_parser.add_argument("--action-id")

    validate_parser = subparsers.add_parser("validate-request", help="Validate an inbound actuation request.")
    validate_parser.add_argument("--decision", required=True)
    validate_parser.add_argument("--action-id", required=True)

    synthetic_parser = subparsers.add_parser("emit-synthetic-event", help="Write a synthetic approval event to JSONL.")
    synthetic_parser.add_argument("--context", required=True)
    synthetic_parser.add_argument("--risk-level", required=True)
    synthetic_parser.add_argument("--action-id")
    synthetic_parser.add_argument("--output", default="var/audit/synthetic-events.jsonl")

    actuate_parser = subparsers.add_parser("actuate-local", help="Invoke the local AppleScript actuator.")
    actuate_parser.add_argument("--decision", required=True)
    actuate_parser.add_argument("--action-id", required=True)
    actuate_parser.add_argument("--allow-live", action="store_true")
    actuate_parser.add_argument("--allow-visual", action="store_true")
    actuate_parser.add_argument("--selector-config")
    actuate_parser.add_argument("--ocr-image-output")

    shortcut_entry_parser = subparsers.add_parser("shortcut-entry", help="Validated entrypoint for iPhone/macOS Shortcuts or SSH.")
    shortcut_entry_parser.add_argument("--decision", required=True)
    shortcut_entry_parser.add_argument("--action-id", required=True)
    shortcut_entry_parser.add_argument("--allow-live", action="store_true")
    shortcut_entry_parser.add_argument("--allow-visual", action="store_true")
    shortcut_entry_parser.add_argument("--selector-config")
    shortcut_entry_parser.add_argument("--audit-path")
    shortcut_entry_parser.add_argument("--ocr-image-output")

    ssh_command_parser = subparsers.add_parser("build-ssh-command", help="Build the SSH command string for a Shortcut.")
    ssh_command_parser.add_argument("--decision", required=True)
    ssh_command_parser.add_argument("--action-id", required=True)
    ssh_command_parser.add_argument("--allow-live", action="store_true")
    ssh_command_parser.add_argument("--allow-visual", action="store_true")
    ssh_command_parser.add_argument("--selector-config")
    ssh_command_parser.add_argument("--audit-path")
    ssh_command_parser.add_argument("--python-path", default="python3")

    shortcut_run_parser = subparsers.add_parser("run-shortcut", help="Run a macOS Shortcut by name.")
    shortcut_run_parser.add_argument("--name", required=True)
    shortcut_run_parser.add_argument("--input-path")
    shortcut_run_parser.add_argument("--output-path")
    shortcut_run_parser.add_argument("--output-type")

    probe_parser = subparsers.add_parser("probe-ui", help="Capture and parse the Codex Accessibility button inventory.")
    probe_parser.add_argument("--output")

    accessibility_parser = subparsers.add_parser(
        "enable-manual-accessibility",
        help="Set AXManualAccessibility on the running Codex app.",
    )
    accessibility_parser.add_argument("--bundle-id", default="com.openai.codex")
    accessibility_parser.add_argument("--app-name", default="Codex")
    accessibility_parser.add_argument("--pid", type=int)
    accessibility_parser.add_argument("--prompt-trust", action="store_true")

    ax_tree_parser = subparsers.add_parser("dump-ax-tree", help="Dump the low-level Accessibility tree for a running process.")
    ax_tree_parser.add_argument("--pid", required=True, type=int)
    ax_tree_parser.add_argument("--max-depth", default=4, type=int)
    ax_tree_parser.add_argument("--max-children", default=20, type=int)
    ax_tree_parser.add_argument("--output")

    ocr_parser = subparsers.add_parser("capture-window-ocr", help="Capture the Codex window and run Apple Vision OCR.")
    ocr_parser.add_argument("--app-name", default="Codex")
    ocr_parser.add_argument("--pid", type=int)
    ocr_parser.add_argument("--image-output")
    ocr_parser.add_argument("--output")
    ocr_parser.add_argument("--target-text", action="append", default=[])
    ocr_parser.add_argument("--required-context", action="append", default=[])

    watch_parser = subparsers.add_parser("watch-sentry", help="Watch the local Sentry scope file for modifications.")
    watch_parser.add_argument("--path", default=str(SENTRY_SCOPE_PATH))
    watch_parser.add_argument("--audit-path", default="var/audit/sentry-scope.jsonl")

    broker_demo_parser = subparsers.add_parser("broker-demo", help="Run a local App Server broker smoke test.")
    broker_demo_parser.add_argument("--prompt", required=True)
    broker_demo_parser.add_argument("--cwd", default=str(_repo_root()))
    broker_demo_parser.add_argument("--approval-policy", default="unlessTrusted")
    broker_demo_parser.add_argument("--sandbox-policy", default="workspaceWrite")
    broker_demo_parser.add_argument("--auto-decision", choices=["accept", "acceptForSession", "decline", "cancel"])
    broker_demo_parser.add_argument("--timeout", type=float, default=45.0)
    broker_demo_parser.add_argument("--audit-dir", default="var/audit")

    bridge_pairing_parser = subparsers.add_parser(
        "bridge-create-pairing",
        help="Create a secure CRA bridge pairing payload and QR stub.",
    )
    bridge_pairing_parser.add_argument("--relay-url", default="ws://127.0.0.1:8787")
    bridge_pairing_parser.add_argument("--bridge-dir", default="var/bridge")
    bridge_pairing_parser.add_argument("--audit-dir", default="var/audit")

    bridge_state_parser = subparsers.add_parser(
        "bridge-state",
        help="Read the current CRA bridge runtime state file.",
    )
    bridge_state_parser.add_argument("--bridge-dir", default="var/bridge")
    bridge_state_parser.add_argument("--audit-dir", default="var/audit")

    bridge_service_parser = subparsers.add_parser(
        "bridge-service",
        help="Run the Remodex-style CRA bridge with a warm local App Server session.",
    )
    bridge_service_parser.add_argument("--relay-url", default="ws://127.0.0.1:8787")
    bridge_service_parser.add_argument("--bridge-dir", default="var/bridge")
    bridge_service_parser.add_argument("--audit-dir", default="var/audit")
    bridge_service_parser.add_argument("--cwd", default=str(_repo_root()))
    bridge_service_parser.add_argument("--prompt")
    bridge_service_parser.add_argument("--approval-policy", default="unlessTrusted")
    bridge_service_parser.add_argument("--sandbox-policy", default="workspaceWrite")
    bridge_service_parser.add_argument("--timeout", type=float, default=300.0)
    bridge_service_parser.add_argument("--poll-interval", type=float, default=0.25)

    broker_replay_parser = subparsers.add_parser(
        "broker-replay",
        help="Replay App Server JSONL fixtures through the broker state machine.",
    )
    broker_replay_parser.add_argument("--input", required=True)
    broker_replay_parser.add_argument("--auto-decision", choices=["accept", "acceptForSession", "decline", "cancel"])
    broker_replay_parser.add_argument("--audit-dir", default="var/audit")

    broker_summarize_parser = subparsers.add_parser(
        "broker-summarize",
        help="Summarize broker audit streams under var/audit.",
    )
    broker_summarize_parser.add_argument("--audit-dir", default="var/audit")

    broker_service_parser = subparsers.add_parser(
        "broker-service",
        help="Run a long-lived App Server broker session with file-backed pending state.",
    )
    broker_service_parser.add_argument("--prompt", required=True)
    broker_service_parser.add_argument("--cwd", default=str(_repo_root()))
    broker_service_parser.add_argument("--approval-policy", default="unlessTrusted")
    broker_service_parser.add_argument("--sandbox-policy", default="workspaceWrite")
    broker_service_parser.add_argument("--timeout", type=float, default=300.0)
    broker_service_parser.add_argument("--poll-interval", type=float, default=0.5)
    broker_service_parser.add_argument("--runtime-dir", default="var/run")
    broker_service_parser.add_argument("--audit-dir", default="var/audit")
    broker_service_parser.add_argument("--imessage-handle")
    broker_service_parser.add_argument("--imessage-poll-limit", type=int, default=10)
    broker_service_parser.add_argument("--imessage-db-path")

    broker_pending_parser = subparsers.add_parser(
        "broker-pending",
        help="Read the file-backed broker runtime state and print pending approvals.",
    )
    broker_pending_parser.add_argument("--runtime-dir", default="var/run")

    broker_shortcut_payload_parser = subparsers.add_parser(
        "broker-shortcut-payload",
        help="Build a Shortcut-ready payload for a pending approval.",
    )
    broker_shortcut_payload_parser.add_argument("--runtime-dir", default="var/run")
    broker_shortcut_payload_parser.add_argument("--request-id")
    broker_shortcut_payload_parser.add_argument("--all", action="store_true")

    broker_respond_parser = subparsers.add_parser(
        "broker-respond",
        help="Queue an approval decision for a running broker service.",
    )
    broker_respond_parser.add_argument("--request-id", required=True)
    broker_respond_parser.add_argument("--decision", required=True, choices=["accept", "acceptForSession", "decline", "cancel"])
    broker_respond_parser.add_argument("--operator-note")
    broker_respond_parser.add_argument("--runtime-dir", default="var/run")

    broker_ssh_command_parser = subparsers.add_parser(
        "build-broker-response-ssh-command",
        help="Build the SSH command string for a Shortcut to return a broker decision.",
    )
    broker_ssh_command_parser.add_argument("--request-id", required=True)
    broker_ssh_command_parser.add_argument("--decision", required=True, choices=["accept", "acceptForSession", "decline", "cancel"])
    broker_ssh_command_parser.add_argument("--operator-note")
    broker_ssh_command_parser.add_argument("--runtime-dir")
    broker_ssh_command_parser.add_argument("--python-path", default="python3")

    imessage_send_parser = subparsers.add_parser("imessage-send", help="Send an iMessage via the Messages app.")
    imessage_send_parser.add_argument("--handle", required=True)
    imessage_send_parser.add_argument("--text", required=True)

    imessage_poll_parser = subparsers.add_parser("imessage-poll", help="Poll recent iMessages for a handle.")
    imessage_poll_parser.add_argument("--handle", required=True)
    imessage_poll_parser.add_argument("--limit", type=int, default=10)
    imessage_poll_parser.add_argument("--db-path")

    imessage_parse_parser = subparsers.add_parser("imessage-parse", help="Parse a message body into a broker response if possible.")
    imessage_parse_parser.add_argument("--text", required=True)

    args = parser.parse_args()

    if args.command == "discover":
        _json_print(discover_codex_environment().to_dict())
        return 0

    if args.command == "summarize-sentry":
        _json_print(summarize_scope_file(Path(args.path)))
        return 0

    if args.command == "build-payload":
        _json_print(build_approval_event(args.context, args.risk_level, args.action_id).to_dict())
        return 0

    if args.command == "validate-request":
        _json_print(build_actuation_request(args.decision, args.action_id).to_dict())
        return 0

    if args.command == "emit-synthetic-event":
        event = build_approval_event(args.context, args.risk_level, args.action_id)
        output_path = Path(args.output)
        append_jsonl(output_path, "synthetic_approval_event", event.to_dict())
        _json_print({"written_to": str(output_path), "event": event.to_dict()})
        return 0

    if args.command == "actuate-local":
        config_path = Path(args.selector_config) if args.selector_config else None
        image_output = Path(args.ocr_image_output) if args.ocr_image_output else None
        _json_print(
            run_local_actuation(
                args.decision,
                args.action_id,
                allow_live=args.allow_live,
                allow_visual=args.allow_visual,
                config_path=config_path,
                image_output=image_output,
            )
        )
        return 0

    if args.command == "shortcut-entry":
        config_path = Path(args.selector_config) if args.selector_config else None
        audit_path = Path(args.audit_path) if args.audit_path else None
        image_output = Path(args.ocr_image_output) if args.ocr_image_output else None
        _json_print(
            handle_shortcut_entry(
                args.decision,
                args.action_id,
                allow_live=args.allow_live,
                allow_visual=args.allow_visual,
                config_path=config_path,
                audit_path=audit_path,
                image_output=image_output,
            )
        )
        return 0

    if args.command == "build-ssh-command":
        config_path = Path(args.selector_config) if args.selector_config else None
        audit_path = Path(args.audit_path) if args.audit_path else None
        print(
            build_ssh_command(
                args.decision,
                args.action_id,
                allow_live=args.allow_live,
                allow_visual=args.allow_visual,
                selector_config=config_path,
                audit_path=audit_path,
                python_path=args.python_path,
            )
        )
        return 0

    if args.command == "run-shortcut":
        input_path = Path(args.input_path) if args.input_path else None
        output_path = Path(args.output_path) if args.output_path else None
        _json_print(
            run_shortcut(
                args.name,
                input_path=input_path,
                output_path=output_path,
                output_type=args.output_type,
            )
        )
        return 0

    if args.command == "probe-ui":
        parsed = parse_probe_output(run_probe())
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(parsed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            _json_print({"written_to": str(output_path), "probe": parsed})
            return 0
        _json_print(parsed)
        return 0

    if args.command == "enable-manual-accessibility":
        _json_print(
            enable_manual_accessibility(
                bundle_id=args.bundle_id,
                app_name=args.app_name,
                pid=args.pid,
                prompt_trust=args.prompt_trust,
            )
        )
        return 0

    if args.command == "dump-ax-tree":
        payload = dump_ax_tree(pid=args.pid, max_depth=args.max_depth, max_children=args.max_children)
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            _json_print({"written_to": str(output_path), "ax_tree": payload})
            return 0
        _json_print(payload)
        return 0

    if args.command == "capture-window-ocr":
        image_output = Path(args.image_output) if args.image_output else None
        payload = capture_codex_window_ocr(app_name=args.app_name, pid=args.pid, image_output=image_output)
        if args.target_text:
            payload["matched_target"] = find_text_target(
                payload,
                text_candidates=args.target_text,
                required_context_phrases=args.required_context,
            )
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            _json_print({"written_to": str(output_path), "ocr": payload})
            return 0
        _json_print(payload)
        return 0

    if args.command == "watch-sentry":
        run_watch(Path(args.path), Path(args.audit_path))
        return 0

    if args.command == "broker-replay":
        audit_paths = default_broker_audit_paths(Path(args.audit_dir))
        payload = replay_messages(
            load_jsonl_messages(Path(args.input)),
            auto_decision=args.auto_decision,
            audit_paths=audit_paths,
        )
        _json_print(payload)
        return 0

    if args.command == "broker-summarize":
        _json_print(summarize_broker_audit(default_broker_audit_paths(Path(args.audit_dir))))
        return 0

    if args.command == "bridge-create-pairing":
        bridge_paths = default_bridge_paths(base_dir=Path(args.bridge_dir), audit_dir=Path(args.audit_dir))
        device_state = load_or_create_bridge_device_state(bridge_paths.device_state_path)
        transport = BridgeSecureTransport(
            session_id=str(uuid.uuid4()),
            relay_url=args.relay_url.rstrip("/"),
            device_state=device_state,
        )
        payload = transport.create_pairing_payload()
        bridge_paths.pairing_payload_path.parent.mkdir(parents=True, exist_ok=True)
        bridge_paths.pairing_payload_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        write_pairing_qr_stub(bridge_paths.pairing_qr_path, payload)
        _json_print(
            {
                "status": "ok",
                "payload": payload,
                "pairing_uri": pairing_uri(payload),
                "payload_path": str(bridge_paths.pairing_payload_path),
                "qr_path": str(bridge_paths.pairing_qr_path),
            }
        )
        return 0

    if args.command == "bridge-state":
        bridge_paths = default_bridge_paths(base_dir=Path(args.bridge_dir), audit_dir=Path(args.audit_dir))
        _json_print(json.loads(bridge_paths.runtime_state_path.read_text(encoding="utf-8")))
        return 0

    if args.command == "bridge-service":
        timeout = args.timeout if args.timeout > 0 else None
        bridge_paths = default_bridge_paths(base_dir=Path(args.bridge_dir), audit_dir=Path(args.audit_dir))
        _json_print(
            run_bridge_service(
                relay_url=args.relay_url,
                bridge_paths=bridge_paths,
                cwd=Path(args.cwd),
                prompt=args.prompt,
                approval_policy=args.approval_policy,
                sandbox_policy=args.sandbox_policy,
                timeout=timeout,
                poll_interval=args.poll_interval,
            )
        )
        return 0

    if args.command == "broker-pending":
        runtime_paths = default_broker_runtime_paths(runtime_dir=Path(args.runtime_dir))
        _json_print(read_runtime_state(runtime_paths.state_path))
        return 0

    if args.command == "broker-shortcut-payload":
        runtime_paths = default_broker_runtime_paths(runtime_dir=Path(args.runtime_dir))
        state_payload = read_runtime_state(runtime_paths.state_path)
        pending = state_payload.get("pending_approvals", [])
        if not isinstance(pending, list):
            raise ValueError("pending_approvals must be a list in runtime state.")

        if args.request_id:
            selected = [
                approval for approval in pending
                if isinstance(approval, dict) and approval.get("request_id") == args.request_id
            ]
        elif args.all:
            selected = [approval for approval in pending if isinstance(approval, dict)]
        else:
            selected = [pending[0]] if pending else []

        def to_shortcut_payload(approval: dict[str, object]) -> dict[str, object]:
            from .models import ApprovalKind, BrokerApprovalRequest, BrokerDecision

            return build_shortcut_approval_payload(
                BrokerApprovalRequest(
                    request_id=str(approval["request_id"]),
                    thread_id=str(approval["thread_id"]),
                    turn_id=str(approval["turn_id"]),
                    item_id=str(approval["item_id"]),
                    kind=ApprovalKind(str(approval["kind"])),
                    summary=str(approval["summary"]),
                    available_decisions=[BrokerDecision(value) for value in approval["available_decisions"]],
                    timestamp=str(approval["timestamp"]),
                    wire_request_id=str(approval["request_id"]),
                )
            )

        payload = [to_shortcut_payload(approval) for approval in selected]
        _json_print(
            {
                "status": "ok",
                "count": len(payload),
                "payload": payload if args.all else (payload[0] if payload else None),
            }
        )
        return 0

    if args.command == "broker-respond":
        runtime_paths = default_broker_runtime_paths(runtime_dir=Path(args.runtime_dir))
        _json_print(
            enqueue_broker_response(
                request_id=args.request_id,
                decision=args.decision,
                operator_note=args.operator_note,
                runtime_paths=runtime_paths,
            )
        )
        return 0

    if args.command == "build-broker-response-ssh-command":
        runtime_dir = Path(args.runtime_dir) if args.runtime_dir else None
        print(
            build_broker_response_ssh_command(
                args.request_id,
                args.decision,
                operator_note=args.operator_note,
                runtime_dir=runtime_dir,
                python_path=args.python_path,
            )
        )
        return 0

    if args.command == "imessage-send":
        _json_print(send_imessage(args.handle, args.text))
        return 0

    if args.command == "imessage-poll":
        db_path = Path(args.db_path) if args.db_path else None
        _json_print(poll_imessages(args.handle, limit=args.limit, db_path=db_path))
        return 0

    if args.command == "imessage-parse":
        _json_print({"parsed": parse_response_message(args.text)})
        return 0

    if args.command == "broker-service":
        timeout = args.timeout if args.timeout > 0 else None
        runtime_paths = default_broker_runtime_paths(
            runtime_dir=Path(args.runtime_dir),
            audit_dir=Path(args.audit_dir),
        )
        _json_print(
            run_broker_service(
                prompt=args.prompt,
                cwd=Path(args.cwd),
                runtime_paths=runtime_paths,
                approval_policy=args.approval_policy,
                sandbox_policy=args.sandbox_policy,
                timeout=timeout,
                poll_interval=args.poll_interval,
                imessage_handle=args.imessage_handle,
                imessage_poll_limit=args.imessage_poll_limit,
                imessage_db_path=Path(args.imessage_db_path) if args.imessage_db_path else None,
            )
        )
        return 0

    if args.command == "broker-demo":
        audit_paths = default_broker_audit_paths(Path(args.audit_dir))

        def log_message(direction: str, message: dict[str, object]) -> None:
            audit_raw_message(audit_paths.raw_messages, direction=direction, message=message)

        events: list[dict[str, object]] = []
        with AppServerClient(cwd=Path(args.cwd), message_logger=log_message) as client:
            initialize_result = client.initialize()
            client.mark_initialized()

            thread_result = client.start_thread(
                cwd=Path(args.cwd),
                approval_policy=args.approval_policy,
                sandbox=args.sandbox_policy,
            )
            thread = thread_result.get("thread", {})
            thread_id = thread.get("id")
            if not isinstance(thread_id, str) or not thread_id:
                raise RuntimeError(f"thread/start did not return a thread id: {thread_result!r}")

            turn_result = client.start_turn(
                thread_id=thread_id,
                prompt=args.prompt,
                cwd=Path(args.cwd),
                approval_policy=args.approval_policy,
                sandbox_policy=args.sandbox_policy,
            )
            turn = turn_result.get("turn", {})
            turn_id = turn.get("id")

            state = BrokerState()
            approval_required = False
            saw_turn_completed = False
            deadline = time.monotonic() + args.timeout

            while time.monotonic() < deadline:
                remaining = max(0.1, deadline - time.monotonic())
                message = client.read_message(timeout=min(0.5, remaining))
                if message is None:
                    if saw_turn_completed:
                        break
                    continue

                emitted = state.handle_message(message)
                if emitted:
                    events.extend(emitted)
                    record_events(emitted, audit_paths=audit_paths)

                approval_events = [event for event in emitted if event.get("event") == "approval_request"]
                if approval_events:
                    approval_required = True
                    if args.auto_decision:
                        for event in approval_events:
                            pending = state.pending_request(event["approval"]["request_id"])
                            response = state.send_decision(event["approval"]["request_id"], args.auto_decision)
                            client.send_response(
                                pending.request.wire_request_id,
                                {"decision": response.decision.value},
                            )
                            decision_event = record_decision_event(response=response, pending=pending)
                            events.append(decision_event)
                            record_events([decision_event], audit_paths=audit_paths)
                    else:
                        break

                if any(event.get("event") == "turn_completed" for event in emitted):
                    saw_turn_completed = True
                    if not approval_required:
                        break

        status = "ok"
        if approval_required and not args.auto_decision and state.unresolved_request_ids():
            status = "approval_pending"
        elif not saw_turn_completed:
            status = "timeout"

        _json_print(
            {
                "status": status,
                "initialize_result": initialize_result,
                "thread_id": thread_id,
                "turn_id": turn_id,
                "approval_required": approval_required,
                "turn_completed": saw_turn_completed,
                "events": events,
                "pending_request_ids": state.unresolved_request_ids(),
            }
        )
        return 0

    parser.error("Unknown command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
