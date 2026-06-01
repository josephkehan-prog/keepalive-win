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
interval, keeping their message loops active. It never steals focus.

With `-BrowserKeepAlive` it also connects to Chrome/Edge via the remote debugging protocol
(CDP) and sends a harmless F15 key event to each M365 tab, resetting the tab-level idle
timer for cases where the server-side M365 session timeout is the root cause. Requires the
browser to be launched with `--remote-debugging-port=9222`.

On exit it always restores normal power behavior (`try/finally`).

## Usage

```powershell
keepalive                          # stay awake until Ctrl+C
keepalive -Minutes 90 -Quiet       # stay awake 90 minutes, no status output
keepalive -IntervalSeconds 30      # nudge every 30s (minimum 10)
keepalive -SystemOnly              # keep the machine awake but let the display sleep
keepalive -AllMicrosoftApps        # also keep Outlook/Teams/Office/Edge non-idle when backgrounded
keepalive -BrowserKeepAlive        # also nudge M365 browser tabs via CDP (see below)
keepalive -WatchProcess teams      # auto-stop when Teams exits
keepalive -Profile meeting         # load the 'meeting' preset from keepalive.json
keepalive -Headless                # run detached in the background, then close the terminal
keepalive -Stop                    # stop the background process started with -Headless
keepalive -Status                  # show whether the logon task and headless process are running
keepalive -Install -Quiet          # auto-start at every logon (see below)
keepalive -Uninstall               # remove the logon auto-start
```

Or run the script directly: `pwsh -File .\keepalive.ps1`. Double-click `keepalive.cmd` to launch.

**Run on login (`-Install`):** `keepalive -Install` registers a *Run at logon* scheduled task
named `KeepAlive` that relaunches the tool automatically (hidden window) each time you sign in.
Any `-IntervalSeconds` / `-Minutes` / `-Quiet` / `-SystemOnly` / `-AllMicrosoftApps` flags you
pass alongside `-Install` are baked into the task. Remove it with `keepalive -Uninstall`.

**Background (`-Headless`):** `keepalive -Headless` launches a hidden, detached copy, writes its
PID to `%TEMP%\keepalive.pid`, and returns immediately so you can close the terminal. Stop it
with `keepalive -Stop`, or check whether it is running with `keepalive -Status`.

**Watch a process (`-WatchProcess`):** `keepalive -WatchProcess teams` stays awake only while
Teams is running. When the process exits, keepalive stops automatically.

**Named profiles (`-Profile`):** Store presets in `keepalive.json` (same directory as the
script). The bundled file includes `meeting` (120 min + SystemOnly), `focus`
(AllMicrosoftApps + Quiet), `overnight`, and `tab` (BrowserKeepAlive). CLI flags always override
profile values.

**Browser tab keep-alive (`-BrowserKeepAlive`):** Launch Chrome or Edge with
`--remote-debugging-port=9222` first, then run `keepalive -BrowserKeepAlive`. The tool will
find and nudge M365 tabs (Outlook, Teams, SharePoint, OneDrive, Office.com) via CDP each
interval. Use this only if the OS-level keep-awake alone does not prevent your M365 session
from signing out (i.e., the cause is a server-side tab-idle timeout).

## Scope & limitation

This keeps the **OS** active — it fixes logouts caused by sleep / screen-lock / idle. It does
**not** bypass authentication, and it cannot guarantee defeat of an admin-enforced *server-side*
M365 idle session timeout that keys off browser-tab interaction. For that case, use
`-BrowserKeepAlive` or see the design notes in
[`plans/keepalive-cli-anti-idle.md`](plans/keepalive-cli-anti-idle.md).

## Files

| File | Purpose |
|---|---|
| `keepalive.ps1` | The CLI (param block + Win32 P/Invoke + run loop + lifecycle management) |
| `KeepAlive.Core.ps1` | Pure, testable logic (interval, flags, loop, PID path, profiles, CDP URL helpers) |
| `KeepAlive.Tests.ps1` | Pester tests (53 tests, 100% core coverage) |
| `keepalive.json` | Named profile presets (`meeting`, `focus`, `overnight`, `tab`) |
| `PSScriptAnalyzerSettings.psd1` | PSScriptAnalyzer rule exclusions for CI |
| `keepalive.cmd` | Double-click / `keepalive` launcher |
| `plans/` | Construction blueprint, including the optional browser keep-alive step |

## Tests

```powershell
Invoke-Pester -Path .\KeepAlive.Tests.ps1
```

Requires PowerShell 7+ and Pester (3.4 ships with Windows; works under pwsh 7).

CI runs both Pester and PSScriptAnalyzer on every push and pull request.
