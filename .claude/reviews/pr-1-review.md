# PR Review: #1 — CI + run-at-logon (-Install) and background (-Headless) features

**Reviewed**: 2026-06-01
**Author**: josephkehan-prog (self-review)
**Branch**: claude/test-coverage-analysis-4LngK → main
**Decision**: COMMENT (draft PR) — no CRITICAL/HIGH issues; a few MEDIUM/LOW nits

## Summary

Adds CI (Pester on Windows) plus three flags — `-Install`/`-Uninstall`, `-Headless`,
`-SystemOnly`, `-AllMicrosoftApps`. The code keeps the repo's pure-vs-side-effect split
cleanly: all new decision logic is in testable Core functions (34 Pester tests now), and
the Win32/Task-Scheduler side effects stay in `keepalive.ps1`. No security concerns. The
findings below are quality/robustness nits, not blockers.

## Findings

### CRITICAL
None.

### HIGH
None.

### MEDIUM

1. **`Test-IsMicrosoftApp` uses culture-sensitive `.ToLower()`** — `KeepAlive.Core.ps1:104`.
   In the Turkish locale (tr-TR), `'VISIO'.ToLower()` → `'vısıo'` (dotless ı), so the
   uppercase image name would fail to match the lowercase `'visio'` in the list. Since the
   target audience is Windows/M365 users who may run non-English locales, use
   `.ToLowerInvariant()` instead. Affects any app name containing `I` (visio, lync via "Lync").
   *Fix:* `$name = $ProcessName.Trim().ToLowerInvariant()`.

2. **`-Uninstall` throws an ugly error when no task exists** — `keepalive.ps1:98-100`.
   `Unregister-ScheduledTask` errors ("No MSFT_ScheduledTask objects found") if the
   `KeepAlive` task was never installed, surfacing a red stack to the user. Guard it:
   check `Get-ScheduledTask -TaskName ... -ErrorAction SilentlyContinue` first and print a
   friendly "nothing to remove" message, or wrap in try/catch.

3. **Side-effecting paths remain untested** (pre-existing gap). `Send-AppNudge`,
   `Install/Uninstall`, `Start-Headless`, and crucially the `try/finally` "always restore
   power" guarantee + run loop in `keepalive.ps1` have no tests. This is the exact gap the
   original coverage analysis flagged; tracked as a follow-up (refactor the loop into a
   sourceable, dependency-injected function). Not introduced by this PR.

### LOW

4. **`.PARAMETER Install` / `.PARAMETER Headless` help is stale** — `keepalive.ps1:28-38`.
   The text still says only `-IntervalSeconds / -Minutes / -Quiet` are baked into the
   relaunch; `-SystemOnly` and `-AllMicrosoftApps` are now propagated too. Update the help.

5. **No precedence note for combined mode flags** — `keepalive.ps1`. `-Install` takes
   priority over `-Headless` if both are passed (Install exits first). Harmless, but a
   one-line comment or a validation message would avoid surprise.

6. **`-AllMicrosoftApps` effectiveness is best-effort** — `keepalive.ps1:155-166`.
   `WM_NULL` keeps a window's message pump active but won't reset app idle states that key
   purely off the global `GetLastInputInfo` (already handled by the F15 nudge). The README
   notes "non-idle", which slightly oversells it for some apps. Consider softening to
   "keeps their message loop active". Design choice, not a bug.

## Validation Results

| Check | Result |
|---|---|
| Type check | N/A (PowerShell) |
| Lint (PSScriptAnalyzer) | Skipped — not in CI or local container |
| Tests (Pester) | Delegated to CI — `Pester (Windows)` job; no local pwsh available |
| Build | N/A |

## Files Reviewed

- `.github/workflows/tests.yml` — Added
- `KeepAlive.Core.ps1` — Modified
- `KeepAlive.Tests.ps1` — Modified
- `keepalive.ps1` — Modified
- `README.md` — Modified
