# CRA Output Contracts

The orchestrator and specialist skills use the following output contracts to keep multi-step CRA work consistent.

## Orchestrator Output

The orchestrator should assemble final delivery using these sections:

- Goal
- Recommended approach
- Files or artifacts created or changed
- Commands to run
- Risks and constraints
- Validation and next checks

## Specialist Deliverables

Each specialist output should be concrete enough to hand to an implementer without extra routing work.

- `cra-backend-developer`: watcher script shape, dependencies, parsing rules, payload schema, test cases, and performance notes
- `cra-macos-engineer`: actuator scripts, launchd plist shape, `launchctl` commands, permission steps, and recovery guidance
- `cra-network-architect`: Tailscale ACL changes, Shortcut flow description, SSH command shape, and off-network validation steps
- `cra-security-specialist`: SSH hardening config, ACL policy, key rotation procedure, and audit findings with approval status

## Delivery Rules

- Every output must state assumptions when the environment is not yet verified.
- Commands should be copyable as written and scoped to the minimum necessary privileges.
- Validation must include at least one end-to-end or integration check relevant to the subsystem.
- Risks should call out concrete breakpoints such as revoked permissions, ACL gaps, webhook downtime, or command injection surfaces.
