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

## 7. Out Of Scope For This Phase

- push or background wake
- LaunchAgent packaging for the self-hosted path
- public VPS deployment
- router/DNS/TLS hardening beyond Quick Tunnel
