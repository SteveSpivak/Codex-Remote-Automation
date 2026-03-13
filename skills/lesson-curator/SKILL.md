---
name: lesson-curator
description: Turn durable findings into repo lessons, update the affected docs or skills, and preserve architecture decisions beyond chat history. Use when a bug, blocker, or proof changes the repo's workflow, architecture, or routing guidance.
---

# Lesson Curator

## Purpose

Preserves important findings as reusable operational knowledge.

## When To Use

- A finding changes the architecture decision
- A new blocker changes the recommended workflow
- A failure mode should update skill routing or runbooks
- A lesson would prevent repeating the same mistake in a future project

## Process

1. Confirm the finding is durable, not a transient glitch.
2. Choose the lesson area under `references/lessons/`.
3. Capture one concrete lesson per file.
4. Update the related docs or skills if the lesson changes behavior.
5. Link the evidence source and the decision that followed from it.

## Required Links

- At least one evidence source
- At least one affected skill or reference doc
- A follow-up action or decision gate

## Hard Rules

- Do not write a lesson for a guess.
- Do not combine unrelated findings into one file.
- If the lesson changes architecture, update the relevant guidance in the same pass.
- Keep the lesson short enough to be reused quickly.

## Deliverables

- Lesson file path
- Related docs or skills updated
- Decision captured
- Follow-up still required, if any

## Output Format

- Lesson title
- Why it matters
- Evidence used
- Docs or skills updated
- Follow-up
