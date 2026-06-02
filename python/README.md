# keepalive (Python port)

A Python port of [keepalive-win](../README.md): a keep-awake CLI that stops M365
web tabs (Outlook / SharePoint / Teams) from auto-logging-out due to sleep,
screen-lock, or idle — now with an optional **system-tray icon** so it can run
quietly from the notification area.

## What it does

While running it:

- blocks system sleep + display-off via `SetThreadExecutionState` (use
  `--system-only` to keep the machine awake while still letting the monitor turn
  off), and
- sends a harmless **F15** keypress every *N* seconds to reset the Windows idle
  timer, which is what drives screen-lock and most app/tab idle detection.

With `--all-microsoft-apps` it also posts a harmless no-op window message
(`WM_NULL`) to each running Microsoft desktop app every interval. With
`--browser-keep-alive` it connects to Chrome/Edge via the DevTools protocol
(CDP) and nudges each M365 tab (requires `--remote-debugging-port=9222`).

Each status line is prefixed with a small ASCII cat that blinks (`=^.^=` /
`=^-^=`) so you can tell at a glance the CLI is still active; on exit it prints a
sleeping cat (`=^.^=zZ`) and always restores normal power behavior.

### System-tray icon (`--tray`)

`--tray` shows a notification-area icon — a blinking cat face that pulses green
while awake and turns amber when paused. Right-click for **Pause / Resume** and
**Quit**. The tray lets you close the console window and keep the machine awake
without a visible terminal:

```bash
keepalive --tray
keepalive --tray --system-only --interval-seconds 45
```

If the optional tray dependencies aren't installed it prints a hint and falls
back to console mode.

## Install

```bash
cd python
pip install .            # core CLI (no third-party deps required)
pip install '.[tray]'    # + system-tray icon (pystray, Pillow)
pip install '.[all]'     # + apps nudge (psutil) + browser nudge (websocket-client)
```

Python 3.9+. The core keep-awake path uses only the standard library and Win32
via `ctypes`; the extras are needed only for the matching optional features.

## Usage

```bash
keepalive                          # stay awake until Ctrl+C
keepalive --minutes 90 --quiet     # stay awake 90 minutes, no status output
keepalive --interval-seconds 30    # nudge every 30s (minimum 10)
keepalive --system-only            # keep the machine awake but let the display sleep
keepalive --all-microsoft-apps     # also keep Outlook/Teams/Office/Edge non-idle when backgrounded
keepalive --browser-keep-alive     # also nudge M365 browser tabs via CDP
keepalive --watch-process teams    # auto-stop when Teams exits
keepalive --profile meeting        # load the 'meeting' preset from keepalive.json
keepalive --tray                   # run from a system-tray icon
keepalive --headless               # run detached in the background, then close the terminal
keepalive --stop                   # stop the background process started with --headless
keepalive --status                 # show whether the logon task / headless process are running
keepalive --install --quiet        # auto-start at every logon (Windows scheduled task)
keepalive --uninstall              # remove the logon auto-start
```

You can also run it without installing: `python -m keepalive ...`.

### Options

| Option | Default | Description |
|---|---|---|
| `--interval-seconds N` | `60` | Seconds between idle-timer nudges (minimum 10). |
| `--minutes N` | `0` | Auto-stop after N minutes; `0` = run until Ctrl+C. |
| `--quiet` | off | Suppress the periodic status line. |
| `--system-only` | off | Keep the machine awake but let the display/monitor sleep. |
| `--all-microsoft-apps` | off | Also keep running Microsoft desktop apps non-idle when backgrounded. |
| `--browser-keep-alive` | off | Also nudge M365 browser tabs via CDP (needs `--remote-debugging-port=9222`). |
| `--watch-process NAME` | — | Auto-stop when the named process (e.g. `teams`) exits. |
| `--profile NAME` | — | Load defaults from a named preset in `keepalive.json`. |
| `--tray` | off | Show a system-tray icon (needs the `tray` extra). |
| `--headless` | off | Relaunch detached in the background and return immediately. |
| `--stop` | off | Stop a background process started with `--headless`. |
| `--status` | off | Show logon-task and headless-process status, then exit. |
| `--install` | off | Register a run-at-logon scheduled task, then exit. |
| `--uninstall` | off | Remove the logon task, then exit. |

CLI flags always take precedence over any value loaded from a `--profile` preset.

## Profiles

Presets live in `keepalive/keepalive.json`, shipped as package data so the
bundled profiles resolve whether you run from source or a pip install (same
format as the PowerShell version):

| Profile | Settings |
|---|---|
| `meeting` | 120 min + `--system-only` |
| `focus` | `--all-microsoft-apps` + `--quiet` |
| `overnight` | 480 min + `--system-only` + `--quiet` |
| `tab` | `--browser-keep-alive` + `--quiet` |
| `tray` | `--tray` + `--quiet` |

```bash
keepalive --profile focus                  # load the 'focus' preset
keepalive --profile meeting --minutes 60   # load 'meeting', but override to 60 min
```

## Architecture

Pure logic is separated from side effects so almost everything is unit-testable
without Windows:

| Module | Responsibility |
|---|---|
| `core.py` | Interval/flags/cat-frame/should-stop — pure |
| `settings.py` | CLI + profile precedence — pure |
| `config.py` | `keepalive.json` loading, PID/task paths — pure |
| `apps.py` | Microsoft app name matching — pure |
| `browser.py` | M365 URL classification — pure |
| `startup.py` | Relaunch argument assembly — pure |
| `runner.py` | The injectable run loop |
| `tray.py` | System-tray icon (presentation pure; pystray lazy) |
| `win32.py` | `SetThreadExecutionState` / F15 via `ctypes` |
| `nudge.py` | App-window + CDP browser nudges |
| `lifecycle.py` | Headless process + run-at-logon task |
| `cli.py` | Argument parsing + command dispatch |

## Tests

```bash
cd python
pip install '.[test]'
pytest --cov=keepalive --cov-report=term-missing
```

153 tests; the pure-logic modules are at 100% coverage and the suite runs on any
platform (the Windows-only side effects are covered via injected fakes).

## Scope & limitation

This keeps the **OS** active — it fixes logouts caused by sleep / screen-lock /
idle. It does **not** bypass authentication, and it cannot guarantee defeat of an
admin-enforced *server-side* M365 idle session timeout. For that case use
`--browser-keep-alive`.
