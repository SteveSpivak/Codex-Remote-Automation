import json
import tempfile
import unittest
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

from cra.remodex_upstream import (
    InstalledRemodexPaths,
    build_patched_runtime,
    codex_login_status,
    launch_agent_payload,
)


class RemodexUpstreamTests(unittest.TestCase):
    def test_build_patched_runtime_copies_package_and_replaces_secure_device_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            package_dir = temp_root / "upstream" / "remodex"
            (package_dir / "bin").mkdir(parents=True)
            (package_dir / "src").mkdir(parents=True)
            (package_dir / "node_modules" / "ws").mkdir(parents=True)
            (package_dir / "package.json").write_text('{"name":"remodex","version":"1.1.5"}\n', encoding="utf-8")
            (package_dir / "bin" / "remodex.js").write_text("console.log('upstream');\n", encoding="utf-8")
            (package_dir / "src" / "secure-device-state.js").write_text("throw new Error('keychain');\n", encoding="utf-8")
            patch_source = temp_root / "patch.js"
            patch_source.write_text("module.exports = { patched: true };\n", encoding="utf-8")

            installed = InstalledRemodexPaths(
                home=temp_root / "home",
                python_path=Path("/opt/homebrew/bin/python3"),
                node_path=Path("/usr/local/bin/node"),
                codex_path=Path("/usr/local/bin/codex"),
                remodex_bin=package_dir / "bin" / "remodex.js",
                remodex_package_dir=package_dir,
                version="1.1.5",
            )

            from cra import remodex_upstream as module

            original_patch_source = module._patch_source_path
            module._patch_source_path = lambda: patch_source
            try:
                result = build_patched_runtime(installed, base_dir=temp_root / "runtime")
            finally:
                module._patch_source_path = original_patch_source

            runtime_package_dir = Path(result["runtime_root"]) / "remodex"
            self.assertTrue((runtime_package_dir / "node_modules" / "ws").exists())
            self.assertEqual(
                (runtime_package_dir / "src" / "secure-device-state.js").read_text(encoding="utf-8"),
                "module.exports = { patched: true };\n",
            )
            metadata = json.loads((Path(result["metadata_path"])).read_text(encoding="utf-8"))
            self.assertEqual(metadata["source_version"], "1.1.5")

    def test_launch_agent_payload_pins_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            installed = InstalledRemodexPaths(
                home=temp_root / "home",
                python_path=Path("/opt/homebrew/bin/python3"),
                node_path=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/node"),
                codex_path=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/codex"),
                remodex_bin=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/remodex"),
                remodex_package_dir=temp_root / "pkg",
                version="1.1.5",
            )
            runtime_root = temp_root / "runtime"
            (runtime_root / "remodex" / "bin").mkdir(parents=True)
            (runtime_root / "remodex" / "bin" / "remodex.js").write_text("", encoding="utf-8")
            (runtime_root / "runtime-metadata.json").write_text(
                json.dumps(
                    {
                        "source_package_dir": str(installed.remodex_package_dir),
                        "source_version": "1.1.5",
                        "patched_file": "src/secure-device-state.js",
                        "patch_source_path": str(Path(__file__).resolve()),
                        "patch_sha256": "x",
                    }
                ),
                encoding="utf-8",
            )

            from cra import remodex_upstream as module

            original_patch_source = module._patch_source_path
            original_runtime_metadata_matches = module._runtime_metadata_matches
            original_build_extra_ca_bundle = module.build_extra_ca_bundle
            module._patch_source_path = lambda: Path(__file__).resolve()
            module._runtime_metadata_matches = lambda runtime, current: True
            module.build_extra_ca_bundle = lambda runtime, common_names: runtime.certs_dir / "extra-ca-bundle.pem"
            try:
                payload = launch_agent_payload(
                    installed,
                    base_dir=runtime_root,
                    extra_ca_common_names=["palo.cellebrite.local", "CLB-CA"],
                )
            finally:
                module._patch_source_path = original_patch_source
                module._runtime_metadata_matches = original_runtime_metadata_matches
                module.build_extra_ca_bundle = original_build_extra_ca_bundle

            self.assertEqual(payload["Label"], "com.stevespivak.remodex.upstream")
            self.assertIn(str(installed.python_path), payload["ProgramArguments"])
            self.assertIn(str(installed.node_path), payload["ProgramArguments"])
            self.assertIn(str(installed.codex_path), payload["ProgramArguments"])
            self.assertIn(str(installed.remodex_bin), payload["ProgramArguments"])
            self.assertEqual(payload["EnvironmentVariables"]["HOME"], str(installed.home))
            self.assertIn(str(installed.node_path.parent), payload["EnvironmentVariables"]["PATH"])
            self.assertTrue(payload["EnvironmentVariables"]["NODE_EXTRA_CA_CERTS"].endswith("extra-ca-bundle.pem"))

    def test_codex_login_status_accepts_logged_in_stdout_even_with_nonzero_exit(self) -> None:
        installed = InstalledRemodexPaths(
            home=Path("/Users/test"),
            python_path=Path("/opt/homebrew/bin/python3"),
            node_path=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/node"),
            codex_path=Path("/Users/test/.nvm/versions/node/v22.22.1/lib/node_modules/@openai/codex/bin/codex.js"),
            remodex_bin=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/remodex"),
            remodex_package_dir=Path("/tmp/remodex"),
            version="1.1.5",
        )

        with patch(
            "cra.remodex_upstream.subprocess.run",
            return_value=CompletedProcess(
                args=[],
                returncode=1,
                stdout="Logged in using ChatGPT\n",
                stderr="warning",
            ),
        ):
            payload = codex_login_status(installed)

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["authenticated"])

    def test_codex_login_status_accepts_logged_in_stderr_even_with_nonzero_exit(self) -> None:
        installed = InstalledRemodexPaths(
            home=Path("/Users/test"),
            python_path=Path("/opt/homebrew/bin/python3"),
            node_path=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/node"),
            codex_path=Path("/Users/test/.nvm/versions/node/v22.22.1/lib/node_modules/@openai/codex/bin/codex.js"),
            remodex_bin=Path("/Users/test/.nvm/versions/node/v22.22.1/bin/remodex"),
            remodex_package_dir=Path("/tmp/remodex"),
            version="1.1.5",
        )

        with patch(
            "cra.remodex_upstream.subprocess.run",
            return_value=CompletedProcess(
                args=[],
                returncode=1,
                stdout="",
                stderr="Logged in using ChatGPT\n",
            ),
        ):
            payload = codex_login_status(installed)

        self.assertEqual(payload["status"], "ok")
        self.assertTrue(payload["authenticated"])


if __name__ == "__main__":
    unittest.main()
