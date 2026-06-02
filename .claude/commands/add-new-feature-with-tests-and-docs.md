---
name: add-new-feature-with-tests-and-docs
description: Workflow command scaffold for add-new-feature-with-tests-and-docs in keepalive-win.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /add-new-feature-with-tests-and-docs

Use this workflow when working on **add-new-feature-with-tests-and-docs** in `keepalive-win`.

## Goal

Implements a new feature, adds corresponding Pester tests, and documents the feature in the README.

## Common Files

- `KeepAlive.Core.ps1`
- `keepalive.ps1`
- `KeepAlive.Tests.ps1`
- `README.md`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Implement core logic in KeepAlive.Core.ps1 (pure/testable helpers and parameter handling).
- Update keepalive.ps1 to wire up the feature to the CLI and handle side effects.
- Add or update Pester tests in KeepAlive.Tests.ps1 to cover the new feature.
- Update README.md to document the new feature, flags, and usage.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.