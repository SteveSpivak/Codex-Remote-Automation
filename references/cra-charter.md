# Project Charter: Codex Remote Automation (CRA)
**Version:** 1.0  
**Status:** Active  
**Owner:** Steve Spivak  
**Last updated:** 2026-03-12

---

## 1. Problem Statement

Autonomous coding agents (Codex) can execute high-stakes actions — force-pushes, destructive file operations, runaway API loops — without human review. Leaving an agent running unattended requires either accepting that risk or staying at the keyboard. Neither is acceptable at scale.

Project CRA solves this by inserting a real-time human-in-the-loop (HITL) gate into the Codex execution path, operable from an iPhone anywhere in the world with sub-second feedback latency.

---

## 2. Goals

| Goal | Measurable outcome |
|------|--------------------|
| Real-time agent approval from iOS | Approve/deny any Codex action within 2 seconds of notification |
| Sub-0.5s feedback loop | iPhone tap → Mac execution in < 500ms (P95) |
| Zero exposed attack surface | No open router ports; no public-internet SSH; no cloud-sync polling |
| Daemon stability | Watcher uptime ≥ 99.9%; auto-restart on failure |
| Minimal system overhead | Watcher CPU < 1%; RAM < 50MB idle |

### Non-goals
- Building a general remote-control framework for arbitrary macOS apps
- Replacing the Codex UI or modifying Codex internals
- Supporting multiple simultaneous approvers

---

## 3. Architecture

### 3.1 Topology

```
Codex (macOS)
    ↓ stdout / log file
Watcher Daemon (Python, launchd)
    ↓ JSON webhook
Pushcut / Pushover API → APNs → iPhone notification
    ↓ user taps Approve / Deny
iOS Shortcut
    ↓ SSH over Tailscale (WireGuard, MagicDNS)
macOS sshd
    ↓ AppleScript / JXA actuator
Codex UI action executed
```

### 3.2 Outbound path (Codex → iPhone)

- Watcher uses Python `watchdog` (FSEvents on macOS) to tail Codex log output — zero UI scraping, near-zero CPU
- On approval-required event: constructs a sanitized JSON payload and POSTs to Pushcut/Pushover webhook
- Payload schema:
  ```json
  {
    "action_id": "<uuid4>",
    "context": "<agent intention, human-readable>",
    "risk_level": "low | medium | high",
    "timestamp": "<ISO8601>"
  }
  ```
- `action_id` is a UUID4 generated per event — prevents replay attacks
- Debounce window: 200ms minimum between notifications for the same action

### 3.3 Inbound path (iPhone → Codex)

- iOS Shortcut receives Pushcut webhook payload, parses `action_id` and decision
- Executes SSH command over Tailscale to macOS: `ssh codex-mac@<macbook>.tailnet.ts.net`
- macOS receives command, runs AppleScript/JXA actuator that clicks the appropriate Codex UI element
- Total target latency: < 500ms from tap to execution

### 3.4 Network security

- **Tailscale** (WireGuard) provides the secure tunnel — no port forwarding, no DDNS, no public exposure
- **Tailscale ACLs** restrict the iPhone node to port 22 on the Codex Mac only
- **SSH**: Ed25519 keys only; `PasswordAuthentication no`; `PermitRootLogin no`
- The Mac is not reachable from the public internet at any point

### 3.5 Explicitly rejected alternatives

| Alternative | Reason rejected |
|-------------|-----------------|
| iCloud / Dropbox / Google Drive polling | 5–120s sync latency; file collision risk; polling limits |
| macOS Accessibility tree scraping | Brittle across app updates; battery drain; high CPU |
| Dynamic DNS + router port forward | Exposes Mac to public internet; requires IP tracking |
| Pushbullet / similar cloud relay | Additional trust boundary; latency unpredictable |

---

## 4. Implementation Phases

### Phase 1 — Security foundation
- Install Tailscale on macOS and iOS; verify peer-to-peer connectivity via MagicDNS
- Generate Ed25519 keypair; configure `sshd_config`: key-only auth, no root login
- Configure Tailscale ACLs to limit iPhone to port 22 on Codex Mac
- **Milestone:** `echo "Hello World"` from iOS Shortcuts to macOS over Tailscale SSH while off local Wi-Fi

### Phase 2 — Outbound trigger
- Implement Python watcher daemon with `watchdog` / FSEvents
- Add debouncing, payload sanitization, and special-character escaping
- Integrate Pushcut/Pushover webhook
- Wrap in `launchd` `.plist` with `KeepAlive`
- **Milestone:** Codex log event → iPhone notification with correct payload in < 2s

### Phase 3 — iOS logic bridge
- Build iOS Shortcut: parse incoming payload, extract `action_id` and `risk_level`
- Design notification UI: color-coded by risk level, lock-screen actionable (no app open required)
- Map decision to sanitized SSH command arguments
- **Milestone:** Notification received → SSH command fires correctly on Approve and Deny paths

### Phase 4 — macOS actuator
- Write AppleScript/JXA scripts that translate SSH command into Codex UI clicks
- Harden: handle Codex not in foreground, handle UI element not found
- Wrap actuator in `launchd` daemon alongside watcher
- **Milestone:** End-to-end — intentional Codex block → notification → iOS approval → Mac executes

### Phase 5 — QA and hardening
- Simulate network drop during approval (cellular dead zone)
- Rapid-fire notification flood test; verify debounce
- Security audit: SSH config, Tailscale ACLs, payload sanitization
- Measure all KPIs against targets
- **Milestone:** All KPI targets met; edge cases documented

---

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| macOS Accessibility permissions revoked after OS update | Medium | High | Launchd restart; alert on daemon failure |
| Tailscale iOS VPN drops on network switch | Medium | Medium | Shortcut retry logic with timeout exception handling |
| AppleScript target element changes after Codex update | Medium | High | Element selection by stable `AXDescription`; test after Codex updates |
| Duplicate notifications from rapid log writes | Low | Medium | 200ms debounce in watcher |
| Payload injection via malformed log output | Low | High | Strict character escaping and JSON schema validation before webhook POST |
| Pushcut/Pushover API downtime | Low | High | Fallback to local notification or audio alert on Mac |

---

## 6. KPIs

| Metric | Target |
|--------|--------|
| Inbound feedback latency (tap → Mac action) | < 500ms P95 |
| Outbound notification latency (event → iPhone vibrate) | < 2.0s |
| Mis-click / misparse rate | 0% |
| Watcher daemon uptime | ≥ 99.9% |
| macOS CPU usage (idle) | < 1% |
| macOS RAM usage (idle) | < 50MB |
| iOS battery contribution | < 1% daily |

---

## 7. Roles

| Role | Responsibility |
|------|---------------|
| macOS Automation Engineer | AppleScript/JXA actuator; launchd daemon management |
| Networking & Mobile Architect | Tailscale setup; iOS Shortcuts logic; Pushcut integration |
| Security Specialist | SSH hardening; Tailscale ACLs; payload sanitization audit |
| Backend / Python Developer | Watcher daemon; log parsing; debounce; webhook integration |

In a single-agent setup (Codex), these roles map to sequential implementation phases rather than parallel team members.

---

## 8. Definition of Done

- [ ] End-to-end flow passes Phase 5 milestone
- [ ] All KPI targets met under simulated adverse conditions
- [ ] Security audit complete: no open ports, no password auth, ACLs locked
- [ ] Launchd daemons auto-restart; watcher survives sleep/wake cycle
- [ ] Playbook written: how to re-authorize Accessibility permissions after macOS update
- [ ] Playbook written: how to rotate SSH keys
