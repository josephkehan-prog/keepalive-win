"""Background/headless process and run-at-logon lifecycle (Windows).

Wraps the Windows-specific bits — ``schtasks`` for the logon task and a
detached ``subprocess`` for ``--headless`` — behind small functions that the
CLI calls. Off Windows these degrade gracefully so importing the module is
always safe.
"""

from __future__ import annotations

import os
import subprocess
import sys
from typing import List, Optional

from .config import pid_file_path, startup_task_name
from .win32 import is_windows


def _relaunch_command(extra_args: List[str]) -> List[str]:
    """Build the command that relaunches this tool with the given flags."""
    return [sys.executable, "-m", "keepalive", *extra_args]


def read_pid() -> Optional[int]:
    """Return the PID stored by a --headless launch, or ``None``."""
    path = pid_file_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="ascii") as handle:
            return int(handle.read().strip())
    except (OSError, ValueError):
        return None


def write_pid(pid: int) -> None:
    with open(pid_file_path(), "w", encoding="ascii") as handle:
        handle.write(str(pid))


def clear_pid() -> None:
    try:
        os.remove(pid_file_path())
    except OSError:
        pass


def pid_running(pid: Optional[int]) -> bool:
    """True when ``pid`` refers to a live process."""
    if not pid:
        return False
    try:
        import psutil

        return psutil.pid_exists(pid)
    except Exception:
        pass
    if is_windows():
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def start_headless(extra_args: List[str]) -> int:
    """Spawn a detached background copy and record its PID. Returns the PID."""
    cmd = _relaunch_command([*extra_args, "--quiet"])
    creationflags = 0
    if is_windows():
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
            subprocess, "DETACHED_PROCESS", 0
        )
    proc = subprocess.Popen(  # noqa: S603 - args are our own, not user input
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
    )
    write_pid(proc.pid)
    return proc.pid


def stop_headless() -> bool:
    """Stop a --headless process via its PID file. False if none was found."""
    pid = read_pid()
    if pid is None:
        return False
    try:
        import psutil

        if psutil.pid_exists(pid):
            psutil.Process(pid).terminate()
    except Exception:
        try:
            os.kill(pid, 9)
        except OSError:
            pass
    clear_pid()
    return True


def install_logon_task(extra_args: List[str]) -> bool:
    """Register a 'run at logon' scheduled task. Windows only; False otherwise."""
    if not is_windows():
        return False
    quoted = " ".join(_relaunch_command([*extra_args, "--quiet"]))
    result = subprocess.run(  # noqa: S603
        [
            "schtasks",
            "/Create",
            "/TN",
            startup_task_name(),
            "/TR",
            quoted,
            "/SC",
            "ONLOGON",
            "/F",
        ],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def uninstall_logon_task() -> bool:
    """Remove the logon task. Windows only; False if absent / off-Windows."""
    if not is_windows():
        return False
    result = subprocess.run(  # noqa: S603
        ["schtasks", "/Delete", "/TN", startup_task_name(), "/F"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def logon_task_installed() -> bool:
    """True when the logon task is registered (Windows only)."""
    if not is_windows():
        return False
    result = subprocess.run(  # noqa: S603
        ["schtasks", "/Query", "/TN", startup_task_name()],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0
