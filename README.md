# keepalive-win

A zero-dependency Windows PowerShell CLI that keeps your machine awake so M365 web tabs
(Outlook / SharePoint / Teams) don't auto-log-out from sleep, screen-lock, or idle.

## How it works

While running, it:
- blocks system sleep + display-off via `SetThreadExecutionState` (use `-SystemOnly` to keep
  the machine awake while still letting the monitor turn off), and
- sends a harmless **F15** keypress every *N* seconds to reset the Windows idle timer
  (`GetLastInputInfo`), which is what drives screen-lock and most app/tab idle detection.

With `-AllMicrosoftApps` it additionally posts a harmless no-op window message (`WM_NULL`) to
each running Microsoft desktop app (Outlook, Teams, Word, Excel, OneNote, Edge, …) every
interval, so they stay non-idle even when minimized or in the background. It never steals focus.

On exit it always restores normal power behavior (`try/finally`).

## Usage

```powershell
keepalive                      # stay awake until Ctrl+C
keepalive -Minutes 90 -Quiet   # stay awake 90 minutes, no status output
keepalive -IntervalSeconds 30  # nudge every 30s (minimum 10)
keepalive -SystemOnly          # keep the machine awake but let the display sleep
keepalive -AllMicrosoftApps    # also keep Outlook/Teams/Office/Edge non-idle when backgrounded
keepalive -Headless            # run detached in the background, then close the terminal
keepalive -Install -Quiet      # auto-start at every logon (see below)
keepalive -Uninstall           # remove the logon auto-start
```

Or run the script directly: `pwsh -File .\keepalive.ps1`. Double-click `keepalive.cmd` to launch.

**Run on login (`-Install`):** `keepalive -Install` registers a *Run at logon* scheduled task
named `KeepAlive` that relaunches the tool automatically (hidden window) each time you sign in.
Any `-IntervalSeconds` / `-Minutes` / `-Quiet` flags you pass alongside `-Install` are baked into
the task. Remove it with `keepalive -Uninstall`. (This automates what you'd otherwise set up by
hand in Task Scheduler.)

**Background (`-Headless`):** `keepalive -Headless` launches a hidden, detached copy and returns
immediately, so you can close the terminal and keep the machine awake. It implies `-Quiet`. Stop
it from Task Manager (end the background `pwsh` process), or use `-Install`/`-Uninstall` if you
want a managed, restart-surviving setup instead.

## Scope & limitation

This keeps the **OS** active — it fixes logouts caused by sleep / screen-lock / idle. It does
**not** bypass authentication, and it cannot guarantee defeat of an admin-enforced *server-side*
M365 idle session timeout that keys off browser-tab interaction. For that case, see the optional
"Step 5: browser keep-alive" in [`plans/keepalive-cli-anti-idle.md`](plans/keepalive-cli-anti-idle.md).

## Files

| File | Purpose |
|---|---|
| `keepalive.ps1` | The CLI (param block + Win32 P/Invoke + run loop + install/headless launch) |
| `KeepAlive.Core.ps1` | Pure, testable logic (interval validation, end-time math, flag/stop logic, relaunch-arg building) |
| `KeepAlive.Tests.ps1` | Pester tests (34 tests, 100% core coverage) |
| `keepalive.cmd` | Double-click / `keepalive` launcher |
| `plans/` | Construction blueprint, including the optional browser keep-alive step |

## Tests

```powershell
Invoke-Pester -Path .\KeepAlive.Tests.ps1
```

Requires PowerShell 7+ and Pester (3.4 ships with Windows; works under pwsh 7).
