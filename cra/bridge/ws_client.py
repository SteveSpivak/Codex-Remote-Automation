from __future__ import annotations

import base64
import hashlib
import os
import select
import socket
import ssl
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse


@dataclass
class WebSocketURL:
    host: str
    port: int
    path: str
    secure: bool


def _parse_url(url: str) -> WebSocketURL:
    parsed = urlparse(url)
    if parsed.scheme not in {"ws", "wss"}:
        raise ValueError("Relay URL must start with ws:// or wss://")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("Relay URL must include a hostname.")
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    return WebSocketURL(host=host, port=port, path=path, secure=parsed.scheme == "wss")


class WebSocketClient:
    def __init__(self, url: str, timeout: float = 5.0) -> None:
        self.url = _parse_url(url)
        self.timeout = timeout
        self._socket: socket.socket | None = None

    def connect(self) -> "WebSocketClient":
        raw = socket.create_connection((self.url.host, self.url.port), timeout=self.timeout)
        if self.url.secure:
            context = ssl.create_default_context()
            raw = context.wrap_socket(raw, server_hostname=self.url.host)

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.url.path} HTTP/1.1\r\n"
            f"Host: {self.url.host}:{self.url.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        )
        raw.sendall(request.encode("utf-8"))
        response = self._recv_http_response(raw)
        if " 101 " not in response.split("\r\n", 1)[0]:
            raise RuntimeError(f"Relay rejected WebSocket upgrade: {response.splitlines()[0]}")
        expected = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("utf-8")).digest()
        ).decode("ascii")
        if f"Sec-WebSocket-Accept: {expected}" not in response:
            raise RuntimeError("Relay returned an invalid WebSocket accept header.")
        self._socket = raw
        return self

    def close(self) -> None:
        if self._socket is None:
            return
        try:
            self._socket.close()
        finally:
            self._socket = None

    def __enter__(self) -> "WebSocketClient":
        return self.connect()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def send_text(self, payload: str) -> None:
        if self._socket is None:
            raise RuntimeError("WebSocket client is not connected.")
        body = payload.encode("utf-8")
        frame = bytearray()
        frame.append(0x81)
        mask = os.urandom(4)
        frame.extend(self._encode_length(len(body), masked=True))
        frame.extend(mask)
        frame.extend(bytes(byte ^ mask[index % 4] for index, byte in enumerate(body)))
        self._socket.sendall(frame)

    def recv_text(self, timeout: float = 0.1) -> Optional[str]:
        if self._socket is None:
            raise RuntimeError("WebSocket client is not connected.")

        ready, _, _ = select.select([self._socket], [], [], timeout)
        if not ready:
            return None

        first = self._recv_exact(2)
        fin_opcode = first[0]
        opcode = fin_opcode & 0x0F
        masked = bool(first[1] & 0x80)
        length = first[1] & 0x7F
        if length == 126:
            length = int.from_bytes(self._recv_exact(2), "big")
        elif length == 127:
            length = int.from_bytes(self._recv_exact(8), "big")
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length) if length else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))

        if opcode == 0x8:
            self.close()
            return None
        if opcode == 0x9:
            self._send_control(0xA, payload)
            return None
        if opcode != 0x1:
            return None
        return payload.decode("utf-8")

    def _send_control(self, opcode: int, payload: bytes) -> None:
        if self._socket is None:
            return
        frame = bytearray([0x80 | opcode])
        frame.extend(self._encode_length(len(payload), masked=True))
        mask = os.urandom(4)
        frame.extend(mask)
        frame.extend(bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload)))
        self._socket.sendall(frame)

    def _recv_exact(self, size: int) -> bytes:
        if self._socket is None:
            raise RuntimeError("WebSocket client is not connected.")
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self._socket.recv(size - len(chunks))
            if not chunk:
                raise RuntimeError("Relay closed the WebSocket connection.")
            chunks.extend(chunk)
        return bytes(chunks)

    def _recv_http_response(self, raw: socket.socket) -> str:
        chunks = bytearray()
        while b"\r\n\r\n" not in chunks:
            chunk = raw.recv(4096)
            if not chunk:
                break
            chunks.extend(chunk)
        return chunks.decode("utf-8")

    def _encode_length(self, size: int, *, masked: bool) -> bytes:
        mask_flag = 0x80 if masked else 0
        if size < 126:
            return bytes([mask_flag | size])
        if size < (1 << 16):
            return bytes([mask_flag | 126]) + size.to_bytes(2, "big")
        return bytes([mask_flag | 127]) + size.to_bytes(8, "big")
