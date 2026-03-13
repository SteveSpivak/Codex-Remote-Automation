# Remodex-Compatible Bridge

This folder contains the phone-compatible bridge path for CRA.

## What It Does

- launches a local `codex app-server`
- keeps the Codex session warm across relay reconnects
- emits a Remodex-compatible QR payload
- performs Remodex-compatible secure pairing and reconnect
- forwards decrypted app messages to Codex and returns Codex messages through encrypted envelopes

## Run

Start the relay first:

```bash
node relay/server.js
```

Then start the bridge:

```bash
node remodex/bridge.js --relay-url ws://<reachable-host>:8787
```

The bridge writes these runtime artifacts under `var/remodex-bridge/` by default:

- `pairing-qr.png`
- `pairing-qr.txt`
- `pairing-payload.json`
- `bridge-state.json`
- `device-state.json`

## Pair-Only Mode

If you only need a fresh QR without launching Codex:

```bash
node remodex/bridge.js --relay-url ws://<reachable-host>:8787 --pair-only
```

## Compatibility Notes

- The QR encodes the raw Remodex pairing JSON, not a custom URI.
- The relay accepts the Remodex-style `/<sessionId>` path and `x-role` header.
- The older CRA-specific Python bridge remains in the repo, but it is not compatible with the Remodex iPhone app.

