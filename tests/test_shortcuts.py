import json
import tempfile
import unittest
from pathlib import Path

from cra.shortcuts import build_shortcuts_command, build_ssh_command, handle_shortcut_entry


class ShortcutsTests(unittest.TestCase):
    def test_build_shortcuts_command_includes_optional_paths(self) -> None:
        command = build_shortcuts_command(
            "CRA Approve",
            input_path=Path("/tmp/input.json"),
            output_path=Path("/tmp/output.json"),
            output_type="public.json",
        )
        self.assertEqual(command[0:3], ["/usr/bin/shortcuts", "run", "CRA Approve"])
        self.assertIn("--input-path", command)
        self.assertIn("--output-path", command)
        self.assertIn("--output-type", command)

    def test_build_ssh_command_targets_shortcut_entry(self) -> None:
        command = build_ssh_command(
            "approve",
            "11111111-1111-4111-8111-111111111111",
            allow_live=True,
            allow_visual=True,
            selector_config=Path("config/codex-selectors.json"),
        )
        self.assertIn("python3 -m cra.cli shortcut-entry", command)
        self.assertIn("--allow-live", command)
        self.assertIn("--allow-visual", command)
        self.assertIn("config/codex-selectors.json", command)

    def test_handle_shortcut_entry_writes_audit_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_path = Path(temp_dir) / "shortcut-entry.jsonl"

            def runner(decision: str, action_id: str, **kwargs):
                return {
                    "status": "ok",
                    "decision": decision,
                    "action_id": action_id,
                    "mode": "live",
                    "method": "accessibility",
                    "kwargs": kwargs,
                }

            result = handle_shortcut_entry(
                "approve",
                "11111111-1111-4111-8111-111111111111",
                allow_live=True,
                allow_visual=True,
                audit_path=audit_path,
                runner=runner,
            )

            self.assertEqual(result["request"]["decision"], "approve")
            self.assertEqual(result["result"]["status"], "ok")
            self.assertTrue(audit_path.exists())

            records = [json.loads(line) for line in audit_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([record["record_type"] for record in records], ["shortcut_request", "shortcut_result"])


if __name__ == "__main__":
    unittest.main()
