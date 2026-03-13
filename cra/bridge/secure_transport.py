from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Callable

from .crypto import (
    base64_encode,
    compute_tag,
    decrypt_text,
    derive_secret,
    encrypt_text,
    json_dumps_compact,
    random_secret,
)
from .device_state import get_trusted_phone, remember_trusted_phone

PAIRING_QR_VERSION = 1
SECURE_PROTOCOL_VERSION = 1
HANDSHAKE_MODE_QR_BOOTSTRAP = "qr_bootstrap"
HANDSHAKE_MODE_TRUSTED_RECONNECT = "trusted_reconnect"
SECURE_SENDER_MAC = "mac"
SECURE_SENDER_IPHONE = "iphone"
MAX_PAIRING_AGE_MS = 5 * 60 * 1000
MAX_BRIDGE_OUTBOUND_MESSAGES = 500
MAX_BRIDGE_OUTBOUND_BYTES = 10 * 1024 * 1024


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class PendingHandshake:
    session_id: str
    handshake_mode: str
    phone_device_id: str
    phone_label: str | None
    base_secret: str
    client_nonce: str
    server_nonce: str
    key_epoch: int


@dataclass
class ActiveSession:
    session_id: str
    phone_device_id: str
    session_secret: str
    key_epoch: int
    next_outbound_counter: int = 1
    last_inbound_counter: int = 0
    is_resumed: bool = False
    send_wire_message: Callable[[str], None] | None = None


class BridgeSecureTransport:
    def __init__(
        self,
        *,
        session_id: str,
        relay_url: str,
        device_state: dict[str, Any],
    ) -> None:
        self.session_id = session_id
        self.relay_url = relay_url
        self.device_state = device_state
        self.pending_pairing: dict[str, Any] | None = None
        self.pending_handshake: PendingHandshake | None = None
        self.active_session: ActiveSession | None = None
        self.live_send_wire_message: Callable[[str], None] | None = None
        self.next_key_epoch = 1
        self.next_bridge_outbound_seq = 1
        self.outbound_buffer: list[dict[str, Any]] = []
        self.outbound_buffer_bytes = 0

    def create_pairing_payload(self) -> dict[str, Any]:
        pairing_secret = random_secret()
        expires_at = _now_ms() + MAX_PAIRING_AGE_MS
        self.pending_pairing = {
            "pairing_secret": pairing_secret,
            "expires_at": expires_at,
        }
        return {
            "v": PAIRING_QR_VERSION,
            "protocolVersion": SECURE_PROTOCOL_VERSION,
            "relayUrl": self.relay_url,
            "sessionId": self.session_id,
            "bridgeDeviceId": self.device_state["bridge_device_id"],
            "pairingSecret": pairing_secret,
            "expiresAt": expires_at,
        }

    def bind_live_send_wire_message(self, callback: Callable[[str], None]) -> None:
        self.live_send_wire_message = callback
        if self.active_session is not None:
            self.active_session.send_wire_message = callback

    def is_secure_channel_ready(self) -> bool:
        return bool(self.active_session and self.active_session.is_resumed)

    def queue_outbound_application_message(
        self,
        payload_text: str,
        send_wire_message: Callable[[str], None] | None = None,
    ) -> None:
        normalized = payload_text.strip()
        if not normalized:
            return
        entry = {
            "bridgeOutboundSeq": self.next_bridge_outbound_seq,
            "payloadText": normalized,
            "sizeBytes": len(normalized.encode("utf-8")),
        }
        self.next_bridge_outbound_seq += 1
        self.outbound_buffer.append(entry)
        self.outbound_buffer_bytes += entry["sizeBytes"]
        self._trim_outbound_buffer()

        sender = send_wire_message or self.live_send_wire_message
        if self.active_session and self.active_session.is_resumed and sender is not None:
            self._send_buffered_entry(entry, sender)

    def handle_incoming_wire_message(
        self,
        raw_message: str,
        *,
        send_control_message: Callable[[dict[str, Any]], None],
        on_application_message: Callable[[str], None],
    ) -> bool:
        try:
            parsed = json.loads(raw_message)
        except json.JSONDecodeError:
            return False

        if not isinstance(parsed, dict):
            return False

        kind = str(parsed.get("kind") or "").strip()
        if not kind:
            return False

        if kind == "clientHello":
            self._handle_client_hello(parsed, send_control_message)
            return True
        if kind == "clientAuth":
            self._handle_client_auth(parsed, send_control_message)
            return True
        if kind == "resumeState":
            self._handle_resume_state(parsed)
            return True
        if kind == "encryptedEnvelope":
            return self._handle_encrypted_envelope(parsed, send_control_message, on_application_message)
        return False

    def _handle_client_hello(self, message: dict[str, Any], send_control_message: Callable[[dict[str, Any]], None]) -> None:
        protocol_version = int(message.get("protocolVersion") or 0)
        session_id = str(message.get("sessionId") or "")
        handshake_mode = str(message.get("handshakeMode") or "")
        phone_device_id = str(message.get("phoneDeviceId") or "")
        phone_label = message.get("phoneLabel")
        client_nonce = str(message.get("clientNonce") or "")
        client_proof = str(message.get("clientProof") or "")

        if protocol_version != SECURE_PROTOCOL_VERSION or session_id != self.session_id:
            send_control_message(self._error("update_required", "Bridge and client protocol versions do not match."))
            return
        if not phone_device_id or not client_nonce or not client_proof:
            send_control_message(self._error("invalid_client_hello", "Handshake is missing required fields."))
            return
        if handshake_mode == HANDSHAKE_MODE_QR_BOOTSTRAP:
            if not self.pending_pairing or _now_ms() > int(self.pending_pairing["expires_at"]):
                send_control_message(self._error("pairing_expired", "The pairing code has expired."))
                return
            base_secret = str(self.pending_pairing["pairing_secret"])
        elif handshake_mode == HANDSHAKE_MODE_TRUSTED_RECONNECT:
            trusted_phone = get_trusted_phone(self.device_state, phone_device_id)
            if trusted_phone is None:
                send_control_message(self._error("phone_not_trusted", "This phone is not trusted for reconnect."))
                return
            base_secret = str(trusted_phone["shared_secret"])
        else:
            send_control_message(self._error("invalid_handshake_mode", "Unknown handshake mode."))
            return

        expected_proof = compute_tag(
            base_secret,
            self._handshake_aad(session_id, handshake_mode, phone_device_id, client_nonce),
            b"",
        )
        if expected_proof != client_proof:
            send_control_message(self._error("invalid_client_proof", "The phone failed bridge authentication."))
            return

        key_epoch = self.next_key_epoch
        server_nonce = random_secret()
        self.pending_handshake = PendingHandshake(
            session_id=session_id,
            handshake_mode=handshake_mode,
            phone_device_id=phone_device_id,
            phone_label=phone_label if isinstance(phone_label, str) else None,
            base_secret=base_secret,
            client_nonce=client_nonce,
            server_nonce=server_nonce,
            key_epoch=key_epoch,
        )
        send_control_message(
            {
                "kind": "serverHello",
                "protocolVersion": SECURE_PROTOCOL_VERSION,
                "sessionId": session_id,
                "handshakeMode": handshake_mode,
                "bridgeDeviceId": self.device_state["bridge_device_id"],
                "serverNonce": server_nonce,
                "keyEpoch": key_epoch,
                "bridgeProof": compute_tag(
                    base_secret,
                    self._auth_aad(session_id, phone_device_id, client_nonce, server_nonce, key_epoch),
                    b"",
                ),
            }
        )

    def _handle_client_auth(self, message: dict[str, Any], send_control_message: Callable[[dict[str, Any]], None]) -> None:
        pending = self.pending_handshake
        if pending is None:
            send_control_message(self._error("unexpected_client_auth", "No handshake is waiting for client auth."))
            return

        session_id = str(message.get("sessionId") or "")
        phone_device_id = str(message.get("phoneDeviceId") or "")
        key_epoch = int(message.get("keyEpoch") or 0)
        client_auth = str(message.get("clientAuth") or "")
        if session_id != pending.session_id or phone_device_id != pending.phone_device_id or key_epoch != pending.key_epoch:
            send_control_message(self._error("invalid_client_auth", "Handshake identifiers do not match."))
            return

        expected_auth = compute_tag(
            pending.base_secret,
            self._auth_aad(session_id, phone_device_id, pending.client_nonce, pending.server_nonce, key_epoch),
            b"clientAuth",
        )
        if client_auth != expected_auth:
            send_control_message(self._error("invalid_client_auth", "The phone failed final authentication."))
            return

        if pending.handshake_mode == HANDSHAKE_MODE_QR_BOOTSTRAP:
            trusted_secret = derive_secret(
                pending.base_secret,
                "trusted-phone",
                self.device_state["bridge_device_id"],
                phone_device_id,
            )
            remember_trusted_phone(
                self.device_state,
                phone_device_id=phone_device_id,
                shared_secret=trusted_secret,
                phone_label=pending.phone_label,
            )
            base_secret = trusted_secret
            self.pending_pairing = None
        else:
            base_secret = pending.base_secret
            trusted_phone = get_trusted_phone(self.device_state, phone_device_id)
            if trusted_phone is not None:
                trusted_phone["last_seen_at"] = str(int(time.time()))

        session_secret = derive_secret(
            base_secret,
            "session",
            session_id,
            phone_device_id,
            pending.client_nonce,
            pending.server_nonce,
            pending.key_epoch,
        )
        self.active_session = ActiveSession(
            session_id=session_id,
            phone_device_id=phone_device_id,
            session_secret=session_secret,
            key_epoch=pending.key_epoch,
            send_wire_message=self.live_send_wire_message,
        )
        self.pending_handshake = None
        self.next_key_epoch += 1

        send_control_message(
            {
                "kind": "secureReady",
                "sessionId": session_id,
                "keyEpoch": self.active_session.key_epoch,
                "bridgeDeviceId": self.device_state["bridge_device_id"],
            }
        )

    def _handle_resume_state(self, message: dict[str, Any]) -> None:
        if self.active_session is None:
            return
        session_id = str(message.get("sessionId") or "")
        key_epoch = int(message.get("keyEpoch") or 0)
        if session_id != self.active_session.session_id or key_epoch != self.active_session.key_epoch:
            return
        self.active_session.is_resumed = True
        last_applied = int(message.get("lastAppliedBridgeOutboundSeq") or 0)
        sender = self.active_session.send_wire_message or self.live_send_wire_message
        if sender is None:
            return
        for entry in self.outbound_buffer:
            if int(entry["bridgeOutboundSeq"]) > last_applied:
                self._send_buffered_entry(entry, sender)

    def _handle_encrypted_envelope(
        self,
        message: dict[str, Any],
        send_control_message: Callable[[dict[str, Any]], None],
        on_application_message: Callable[[str], None],
    ) -> bool:
        if self.active_session is None:
            send_control_message(self._error("secure_channel_unavailable", "The secure channel is not ready."))
            return True

        session_id = str(message.get("sessionId") or "")
        key_epoch = int(message.get("keyEpoch") or 0)
        sender = str(message.get("sender") or "")
        counter = int(message.get("counter") or 0)
        if (
            session_id != self.active_session.session_id
            or key_epoch != self.active_session.key_epoch
            or sender != SECURE_SENDER_IPHONE
            or counter <= self.active_session.last_inbound_counter
        ):
            send_control_message(self._error("invalid_envelope", "Rejected invalid or replayed envelope."))
            return True

        aad = self._envelope_aad(session_id, key_epoch, sender, counter)
        plaintext = decrypt_text(
            self.active_session.session_secret,
            aad,
            str(message.get("ciphertext") or ""),
            str(message.get("tag") or ""),
        )
        if plaintext is None:
            send_control_message(self._error("decrypt_failed", "Unable to decrypt secure payload."))
            return True

        self.active_session.last_inbound_counter = counter
        on_application_message(plaintext)
        return True

    def _send_buffered_entry(self, entry: dict[str, Any], send_wire_message: Callable[[str], None]) -> None:
        if self.active_session is None:
            return
        counter = self.active_session.next_outbound_counter
        aad = self._envelope_aad(self.active_session.session_id, self.active_session.key_epoch, SECURE_SENDER_MAC, counter)
        payload = json_dumps_compact(
            {
                "bridgeOutboundSeq": entry["bridgeOutboundSeq"],
                "payloadText": entry["payloadText"],
            }
        )
        ciphertext, tag = encrypt_text(self.active_session.session_secret, aad, payload)
        envelope = {
            "kind": "encryptedEnvelope",
            "v": SECURE_PROTOCOL_VERSION,
            "sessionId": self.active_session.session_id,
            "keyEpoch": self.active_session.key_epoch,
            "sender": SECURE_SENDER_MAC,
            "counter": counter,
            "ciphertext": ciphertext,
            "tag": tag,
        }
        self.active_session.next_outbound_counter += 1
        send_wire_message(json_dumps_compact(envelope))

    def _trim_outbound_buffer(self) -> None:
        while (
            len(self.outbound_buffer) > MAX_BRIDGE_OUTBOUND_MESSAGES
            or self.outbound_buffer_bytes > MAX_BRIDGE_OUTBOUND_BYTES
        ):
            removed = self.outbound_buffer.pop(0)
            self.outbound_buffer_bytes = max(0, self.outbound_buffer_bytes - int(removed["sizeBytes"]))

    def _handshake_aad(self, session_id: str, handshake_mode: str, phone_device_id: str, client_nonce: str) -> bytes:
        return json_dumps_compact(
            {
                "sessionId": session_id,
                "handshakeMode": handshake_mode,
                "phoneDeviceId": phone_device_id,
                "clientNonce": client_nonce,
            }
        ).encode("utf-8")

    def _auth_aad(
        self,
        session_id: str,
        phone_device_id: str,
        client_nonce: str,
        server_nonce: str,
        key_epoch: int,
    ) -> bytes:
        return json_dumps_compact(
            {
                "sessionId": session_id,
                "phoneDeviceId": phone_device_id,
                "clientNonce": client_nonce,
                "serverNonce": server_nonce,
                "keyEpoch": key_epoch,
            }
        ).encode("utf-8")

    def _envelope_aad(self, session_id: str, key_epoch: int, sender: str, counter: int) -> bytes:
        return json_dumps_compact(
            {
                "sessionId": session_id,
                "keyEpoch": key_epoch,
                "sender": sender,
                "counter": counter,
            }
        ).encode("utf-8")

    def _error(self, code: str, message: str) -> dict[str, Any]:
        return {"kind": "secureError", "code": code, "message": message}
