import unittest

from cra.validation import (
    build_actuation_request,
    build_approval_event,
    sanitize_text,
    validate_uuid,
)


class ValidationTests(unittest.TestCase):
    def test_sanitize_text_removes_control_characters_and_quotes(self) -> None:
        self.assertEqual(sanitize_text('Need "approval"\nnow\\please'), "Need approval now please")

    def test_validate_uuid_normalizes_uuid(self) -> None:
        value = validate_uuid("11111111-1111-4111-8111-111111111111")
        self.assertEqual(value, "11111111-1111-4111-8111-111111111111")

    def test_build_payload_generates_uuid_when_missing(self) -> None:
        event = build_approval_event("Run risky command", "medium")
        self.assertEqual(event.risk_level.value, "medium")
        self.assertTrue(event.action_id)

    def test_build_actuation_request_validates_decision(self) -> None:
        request = build_actuation_request("approve", "11111111-1111-4111-8111-111111111111")
        self.assertEqual(request.decision.value, "approve")


if __name__ == "__main__":
    unittest.main()
