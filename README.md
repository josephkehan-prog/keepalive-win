# keepalive-win

A zero-dependency Windows PowerShell CLI that keeps your machine awake so M365 web tabs
(Outlook / SharePoint / Teams) don't auto-log-out from sleep, screen-lock, or idle.

## How it works

While running, it:
- blocks system sleep + display-off via `SetThreadExecutionState`, and
- sends a harmless **F15** keypress every *N* seconds to reset the Windows idle timer
  (`GetLastInputInfo`), which is what drives screen-lock and most app/tab idle detection.

On exit it always restores normal power behavior (`try/finally`).

## Usage

```powershell
keepalive                      # stay awake until Ctrl+C
keepalive -Minutes 90 -Quiet   # stay awake 90 minutes, no status output
keepalive -IntervalSeconds 30  # nudge every 30s (minimum 10)
```

Or run the script directly: `pwsh -File .\keepalive.ps1`. Double-click `keepalive.cmd` to launch.

**Run on login:** Task Scheduler → trigger *At log on* → action `pwsh -File <path>\keepalive.ps1 -Quiet`.

## Scope & limitation

This keeps the **OS** active — it fixes logouts caused by sleep / screen-lock / idle. It does
**not** bypass authentication, and it cannot guarantee defeat of an admin-enforced *server-side*
M365 idle session timeout that keys off browser-tab interaction. For that case, see the optional
"Step 5: browser keep-alive" in [`plans/keepalive-cli-anti-idle.md`](plans/keepalive-cli-anti-idle.md).

## Files

| File | Purpose |
|---|---|
| `keepalive.ps1` | The CLI (param block + Win32 P/Invoke + run loop) |
| `KeepAlive.Core.ps1` | Pure, testable logic (interval validation, end-time math, flag/stop logic) |
| `KeepAlive.Tests.ps1` | Pester tests (13 tests, 100% core coverage) |
| `keepalive.cmd` | Double-click / `keepalive` launcher |
| `plans/` | Construction blueprint, including the optional browser keep-alive step |

## Tests

```powershell
Invoke-Pester -Path .\KeepAlive.Tests.ps1
```

Requires PowerShell 7+ and Pester (3.4 ships with Windows; works under pwsh 7).
