"""Command-line interface for the keep-alive tool.

Wires the pure logic, Win32 side effects, lifecycle helpers and the optional
system-tray icon together. The :func:`build_parser` and :func:`cli_to_settings`
helpers are pure so the argument surface stays testable.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
from typing import Dict, List, Optional, Sequence

from . import __version__
from .config import pid_file_path, read_profile_config, startup_task_name, profile_settings
from .lifecycle import (
    install_logon_task,
    logon_task_installed,
    pid_running,
    read_pid,
    start_headless,
    stop_headless,
    uninstall_logon_task,
)
from .nudge import (
    browser_debug_port_open,
    make_watch_process_stopper,
    send_app_nudge,
    send_browser_nudge,
)
from .runner import run_keepalive
from .settings import Settings, resolve_settings
from .startup import startup_arguments
from .core import apply_jitter, idle_exceeded, interval_valid
from .win32 import enable_stay_awake, get_idle_seconds, restore_power, send_idle_nudge

DEFAULT_CONFIG_NAME = "keepalive.json"


def build_parser() -> argparse.ArgumentParser:
    """Construct the argument parser (pure — no side effects)."""
    parser = argparse.ArgumentParser(
        prog="keepalive",
        description=(
            "Keep Windows awake so M365 web tabs don't auto-log-out from sleep, "
            "screen-lock, or idle. Sends a harmless F15 nudge each interval and "
            "blocks sleep via SetThreadExecutionState."
        ),
    )
    parser.add_argument("--version", action="version", version=f"keepalive {__version__}")
    # Run options (None default = "not provided", so a --profile can fill them).
    parser.add_argument("--interval-seconds", type=int, default=None,
                        help="Seconds between idle-timer nudges (minimum 10). Default 60.")
    parser.add_argument("--minutes", type=int, default=None,
                        help="Auto-stop after N minutes. 0 = run until Ctrl+C. Default 0.")
    parser.add_argument("--quiet", action="store_true", help="Suppress the periodic status line.")
    parser.add_argument("--system-only", action="store_true",
                        help="Keep the machine awake but let the display sleep.")
    parser.add_argument("--all-microsoft-apps", action="store_true",
                        help="Also keep backgrounded Microsoft desktop apps non-idle.")
    parser.add_argument("--browser-keep-alive", action="store_true",
                        help="Also nudge M365 browser tabs via CDP (needs --remote-debugging-port=9222).")
    parser.add_argument("--watch-process", default="", metavar="NAME",
                        help="Auto-stop when the named process (e.g. teams) exits.")
    parser.add_argument("--profile", default="", metavar="NAME",
                        help="Load defaults from a named preset in keepalive.json.")
    parser.add_argument("--tray", action="store_true",
                        help="Show a system-tray icon to run quietly from the notification area.")
    parser.add_argument("--jitter", type=int, default=None, metavar="SECONDS",
                        help="Randomize each nudge interval by +/- SECONDS so the pattern looks less robotic.")
    parser.add_argument("--max-idle", type=int, default=None, metavar="MINUTES",
                        help="Auto-stop once real user input has been idle this long (machine truly abandoned).")
    # Lifecycle (each exits after running).
    parser.add_argument("--install", action="store_true", help="Register a run-at-logon task, then exit.")
    parser.add_argument("--uninstall", action="store_true", help="Remove the logon task, then exit.")
    parser.add_argument("--headless", action="store_true",
                        help="Relaunch detached in the background and return immediately.")
    parser.add_argument("--stop", action="store_true", help="Stop a --headless background process.")
    parser.add_argument("--status", action="store_true",
                        help="Show logon-task and headless-process status, then exit.")
    return parser


def cli_to_settings(args: argparse.Namespace, config_path: Optional[str] = None) -> Settings:
    """Resolve parsed args + an optional profile into final ``Settings``."""
    preset: Optional[Dict] = None
    if args.profile:
        path = config_path or _default_config_path()
        profiles = read_profile_config(path)
        preset = profile_settings(profiles, args.profile)
        if preset is None:
            raise SystemExit(f"Profile '{args.profile}' not found in '{path}'.")
    cli = {
        "interval_seconds": args.interval_seconds,
        "minutes": args.minutes,
        "quiet": args.quiet,
        "system_only": args.system_only,
        "all_microsoft_apps": args.all_microsoft_apps,
        "browser_keep_alive": args.browser_keep_alive,
        "tray": args.tray,
        "jitter": args.jitter,
        "max_idle": args.max_idle,
    }
    return resolve_settings(cli, preset)


def _default_config_path() -> str:
    # keepalive.json ships as package data alongside the modules, so the
    # bundled profiles resolve whether running from source or a pip install.
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), DEFAULT_CONFIG_NAME)


def _relaunch_flags(settings: Settings) -> List[str]:
    return startup_arguments(
        interval_seconds=settings.interval_seconds,
        minutes=settings.minutes,
        quiet=settings.quiet,
        system_only=settings.system_only,
        all_microsoft_apps=settings.all_microsoft_apps,
        tray=settings.tray,
    )


def _handle_lifecycle(args: argparse.Namespace, settings: Settings) -> Optional[int]:
    """Run a lifecycle sub-command if requested. Returns an exit code or None."""
    if args.install and args.uninstall:
        print("Use either --install or --uninstall, not both.", file=sys.stderr)
        return 1
    if args.uninstall:
        ok = uninstall_logon_task()
        print(f"Removed the '{startup_task_name()}' logon task." if ok
              else f"No '{startup_task_name()}' logon task to remove (or not on Windows).")
        return 0
    if args.install:
        ok = install_logon_task(_relaunch_flags(settings))
        print(f"Installed '{startup_task_name()}' to run at logon." if ok
              else "Could not install the logon task (Windows + schtasks required).")
        return 0
    if args.stop:
        print("Stopped the background keepalive process." if stop_headless()
              else f"No background keepalive process found (no PID file at '{pid_file_path()}').")
        return 0
    if args.status:
        _print_status()
        return 0
    if args.headless:
        pid = start_headless(_relaunch_flags(settings))
        print(f"Keep-awake started in the background (PID {pid}). "
              "Use 'keepalive --stop' to stop it, or 'keepalive --status' to check.")
        return 0
    return None


def _print_status() -> None:
    if logon_task_installed():
        print(f"Logon task '{startup_task_name()}': installed")
    else:
        print("No logon task installed.")
    pid = read_pid()
    if pid_running(pid):
        print(f"Headless process: PID {pid}, running")
    else:
        print("No headless process running.")


def _build_callbacks(settings: Settings):
    """Assemble the optional nudge callbacks the run loop will fire."""
    app_nudge = send_app_nudge if settings.all_microsoft_apps else None
    browser_nudge = send_browser_nudge if settings.browser_keep_alive else None
    return app_nudge, browser_nudge


def _build_next_interval(settings: Settings):
    """A per-cycle interval provider for --jitter, or None when disabled."""
    if settings.jitter > 0:
        return lambda: apply_jitter(settings.interval_seconds, settings.jitter)
    return None


def _idle_stopper(settings: Settings):
    """A stop predicate that fires once real user-idle exceeds --max-idle."""
    if settings.max_idle > 0:
        return lambda: idle_exceeded(get_idle_seconds(), settings.max_idle)
    return None


def _compose_stop_when(*predicates):
    """Combine stop predicates with OR; returns None when none are active."""
    active = [p for p in predicates if p]
    if not active:
        return None
    return lambda: any(p() for p in active)


def run(args: argparse.Namespace, settings: Settings) -> int:
    """Run the foreground (or tray) keep-alive loop. Returns an exit code."""
    if not interval_valid(settings.interval_seconds):
        print(f"--interval-seconds must be >= 10 (got {settings.interval_seconds}).", file=sys.stderr)
        return 1

    if settings.browser_keep_alive and not browser_debug_port_open():
        print("Warning: no Chrome/Edge debug port at localhost:9222. Launch the browser "
              "with --remote-debugging-port=9222 to enable browser tab keep-alive.", file=sys.stderr)

    mode_suffix = " (display may sleep)" if settings.system_only else ""
    app_nudge, browser_nudge = _build_callbacks(settings)
    watch_stopper = make_watch_process_stopper(args.watch_process)
    stop_when = _compose_stop_when(watch_stopper, _idle_stopper(settings))
    next_interval = _build_next_interval(settings)

    def enable() -> None:
        enable_stay_awake(keep_display_on=not settings.system_only)

    if settings.tray:
        return _run_with_tray(settings, mode_suffix, enable, app_nudge,
                              browser_nudge, stop_when, next_interval)

    try:
        run_keepalive(
            interval_seconds=settings.interval_seconds,
            minutes=settings.minutes,
            quiet=settings.quiet,
            mode_suffix=mode_suffix,
            enable=enable,
            restore=restore_power,
            nudge=send_idle_nudge,
            app_nudge=app_nudge,
            browser_nudge=browser_nudge,
            stop_when=stop_when,
            next_interval=next_interval,
        )
    except KeyboardInterrupt:
        pass
    return 0


def _run_with_tray(settings, mode_suffix, enable, app_nudge, browser_nudge,
                   stop_when, next_interval) -> int:
    from .tray import TrayController, tray_available

    if not tray_available():
        print("Tray icon needs 'pystray' and 'Pillow'. Install with: "
              "pip install 'keepalive[tray]'. Falling back to console mode.", file=sys.stderr)
        return run_console_fallback(settings, mode_suffix, enable, app_nudge,
                                    browser_nudge, stop_when, next_interval)

    controller = TrayController(interval_seconds=settings.interval_seconds, mode_suffix=mode_suffix)

    def combined_stop() -> bool:
        return controller.should_stop() or bool(stop_when and stop_when())

    def gated_nudge(fn):
        # Honour the tray Pause toggle: skip the nudge while paused.
        if fn is None:
            return None

        def _wrapped():
            if not controller.paused():
                fn()

        return _wrapped

    def loop() -> None:
        run_keepalive(
            interval_seconds=settings.interval_seconds,
            minutes=settings.minutes,
            quiet=settings.quiet,
            mode_suffix=mode_suffix,
            enable=enable,
            restore=restore_power,
            nudge=gated_nudge(send_idle_nudge),
            app_nudge=gated_nudge(app_nudge),
            browser_nudge=gated_nudge(browser_nudge),
            stop_when=combined_stop,
            on_status=controller.on_status,
            next_interval=next_interval,
        )

    controller.run(loop)
    return 0


def run_console_fallback(settings, mode_suffix, enable, app_nudge, browser_nudge,
                         stop_when, next_interval=None) -> int:
    try:
        run_keepalive(
            interval_seconds=settings.interval_seconds,
            minutes=settings.minutes,
            quiet=settings.quiet,
            mode_suffix=mode_suffix,
            enable=enable,
            restore=restore_power,
            nudge=send_idle_nudge,
            app_nudge=app_nudge,
            browser_nudge=browser_nudge,
            stop_when=stop_when,
            next_interval=next_interval,
        )
    except KeyboardInterrupt:
        pass
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        settings = cli_to_settings(args)
    except SystemExit as exc:
        if isinstance(exc.code, str):
            print(exc.code, file=sys.stderr)
            return 1
        raise

    lifecycle_code = _handle_lifecycle(args, settings)
    if lifecycle_code is not None:
        return lifecycle_code

    return run(args, settings)
