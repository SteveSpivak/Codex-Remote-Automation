# Remodex Compatibility Study

This folder is an experiment and compatibility study, not the canonical CRA implementation path.

## Purpose

- capture what CRA learned while reverse-engineering and emulating upstream Remodex behavior
- provide a local sandbox for protocol experiments
- preserve research artifacts that may inform a future minimal fork

## What This Folder Is Not

- not the primary bridge implementation
- not proof that the Remodex iPhone app supports every self-hosted relay shape here
- not a substitute for proving the official upstream `remodex` package first

## Current Policy

1. Prove the official upstream package and app first.
2. Wrap upstream behavior thinly for CRA audit and policy needs.
3. Fork only if upstream proof identifies a hard blocker.

## Related Docs

- [Upstream research notes](../references/research/remodex-upstream-assessment.md)
- [Project charter](../references/cra-charter.md)
