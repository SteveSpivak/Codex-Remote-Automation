# Remodex Upstream Assessment

Last updated: 2026-03-13

## Summary

Current evidence is strong enough to reject a custom bridge rewrite as the default path. It is not yet strong enough to declare self-hosted CRA relay support fully proven for the current Remodex iPhone app.

## Evidence Sources

- Upstream README: [github.com/Emanuele-web04/remodex](https://github.com/Emanuele-web04/remodex)
- Installed npm package: `remodex@1.1.5`
- Upstream source inspected locally from the installed package
- Apple App Transport Security docs:
  - [NSAllowsLocalNetworking](https://developer.apple.com/documentation/bundleresources/information-property-list/nsapptransportsecurity/nsallowslocalnetworking)
  - [Preventing Insecure Network Connections](https://developer.apple.com/documentation/security/preventing-insecure-network-connections)

## Confirmed Findings

### Upstream package behavior

- The official package exposes `remodex up`, `remodex resume`, and `remodex watch`.
- The upstream package defaults `REMODEX_RELAY` to `wss://api.phodex.app/relay`.
- The package accepts override env vars including:
  - `REMODEX_RELAY`
  - `REMODEX_CODEX_ENDPOINT`
  - `REMODEX_REFRESH_COMMAND`
  - `REMODEX_REFRESH_ENABLED`
  - `REMODEX_PUSH_SERVICE_URL`
- Bridge identity state is persisted under `~/.remodex`, and on macOS the package attempts Keychain-backed storage for device identity.

### Upstream README guidance

- The README says the full phone-to-Mac flow still depends on `api.phodex.app` during the current testing phase.
- The README says self-hosting is supported in principle and the relay code is included.
- Those two statements together mean self-hosting is a direction, not yet a proven baseline for this repo.

### Local runtime checks

- The official upstream bridge starts locally and produces a valid Remodex QR.
- The official upstream bridge can pair the phone successfully when the Mac can reach the relay without breaking Codex authentication.
- The official upstream bridge connected successfully to the local repo relay in a Mac-only test.
- That proves the local relay can satisfy the upstream bridge handshake at least at a basic level.
- It does not prove that the iPhone app accepts the same local relay path.
- The local repo relay exposes only WebSocket session routing and `/health`; it does not implement the upstream `/v1/push/session/*` endpoints.
- That means `push notify failed: not_found` is expected on the current local relay and should not be treated as proof that hosted upstream push is broken.
- In upstream `secure-transport.js`, trusted reconnect still calls `rememberTrustedPhone(...)`.
- In upstream `secure-device-state.js`, `rememberTrustedPhone(...)` always tries a Keychain-backed write first on macOS.
- That explains the repeated Keychain prompt on reconnect and justifies a minimal local patch at the device-state persistence layer.
- On this Mac, the hosted relay path is currently behind TLS interception by a Cellebrite/Palo certificate chain.
- A direct Node WebSocket connection to `wss://api.phodex.app/relay/...` fails with `self-signed certificate in certificate chain` unless the local intercepting CAs are exported and injected with `NODE_EXTRA_CA_CERTS`.
- After the intercepting CAs are trusted for Node, the hosted WebSocket still resets with `ECONNRESET` before Remodex reaches `[remodex] connected`.
- That means the current blocker is no longer the Keychain prompt or repo wrapper. It is the active network path between this Mac and the hosted relay.

### Hosted relay environment constraint

- `openssl s_client` against `api.phodex.app:443` on this Mac currently shows an intercepting issuer chain that includes `CN=palo.cellebrite.local`.
- The same machine can establish raw TLS to the host, but Node WebSocket traffic is still reset after CA trust is injected.
- For this environment, hosted upstream should be treated as "blocked by network policy until proven otherwise" rather than "broken in CRA."
- The practical proof gate is now:
  - test the hosted path on a non-intercepted network such as a hotspot or home Wi-Fi
  - if that works, keep hosted upstream as the default daily-driver path
  - if that still fails, or if this managed network is the permanent environment, prefer the local or self-hosted relay path for this machine

## Open Questions

- Does the iPhone app accept plain `ws://` on LAN, or does it effectively require `wss://`?
- Does the iPhone app rely on hosted relay semantics beyond the basic QR payload and socket path?
- Can the full approval flow work without the hosted push service?
- Is self-hosting officially supported for the current phone build or only intended for a future phase?
- Can the hosted upstream relay be reached reliably from this managed network even after Node trusts the intercepting CA chain?

## CRA Implications

- Primary path should be: prove official `remodex` first.
- CRA should wrap upstream behavior thinly for audit, policy, and replay needs.
- The in-repo `remodex/` folder should be treated as a compatibility study only.
- The local relay remains a research surface; hosted upstream is the daily-driver baseline for this repo.
- For managed networks that intercept TLS, hosted upstream may be impractical even when the wrapper and patch are correct.
- The smallest justified fork point is upstream `secure-device-state.js`, not the full bridge or relay.
- Forking bridge or relay behavior should happen only after a known-good upstream phone pairing exists and a hard blocker is documented.

## Decision Gate

Wrap upstream and do not fork if:

- official Remodex bridge starts
- phone pairs
- approvals round-trip
- hosted or self-hosted relay constraints are acceptable

Fork the minimum surface necessary only if:

- upstream app blocks the required deployment model
- upstream relay assumptions violate a hard project constraint
- upstream bridge lacks an extension point required for audit or policy
