"""Relaunch-argument assembly for the --install task and --headless launch.

Pure string/list assembly so it can be unit-tested without touching the
Windows Task Scheduler or spawning a process. Only non-default flags are
emitted, so a plain relaunch stays minimal — mirroring ``Get-StartupArguments``
from the PowerShell original.
"""

from __future__ import annotations

from typing import List

# Defaults that, when matched, are omitted from the relaunch arguments.
DEFAULT_INTERVAL_SECONDS = 60
DEFAULT_MINUTES = 0


def startup_arguments(
    *,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
    minutes: int = DEFAULT_MINUTES,
    quiet: bool = False,
    system_only: bool = False,
    all_microsoft_apps: bool = False,
    tray: bool = False,
    jitter: int = 0,
    max_idle: int = 0,
) -> List[str]:
    """Build the keepalive CLI flags used to relaunch the tool.

    Returns the argument list (e.g. ``["--minutes", "90", "--quiet"]``) with
    only the non-default options included. The caller prepends the Python
    interpreter / entry-point invocation.
    """
    args: List[str] = []
    if interval_seconds != DEFAULT_INTERVAL_SECONDS:
        args += ["--interval-seconds", str(interval_seconds)]
    if minutes != DEFAULT_MINUTES:
        args += ["--minutes", str(minutes)]
    if quiet:
        args.append("--quiet")
    if system_only:
        args.append("--system-only")
    if all_microsoft_apps:
        args.append("--all-microsoft-apps")
    if tray:
        args.append("--tray")
    if jitter:
        args += ["--jitter", str(jitter)]
    if max_idle:
        args += ["--max-idle", str(max_idle)]
    return args
