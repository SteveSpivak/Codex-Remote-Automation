# remodex home breaks codex auth

Date: 2026-03-13
Area: platform
Status: validated

## Context

We ran the official upstream `remodex up` bridge while overriding `HOME` to a temporary directory in order to avoid writing under the real user home during testing.

## Trigger

The bridge paired with the phone, but Codex requests failed with `401 Unauthorized: Missing bearer or basic authentication`.

## What Happened

The upstream Remodex package spawns `codex app-server` using the inherited environment. Overriding `HOME` hid the normal `~/.codex` login state, so Codex started without the existing ChatGPT authentication context.

## Lesson

Do not override `HOME` for real upstream bridge tests unless you also intend to create a separate Codex login state in that home directory.

## Evidence

- `codex login status` under the real home reported `Logged in using ChatGPT`
- the bridge paired successfully before the 401s, proving the failure was after mobile pairing
- the 401 disappeared as the main suspected root cause once the `HOME` override was identified

## Decision

Use the real home directory for upstream Remodex proof runs unless a test explicitly requires isolated state.

## Follow-Up

- keep this rule in operator guidance
- if isolated-state testing is required later, log in Codex explicitly in that isolated home

## Related Skills

- `cra-macos-engineer`
- `cra-upstream-integration`
