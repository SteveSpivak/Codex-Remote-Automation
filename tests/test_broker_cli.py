import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
