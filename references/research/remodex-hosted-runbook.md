# Remodex Hosted Wrapper Runbook

Use this runbook for the daily-driver path: official hosted Remodex relay, repo-managed file-backed wrapper, and optional LaunchAgent packaging.

## 1. Build Or Refresh The Patched Runtime

```bash
python3 -m cra.cli remodex-upstream-build
```

This copies the installed upstream `remodex` package into `var/generated/remodex-upstream/` and replaces only `src/secure-device-state.js` with the repo-managed file-backed variant.

## 2. Run Hosted Remodex Through The Wrapper

```bash
bash scripts/remodex_upstream.sh
```

Wrapper behavior:

- uses the real user `HOME`
- uses the hosted upstream relay defaults
- does not set `REMODEX_RELAY`
- does not blank `REMODEX_PUSH_SERVICE_URL`
- runs `codex login status` before launching Remodex

## 3. First Pairing Checks

After the first clean hosted pairing:

```bash
cat ~/.remodex/device-state.json
```

Expected:

- the file exists
- it contains `macDeviceId`
- it contains `macIdentityPublicKey`
- after the phone is trusted, it contains one `trustedPhones` entry

## 4. Reconnect Checks

Stop and rerun the wrapper:

```bash
bash scripts/remodex_upstream.sh
```

Expected:

- `trusted_reconnect` appears in Remodex logs
- the repeated Keychain prompt does not appear
- the wrapper does not require `HOME` overrides

## 5. Install The LaunchAgent

Write and load the LaunchAgent:

```bash
bash scripts/install_remodex_launchagent.sh --bootstrap
```

Inspect status:

```bash
bash scripts/remodex_launchagent_status.sh
```

Remove it later if needed:

```bash
bash scripts/uninstall_remodex_launchagent.sh
```

## 6. Logs

Default log paths:

- `~/Library/Logs/Remodex/remodex.stdout.log`
- `~/Library/Logs/Remodex/remodex.stderr.log`

The LaunchAgent plist is written to:

- `~/Library/LaunchAgents/com.stevespivak.remodex.upstream.plist`
