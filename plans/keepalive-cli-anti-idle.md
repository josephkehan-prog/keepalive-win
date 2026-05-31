# Blueprint: `keepalive` — Anti-Idle Keep-Awake CLI

**Objective:** A Windows CLI that prevents auto-logout from Outlook / SharePoint / Teams (web tabs) by keeping the machine awake and the Windows idle timer reset.

**Surface:** Web / browser tabs · **Approach:** OS anti-idle keep-awake (chosen)
**Language:** PowerShell 7+ (`.ps1`, zero install, native Win32) · **Mode:** Direct (not a git repo — no branches/PRs)
**Date:** 2026-05-31

---

## What this actually does (and its limit)

Two mechanisms run together while the CLI is open:

1. **`SetThreadExecutionState`** (kernel32) with `ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED`
   → Windows will not sleep or turn the display off while the process is alive. Cleanly reset on exit.
2. **`keybd_event` F15** (user32) every *N* seconds → injects a harmless key (F15 does nothing on modern keyboards, never interferes with typing). This **resets `GetLastInputInfo`**, the idle timer that drives screen-lock and most app/tab idle detection.

**Defeats:** machine sleep, display-off, screen-lock-on-idle, and last-input-based idle logout. This covers the common case where you return to a slept/locked machine and have to re-auth.

**Does NOT guarantee:** a server-side M365 "idle session sign-out" (admin policy) that keys off interaction with the *specific browser tab*. If that's your real cause, build **Step 5 (optional)**.

> Note: keeping *your own* session alive on *your own* account is benign. If your machine is corporate-managed, an admin-enforced timeout exists for a security reason — this tool keeps the OS active, it does not bypass authentication or conditional access.

---

## Dependency graph

```
Step 1 (scaffold) --> Step 2 (Win32 core) --> Step 3 (run loop + cleanup) --> Step 4 (test/package)
                                                                                 \-> Step 5 (OPTIONAL: browser keep-alive)
```
All steps are serial (single file). Step 5 is independent and only built if Step 4 testing shows server-side idle timeout is the cause.

---

## Step 1 — Scaffold `keepalive.ps1` + params + help

**Context brief:** New single-file CLI at `C:\Users\19172\Desktop\Project\keepalive.ps1`. No prior context needed.

**Tasks:**
- Create `keepalive.ps1` with a `param()` block:
  - `[int]$IntervalSeconds = 60` — how often to nudge the idle timer.
  - `[int]$Minutes = 0` — auto-stop after N minutes; `0` = run until Ctrl+C.
  - `[switch]$Quiet` — suppress the periodic status line.
- Add a comment-based help header (`<# .SYNOPSIS / .EXAMPLE #>`) so `Get-Help .\keepalive.ps1` works.
- Validate `$IntervalSeconds -ge 10` (reject absurdly low intervals), exit with a clear message otherwise.

**Verify:** `pwsh -File .\keepalive.ps1 -IntervalSeconds 5` prints the validation error and exits non-zero. `Get-Help .\keepalive.ps1` shows synopsis.

**Exit criteria:** Script parses, params bind, help renders. No keep-awake logic yet.

---

## Step 2 — Win32 keep-awake core via `Add-Type`

**Context brief:** Add the P/Invoke layer to `keepalive.ps1` from Step 1.

**Tasks:**
- `Add-Type` a small C# class exposing:
  ```csharp
  [DllImport("kernel32.dll", SetLastError=true)]
  public static extern uint SetThreadExecutionState(uint esFlags);
  [DllImport("user32.dll")]
  public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, System.UIntPtr dwExtraInfo);
  ```
- Constants: `ES_CONTINUOUS=0x80000000`, `ES_SYSTEM_REQUIRED=0x1`, `ES_DISPLAY_REQUIRED=0x2`; `VK_F15=0x7E`, `KEYEVENTF_KEYUP=0x2`.
- Helper functions:
  - `Enable-StayAwake` -> `SetThreadExecutionState(ES_CONTINUOUS -bor ES_SYSTEM_REQUIRED -bor ES_DISPLAY_REQUIRED)`.
  - `Restore-Power` -> `SetThreadExecutionState(ES_CONTINUOUS)` (clears the requirement flags).
  - `Send-Nudge` -> `keybd_event(0x7E,0,0,0)` then `keybd_event(0x7E,0,KEYEVENTF_KEYUP,0)`.

**Verify:** Manually call `Enable-StayAwake; Send-Nudge; Restore-Power` in a `pwsh` session — no exceptions; `powercfg /requests` shows a `SYSTEM`/`DISPLAY` request from pwsh while enabled and none after restore.

**Exit criteria:** All three helpers run without error and `powercfg /requests` confirms the awake request appears and clears.

---

## Step 3 — Run loop, auto-stop, and guaranteed cleanup

**Context brief:** Wire Steps 1–2 into the main loop. The critical correctness requirement: **power state must always be restored**, even on Ctrl+C.

**Tasks:**
- Wrap the loop in `try { ... } finally { Restore-Power }` so Ctrl+C / errors never leave the machine permanently awake.
- Loop: call `Enable-StayAwake` once before the loop (it persists via `ES_CONTINUOUS`), then every `$IntervalSeconds`: `Send-Nudge`; if not `-Quiet`, print `"[hh:mm:ss] awake — next nudge in {N}s"`.
- Honor `-Minutes`: compute an end time from a start stamp captured at launch; exit the loop when reached. (Capture start time once at runtime — do not hardcode.)
- Print a clear banner on start (`Keeping awake. Press Ctrl+C to stop.`) and a `Stopped — normal power behavior restored.` line in `finally`.

**Verify:**
- `pwsh -File .\keepalive.ps1 -Minutes 1` runs ~60s then self-stops and prints the restore line.
- During a run, `powercfg /requests` lists the request; after Ctrl+C it is gone.
- Leave it running and confirm the screen does not lock / machine does not sleep over the idle threshold.

**Exit criteria:** Tool keeps the machine awake for the whole run, auto-stops on `-Minutes`, and **always** restores power state on exit (tested with Ctrl+C mid-run).

---

## Step 4 — Test against real logout + package for daily use

**Context brief:** Validate the actual goal and make it one-command easy to launch.

**Tasks:**
- Real-world test: start the CLI, leave Outlook/SharePoint/Teams web tabs open, walk away past your usual logout window, confirm you're still signed in.
- Add a `keepalive.cmd` one-liner launcher (`pwsh -ExecutionPolicy Bypass -File "%~dp0keepalive.ps1" %*`) so it runs by double-click / `keepalive` from cmd.
- Document in a top-of-file comment: run-on-login option via **Task Scheduler** (trigger: At log on -> action: `pwsh -File ...\keepalive.ps1 -Quiet`), and how to stop it.

**Verify:** Cold launch via `keepalive.cmd` works. You stay logged into the web apps across a full idle window.

**Exit criteria:** Confirmed: no more auto-logout from sleep/lock/idle. If you ARE still logged out despite the machine staying awake -> the cause is server-side tab idle timeout -> proceed to Step 5.

---

## Step 5 — OPTIONAL: browser-tab keep-alive (only if Step 4 still logs you out)

**Context brief:** Build this *only* if Step 4 proves the logout is server-side M365 idle timeout (machine stayed awake but tab still signed out). Reliable fix = periodically interact with the actual tab.

**Tasks (design options, pick one):**
- **A — Edge/Chrome remote debugging:** launch the browser with `--remote-debugging-port`, attach via CDP, and every few minutes dispatch a tiny scroll/focus on the M365 tabs. Most reliable; resets the server idle timer for real.
- **B — Playwright/Selenium driven profile:** drive a persistent browser context that periodically reloads or clicks within each app. Heavier dependency.
- Keep it scoped to the specific M365 origins; do not type into or mutate content — focus/scroll only.

**Verify:** With the machine *allowed* to idle but Step 5 running, the web session survives past the server idle window.

**Exit criteria:** Web session persists with no machine-level keep-awake — proving the tab-interaction path works.

---

## Anti-patterns to avoid

- Leaving `ES_DISPLAY_REQUIRED` set after exit (drains battery, screen never sleeps again) -> enforced by the `finally { Restore-Power }` in Step 3.
- Using `Start-Sleep` so long that Ctrl+C feels unresponsive -> sleep in <= a few-second increments inside the interval, or rely on the loop cadence; keep the tool interruptible.
- Sending a *real* key (Space/Shift) that interferes with whatever has focus -> use **F15** specifically.
- Hardcoding a start timestamp for `-Minutes` -> capture it at runtime.
- Treating this as an auth bypass -> it is not; it only keeps the OS active.
