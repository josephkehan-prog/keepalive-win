"""Windows power/idle side effects via ``ctypes``.

These functions only do real work on Windows; the module imports cleanly on any
platform so the pure logic and tests stay cross-platform. Win32 handles are
resolved lazily inside each call rather than at import time.
"""

from __future__ import annotations

import sys

from .core import awake_flags, release_flags

# Virtual-key code for F15 — a key no normal keyboard sends, so nudging it
# resets the idle timer without disturbing the user's input.
VK_F15 = 0x7E
KEYEVENTF_KEYUP = 0x0002
WM_NULL = 0x0000


def is_windows() -> bool:
    return sys.platform.startswith("win")


def _user32():
    import ctypes

    return ctypes.windll.user32


def _kernel32():
    import ctypes

    return ctypes.windll.kernel32


def enable_stay_awake(keep_display_on: bool = True) -> None:
    """Block sleep (and optionally display-off) for the rest of the run."""
    if not is_windows():
        return
    _kernel32().SetThreadExecutionState(awake_flags(keep_display_on=keep_display_on))


def restore_power() -> None:
    """Restore normal power behaviour (clears the keep-awake request)."""
    if not is_windows():
        return
    _kernel32().SetThreadExecutionState(release_flags())


def send_idle_nudge() -> None:
    """Send a harmless F15 key down+up to reset the Windows idle timer."""
    if not is_windows():
        return
    user32 = _user32()
    user32.keybd_event(VK_F15, 0, 0, 0)
    user32.keybd_event(VK_F15, 0, KEYEVENTF_KEYUP, 0)
