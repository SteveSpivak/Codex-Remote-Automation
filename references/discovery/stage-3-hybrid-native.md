# Stage 3 Hybrid Native Fallback Notes

These notes describe the hybrid-native fallback prototype. They are retained for fallback and discovery work after the App-Server-first pivot.

## What Was Added

- A validated `shortcut-entry` CLI command and thin shell wrapper for iPhone/macOS Shortcuts
- An Apple Vision OCR helper that captures the visible Codex window and returns text plus screen coordinates
- A click helper that can actuate the OCR target only after the expected prompt context is present in the OCR output

## Current Fallback Strategy Order

1. Accessibility selector by frozen `AXDescription`
2. Vision OCR using `ocr_text_candidates` plus `required_context_phrases`
3. CLI/MCP pivot if neither path is reliable enough

## Constraints

- The OCR path depends on Screen Recording permission for the helper binary.
- The click path depends on Accessibility permission for the helper binary.
- Visual fallback should remain disabled until `config/codex-selectors.json` is populated with real prompt-state context phrases.
- The March 13, 2026 live probe compiled cleanly but returned `No matching on-screen window was found.`, so the next live validation still requires a visible Codex approval window on the active Space.

## Open-Source Fallback Candidates

- SikuliX
- UI.Vision

These are intentionally not wired into the critical path. Only evaluate them if Apple-native OCR cannot reach the required reliability.
