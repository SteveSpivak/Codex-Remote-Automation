from __future__ import annotations

import argparse
import json
from pathlib import Path

from .ax_tree import dump_ax_tree
from .accessibility import enable_manual_accessibility
from .actuator import run_local_actuation
from .audit import append_jsonl
from .discovery import SENTRY_SCOPE_PATH, discover_codex_environment
from .shortcuts import build_ssh_command, handle_shortcut_entry, run_shortcut
from .ui_probe import parse_probe_output, run_probe
from .validation import build_actuation_request, build_approval_event
from .vision import capture_codex_window_ocr, find_text_target
from .watcher import run_watch, summarize_scope_file


def _json_print(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


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

    parser.error("Unknown command.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
