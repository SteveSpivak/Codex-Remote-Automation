from __future__ import annotations

import json
import select
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Dict

JSONDict = Dict[str, Any]
MessageLogger = Callable[[str, JSONDict], None]

THREAD_APPROVAL_POLICY_ALIASES = {
    "unlessTrusted": "untrusted",
    "untrusted": "untrusted",
    "on-failure": "on-failure",
    "onFailure": "on-failure",
    "on-request": "on-request",
    "onRequest": "on-request",
    "never": "never",
}

THREAD_SANDBOX_ALIASES = {
    "workspaceWrite": "workspace-write",
    "workspace-write": "workspace-write",
    "readOnly": "read-only",
    "read-only": "read-only",
    "dangerFullAccess": "danger-full-access",
    "danger-full-access": "danger-full-access",
}

TURN_SANDBOX_POLICY_ALIASES = {
    "workspaceWrite": {"type": "workspaceWrite"},
    "workspace-write": {"type": "workspaceWrite"},
    "readOnly": {"type": "readOnly"},
    "read-only": {"type": "readOnly"},
    "dangerFullAccess": {"type": "dangerFullAccess"},
    "danger-full-access": {"type": "dangerFullAccess"},
}


class AppServerError(RuntimeError):
    """Raised when the App Server transport or protocol fails."""


class AppServerTimeoutError(TimeoutError):
    """Raised when the App Server fails to reply within the timeout."""


class AppServerClient:
    def __init__(
        self,
        *,
        cwd: Path,
        command: list[str] | None = None,
        message_logger: MessageLogger | None = None,
    ) -> None:
        self.cwd = Path(cwd)
        self.command = command or ["codex", "app-server", "--listen", "stdio://"]
        self.message_logger = message_logger
        self._process: subprocess.Popen[str] | None = None
        self._buffered_messages: list[JSONDict] = []
        self._next_request_id = 1

    def start(self) -> "AppServerClient":
        if self._process is not None:
            return self
        self._process = subprocess.Popen(
            self.command,
            cwd=str(self.cwd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        return self

    def close(self) -> None:
        if self._process is None:
            return
        if self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)
        self._process = None
        self._buffered_messages.clear()

    def __enter__(self) -> "AppServerClient":
        return self.start()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _ensure_running(self) -> subprocess.Popen[str]:
        if self._process is None:
            raise AppServerError("App Server process has not been started.")
        return self._process

    def _log_message(self, direction: str, message: JSONDict) -> None:
        if self.message_logger is not None:
            self.message_logger(direction, message)

    def _send_message(self, message: JSONDict) -> None:
        process = self._ensure_running()
        if process.stdin is None:
            raise AppServerError("App Server stdin is unavailable.")
        process.stdin.write(json.dumps(message, sort_keys=True) + "\n")
        process.stdin.flush()
        self._log_message("outbound", message)

    def _read_line(self, timeout: float | None) -> str | None:
        process = self._ensure_running()
        if process.stdout is None:
            raise AppServerError("App Server stdout is unavailable.")

        while True:
            if timeout is None:
                ready = [process.stdout]
            else:
                ready, _, _ = select.select([process.stdout], [], [], timeout)
            if not ready:
                return None

            line = process.stdout.readline()
            if line:
                return line
            if process.poll() is not None:
                return None

    def _read_message_internal(self, timeout: float | None) -> JSONDict | None:
        line = self._read_line(timeout)
        if line is None:
            return None
        payload = json.loads(line)
        if not isinstance(payload, dict):
            raise AppServerError(f"Unexpected App Server payload: {payload!r}")
        self._log_message("inbound", payload)
        return payload

    def read_message(self, timeout: float | None = None) -> JSONDict | None:
        if self._buffered_messages:
            return self._buffered_messages.pop(0)
        return self._read_message_internal(timeout)

    def send_request(self, method: str, params: JSONDict | None = None) -> int:
        request_id = self._next_request_id
        self._next_request_id += 1
        payload: JSONDict = {"id": request_id, "method": method}
        if params is not None:
            payload["params"] = params
        self._send_message(payload)
        return request_id

    def send_notification(self, method: str, params: JSONDict | None = None) -> None:
        payload: JSONDict = {"method": method}
        if params is not None:
            payload["params"] = params
        self._send_message(payload)

    def send_response(self, request_id: str | int, result: JSONDict) -> None:
        self._send_message({"id": request_id, "result": result})

    def wait_for_response(self, request_id: str | int, timeout: float = 15.0) -> JSONDict:
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise AppServerTimeoutError(f"Timed out waiting for response to request {request_id!r}.")

            message = self._read_message_internal(remaining)
            if message is None:
                raise AppServerTimeoutError(f"Timed out waiting for response to request {request_id!r}.")

            if message.get("id") == request_id and "method" not in message:
                if "error" in message:
                    raise AppServerError(f"App Server returned an error for request {request_id!r}: {message['error']!r}")
                return message

            self._buffered_messages.append(message)

    def request(self, method: str, params: JSONDict | None = None, *, timeout: float = 15.0) -> Any:
        request_id = self.send_request(method, params=params)
        return self.wait_for_response(request_id, timeout=timeout).get("result")

    def initialize(
        self,
        *,
        client_name: str = "cra-broker",
        client_version: str = "0.1.0",
        experimental_api: bool = True,
        opt_out_notification_methods: list[str] | None = None,
        timeout: float = 15.0,
    ) -> Any:
        params: JSONDict = {
            "clientInfo": {
                "name": client_name,
                "version": client_version,
            }
        }
        capabilities: JSONDict = {"experimentalApi": experimental_api}
        if opt_out_notification_methods:
            capabilities["optOutNotificationMethods"] = opt_out_notification_methods
        params["capabilities"] = capabilities
        return self.request("initialize", params=params, timeout=timeout)

    def mark_initialized(self) -> None:
        self.send_notification("initialized")

    def start_thread(
        self,
        *,
        cwd: Path,
        approval_policy: str = "unlessTrusted",
        sandbox: str = "workspaceWrite",
        timeout: float = 30.0,
    ) -> Any:
        approval_value = THREAD_APPROVAL_POLICY_ALIASES.get(approval_policy, approval_policy)
        sandbox_value = THREAD_SANDBOX_ALIASES.get(sandbox, sandbox)
        params: JSONDict = {
            "approvalPolicy": approval_value,
            "cwd": str(cwd),
            "personality": "pragmatic",
            "sandbox": sandbox_value,
        }
        return self.request("thread/start", params=params, timeout=timeout)

    def start_turn(
        self,
        *,
        thread_id: str,
        prompt: str,
        cwd: Path,
        approval_policy: str = "unlessTrusted",
        sandbox_policy: str = "workspaceWrite",
        timeout: float = 30.0,
    ) -> Any:
        approval_value = THREAD_APPROVAL_POLICY_ALIASES.get(approval_policy, approval_policy)
        sandbox_value = TURN_SANDBOX_POLICY_ALIASES.get(sandbox_policy, {"type": sandbox_policy})
        params: JSONDict = {
            "approvalPolicy": approval_value,
            "cwd": str(cwd),
            "input": [{"type": "text", "text": prompt}],
            "sandboxPolicy": sandbox_value,
            "threadId": thread_id,
        }
        return self.request("turn/start", params=params, timeout=timeout)
