from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .broker_service import write_json_atomic


LAUNCH_AGENT_LABEL = "com.stevespivak.remodex.upstream"
SELFHOSTED_RUNTIME_DIRNAME = "remodex-selfhosted"


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _patch_source_path() -> Path:
    return _repo_root() / "scripts" / "remodex_secure_device_state.filebacked.js"


def _runtime_root(base_dir: Path | None = None) -> Path:
    return (base_dir or (_repo_root() / "var" / "generated" / "remodex-upstream")).resolve()


def _selfhosted_runtime_root(base_dir: Path | None = None) -> Path:
    return (base_dir or (_repo_root() / "var" / "generated" / SELFHOSTED_RUNTIME_DIRNAME)).resolve()


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


@dataclass(frozen=True)
class SelfHostedRuntimePaths:
    runtime_root: Path
    state_path: Path
    relay_log_path: Path
    tunnel_log_path: Path


@dataclass
class ManagedChildProcess:
    process: subprocess.Popen[Any]
    log_path: Path
    log_handle: Any
    drain_thread: threading.Thread | None = None


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


def selfhosted_runtime_paths(*, base_dir: Path | None = None) -> SelfHostedRuntimePaths:
    root = _selfhosted_runtime_root(base_dir)
    return SelfHostedRuntimePaths(
        runtime_root=root,
        state_path=root / "selfhosted-state.json",
        relay_log_path=root / "relay.log",
        tunnel_log_path=root / "cloudflared.log",
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
    relay_url_override: str | None = None,
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
    if relay_url_override:
        env["REMODEX_RELAY"] = relay_url_override
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


def ensure_codex_authenticated(
    installed: InstalledRemodexPaths,
    *,
    extra_ca_cert_path: Path | None = None,
) -> dict[str, Any]:
    status = codex_login_status(installed, extra_ca_cert_path=extra_ca_cert_path)
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
    ensure_codex_authenticated(installed, extra_ca_cert_path=extra_ca_cert_path)
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


def _tail_log(log_path: Path, *, max_chars: int = 4000) -> str:
    if not log_path.exists():
        return ""
    return log_path.read_text(encoding="utf-8", errors="replace")[-max_chars:]


def normalize_public_relay_base_url(value: str) -> str:
    candidate = value.strip().rstrip("/")
    if not candidate:
        raise ValueError("Public relay base URL cannot be empty.")

    if candidate.startswith("https://"):
        candidate = "wss://" + candidate[len("https://") :]
    elif candidate.startswith("http://"):
        candidate = "ws://" + candidate[len("http://") :]

    if not (candidate.startswith("ws://") or candidate.startswith("wss://")):
        raise ValueError("Public relay base URL must start with ws://, wss://, http://, or https://")

    if not candidate.endswith("/relay"):
        candidate = candidate + "/relay"
    return candidate


_QUICK_TUNNEL_URL_RE = re.compile(r"https://[^\s|]+")


def extract_quick_tunnel_url(line: str) -> str | None:
    matches = _QUICK_TUNNEL_URL_RE.findall(line)
    for match in matches:
        if "trycloudflare.com" in match:
            return match.rstrip("/")
    return None


def _write_selfhosted_state(paths: SelfHostedRuntimePaths, payload: dict[str, Any]) -> None:
    paths.runtime_root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(paths.state_path, payload)


def _wait_for_relay_health(
    *,
    host: str,
    port: int,
    relay_process: ManagedChildProcess,
    timeout_seconds: float = 10.0,
) -> None:
    deadline = time.monotonic() + timeout_seconds
    health_url = f"http://{host}:{port}/health"
    last_error = ""
    while time.monotonic() < deadline:
        if relay_process.process.poll() is not None:
            raise RuntimeError(
                "Relay exited before becoming healthy.\n"
                f"Log tail:\n{_tail_log(relay_process.log_path)}"
            )
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError) as exc:
            last_error = str(exc)
        time.sleep(0.2)
    raise RuntimeError(f"Relay did not become healthy at {health_url}: {last_error or 'timed out'}")


def _wait_for_public_hostname(public_url: str, *, timeout_seconds: float = 30.0) -> None:
    host = urlparse(public_url).hostname or ""
    if not host:
        raise RuntimeError(f"Unable to parse a hostname from Quick Tunnel URL: {public_url}")

    deadline = time.monotonic() + timeout_seconds
    last_error = ""
    while time.monotonic() < deadline:
        try:
            socket.gethostbyname_ex(host)
            return
        except OSError as exc:
            last_error = str(exc)
        time.sleep(1.0)
    raise RuntimeError(f"Quick Tunnel hostname did not resolve yet: {host} ({last_error or 'timed out'})")


def _spawn_relay_process(
    installed: InstalledRemodexPaths,
    *,
    runtime_paths: SelfHostedRuntimePaths,
    relay_host: str,
    relay_port: int,
) -> ManagedChildProcess:
    runtime_paths.runtime_root.mkdir(parents=True, exist_ok=True)
    relay_log_handle = runtime_paths.relay_log_path.open("a", encoding="utf-8")
    relay_env = dict(os.environ)
    relay_env["CRA_RELAY_HOST"] = relay_host
    relay_env["CRA_RELAY_PORT"] = str(relay_port)
    relay_process = subprocess.Popen(
        [
            str(installed.node_path),
            str((_repo_root() / "relay" / "server.js").resolve()),
        ],
        cwd=str(_repo_root()),
        env=relay_env,
        stdout=relay_log_handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return ManagedChildProcess(
        process=relay_process,
        log_path=runtime_paths.relay_log_path,
        log_handle=relay_log_handle,
    )


def _stream_to_log(stream: Any, log_handle: Any) -> None:
    try:
        for line in iter(stream.readline, ""):
            log_handle.write(line)
            log_handle.flush()
    finally:
        stream.close()


def _spawn_quick_tunnel(
    *,
    runtime_paths: SelfHostedRuntimePaths,
    relay_host: str,
    relay_port: int,
    cloudflared_path: Path,
    timeout_seconds: float = 20.0,
) -> tuple[ManagedChildProcess, str]:
    runtime_paths.runtime_root.mkdir(parents=True, exist_ok=True)
    tunnel_log_handle = runtime_paths.tunnel_log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        [
            str(cloudflared_path),
            "tunnel",
            "--url",
            f"http://{relay_host}:{relay_port}",
        ],
        cwd=str(_repo_root()),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    if process.stdout is None:
        raise RuntimeError("cloudflared tunnel did not expose a readable stdout stream.")

    public_url = ""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            break
        line = process.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        tunnel_log_handle.write(line)
        tunnel_log_handle.flush()
        candidate = extract_quick_tunnel_url(line)
        if candidate:
            public_url = candidate
            break

    if not public_url:
        process.terminate()
        process.wait(timeout=5)
        tunnel_log_handle.flush()
        raise RuntimeError(
            "cloudflared did not emit a Quick Tunnel URL.\n"
            f"Log tail:\n{_tail_log(runtime_paths.tunnel_log_path)}"
        )

    drain_thread = threading.Thread(
        target=_stream_to_log,
        args=(process.stdout, tunnel_log_handle),
        daemon=True,
    )
    drain_thread.start()
    return (
        ManagedChildProcess(
            process=process,
            log_path=runtime_paths.tunnel_log_path,
            log_handle=tunnel_log_handle,
            drain_thread=drain_thread,
        ),
        public_url,
    )


def _terminate_child(child: ManagedChildProcess | None) -> None:
    if child is None:
        return
    try:
        if child.process.poll() is None:
            child.process.terminate()
            try:
                child.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.process.kill()
                child.process.wait(timeout=5)
    finally:
        child.log_handle.close()


def _run_foreground_process(argv: list[str], *, cwd: str, env: dict[str, str]) -> int:
    process = subprocess.Popen(argv, cwd=cwd, env=env)
    try:
        return process.wait()
    except KeyboardInterrupt:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        return 130


def run_selfhosted_remodex(
    installed: InstalledRemodexPaths,
    *,
    base_dir: Path | None = None,
    command: str = "up",
    thread_id: str | None = None,
    public_relay_base_url: str | None = None,
    relay_host: str = "127.0.0.1",
    relay_port: int = 8787,
    cloudflared_path: str | None = None,
    extra_ca_common_names: list[str] | None = None,
) -> int:
    runtime = ensure_patched_runtime(installed, base_dir=base_dir)
    runtime_state_paths = selfhosted_runtime_paths(base_dir=runtime.runtime_root)
    extra_ca_cert_path = build_extra_ca_bundle(runtime, common_names=extra_ca_common_names or [])
    ensure_codex_authenticated(installed, extra_ca_cert_path=extra_ca_cert_path)

    state_payload: dict[str, Any] = {
        "status": "starting",
        "runtime_root": str(runtime.runtime_root),
        "relay_log_path": str(runtime_state_paths.relay_log_path),
        "tunnel_log_path": str(runtime_state_paths.tunnel_log_path),
        "relay_host": relay_host,
        "relay_port": relay_port,
    }
    _write_selfhosted_state(runtime_state_paths, state_payload)

    relay_process: ManagedChildProcess | None = None
    tunnel_process: ManagedChildProcess | None = None
    public_tunnel_url = ""
    try:
        relay_process = _spawn_relay_process(
            installed,
            runtime_paths=runtime_state_paths,
            relay_host=relay_host,
            relay_port=relay_port,
        )
        _wait_for_relay_health(
            host=relay_host,
            port=relay_port,
            relay_process=relay_process,
        )

        if public_relay_base_url:
            relay_base_url = normalize_public_relay_base_url(public_relay_base_url)
        else:
            try:
                resolved_cloudflared = _resolve_command_path("cloudflared", cloudflared_path)
            except FileNotFoundError as exc:
                raise RuntimeError(
                    "cloudflared is required for the self-hosted Quick Tunnel path. "
                    "Install it first, for example with `brew install cloudflared`."
                ) from exc
            tunnel_process, public_tunnel_url = _spawn_quick_tunnel(
                runtime_paths=runtime_state_paths,
                relay_host=relay_host,
                relay_port=relay_port,
                cloudflared_path=resolved_cloudflared,
            )
            _wait_for_public_hostname(public_tunnel_url)
            relay_base_url = normalize_public_relay_base_url(public_tunnel_url)

        state_payload.update(
            {
                "status": "ready",
                "public_tunnel_url": public_tunnel_url or None,
                "remodex_relay_url": relay_base_url,
            }
        )
        _write_selfhosted_state(runtime_state_paths, state_payload)

        print(f"[cra-selfhosted] relay log: {runtime_state_paths.relay_log_path}")
        if public_tunnel_url:
            print(f"[cra-selfhosted] quick tunnel: {public_tunnel_url}")
        print(f"[cra-selfhosted] REMODEX_RELAY={relay_base_url}")

        argv = [str(installed.node_path), str(runtime.entrypoint_path), command]
        if command == "watch" and thread_id:
            argv.append(thread_id)
        returncode = _run_foreground_process(
            argv,
            cwd=str(_repo_root()),
            env=_runtime_env(
                installed,
                extra_ca_cert_path=extra_ca_cert_path,
                relay_url_override=relay_base_url,
            ),
        )
        state_payload["status"] = "interrupted" if returncode == 130 else "exited"
        state_payload["returncode"] = returncode
        _write_selfhosted_state(runtime_state_paths, state_payload)
        return returncode
    except Exception as exc:
        state_payload["status"] = "error"
        state_payload["error"] = str(exc)
        _write_selfhosted_state(runtime_state_paths, state_payload)
        raise
    finally:
        _terminate_child(tunnel_process)
        _terminate_child(relay_process)


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
