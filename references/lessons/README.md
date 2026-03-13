# CRA Lessons Architecture

Use this tree to preserve durable lessons by topic instead of leaving them only in chat history.

## Goals

- keep lessons close to the repo and architecture docs
- make lessons searchable by topic
- separate proven findings from guesses
- connect lessons back to the skill or subsystem they should update

## Folder Taxonomy

- `platform/`
  - Codex CLI, App Server, auth, config, `.codex`, local runtime behavior
- `upstream/`
  - Remodex package behavior, env vars, upgrade drift, fork-gate evidence
- `mobile/`
  - iPhone app behavior, pairing, scan flow, ATS, relay reachability
- `relay/`
  - hosted-vs-self-hosted evidence, transport quirks, TLS, reconnect behavior
- `security/`
  - trust boundaries, state storage, keychain, risk decisions
- `fallback/`
  - Shortcuts, iMessage, Accessibility, OCR, emergency-only lessons
- `workflow/`
  - skill usage, repo operating rules, implementation process, validation flow

## File Naming

Use one lesson per file:

`YYYY-MM-DD-short-slug.md`

Example:

`2026-03-13-remodex-home-breaks-codex-auth.md`

## Required Sections

- `Context`
- `Trigger`
- `What Happened`
- `Lesson`
- `Evidence`
- `Decision`
- `Follow-Up`
- `Related Skills`

## Rules

- Keep one concrete lesson per file.
- Put raw facts before interpretation.
- Link a lesson to at least one skill or reference doc that should change because of it.
- If a lesson changes the architecture, also update:
  - `references/cra-charter.md`
  - `references/cra-standards.md`
  - the affected skill file

## Fast Path

Create a new lesson file with:

```bash
bash scripts/new_lesson.sh <area> <slug>
```
