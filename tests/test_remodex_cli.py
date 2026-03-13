import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from cra.cli import main


class RemodexCliTests(unittest.TestCase):
    def test_remodex_build_command_prints_runtime_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = {
                "status": "ok",
                "runtime_root": temp_dir,
                "entrypoint_path": f"{temp_dir}/remodex/bin/remodex.js",
                "metadata_path": f"{temp_dir}/runtime-metadata.json",
                "device_state_path": "/Users/test/.remodex/device-state.json",
                "source_package_dir": "/pkg/remodex",
                "source_version": "1.1.5",
            }
            stdout = io.StringIO()
            with patch("cra.cli.resolve_installed_remodex", return_value=object()), patch(
                "cra.cli.build_patched_runtime", return_value=payload
            ), patch(
                "sys.argv",
                ["cra.cli", "remodex-upstream-build", "--runtime-dir", temp_dir],
            ):
                with redirect_stdout(stdout):
                    exit_code = main()

        result = json.loads(stdout.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["source_version"], "1.1.5")

    def test_remodex_launch_agent_commands_delegate_to_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            install_path = Path(temp_dir) / "com.stevespivak.remodex.upstream.plist"
            install_stdout = io.StringIO()
            status_stdout = io.StringIO()
            uninstall_stdout = io.StringIO()

            with patch("cra.cli.resolve_installed_remodex", return_value=object()), patch(
                "cra.cli.install_launch_agent",
                return_value={"status": "written", "plist_path": str(install_path)},
            ), patch(
                "sys.argv",
                ["cra.cli", "remodex-install-launch-agent", "--install-path", str(install_path)],
            ):
                with redirect_stdout(install_stdout):
                    install_exit = main()

            with patch(
                "cra.cli.launch_agent_status",
                return_value={"loaded": False, "plist_exists": True, "plist_path": str(install_path)},
            ), patch(
                "sys.argv",
                ["cra.cli", "remodex-launch-agent-status", "--install-path", str(install_path)],
            ):
                with redirect_stdout(status_stdout):
                    status_exit = main()

            with patch(
                "cra.cli.uninstall_launch_agent",
                return_value={"status": "removed", "plist_path": str(install_path)},
            ), patch(
                "sys.argv",
                ["cra.cli", "remodex-uninstall-launch-agent", "--install-path", str(install_path)],
            ):
                with redirect_stdout(uninstall_stdout):
                    uninstall_exit = main()

        self.assertEqual(install_exit, 0)
        self.assertEqual(status_exit, 0)
        self.assertEqual(uninstall_exit, 0)
        self.assertEqual(json.loads(install_stdout.getvalue())["status"], "written")
        self.assertTrue(json.loads(status_stdout.getvalue())["plist_exists"])
        self.assertEqual(json.loads(uninstall_stdout.getvalue())["status"], "removed")


if __name__ == "__main__":
    unittest.main()
