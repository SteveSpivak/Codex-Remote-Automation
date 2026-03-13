# prove upstream before forking remodex

Date: 2026-03-13
Area: upstream
Status: validated

## Context

CRA initially moved toward a custom Remodex-compatible bridge and relay implementation before proving the official upstream package in the target environment.

## Trigger

The custom path produced QR and protocol artifacts, but compatibility with the real Remodex iPhone app remained uncertain.

## What Happened

Local reverse engineering was useful for understanding payload shape and relay expectations, but it was not sufficient proof that the official iPhone app would accept the custom implementation as a full substitute for the upstream bridge.

## Lesson

For third-party bridge products, prove the upstream package first, then wrap it, and only fork where evidence shows a hard requirement cannot be met otherwise.

## Evidence

- the official upstream package could be installed and launched locally
- the official bridge produced valid pairing behavior
- the custom implementation still left critical uncertainty around official iPhone-app acceptance

## Decision

Adopt an upstream-first strategy for CRA and treat the in-repo `remodex/` folder as a compatibility study rather than the canonical implementation path.

## Follow-Up

- keep a narrow `cra-upstream-integration` skill
- require a known-good upstream phone pairing before any bridge or relay fork is approved

## Related Skills

- `cra-orchestrator`
- `cra-upstream-integration`
