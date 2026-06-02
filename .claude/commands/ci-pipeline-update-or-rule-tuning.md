---
name: ci-pipeline-update-or-rule-tuning
description: Workflow command scaffold for ci-pipeline-update-or-rule-tuning in keepalive-win.
allowed_tools: ["Bash", "Read", "Write", "Grep", "Glob"]
---

# /ci-pipeline-update-or-rule-tuning

Use this workflow when working on **ci-pipeline-update-or-rule-tuning** in `keepalive-win`.

## Goal

Modifies the CI pipeline for Pester or PSScriptAnalyzer, including workflow YAML and analyzer settings.

## Common Files

- `.github/workflows/tests.yml`
- `PSScriptAnalyzerSettings.psd1`

## Suggested Sequence

1. Understand the current state and failure mode before editing.
2. Make the smallest coherent change that satisfies the workflow goal.
3. Run the most relevant verification for touched files.
4. Summarize what changed and what still needs review.

## Typical Commit Signals

- Edit .github/workflows/tests.yml to add, modify, or fix CI steps for running tests or static analysis.
- Edit PSScriptAnalyzerSettings.psd1 to add, exclude, or whitelist rules as needed.
- Optionally, update code files (e.g., keepalive.ps1, KeepAlive.Core.ps1) to comply with or suppress analyzer findings.

## Notes

- Treat this as a scaffold, not a hard-coded script.
- Update the command if the workflow evolves materially.