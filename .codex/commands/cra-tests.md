---
description: Run the CRA unit tests and summarize failures or residual risks.
---

From the repo root:

1. Run `python3 -m unittest discover -s tests -p 'test_*.py'`.
2. Report failures first, then any fallback or architecture risks that remain.
3. Do not edit files unless the user explicitly asked for implementation work.
