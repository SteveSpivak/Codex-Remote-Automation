import io
import json
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cra.cli import main
from cra.imessage import compose_approval_message, find_response_messages, parse_response_message, poll_imessages
from cra.models import ApprovalKind, BrokerApprovalRequest, BrokerDecision


class IMessageTests(unittest.TestCase):
    def test_compose_approval_message_includes_reply_instructions(self) -> None:
        approval = BrokerApprovalRequest(
            request_id="req-1",
            thread_id="thread-1",
            turn_id="turn-1",
            item_id="cmd-1",
            kind=ApprovalKind.COMMAND_EXECUTION,
            summary="Run curl https://example.com",
            available_decisions=[
                BrokerDecision.ACCEPT,
                BrokerDecision.ACCEPT_FOR_SESSION,
                BrokerDecision.DECLINE,
                BrokerDecision.CANCEL,
            ],
            timestamp="2026-03-13T00:00:00+00:00",
            wire_request_id=1,
        )

        message = compose_approval_message(approval)
        self.assertIn("request_id: req-1", message)
        self.assertIn("decline req-1", message)
        self.assertIn("acceptForSession req-1", message)

    def test_parse_response_message_supports_plaintext_and_json(self) -> None:
        self.assertEqual(
            parse_response_message("decline req-1"),
            {"request_id": "req-1", "decision": "decline"},
        )
        self.assertEqual(
            parse_response_message('{"request_id":"req-2","decision":"accept"}'),
            {"request_id": "req-2", "decision": "accept"},
        )
        self.assertIsNone(parse_response_message("sounds good, thanks"))

    def test_poll_imessages_reads_messages_db_and_prefers_inbound_messages(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "chat.db"
            connection = sqlite3.connect(db_path)
            connection.execute("CREATE TABLE handle (id TEXT)")
            connection.execute(
                "CREATE TABLE message (guid TEXT, text TEXT, attributedBody BLOB, is_from_me INTEGER, date INTEGER, handle_id INTEGER)"
            )
            connection.execute("INSERT INTO handle (id) VALUES (?)", ("steven.s.spivak@me.com",))
            handle_rowid = connection.execute("SELECT ROWID FROM handle").fetchone()[0]
            connection.execute(
                "INSERT INTO message (guid, text, attributedBody, is_from_me, date, handle_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("msg-1", "decline req-1", None, 0, 10_000_000_000, handle_rowid),
            )
            connection.execute(
                "INSERT INTO message (guid, text, attributedBody, is_from_me, date, handle_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("msg-2", "accept req-1", None, 1, 20_000_000_000, handle_rowid),
            )
            connection.commit()
            connection.close()

            polled = poll_imessages("steven.s.spivak@me.com", limit=5, db_path=db_path)
            parsed = find_response_messages(polled["messages"])

        self.assertEqual(polled["status"], "ok")
        self.assertEqual(polled["messages"][0]["message_id"], "msg-2")
        self.assertEqual(parsed, [{"request_id": "req-1", "decision": "decline"}])

    def test_poll_imessages_falls_back_to_attributed_body_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "chat.db"
            connection = sqlite3.connect(db_path)
            connection.execute("CREATE TABLE handle (id TEXT)")
            connection.execute(
                "CREATE TABLE message (guid TEXT, text TEXT, attributedBody BLOB, is_from_me INTEGER, date INTEGER, handle_id INTEGER)"
            )
            connection.execute("INSERT INTO handle (id) VALUES (?)", ("steven.s.spivak@me.com",))
            handle_rowid = connection.execute("SELECT ROWID FROM handle").fetchone()[0]
            connection.execute(
                "INSERT INTO message (guid, text, attributedBody, is_from_me, date, handle_id) VALUES (?, ?, ?, ?, ?, ?)",
                ("msg-3", None, b"xx decline req-3 yy", 0, 10_000_000_000, handle_rowid),
            )
            connection.commit()
            connection.close()

            polled = poll_imessages("steven.s.spivak@me.com", limit=5, db_path=db_path)

        self.assertEqual(polled["messages"][0]["text"], "xx decline req-3 yy")

    def test_imessage_parse_cli_returns_normalized_response(self) -> None:
        stdout = io.StringIO()
        with patch("sys.argv", ["cra.cli", "imessage-parse", "--text", "acceptForSession req-9"]):
            with redirect_stdout(stdout):
                exit_code = main()

        payload = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["parsed"]["request_id"], "req-9")
        self.assertEqual(payload["parsed"]["decision"], "acceptForSession")


if __name__ == "__main__":
    unittest.main()
