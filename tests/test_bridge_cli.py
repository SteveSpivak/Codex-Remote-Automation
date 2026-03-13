import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cra.cli import main


class BridgeCliTests(unittest.TestCase):
    def test_bridge_create_pairing_writes_payload_and_qr_assets(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            stdout = io.StringIO()
            def fake_write_pairing_qr_image(path: Path, _payload: dict[str, object]) -> Path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fake-png")
                return path

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
                with patch("cra.cli.write_pairing_qr_image", side_effect=fake_write_pairing_qr_image):
                    with redirect_stdout(stdout):
                        exit_code = main()

            payload = json.loads(stdout.getvalue())
            qr_path = Path(payload["qr_path"])
            qr_stub_path = Path(payload["qr_stub_path"])
            payload_path = Path(payload["payload_path"])
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload_path.exists())
            self.assertTrue(qr_path.exists())
            self.assertTrue(qr_stub_path.exists())
            self.assertEqual(qr_path.suffix, ".png")
            self.assertEqual(payload["payload"]["relayUrl"], "ws://relay.test:8787")


if __name__ == "__main__":
    unittest.main()
