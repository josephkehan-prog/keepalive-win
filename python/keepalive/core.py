"""Pure, testable keep-alive logic.

No side effects live here: the Win32 calls are in :mod:`keepalive.win32`.
This mirrors ``KeepAlive.Core.ps1`` from the PowerShell original so the two
implementations stay behaviourally identical and unit-testable.
"""

from __future__ import annotations

import random as _random
from datetime import datetime, timedelta
from typing import Optional

# GetTickCount wraps at 2**32 milliseconds (~49.7 days).
_TICK_WRAP_MASK = 0xFFFFFFFF

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


def apply_jitter(interval_seconds: int, jitter_seconds: int, rng=None) -> int:
    """Return the interval randomized by ``±jitter_seconds``.

    ``jitter_seconds <= 0`` disables jitter and returns the interval unchanged.
    The result is clamped to at least 1 second so a large jitter can never
    produce a zero or negative wait. ``rng`` is injectable for deterministic
    tests; it defaults to the module ``random``.
    """
    if jitter_seconds <= 0:
        return interval_seconds
    rng = rng or _random
    delta = rng.randint(-jitter_seconds, jitter_seconds)
    return max(1, interval_seconds + delta)


def idle_exceeded(idle_seconds: float, max_idle_minutes: int) -> bool:
    """True when real user-input idle time has passed the configured limit.

    ``max_idle_minutes <= 0`` disables the check (returns ``False``). Used to
    stop the keep-alive once the machine has genuinely been abandoned, so it
    can fall back to normal power management.
    """
    if max_idle_minutes <= 0:
        return False
    return idle_seconds >= max_idle_minutes * 60


def idle_seconds_from_ticks(last_input_ms: int, now_ms: int) -> float:
    """Seconds between the last input tick and now, handling 32-bit wraparound.

    Both values come from the Win32 millisecond tick counter, which wraps at
    2**32. Masking the difference keeps the result correct across a wrap.
    """
    diff = (now_ms - last_input_ms) & _TICK_WRAP_MASK
    return diff / 1000.0


def should_stop(now: datetime, end: Optional[datetime]) -> bool:
    """True once ``now`` has reached the auto-stop time.

    ``end is None`` means no end time was set, so the loop never auto-stops.
    """
    if end is None:
        return False
    return now >= end
