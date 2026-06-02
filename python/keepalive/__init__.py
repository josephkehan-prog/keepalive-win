"""keepalive — a Python port of the keepalive-win CLI.

Keeps Windows awake so M365 web tabs (Outlook / SharePoint / Teams) don't
auto-log-out from sleep, screen-lock, or idle. Adds an optional system-tray
icon so the keep-alive can run quietly from the notification area.

The package is split into pure, testable logic (``core``, ``config``,
``apps``, ``browser``, ``startup``, ``runner``, ``tray``) and the Windows-only
side effects that live behind ``ctypes`` in ``win32`` / ``nudge``.
"""

__version__ = "1.0.0"

# Re-export the most commonly used pure helpers for convenient importing.
from .core import (
    MIN_INTERVAL_SECONDS,
    cat_frame,
    awake_flags,
    end_time,
    interval_valid,
    should_stop,
)

__all__ = [
    "__version__",
    "MIN_INTERVAL_SECONDS",
    "cat_frame",
    "awake_flags",
    "end_time",
    "interval_valid",
    "should_stop",
]
