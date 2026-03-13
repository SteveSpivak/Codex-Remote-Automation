# Quick Tunnel DNS can block self-hosted proof before Remodex ever connects

Date: 2026-03-13
Area: relay
Status: validated

## Context

The self-hosted proof path was changed to use the official `remodex` package, a local transport-only relay, and a Cloudflare Quick Tunnel that exposes the relay as a public `wss://` endpoint for the official iPhone app.

## Trigger

The self-hosted wrapper produced a real Quick Tunnel URL, but upstream Remodex still fell into a `connecting` or `disconnected` loop and the relay never logged an incoming peer connection.

## What Happened

The tunnel itself registered successfully, but the generated `*.trycloudflare.com` hostname did not resolve locally on this machine. That meant the wrapper was launching Remodex against a public relay URL that was not yet usable from the Mac itself.

## Lesson

For a Quick Tunnel based self-hosted proof, DNS readiness is part of the transport proof. A valid-looking public tunnel URL is not enough. The wrapper should wait for the hostname to resolve before launching Remodex, otherwise the result looks like a generic reconnect loop and wastes debugging time.

## Evidence

- `cloudflared` logs showed successful Quick Tunnel creation and connection registration
- direct hostname lookup for the generated `*.trycloudflare.com` host returned `nodename nor servname provided, or not known`
- the relay state stayed in startup until the tunnel hostname became resolvable

## Decision

Treat Quick Tunnel DNS resolution as a first-class gate in the self-hosted path. If the hostname does not resolve, stop with a clear error instead of starting the Remodex runtime.

## Follow-Up

- Retry with a new Quick Tunnel host if the previous one never resolves
- If this keeps happening on the current machine or network, use a named tunnel or another public TLS front door instead of Quick Tunnel
- Do not treat this as proof that the official iPhone app rejects self-hosted `wss://`

## Related Skills

- `cra-network-architect`
- `cra-test-engineer`
- `lesson-curator`
