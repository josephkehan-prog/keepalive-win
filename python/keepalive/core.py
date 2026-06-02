"""Pure, testable keep-alive logic.

No side effects live here: the Win32 calls are in :mod:`keepalive.win32`.
This mirrors ``KeepAlive.Core.ps1`` from the PowerShell original so the two
implementations stay behaviourally identical and unit-testable.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

# Minimum interval guard: anything faster than this is pointless thrash.
MIN_INTERVAL_SECONDS = 10

# ASCII cat frames for the "CLI is active" indicator shown on each status line.
# Alternating frames make the cat blink, so it's visually obvious the loop is
# still alive. ASCII-only by design, matching the PowerShell original.
CAT_FRAMES = ("=^.^=", "=^-^=")

# Win32 SetThreadExecutionState bit flags (see awake_flags()).
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002


def cat_frame(counter: int = 0) -> str:
    """Return the cat frame for a tick counter, cycling through the frames.

    Pure and deterministic so the animation can be unit-tested without timing.
    A negative counter is handled by taking the absolute value first.
    """
    return CAT_FRAMES[abs(int(counter)) % len(CAT_FRAMES)]


def interval_valid(interval_seconds: int) -> bool:
    """True when the requested nudge interval meets the minimum."""
    return interval_seconds >= MIN_INTERVAL_SECONDS


def end_time(start: datetime, minutes: int) -> Optional[datetime]:
    """Compute the auto-stop time, or ``None`` to run until stopped.

    ``minutes <= 0`` means "run forever" and returns ``None``.
    """
    if minutes <= 0:
        return None
    return start + timedelta(minutes=minutes)


def awake_flags(keep_system_awake: bool = True, keep_display_on: bool = True) -> int:
    """Compose the ``SetThreadExecutionState`` bitmask that keeps Windows awake.

    ``ES_CONTINUOUS`` is always set so the state persists across the run.
    ``ES_SYSTEM_REQUIRED`` blocks system sleep; ``ES_DISPLAY_REQUIRED`` blocks
    display-off. Default keeps both; clearing ``keep_display_on`` lets the
    monitor sleep while the machine itself stays awake (avoids sleep/idle
    logout, saves the screen). The result is masked to an unsigned 32-bit value.
    """
    flags = ES_CONTINUOUS
    if keep_system_awake:
        flags |= ES_SYSTEM_REQUIRED
    if keep_display_on:
        flags |= ES_DISPLAY_REQUIRED
    return flags & 0xFFFFFFFF


def release_flags() -> int:
    """The bitmask used on exit to restore normal power behaviour."""
    return ES_CONTINUOUS


def should_stop(now: datetime, end: Optional[datetime]) -> bool:
    """True once ``now`` has reached the auto-stop time.

    ``end is None`` means no end time was set, so the loop never auto-stops.
    """
    if end is None:
        return False
    return now >= end
