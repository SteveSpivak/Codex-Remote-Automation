# Codex Remote Automation

Codex Remote Automation (CRA) is a documentation-first project for adding a human-in-the-loop approval gate to Codex actions on macOS. The system routes approval requests from a Mac to an iPhone, then sends the user's decision back over a locked-down Tailscale and SSH path to actuate the Codex UI.

This repository currently contains the project charter, the CRA routing skill, and four specialist skills that break the system into security, networking, macOS automation, and backend watcher concerns. It is intentionally documentation-only in this first version.

## Architecture Summary

- Outbound path: Codex output -> Python watcher daemon -> Pushcut/Pushover -> iPhone notification
- Inbound path: iPhone Shortcut -> Tailscale SSH -> macOS actuator -> Codex UI action
- Security model: no public exposure, key-only SSH, tight Tailscale ACLs, payload sanitization throughout

## Repository Layout

```text
.
|-- README.md
|-- references/
|   |-- cra-anti-patterns.md
|   |-- cra-charter.md
|   |-- cra-standards.md
|   `-- output-contracts.md
`-- skills/
    |-- cra-backend-developer/SKILL.md
    |-- cra-macos-engineer/SKILL.md
    |-- cra-network-architect/SKILL.md
    |-- cra-orchestrator/SKILL.md
    `-- cra-security-specialist/SKILL.md
```

## Core Docs

- [Project charter](references/cra-charter.md)
- [CRA standards](references/cra-standards.md)
- [CRA anti-patterns](references/cra-anti-patterns.md)
- [CRA output contracts](references/output-contracts.md)

## Skills

- [CRA orchestrator](skills/cra-orchestrator/SKILL.md)
- [CRA backend developer](skills/cra-backend-developer/SKILL.md)
- [CRA macOS engineer](skills/cra-macos-engineer/SKILL.md)
- [CRA network architect](skills/cra-network-architect/SKILL.md)
- [CRA security specialist](skills/cra-security-specialist/SKILL.md)
