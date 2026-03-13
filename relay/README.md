# CRA Relay

Self-hosted, transport-only WebSocket relay for CRA bridge sessions.

## Run

```bash
cd relay
npm install
npm run start
```

## Endpoint shape

- Canonical upstream path: `ws://<host>:8787/relay/<session_id>` with `x-role: mac|iphone|phone`
- Legacy CRA path: `ws://<host>:8787/session/<session_id>?role=mac|iphone`
- Legacy direct path: `ws://<host>:8787/<session_id>` with `x-role: mac|iphone|phone`

The relay does not decrypt CRA payloads. It routes opaque text frames between peers in the same session.

## Public Quick Tunnel

For the first internet-reachable self-hosted proof on this Mac, expose the relay with Cloudflare Quick Tunnel:

```bash
cloudflared tunnel --url http://127.0.0.1:8787
```

The public relay base used by upstream Remodex should then be:

```text
wss://<quick-tunnel-host>/relay
```
