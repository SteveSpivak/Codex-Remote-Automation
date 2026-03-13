# CRA Relay

Self-hosted, transport-only WebSocket relay for CRA bridge sessions.

## Run

```bash
cd relay
npm run start
```

## Endpoint shape

- Mac bridge: `ws://<host>:8787/session/<session_id>?role=mac`
- iPhone app: `ws://<host>:8787/session/<session_id>?role=iphone`

The relay does not decrypt CRA payloads. It routes opaque text frames between peers in the same session.
