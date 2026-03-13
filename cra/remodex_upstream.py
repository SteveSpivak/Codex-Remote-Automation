from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .broker_service import write_json_atomic


LAUNCH_AGENT_LABEL = "com.stevespivak.remodex.upstream"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _patch_source_path() -> Path:
    return _repo_root() / "scripts" / "remodex_secure_device_state.filebacked.js"


def _runtime_root(base_dir: Path | None = None) -> Path:
    return (base_dir or (_repo_root() / "var" / "generated" / "remodex-upstream")).resolve()


def _user_home(home: Path | None = None) -> Path:
    return (home or Path.home()).expanduser().resolve()


def _launch_agent_dir(home: Path | None = None) -> Path:
    return _user_home(home) / "Library" / "LaunchAgents"


def _launch_agent_path(home: Path | None = None) -> Path:
    return _launch_agent_dir(home) / f"{LAUNCH_AGENT_LABEL}.plist"


def _log_dir(home: Path | None = None) -> Path:
    return _user_home(home) / "Library" / "Logs" / "Remodex"


@dataclass(frozen=True)
class InstalledRemodexPaths:
    home: Path
    python_path: Path
    node_path: Path
    codex_path: Path
    remodex_bin: Path
    remodex_package_dir: Path
    version: str


@dataclass(frozen=True)
class GeneratedRemodexRuntime:
    runtime_root: Path
    package_dir: Path
    entrypoint_path: Path
    metadata_path: Path
    patch_source_path: Path
    device_state_path: Path
    certs_dir: Path


def _resolve_command_path(command: str, explicit: str | None = None) -> Path:
    candidate = Path(explicit).expanduser() if explicit else None
    if candidate:
        resolved = candidate.resolve()
        if resolved.exists():
            return resolved
        raise FileNotFoundError(f"{command} path does not exist: {candidate}")

    discovered = shutil.which(command)
    if not discovered:
        raise FileNotFoundError(f"Unable to find `{command}` on PATH.")
    return Path(discovered).expanduser().resolve()


def _node_aware_command(script_path: Path, node_path: Path, *args: str) -> list[str]:
    resolved = script_path.expanduser().resolve()
    if resolved.suffix == ".js":
        return [str(node_path), str(resolved), *args]
    return [str(resolved), *args]


def _resolve_remodex_package_dir(remodex_bin: Path) -> Path:
    resolved = remodex_bin.resolve()
    candidates = [resolved.parent.parent, *resolved.parents]
    for candidate in candidates:
        if (
            (candidate / "package.json").exists()
            and (candidate / "bin").exists()
            and (candidate / "src" / "bridge.js").exists()
        ):
            return candidate
    raise FileNotFoundError(f"Unable to resolve the remodex package root from {remodex_bin}")


def resolve_installed_remodex(
    *,
    home: str | None = None,
    python_path: str | None = None,
    node_path: str | None = None,
    codex_path: str | None = None,
    remodex_bin: str | None = None,
) -> InstalledRemodexPaths:
    resolved_home = _user_home(Path(home) if home else None)
    resolved_python = _resolve_command_path("python3", python_path or sys.executable)
    resolved_node = _resolve_command_path("node", node_path)
    resolved_codex = _resolve_command_path("codex", codex_path)
    resolved_remodex_bin = _resolve_command_path("remodex", remodex_bin)
    package_dir = _resolve_remodex_package_dir(resolved_remodex_bin)
    package_payload = json.loads((package_dir / "package.json").read_text(encoding="utf-8"))
    version = str(package_payload.get("version", "")).strip() or "unknown"
    return InstalledRemodexPaths(
        home=resolved_home,
        python_path=resolved_python,
        node_path=resolved_node,
        codex_path=resolved_codex,
        remodex_bin=resolved_remodex_bin,
        remodex_package_dir=package_dir,
        version=version,
    )


def runtime_paths(
    *,
    base_dir: Path | None = None,
    home: Path | None = None,
) -> GeneratedRemodexRuntime:
    root = _runtime_root(base_dir)
    return GeneratedRemodexRuntime(
        runtime_root=root,
        package_dir=root / "remodex",
        entrypoint_path=root / "remodex" / "bin" / "remodex.js",
        metadata_path=root / "runtime-metadata.json",
        patch_source_path=_patch_source_path(),
        device_state_path=_user_home(home) / ".remodex" / "device-state.json",
        certs_dir=root / "certs",
    )


def _patch_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_metadata_matches(
    runtime: GeneratedRemodexRuntime,
    installed: InstalledRemodexPaths,
) -> bool:
    if not runtime.metadata_path.exists() or not runtime.entrypoint_path.exists():
        return False
    try:
        payload = json.loads(runtime.metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return payload == {
        "source_package_dir": str(installed.remodex_package_dir),
        "source_version": installed.version,
        "patched_file": "src/secure-device-state.js",
        "patch_source_path": str(runtime.patch_source_path),
        "patch_sha256": _patch_digest(runtime.patch_source_path),
    }


def build_patched_runtime(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    runtime = runtime_paths(base_dir=base_dir, home=installed.home)
    runtime.runtime_root.mkdir(parents=True, exist_ok=True)
    if runtime.package_dir.is_symlink() or runtime.package_dir.is_file():
        runtime.package_dir.unlink()
    elif runtime.package_dir.exists():
        shutil.rmtree(runtime.package_dir)
    shutil.copytree(installed.remodex_package_dir, runtime.package_dir, symlinks=True)
    shutil.copy2(runtime.patch_source_path, runtime.package_dir / "src" / "secure-device-state.js")
    metadata = {
        "source_package_dir": str(installed.remodex_package_dir),
        "source_version": installed.version,
        "patched_file": "src/secure-device-state.js",
        "patch_source_path": str(runtime.patch_source_path),
        "patch_sha256": _patch_digest(runtime.patch_source_path),
    }
    write_json_atomic(runtime.metadata_path, metadata)
    return {
        "status": "ok",
        "runtime_root": str(runtime.runtime_root),
        "entrypoint_path": str(runtime.entrypoint_path),
        "metadata_path": str(runtime.metadata_path),
        "device_state_path": str(runtime.device_state_path),
        "source_package_dir": str(installed.remodex_package_dir),
        "source_version": installed.version,
    }


def ensure_patched_runtime(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
) -> GeneratedRemodexRuntime:
    runtime = runtime_paths(base_dir=base_dir, home=installed.home)
    if not _runtime_metadata_matches(runtime, installed):
        build_patched_runtime(installed, base_dir=base_dir)
    return runtime


def _sanitize_cert_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "extra-ca"


def export_extra_ca_certificates(
    runtime: GeneratedRemodexRuntime,
    *,
    common_names: list[str],
) -> list[Path]:
    exported_paths: list[Path] = []
    runtime.certs_dir.mkdir(parents=True, exist_ok=True)
    keychains = [
        "/Library/Keychains/System.keychain",
        "/System/Library/Keychains/SystemRootCertificates.keychain",
        str(_user_home() / "Library" / "Keychains" / "login.keychain-db"),
    ]
    for common_name in [value.strip() for value in common_names if value and value.strip()]:
        pem_output = ""
        for keychain in keychains:
            completed = subprocess.run(
                ["security", "find-certificate", "-a", "-c", common_name, "-p", keychain],
                capture_output=True,
                text=True,
                check=False,
            )
            if completed.returncode == 0 and completed.stdout.strip():
                pem_output = completed.stdout.strip() + "\n"
                break
        if not pem_output:
            continue
        destination = runtime.certs_dir / f"{_sanitize_cert_name(common_name)}.pem"
        destination.write_text(pem_output, encoding="utf-8")
        exported_paths.append(destination)
    return exported_paths


def build_extra_ca_bundle(runtime: GeneratedRemodexRuntime, *, common_names: list[str]) -> Path | None:
    exported_paths = export_extra_ca_certificates(runtime, common_names=common_names)
    if not exported_paths:
        return None
    bundle_path = runtime.certs_dir / "extra-ca-bundle.pem"
    bundle_text = "\n".join(path.read_text(encoding="utf-8").strip() for path in exported_paths if path.exists()).strip()
    if not bundle_text:
        return None
    bundle_path.write_text(bundle_text + "\n", encoding="utf-8")
    return bundle_path


def _runtime_env(
    installed: InstalledRemodexPaths,
    *,
    extra_ca_cert_path: Path | None = None,
) -> dict[str, str]:
    env = dict(os.environ)
    env["HOME"] = str(installed.home)
    path_entries = [
        str(installed.node_path.parent),
        str(installed.python_path.parent),
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
        "/opt/homebrew/bin",
    ]
    existing_path = env.get("PATH", "")
    if existing_path:
        path_entries.extend([entry for entry in existing_path.split(os.pathsep) if entry])
    env["PATH"] = os.pathsep.join(dict.fromkeys(path_entries))
    if extra_ca_cert_path is not None:
        env["NODE_EXTRA_CA_CERTS"] = str(extra_ca_cert_path)
    for key in [
        "REMODEX_RELAY",
        "PHODEX_RELAY",
        "REMODEX_PUSH_SERVICE_URL",
        "REMODEX_CODEX_ENDPOINT",
        "PHODEX_CODEX_ENDPOINT",
        "REMODEX_REFRESH_COMMAND",
        "PHODEX_ON_PHONE_MESSAGE",
        "REMODEX_REFRESH_ENABLED",
    ]:
        env.pop(key, None)
    return env


def codex_login_status(installed: InstalledRemodexPaths, *, extra_ca_cert_path: Path | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        _node_aware_command(installed.codex_path, installed.node_path, "login", "status"),
        capture_output=True,
        text=True,
        env=_runtime_env(installed, extra_ca_cert_path=extra_ca_cert_path),
        check=False,
    )
    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    authenticated = "Logged in" in stdout or "Logged in" in stderr
    return {
        "status": "ok" if (completed.returncode == 0 or authenticated) else "error",
        "returncode": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "authenticated": authenticated,
    }


def ensure_codex_authenticated(installed: InstalledRemodexPaths) -> dict[str, Any]:
    status = codex_login_status(installed)
    if status["authenticated"]:
        return status
    details = status["stderr"] or status["stdout"] or "Codex is not authenticated."
    raise RuntimeError(f"codex login status failed: {details}")


def run_upstream_remodex(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
    command: str = "up",
    thread_id: str | None = None,
    extra_ca_common_names: list[str] | None = None,
) -> int:
    runtime = ensure_patched_runtime(installed, base_dir=base_dir)
    extra_ca_cert_path = None
    if extra_ca_common_names:
        extra_ca_cert_path = build_extra_ca_bundle(runtime, common_names=extra_ca_common_names)
    ensure_codex_authenticated(installed)
    argv = [str(installed.node_path), str(runtime.entrypoint_path), command]
    if command == "watch" and thread_id:
        argv.append(thread_id)
    completed = subprocess.run(
        argv,
        cwd=str(_repo_root()),
        env=_runtime_env(installed, extra_ca_cert_path=extra_ca_cert_path),
        check=False,
    )
    return completed.returncode


def launch_agent_payload(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
    stdout_log: Path | None = None,
    stderr_log: Path | None = None,
    extra_ca_common_names: list[str] | None = None,
) -> dict[str, Any]:
    runtime = ensure_patched_runtime(installed, base_dir=base_dir)
    extra_ca_cert_path = build_extra_ca_bundle(runtime, common_names=extra_ca_common_names or [])
    log_root = _log_dir(installed.home)
    stdout_path = (stdout_log or (log_root / "remodex.stdout.log")).expanduser().resolve()
    stderr_path = (stderr_log or (log_root / "remodex.stderr.log")).expanduser().resolve()
    environment = {
        "HOME": str(installed.home),
        "PYTHONPATH": str(_repo_root()),
        "PATH": _runtime_env(installed, extra_ca_cert_path=extra_ca_cert_path)["PATH"],
    }
    if extra_ca_cert_path is not None:
        environment["NODE_EXTRA_CA_CERTS"] = str(extra_ca_cert_path)
    return {
        "Label": LAUNCH_AGENT_LABEL,
        "ProgramArguments": [
            str(installed.python_path),
            "-m",
            "cra.cli",
            "remodex-upstream-run",
            "--runtime-dir",
            str(runtime.runtime_root),
            "--home",
            str(installed.home),
            "--python-path",
            str(installed.python_path),
            "--node-path",
            str(installed.node_path),
            "--codex-path",
            str(installed.codex_path),
            "--remodex-bin",
            str(installed.remodex_bin),
        ],
        "WorkingDirectory": str(_repo_root()),
        "EnvironmentVariables": environment,
        "RunAtLoad": True,
        "KeepAlive": True,
        "ThrottleInterval": 10,
        "StandardOutPath": str(stdout_path),
        "StandardErrorPath": str(stderr_path),
        "ProcessType": "Background",
    }


def render_launch_agent_plist(payload: dict[str, Any]) -> bytes:
    return plistlib.dumps(payload, sort_keys=False)


def write_launch_agent_file(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
    install_path: Path | None = None,
    stdout_log: Path | None = None,
    stderr_log: Path | None = None,
    extra_ca_common_names: list[str] | None = None,
) -> dict[str, Any]:
    payload = launch_agent_payload(
        installed,
        base_dir=base_dir,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        extra_ca_common_names=extra_ca_common_names,
    )
    destination = (install_path or _launch_agent_path(installed.home)).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    Path(payload["StandardOutPath"]).parent.mkdir(parents=True, exist_ok=True)
    Path(payload["StandardErrorPath"]).parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(render_launch_agent_plist(payload))
    return {
        "status": "written",
        "label": LAUNCH_AGENT_LABEL,
        "plist_path": str(destination),
        "stdout_log": payload["StandardOutPath"],
        "stderr_log": payload["StandardErrorPath"],
        "program_arguments": payload["ProgramArguments"],
    }


def install_launch_agent(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
    install_path: Path | None = None,
    stdout_log: Path | None = None,
    stderr_log: Path | None = None,
    bootstrap: bool = False,
    extra_ca_common_names: list[str] | None = None,
) -> dict[str, Any]:
    result = write_launch_agent_file(
        installed,
        base_dir=base_dir,
        install_path=install_path,
        stdout_log=stdout_log,
        stderr_log=stderr_log,
        extra_ca_common_names=extra_ca_common_names,
    )
    if bootstrap:
        destination = Path(result["plist_path"])
        domain = f"gui/{os.getuid()}"
        subprocess.run(["launchctl", "bootout", domain, str(destination)], check=False, capture_output=True, text=True)
        subprocess.run(["launchctl", "bootstrap", domain, str(destination)], check=True)
        subprocess.run(["launchctl", "kickstart", "-k", f"{domain}/{LAUNCH_AGENT_LABEL}"], check=True)
        result["status"] = "installed"
        result["bootstrapped"] = True
    return result


def uninstall_launch_agent(
    *,
    home: str | None = None,
    install_path: Path | None = None,
    bootout: bool = True,
) -> dict[str, Any]:
    destination = (install_path or _launch_agent_path(Path(home) if home else None)).expanduser().resolve()
    bootout_ran = False
    if bootout:
        domain = f"gui/{os.getuid()}"
        subprocess.run(["launchctl", "bootout", domain, str(destination)], check=False, capture_output=True, text=True)
        bootout_ran = True
    existed = destination.exists()
    if existed:
        destination.unlink()
    return {
        "status": "removed" if existed else "not_found",
        "label": LAUNCH_AGENT_LABEL,
        "plist_path": str(destination),
        "bootout_attempted": bootout_ran,
    }


def launch_agent_status(
    *,
    home: str | None = None,
    install_path: Path | None = None,
) -> dict[str, Any]:
    destination = (install_path or _launch_agent_path(Path(home) if home else None)).expanduser().resolve()
    domain = f"gui/{os.getuid()}/{LAUNCH_AGENT_LABEL}"
    completed = subprocess.run(
        ["launchctl", "print", domain],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "label": LAUNCH_AGENT_LABEL,
        "plist_path": str(destination),
        "plist_exists": destination.exists(),
        "loaded": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
