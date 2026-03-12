import json
import tempfile
import unittest
from pathlib import Path

from cra.broker import (
    BrokerState,
    default_broker_audit_paths,
    normalize_approval_request,
    replay_messages,
    summarize_broker_audit,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class BrokerTests(unittest.TestCase):
    def test_normalize_command_approval_request_uses_reason_and_decisions(self) -> None:
        message = {
            "id": 42,
            "method": "item/commandExecution/requestApproval",
            "params": {
                "threadId": "thread-1",
                "turnId": "turn-1",
                "itemId": "cmd-1",
                "command": "rm -rf /tmp/demo",
                "cwd": "/repo",
                "reason": "Need approval to remove generated files",
                "availableDecisions": ["accept", "decline", "cancel", "accept"],
            },
        }

        approval = normalize_approval_request(message)
        self.assertEqual(approval.request_id, "42")
        self.assertEqual(approval.summary, "Need approval to remove generated files")
        self.assertEqual(
            [decision.value for decision in approval.available_decisions],
            ["accept", "decline", "cancel"],
        )

    def test_normalize_command_approval_request_includes_network_context(self) -> None:
        message = {
            "id": "req-2",
            "method": "item/commandExecution/requestApproval",
            "params": {
                "threadId": "thread-1",
                "turnId": "turn-1",
                "itemId": "cmd-2",
                "command": "curl https://api.example.com/data",
                "cwd": "/repo",
                "networkApprovalContext": {"host": "api.example.com", "protocol": "https"},
            },
        }

        approval = normalize_approval_request(message)
        self.assertIn("Network approval for https api.example.com", approval.summary)
        self.assertIn("Run command", approval.summary)

    def test_normalize_file_change_approval_request_uses_item_snapshot(self) -> None:
        message = {
            "id": "req-3",
            "method": "item/fileChange/requestApproval",
            "params": {
                "threadId": "thread-2",
                "turnId": "turn-2",
                "itemId": "file-1",
                "grantRoot": "/repo",
            },
        }
        item_snapshot = {
            "id": "file-1",
            "type": "fileChange",
            "status": "inProgress",
            "changes": [
                {"kind": "update", "path": "README.md", "diff": "@@ -1 +1 @@"},
                {"kind": "update", "path": "cra/broker.py", "diff": "@@ -1 +1 @@"},
            ],
        }

        approval = normalize_approval_request(message, item_snapshot=item_snapshot)
        self.assertEqual(approval.kind.value, "file_change")
        self.assertIn("README.md", approval.summary)
        self.assertIn("/repo", approval.summary)
        self.assertEqual(
            [decision.value for decision in approval.available_decisions],
            ["accept", "acceptForSession", "decline", "cancel"],
        )

    def test_send_decision_rejects_stale_request_after_resolve(self) -> None:
        state = BrokerState()
        state.handle_message(
            {
                "id": 9,
                "method": "item/commandExecution/requestApproval",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "itemId": "cmd-1",
                    "command": "git status",
                    "cwd": "/repo",
                },
            }
        )
        state.handle_message(
            {
                "method": "serverRequest/resolved",
                "params": {"requestId": 9, "threadId": "thread-1"},
            }
        )

        with self.assertRaisesRegex(ValueError, "not pending"):
            state.send_decision("9", "decline")

    def test_item_completed_clears_pending_request(self) -> None:
        state = BrokerState()
        state.handle_message(
            {
                "id": "req-4",
                "method": "item/fileChange/requestApproval",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "itemId": "file-1",
                    "grantRoot": "/repo",
                },
            }
        )

        events = state.handle_message(
            {
                "method": "item/completed",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "item": {
                        "id": "file-1",
                        "type": "fileChange",
                        "status": "declined",
                        "changes": [],
                    },
                },
            }
        )

        self.assertFalse(state.has_pending("req-4"))
        self.assertEqual(events[0]["reason"], "item_completed")

    def test_replay_messages_writes_decisions_and_summary(self) -> None:
        fixture = FIXTURES_DIR / "broker_file_change_flow.jsonl"
        messages = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines()]

        with tempfile.TemporaryDirectory() as temp_dir:
            audit_paths = default_broker_audit_paths(Path(temp_dir))
            replay = replay_messages(messages, auto_decision="decline", audit_paths=audit_paths)
            summary = summarize_broker_audit(audit_paths)

        self.assertEqual(replay["status"], "ok")
        self.assertEqual(summary["approvals_seen"], 1)
        self.assertEqual(summary["decisions_sent"], 1)
        self.assertEqual(summary["unresolved_request_ids"], [])


if __name__ == "__main__":
    unittest.main()
