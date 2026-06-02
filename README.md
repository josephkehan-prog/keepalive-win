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

While it runs, each status line is prefixed with a small ASCII cat that blinks
(`=^.^=` / `=^-^=`) so you can tell at a glance the CLI is still active; on exit it
prints a sleeping cat (`=^.^=zZ`).

On exit it always restores normal power behavior (`try/finally`).

## Getting started

### Prerequisites

- **Windows** (the keep-awake and idle-nudge use Win32 APIs)
- **PowerShell 7+** (`pwsh`). Check with `pwsh --version`; install from the
  [PowerShell releases](https://github.com/PowerShell/PowerShell/releases) if needed.

### Set up

1. **Get the files.** Clone or download this repo to a folder you'll keep, e.g.
   `C:\Tools\keepalive-win`:
   ```powershell
   git clone https://github.com/josephkehan-prog/keepalive-win.git C:\Tools\keepalive-win
   cd C:\Tools\keepalive-win
   ```
2. **Run it once to confirm it works:**
   ```powershell
   pwsh -File .\keepalive.ps1 -Minutes 1
   ```
   You should see the banner and a blinking `=^.^=` status line. It stops itself
   after a minute (or press **Ctrl+C**).
3. **(Optional) Make `keepalive` callable from anywhere.** Add the folder to your
   `PATH` so the bundled `keepalive.cmd` launcher resolves as just `keepalive`:
   ```powershell
   $env:PATH += ';C:\Tools\keepalive-win'          # current session only
   [Environment]::SetEnvironmentVariable('PATH',
     [Environment]::GetEnvironmentVariable('PATH','User') + ';C:\Tools\keepalive-win',
     'User')                                        # persist for your user
   ```
   After this, every `keepalive ...` example below works directly. Without it,
   substitute `pwsh -File .\keepalive.ps1 ...`. You can also just double-click
   `keepalive.cmd` to launch with defaults.

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

### Parameters

| Parameter | Type | Default | Description |
|---|---|---|---|
| `-IntervalSeconds` | int | `60` | Seconds between idle-timer nudges (minimum 10). |
| `-Minutes` | int | `0` | Auto-stop after N minutes; `0` = run until Ctrl+C. |
| `-Quiet` | switch | off | Suppress the periodic status line. |
| `-SystemOnly` | switch | off | Keep the machine awake but let the display/monitor sleep. |
| `-AllMicrosoftApps` | switch | off | Also keep running Microsoft desktop apps non-idle when backgrounded. |
| `-BrowserKeepAlive` | switch | off | Also nudge M365 browser tabs via CDP (needs `--remote-debugging-port=9222`). |
| `-WatchProcess` | string | — | Auto-stop when the named process (e.g. `teams`) exits. |
| `-Profile` | string | — | Load defaults from a named preset in `keepalive.json`. |
| `-Headless` | switch | off | Run detached in the background and return immediately. |
| `-Stop` | switch | off | Stop a background process started with `-Headless`. |
| `-Status` | switch | off | Show logon-task and headless-process status, then exit. |
| `-Install` | switch | off | Register a "run at logon" scheduled task, then exit. |
| `-Uninstall` | switch | off | Remove the logon task, then exit. |

CLI flags always take precedence over any value loaded from a `-Profile` preset.

## How-to guide

### Stay awake during a meeting or presentation

Block sleep/lock for a fixed window and stay quiet:

```powershell
keepalive -Minutes 120 -SystemOnly
```

This keeps the machine awake for two hours while still letting the monitor power
down to save the screen. Equivalent to the bundled `meeting` profile.

### Keep working without a visible terminal (`-Headless`)

Launch a hidden, detached copy and return immediately, so you can close the
terminal:

```powershell
keepalive -Headless          # starts in the background, writes %TEMP%\keepalive.pid
keepalive -Status            # confirm it's running (shows PID + uptime)
keepalive -Stop              # stop it when you're done
```

### Start automatically every time you sign in (`-Install`)

Register a *Run at logon* scheduled task named `KeepAlive` (hidden window):

```powershell
keepalive -Install -Quiet            # bake -Quiet into the task; runs at each logon
keepalive -Status                    # verify the task is registered
keepalive -Uninstall                 # remove it later
```

Any `-IntervalSeconds` / `-Minutes` / `-Quiet` / `-SystemOnly` / `-AllMicrosoftApps`
flags passed alongside `-Install` are baked into the task.

### Stay awake only while a specific app is open (`-WatchProcess`)

Auto-stop when the named process exits — handy for "stay awake while Teams runs":

```powershell
keepalive -WatchProcess teams        # checks every interval; stops when Teams closes
```

Use the process name without `.exe` (e.g. `teams`, `outlook`, `zoom`).

### Keep backgrounded Microsoft apps non-idle (`-AllMicrosoftApps`)

Posts a harmless no-op window message (`WM_NULL`) to each running Microsoft
desktop app (Outlook, Teams, Word, Excel, OneNote, Edge, …) every interval,
keeping their message loops active without stealing focus:

```powershell
keepalive -AllMicrosoftApps
```

### Keep M365 browser tabs signed in (`-BrowserKeepAlive`)

Use this only if the OS-level keep-awake alone does **not** stop your M365 session
from signing out (i.e. the cause is a server-side tab-idle timeout).

1. Launch Chrome or Edge with remote debugging enabled:
   ```powershell
   & "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
   ```
2. Run keepalive with the flag:
   ```powershell
   keepalive -BrowserKeepAlive
   ```

It finds and nudges M365 tabs (Outlook, Teams, SharePoint, OneDrive, Office.com)
via CDP each interval. If no debug port is found it warns and continues with the
normal OS-level keep-awake.

### Use a saved preset (`-Profile`)

Presets live in `keepalive.json` (same folder as the script). The bundled file
includes:

| Profile | Settings |
|---|---|
| `meeting` | 120 min + `-SystemOnly` |
| `focus` | `-AllMicrosoftApps` + `-Quiet` |
| `overnight` | 480 min + `-SystemOnly` + `-Quiet` |
| `tab` | `-BrowserKeepAlive` + `-Quiet` |

```powershell
keepalive -Profile focus                 # load the 'focus' preset
keepalive -Profile meeting -Minutes 60   # load 'meeting', but override to 60 min
```

Add your own presets by editing `keepalive.json`; CLI flags always override
profile values.

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
| `KeepAlive.Tests.ps1` | Pester tests (60 tests, 100% core coverage) |
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
