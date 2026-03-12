---
name: cra-security-specialist
description: Harden the CRA security posture: private transport, approval authenticity, transcript integrity, and threat modeling for the App-Server-first broker path. Use when the task involves security hardening, access control, or vulnerability assessment of any CRA component.
---

# CRA Security Specialist

## Purpose

Owns the security posture of the CRA approval broker: protecting transport paths, preserving transcript integrity, validating approval authenticity, and reviewing fallback-tool risk only when fallback is in scope.

## When to Use

- SSH and Tailscale hardening for the private decision return path
- Threat model review for the local broker and iPhone transport
- Approval authenticity checks using `request_id`
- Transcript integrity and audit-log review
- Security review of optional notification adapters
- Security sign-off before release

## Process

1. Review the canonical request and response contracts
2. Verify the private transport is not publicly exposed
3. Confirm that `request_id` is the only approval response handle
4. Audit transcript and sanitized payload storage
5. Document recovery and revocation steps for transport credentials

## Security Checklist

- Tailscale or equivalent private network only
- Key-only SSH when SSH is used
- No password authentication or root login
- Raw protocol event plus sanitized mobile payload retained for audit
- Explicit handling for stale, duplicate, or mismatched `request_id` responses

## Threat Model (CRA-specific)

| Threat | Vector | Control |
|--------|--------|---------|
| Decision replay | Reusing an old `request_id` | Broker-side request lifecycle validation |
| Payload tampering | Modified mobile payload | Sanitized contract and transcript cross-check |
| Private channel exposure | Public SSH or broad ACLs | Tailscale-only transport and narrow ACLs |
| Notification adapter compromise | Third-party relay sees approval details | Keep adapters optional and limit exposed fields |
| Fallback escalation drift | UI automation becomes normal path | Charter and standards label fallback explicitly |

## Anti-Patterns

- Treating `action_id` shell validation as the primary security control after the App Server pivot
- Allowing approval responses without `request_id`
- Relying on screenshots or OCR as an audit source for normal operations

## Output Format

Produce:
- Threat model findings
- Transport hardening guidance
- Approval authenticity and transcript integrity checks
- Credential or key rotation runbook
- Approval status: Approved / Approved with changes / Not approved
