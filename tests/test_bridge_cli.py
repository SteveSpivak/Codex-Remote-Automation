import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cra.cli import main


class BridgeCliTests(unittest.TestCase):
    def test_bridge_create_pairing_writes_payload_and_qr_stub(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()
            with patch(
                "sys.argv",
                [
                    "cra.cli",
                    "bridge-create-pairing",
                    "--relay-url",
                    "ws://relay.test:8787",
                    "--bridge-dir",
                    temp_dir,
                    "--audit-dir",
                    temp_dir,
                ],
            ):
                with redirect_stdout(stdout):
                    exit_code = main()

            payload = json.loads(stdout.getvalue())
            qr_path = Path(payload["qr_path"])
            payload_path = Path(payload["payload_path"])
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload_path.exists())
            self.assertTrue(qr_path.exists())
            self.assertEqual(payload["payload"]["relayUrl"], "ws://relay.test:8787")


if __name__ == "__main__":
    unittest.main()
