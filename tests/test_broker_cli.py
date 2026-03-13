import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cra.broker import BrokerState
from cra.broker_service import build_runtime_state_payload, default_broker_runtime_paths, write_json_atomic
from cra.cli import main


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "broker_command_flow.jsonl"


class BrokerCliTests(unittest.TestCase):
    def test_broker_replay_command_prints_normalized_events(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()
            argv = [
                "cra.cli",
                "broker-replay",
                "--input",
                str(FIXTURE_PATH),
                "--auto-decision",
                "decline",
                "--audit-dir",
                temp_dir,
            ]
            with patch("sys.argv", argv):
                with redirect_stdout(stdout):
                    exit_code = main()

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["events"])

    def test_broker_pending_and_respond_commands_use_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_paths = default_broker_runtime_paths(runtime_dir=Path(temp_dir))
            state = BrokerState()
            state.handle_message(
                {
                    "id": "req-9",
                    "method": "item/commandExecution/requestApproval",
                    "params": {
                        "threadId": "thread-1",
                        "turnId": "turn-1",
                        "itemId": "cmd-9",
                        "command": "git status",
                        "cwd": "/repo",
                    },
                }
            )
            write_json_atomic(
                runtime_paths.state_path,
                build_runtime_state_payload(
                    status="approval_pending",
                    state=state,
                    runtime_paths=runtime_paths,
                    approval_required=True,
                    turn_completed=False,
                    thread_id="thread-1",
                    turn_id="turn-1",
                ),
            )
            runtime_paths.response_queue_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_paths.response_queue_path.write_text("", encoding="utf-8")

            pending_stdout = io.StringIO()
            with patch("sys.argv", ["cra.cli", "broker-pending", "--runtime-dir", temp_dir]):
                with redirect_stdout(pending_stdout):
                    pending_exit_code = main()

            respond_stdout = io.StringIO()
            with patch(
                "sys.argv",
                ["cra.cli", "broker-respond", "--runtime-dir", temp_dir, "--request-id", "req-9", "--decision", "decline"],
            ):
                with redirect_stdout(respond_stdout):
                    respond_exit_code = main()

        pending_payload = json.loads(pending_stdout.getvalue())
        respond_payload = json.loads(respond_stdout.getvalue())
        self.assertEqual(pending_exit_code, 0)
        self.assertEqual(respond_exit_code, 0)
        self.assertEqual(pending_payload["pending_count"], 1)
        self.assertEqual(respond_payload["status"], "queued")

    def test_broker_shortcut_payload_and_operator_note_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_paths = default_broker_runtime_paths(runtime_dir=Path(temp_dir))
            state = BrokerState()
            state.handle_message(
                {
                    "id": "req-10",
                    "method": "item/fileChange/requestApproval",
                    "params": {
                        "threadId": "thread-1",
                        "turnId": "turn-1",
                        "itemId": "file-10",
                        "grantRoot": "/repo",
                    },
                }
            )
            write_json_atomic(
                runtime_paths.state_path,
                build_runtime_state_payload(
                    status="approval_pending",
                    state=state,
                    runtime_paths=runtime_paths,
                    approval_required=True,
                    turn_completed=False,
                    thread_id="thread-1",
                    turn_id="turn-1",
                ),
            )
            runtime_paths.response_queue_path.parent.mkdir(parents=True, exist_ok=True)
            runtime_paths.response_queue_path.write_text("", encoding="utf-8")

            shortcut_stdout = io.StringIO()
            with patch("sys.argv", ["cra.cli", "broker-shortcut-payload", "--runtime-dir", temp_dir]):
                with redirect_stdout(shortcut_stdout):
                    shortcut_exit_code = main()

            ssh_stdout = io.StringIO()
            with patch(
                "sys.argv",
                [
                    "cra.cli",
                    "build-broker-response-ssh-command",
                    "--request-id",
                    "req-10",
                    "--decision",
                    "decline",
                    "--operator-note",
                    "Need a human review first",
                    "--runtime-dir",
                    temp_dir,
                ],
            ):
                with redirect_stdout(ssh_stdout):
                    ssh_exit_code = main()

        shortcut_payload = json.loads(shortcut_stdout.getvalue())
        ssh_command = ssh_stdout.getvalue().strip()
        self.assertEqual(shortcut_exit_code, 0)
        self.assertEqual(ssh_exit_code, 0)
        self.assertEqual(shortcut_payload["payload"]["request_id"], "req-10")
        self.assertTrue(shortcut_payload["payload"]["operator_note_enabled"])
        self.assertIn("--operator-note", ssh_command)
        self.assertIn("Need a human review first", ssh_command)


if __name__ == "__main__":
    unittest.main()
