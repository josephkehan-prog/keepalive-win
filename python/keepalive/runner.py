"""The keep-alive run loop — injectable for testing.

All side-effecting operations (Win32 calls, sleeping, the clock) are passed in
as callables so the loop can be unit-tested without P/Invoke or real waiting.
This mirrors ``Invoke-KeepAlive`` from the PowerShell original.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Callable, Optional

from .core import cat_frame, end_time, should_stop

# Type alias for the no-argument side-effect callbacks.
Action = Callable[[], None]


def _default_emit(line: str) -> None:
    print(line)


def run_keepalive(
    *,
    interval_seconds: int = 60,
    minutes: int = 0,
    quiet: bool = False,
    mode_suffix: str = "",
    enable: Optional[Action] = None,
    restore: Optional[Action] = None,
    nudge: Optional[Action] = None,
    app_nudge: Optional[Action] = None,
    browser_nudge: Optional[Action] = None,
    stop_when: Optional[Callable[[], bool]] = None,
    clock: Optional[Callable[[], datetime]] = None,
    tick: Optional[Action] = None,
    emit: Optional[Callable[[str], None]] = None,
    on_status: Optional[Callable[[int, str, datetime], None]] = None,
    next_interval: Optional[Callable[[], int]] = None,
) -> None:
    """Run the keep-alive loop until auto-stop, ``stop_when``, or interruption.

    Parameters mirror the PowerShell ``Invoke-KeepAlive``:

    * ``enable`` / ``restore`` bracket the loop (restore always runs, even on
      error — the power state is guaranteed to be cleaned up).
    * ``nudge`` / ``app_nudge`` / ``browser_nudge`` fire once per interval.
    * ``stop_when`` ends the loop when it returns truthy (e.g. watched process
      exited, or a tray "Quit" was clicked).
    * ``clock`` / ``tick`` / ``emit`` are injected in tests to avoid real time
      and real I/O. ``tick`` defaults to ``time.sleep(1)``.
    * ``on_status`` is notified ``(tick, frame, now)`` on each status emission,
      letting a tray icon animate in step with the CLI.
    * ``next_interval``, when given, supplies the wait (in seconds) for the
      upcoming cycle instead of the fixed ``interval_seconds`` — used by
      ``--jitter`` to vary each interval.
    """
    clock = clock or datetime.now
    emit = emit or _default_emit
    do_tick: Action = tick if tick is not None else (lambda: time.sleep(1))

    start = clock()
    end = end_time(start, minutes)
    if end is not None:
        banner = (
            f"{cat_frame()} Keeping awake{mode_suffix} until "
            f"{end.strftime('%H:%M:%S')}. Press Ctrl+C to stop."
        )
    else:
        banner = f"{cat_frame()} Keeping awake{mode_suffix}. Press Ctrl+C to stop."
    emit(banner)

    # Counts status lines so the cat blinks (alternates frames) each tick — a
    # live sign that the keep-alive loop is still running.
    status_tick = 0
    try:
        if enable:
            enable()
        while True:
            if should_stop(clock(), end):
                break
            if stop_when and stop_when():
                break
            if nudge:
                nudge()
            if app_nudge:
                app_nudge()
            if browser_nudge:
                browser_nudge()
            current_interval = next_interval() if next_interval else interval_seconds
            if not quiet:
                now = clock()
                frame = cat_frame(status_tick)
                emit(
                    f"{frame} [{now.strftime('%H:%M:%S')}] awake - "
                    f"next nudge in {current_interval}s"
                )
                if on_status:
                    on_status(status_tick, frame, now)
                status_tick += 1
            # Sleep in 1s slices so Ctrl+C and --minutes stay responsive.
            for _ in range(current_interval):
                if should_stop(clock(), end):
                    break
                if stop_when and stop_when():
                    break
                do_tick()
    finally:
        if restore:
            restore()
        emit("=^.^=zZ Stopped - normal power behavior restored.")
