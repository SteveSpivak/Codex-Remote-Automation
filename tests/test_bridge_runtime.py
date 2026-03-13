import json
import unittest

from cra.bridge.runtime import BridgeRuntime


class BridgeRuntimeTests(unittest.TestCase):
    def test_warm_bridge_suppresses_duplicate_initialize(self) -> None:
        runtime = BridgeRuntime()
        runtime.codex_handshake_state = "warm"

        result = runtime.handle_phone_message(json.dumps({"id": "init-1", "method": "initialize"}))

        self.assertEqual(result["forward_to_codex"], [])
        self.assertEqual(result["phone_messages"][0]["result"]["bridgeManaged"], True)

    def test_cold_initialize_is_forwarded_and_warm_response_tracked(self) -> None:
        runtime = BridgeRuntime()
        result = runtime.handle_phone_message(json.dumps({"id": "init-2", "method": "initialize"}))
        self.assertEqual(result["forward_to_codex"][0]["id"], "init-2")

        result = runtime.handle_codex_message({"id": "init-2", "result": {"ok": True}})
        self.assertEqual(runtime.codex_handshake_state, "warm")
        self.assertEqual(result["phone_messages"], [])
        self.assertEqual(result["broker_events"], [])

    def test_codex_approval_updates_phone_snapshot(self) -> None:
        runtime = BridgeRuntime()
        result = runtime.handle_codex_message(
            {
                "id": "req-1",
                "method": "item/commandExecution/requestApproval",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "itemId": "cmd-1",
                    "command": "git push origin main",
                    "cwd": "/repo",
                },
            }
        )
        self.assertEqual(result["phone_messages"][0]["method"], "bridge/pendingApprovalsUpdated")
        self.assertEqual(result["phone_messages"][0]["params"]["pendingCount"], 1)
        self.assertEqual(result["broker_events"][0]["event"], "approval_request")

    def test_phone_decision_creates_codex_response_and_snapshot(self) -> None:
        runtime = BridgeRuntime()
        runtime.handle_codex_message(
            {
                "id": "req-2",
                "method": "item/commandExecution/requestApproval",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "itemId": "cmd-2",
                    "command": "rm -rf /tmp/demo",
                    "cwd": "/repo",
                },
            }
        )

        result = runtime.handle_phone_message(
            json.dumps(
                {
                    "id": "phone-1",
                    "method": "bridge/respondApproval",
                    "params": {
                        "requestId": "req-2",
                        "decision": "decline",
                        "operatorNote": "Need manual confirmation",
                    },
                }
            )
        )

        self.assertEqual(result["codex_responses"][0]["id"], "req-2")
        self.assertEqual(result["codex_responses"][0]["result"]["decision"], "decline")
        self.assertEqual(result["phone_messages"][0]["result"]["accepted"], True)
        self.assertEqual(result["phone_messages"][1]["params"]["pendingCount"], 0)
        self.assertEqual(result["broker_events"][0]["event"], "decision_sent")

    def test_stale_phone_decision_is_rejected(self) -> None:
        runtime = BridgeRuntime()
        result = runtime.handle_phone_message(
            json.dumps(
                {
                    "id": "phone-2",
                    "method": "bridge/respondApproval",
                    "params": {"requestId": "missing", "decision": "decline"},
                }
            )
        )
        self.assertIn("not pending", result["phone_messages"][0]["error"]["message"])


if __name__ == "__main__":
    unittest.main()
