import tempfile
import threading
import time
import unittest
from pathlib import Path

from cra.broker import BrokerState
from cra.broker_service import (
    build_runtime_state_payload,
    default_broker_runtime_paths,
    enqueue_broker_response,
    load_response_requests,
    read_runtime_state,
    run_broker_service,
    write_json_atomic,
)


class _FakeClient:
    def __init__(self, messages=None, **kwargs):
        self.messages = list(messages or [])
        self.responses = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def initialize(self):
        return {"userAgent": "fake-client"}

    def mark_initialized(self):
        return None

    def start_thread(self, **kwargs):
        return {"thread": {"id": "thread-1"}}

    def start_turn(self, **kwargs):
        return {"turn": {"id": "turn-1", "status": "inProgress"}}

    def read_message(self, timeout=None):
        if self.messages:
            return self.messages.pop(0)
        if timeout:
            time.sleep(min(timeout, 0.01))
        return None

    def send_response(self, request_id, result):
        self.responses.append({"id": request_id, "result": result})


class BrokerServiceTests(unittest.TestCase):
    def test_enqueue_broker_response_writes_queue_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_paths = default_broker_runtime_paths(runtime_dir=Path(temp_dir))
            state = BrokerState()
            state.handle_message(
                {
                    "id": "req-1",
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

            payload = enqueue_broker_response(
                request_id="req-1",
                decision="decline",
                runtime_paths=runtime_paths,
            )
            queued, _ = load_response_requests(runtime_paths.response_queue_path)

        self.assertEqual(payload["status"], "queued")
        self.assertEqual(queued[0]["request_id"], "req-1")
        self.assertEqual(queued[0]["decision"], "decline")

    def test_enqueue_broker_response_rejects_duplicate_or_unknown_request(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_paths = default_broker_runtime_paths(runtime_dir=Path(temp_dir))
            state = BrokerState()
            state.handle_message(
                {
                    "id": "req-2",
                    "method": "item/fileChange/requestApproval",
                    "params": {
                        "threadId": "thread-1",
                        "turnId": "turn-1",
                        "itemId": "file-1",
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

            enqueue_broker_response(request_id="req-2", decision="accept", runtime_paths=runtime_paths)

            with self.assertRaisesRegex(ValueError, "already has a queued decision"):
                enqueue_broker_response(request_id="req-2", decision="decline", runtime_paths=runtime_paths)

            with self.assertRaisesRegex(ValueError, "not currently pending"):
                enqueue_broker_response(request_id="missing", decision="decline", runtime_paths=runtime_paths)

    def test_run_broker_service_processes_queued_response(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runtime_paths = default_broker_runtime_paths(
                runtime_dir=Path(temp_dir) / "run",
                audit_dir=Path(temp_dir) / "audit",
            )
            approval_message = {
                "id": 101,
                "method": "item/commandExecution/requestApproval",
                "params": {
                    "threadId": "thread-1",
                    "turnId": "turn-1",
                    "itemId": "cmd-1",
                    "command": "curl https://example.com",
                    "cwd": "/repo",
                },
            }
            fake_client = _FakeClient(messages=[approval_message])

            result_holder = {}

            def target():
                result_holder["result"] = run_broker_service(
                    prompt="fetch example",
                    cwd=Path("/repo"),
                    runtime_paths=runtime_paths,
                    timeout=0.2,
                    poll_interval=0.01,
                    client_factory=lambda **kwargs: fake_client,
                )

            thread = threading.Thread(target=target)
            thread.start()

            deadline = time.time() + 1.0
            while time.time() < deadline:
                if runtime_paths.state_path.exists():
                    state_payload = read_runtime_state(runtime_paths.state_path)
                    if state_payload.get("pending_count") == 1:
                        break
                time.sleep(0.01)

            enqueue_broker_response(request_id="101", decision="decline", runtime_paths=runtime_paths)
            thread.join(timeout=2.0)

        self.assertFalse(thread.is_alive())
        self.assertEqual(fake_client.responses[0]["result"]["decision"], "decline")
        self.assertEqual(result_holder["result"]["status"], "timeout")


if __name__ == "__main__":
    unittest.main()
