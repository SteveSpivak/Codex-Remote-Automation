import json
import unittest

from cra.bridge.crypto import compute_tag, encrypt_text
from cra.bridge.secure_transport import (
    HANDSHAKE_MODE_QR_BOOTSTRAP,
    HANDSHAKE_MODE_TRUSTED_RECONNECT,
    SECURE_SENDER_IPHONE,
    BridgeSecureTransport,
)


def _device_state() -> dict[str, object]:
    return {
        "bridge_device_id": "bridge-1",
        "bridge_secret": "YnJpZGdlLXNlY3JldC0wMDAwMDAwMDAwMDAwMDAwMDAwMDA=",  # bridge-secret-000...
        "trusted_phones": {},
    }


class BridgeSecureTransportTests(unittest.TestCase):
    def test_qr_bootstrap_creates_trusted_phone_and_flushes_buffer_on_resume(self) -> None:
        state = _device_state()
        transport = BridgeSecureTransport(session_id="session-1", relay_url="ws://relay", device_state=state)
        pairing = transport.create_pairing_payload()

        control_messages = []
        app_messages = []

        hello = {
            "kind": "clientHello",
            "protocolVersion": 1,
            "sessionId": "session-1",
            "handshakeMode": HANDSHAKE_MODE_QR_BOOTSTRAP,
            "phoneDeviceId": "phone-1",
            "phoneLabel": "Steve iPhone",
            "clientNonce": "client-nonce",
            "clientProof": compute_tag(
                pairing["pairingSecret"],
                transport._handshake_aad("session-1", HANDSHAKE_MODE_QR_BOOTSTRAP, "phone-1", "client-nonce"),
                b"",
            ),
        }
        handled = transport.handle_incoming_wire_message(
            json.dumps(hello),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )
        self.assertTrue(handled)
        self.assertEqual(control_messages[0]["kind"], "serverHello")

        client_auth = {
            "kind": "clientAuth",
            "sessionId": "session-1",
            "phoneDeviceId": "phone-1",
            "keyEpoch": control_messages[0]["keyEpoch"],
            "clientAuth": compute_tag(
                pairing["pairingSecret"],
                transport._auth_aad(
                    "session-1",
                    "phone-1",
                    "client-nonce",
                    control_messages[0]["serverNonce"],
                    control_messages[0]["keyEpoch"],
                ),
                b"clientAuth",
            ),
        }
        transport.handle_incoming_wire_message(
            json.dumps(client_auth),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )

        self.assertEqual(control_messages[-1]["kind"], "secureReady")
        self.assertIn("phone-1", state["trusted_phones"])

        outbound = []
        transport.bind_live_send_wire_message(outbound.append)
        transport.queue_outbound_application_message('{"method":"bridge/pendingApprovalsUpdated"}')
        self.assertEqual(outbound, [])

        transport.handle_incoming_wire_message(
            json.dumps(
                {
                    "kind": "resumeState",
                    "sessionId": "session-1",
                    "keyEpoch": control_messages[-1]["keyEpoch"],
                    "lastAppliedBridgeOutboundSeq": 0,
                }
            ),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )
        self.assertEqual(len(outbound), 1)
        self.assertIn("encryptedEnvelope", outbound[0])
        self.assertNotIn("pendingApprovalsUpdated", outbound[0])

    def test_trusted_reconnect_and_replay_rejection(self) -> None:
        state = _device_state()
        state["trusted_phones"] = {
            "phone-1": {
                "device_id": "phone-1",
                "phone_label": "Steve iPhone",
                "shared_secret": "cGhvbmUtc2VjcmV0LTAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=",
                "paired_at": "2026-03-13T00:00:00+00:00",
                "last_seen_at": "2026-03-13T00:00:00+00:00",
            }
        }
        transport = BridgeSecureTransport(session_id="session-2", relay_url="ws://relay", device_state=state)
        control_messages = []
        app_messages = []
        trusted_secret = state["trusted_phones"]["phone-1"]["shared_secret"]  # type: ignore[index]

        hello = {
            "kind": "clientHello",
            "protocolVersion": 1,
            "sessionId": "session-2",
            "handshakeMode": HANDSHAKE_MODE_TRUSTED_RECONNECT,
            "phoneDeviceId": "phone-1",
            "clientNonce": "reconnect-nonce",
            "clientProof": compute_tag(
                trusted_secret,
                transport._handshake_aad("session-2", HANDSHAKE_MODE_TRUSTED_RECONNECT, "phone-1", "reconnect-nonce"),
                b"",
            ),
        }
        transport.handle_incoming_wire_message(
            json.dumps(hello),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )
        transport.handle_incoming_wire_message(
            json.dumps(
                {
                    "kind": "clientAuth",
                    "sessionId": "session-2",
                    "phoneDeviceId": "phone-1",
                    "keyEpoch": control_messages[-1]["keyEpoch"],
                    "clientAuth": compute_tag(
                        trusted_secret,
                        transport._auth_aad(
                            "session-2",
                            "phone-1",
                            "reconnect-nonce",
                            control_messages[-1]["serverNonce"],
                            control_messages[-1]["keyEpoch"],
                        ),
                        b"clientAuth",
                    ),
                }
            ),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )
        transport.handle_incoming_wire_message(
            json.dumps(
                {
                    "kind": "resumeState",
                    "sessionId": "session-2",
                    "keyEpoch": control_messages[-1]["keyEpoch"],
                    "lastAppliedBridgeOutboundSeq": 0,
                }
            ),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )

        session_secret = transport.active_session.session_secret  # type: ignore[union-attr]
        aad = transport._envelope_aad("session-2", transport.active_session.key_epoch, SECURE_SENDER_IPHONE, 1)  # type: ignore[union-attr]
        ciphertext, tag = encrypt_text(session_secret, aad, '{"method":"bridge/getPendingApprovals","id":"1"}')
        envelope = {
            "kind": "encryptedEnvelope",
            "v": 1,
            "sessionId": "session-2",
            "keyEpoch": transport.active_session.key_epoch,  # type: ignore[union-attr]
            "sender": SECURE_SENDER_IPHONE,
            "counter": 1,
            "ciphertext": ciphertext,
            "tag": tag,
        }
        transport.handle_incoming_wire_message(
            json.dumps(envelope),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )
        self.assertEqual(app_messages[-1], '{"method":"bridge/getPendingApprovals","id":"1"}')

        transport.handle_incoming_wire_message(
            json.dumps(envelope),
            send_control_message=control_messages.append,
            on_application_message=app_messages.append,
        )
        self.assertEqual(control_messages[-1]["code"], "invalid_envelope")

    def test_pairing_expiry_is_rejected(self) -> None:
        state = _device_state()
        transport = BridgeSecureTransport(session_id="session-3", relay_url="ws://relay", device_state=state)
        pairing = transport.create_pairing_payload()
        transport.pending_pairing["expires_at"] = 0  # type: ignore[index]
        control_messages = []

        hello = {
            "kind": "clientHello",
            "protocolVersion": 1,
            "sessionId": "session-3",
            "handshakeMode": HANDSHAKE_MODE_QR_BOOTSTRAP,
            "phoneDeviceId": "phone-1",
            "clientNonce": "expired",
            "clientProof": compute_tag(
                pairing["pairingSecret"],
                transport._handshake_aad("session-3", HANDSHAKE_MODE_QR_BOOTSTRAP, "phone-1", "expired"),
                b"",
            ),
        }
        transport.handle_incoming_wire_message(
            json.dumps(hello),
            send_control_message=control_messages.append,
            on_application_message=lambda _message: None,
        )
        self.assertEqual(control_messages[-1]["code"], "pairing_expired")


if __name__ == "__main__":
    unittest.main()
