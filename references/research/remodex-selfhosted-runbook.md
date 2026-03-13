# Remodex Self-Hosted Relay Runbook

Use this runbook for the first self-hosted public relay proof on this Mac. The goal is not a daily-driver setup yet. The goal is one stable foreground-connected session and one successful approval round-trip using the official `remodex` package and the official Remodex iPhone app.

## 1. Install Relay Dependency

```bash
cd /Users/steve.spivak/Documents/MAcosAutomation/relay
npm install
```

## 2. Install Cloudflare Quick Tunnel

If `cloudflared` is not already installed:

```bash
brew install cloudflared
```

## 3. Start The Self-Hosted Wrapper

```bash
cd /Users/steve.spivak/Documents/MAcosAutomation
bash scripts/remodex_selfhosted.sh
```

Expected startup output includes:

- the relay log path
- the Quick Tunnel URL
- the effective `REMODEX_RELAY=wss://<quick-tunnel-host>/relay`
- the standard upstream Remodex QR payload output

The wrapper:

- uses the real user `HOME`
- keeps the file-backed Remodex device-state patch
- starts the local relay on `127.0.0.1:8787`
- creates a Cloudflare Quick Tunnel
- launches the official upstream `remodex up` against the public `wss://` relay URL

If you are using a stable private or public relay address instead of Quick Tunnel, pass it explicitly:

```bash
cd /Users/steve.spivak/Documents/MAcosAutomation
python3 -m cra.cli remodex-selfhosted-run --public-relay-base-url http://10.97.52.64:8787 --relay-host 0.0.0.0
```

## 4. Control-Path Proof

First prove the app can stay connected long enough to run a deterministic command.

Success criteria:

- the iPhone app scans the QR
- Remodex reaches `connected`
- the app can run a simple command on the Mac

Example command to test from the phone:

```text
printf 'selfhosted-ok\n' > /tmp/remodex-selfhosted-test.txt
```

Verify on the Mac:

```bash
cat /tmp/remodex-selfhosted-test.txt
```

Expected output:

```text
selfhosted-ok
```

## 5. Approval Proof

Once the control path works, trigger one approval-needed Codex action and resolve it from the phone.

Success criteria:

- the phone stays connected
- the approval request appears
- approve or decline resolves the correct action
- Codex receives the correct result

## 6. Logs And State

The self-hosted wrapper writes runtime artifacts under:

- `var/generated/remodex-selfhosted/selfhosted-state.json`
- `var/generated/remodex-selfhosted/relay.log`
- `var/generated/remodex-selfhosted/cloudflared.log`

Use these to classify failures:

- connect fails before `connected` -> transport or official-app self-hosting issue
- connect works but commands fail -> Codex bridge/runtime issue
- commands work but approvals fail -> approval-wrapper issue

If the wrapper exits with:

```text
Quick Tunnel hostname did not resolve yet: <host>
```

that is a public-DNS readiness blocker on the current machine or network. Retry with a new tunnel or use a named tunnel or other public TLS front door before blaming the relay implementation.

## 7. Auto-Start In Terminal At Login

Use this only after the self-hosted command path is already working manually.

```bash
cd /Users/steve.spivak/Documents/MAcosAutomation
bash scripts/install_remodex_selfhosted_terminal_launchagent.sh --public-relay-base-url http://10.97.52.64:8787 --relay-host 0.0.0.0 --bootstrap
```

What it does:

- writes a user LaunchAgent under `~/Library/LaunchAgents`
- runs at login in the Aqua session
- opens Terminal
- runs the self-hosted wrapper with the configured relay URL
- leaves the Terminal window open so the QR remains visible

Check status:

```bash
bash scripts/remodex_selfhosted_terminal_launchagent_status.sh
```

Remove it:

```bash
bash scripts/uninstall_remodex_selfhosted_terminal_launchagent.sh
```

## 8. Out Of Scope For This Phase

- push or background wake
- public VPS deployment
- router/DNS/TLS hardening beyond Quick Tunnel
