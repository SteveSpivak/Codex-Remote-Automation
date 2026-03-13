# Managed network can break hosted Remodex after TLS trust is fixed

Date: 2026-03-13
Area: relay
Status: validated

## Context

The hosted Remodex path was stabilized with a repo-managed wrapper, file-backed device state, and LaunchAgent support. The remaining goal was to make the official hosted relay at `wss://api.phodex.app/relay` reliable on this Mac.

## Trigger

The upstream Remodex logs kept looping between:

- `[remodex] connecting`
- `[remodex] disconnected`

even after the Keychain persistence issue was patched locally.

## What Happened

Direct Node WebSocket tests to the hosted relay failed with a certificate-chain error because this Mac is behind a Cellebrite or Palo TLS interception chain. Exporting the intercepting CAs and injecting them with `NODE_EXTRA_CA_CERTS` fixed the trust error, but the WebSocket still failed with `ECONNRESET` before the bridge ever reached `connected`.

## Lesson

Once the wrapper, device-state patch, and Codex auth are known-good, a repeated hosted `connecting` or `disconnected` loop can be a network-policy blocker rather than a Remodex or CRA bug. Fixing certificate trust alone is not enough when the upstream WebSocket is still being reset after TLS interception.

## Evidence

- `openssl s_client -connect api.phodex.app:443 -servername api.phodex.app` showed an issuer chain including `CN=palo.cellebrite.local`
- Node WebSocket without extra CAs failed with `self-signed certificate in certificate chain`
- Node WebSocket with the exported Cellebrite or Palo CA bundle failed later with `ECONNRESET`
- Remodex wrapper logs continued to show repeated `connecting` and `disconnected` without ever reaching `connected`

## Decision

Treat hosted upstream as blocked on this managed network until a non-intercepted network proves otherwise. Keep the hosted path as the architectural baseline, but do not keep reworking the CRA wrapper when the remaining failures are network-induced.

## Follow-Up

- Test hosted upstream on a non-intercepted network such as a hotspot or home Wi-Fi
- If hosted works there, keep hosted upstream as the default and document this network as unsupported
- If hosted still fails, re-evaluate the self-hosted relay path with the official upstream bridge before changing the mobile client again

## Related Skills

- `cra-orchestrator`
- `cra-upstream-integration`
- `cra-network-architect`
