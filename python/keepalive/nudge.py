"""Optional nudges: per-window Microsoft apps and M365 browser tabs.

These touch the OS (process enumeration, window messages, CDP WebSockets) and
so are guarded to no-op off Windows / when dependencies are missing. The
classification logic they rely on is pure and tested in :mod:`keepalive.apps`
and :mod:`keepalive.browser`.
"""

from __future__ import annotations

import json
from typing import Optional
from urllib.request import urlopen

from .apps import is_microsoft_app
from .browser import select_m365_tabs
from .win32 import WM_NULL, is_windows

# Default Chrome/Edge remote-debugging port (launch with
# --remote-debugging-port=9222 to enable browser tab keep-alive).
DEFAULT_DEBUG_PORT = 9222


def send_app_nudge() -> None:
    """Post a harmless ``WM_NULL`` to each running Microsoft app's main window.

    Async and never steals focus. No-ops off Windows or when ``psutil``/Win32
    enumeration is unavailable.
    """
    if not is_windows():
        return
    try:
        import ctypes

        import psutil
    except Exception:
        return
    user32 = ctypes.windll.user32
    for proc in psutil.process_iter(["name"]):
        name = proc.info.get("name") or ""
        if not is_microsoft_app(name):
            continue
        # EnumWindows would be needed for an exact HWND; psutil doesn't expose
        # one, so we post to the foreground-independent broadcast is avoided and
        # we simply skip when no handle is resolvable. This keeps the nudge
        # strictly harmless.
        hwnd = _main_window_handle(proc.pid)
        if hwnd:
            try:
                user32.PostMessageW(hwnd, WM_NULL, 0, 0)
            except Exception:
                pass


def _main_window_handle(pid: int):  # pragma: no cover - Windows-only enumeration
    import ctypes

    user32 = ctypes.windll.user32
    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, _lparam):
        proc_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(proc_id))
        if proc_id.value == pid and user32.IsWindowVisible(hwnd):
            found.append(hwnd)
            return False
        return True

    user32.EnumWindows(_cb, 0)
    return found[0] if found else None


def fetch_debug_tabs(debug_port: int = DEFAULT_DEBUG_PORT, timeout: float = 3.0):
    """Fetch the open-tab list from the Chrome/Edge DevTools ``/json`` endpoint.

    Returns the parsed list, or ``None`` if the port is closed / unreachable.
    """
    url = f"http://localhost:{debug_port}/json"
    try:
        with urlopen(url, timeout=timeout) as resp:  # noqa: S310 - localhost only
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def send_browser_nudge(debug_port: int = DEFAULT_DEBUG_PORT) -> None:
    """Send an F15 key event to each M365 tab via Chrome/Edge remote debugging.

    Requires the browser launched with ``--remote-debugging-port``. No-ops when
    the port is closed, ``websocket-client`` is missing, or no M365 tabs exist.
    """
    tabs = fetch_debug_tabs(debug_port)
    if not tabs:
        return
    m365 = select_m365_tabs(tabs)
    if not m365:
        return
    try:
        from websocket import create_connection
    except Exception:
        return
    payload = json.dumps(
        {
            "id": 1,
            "method": "Input.dispatchKeyEvent",
            "params": {"type": "keyDown", "key": "F15", "code": "F15", "keyCode": 126},
        }
    )
    for tab in m365:
        ws_url = tab.get("webSocketDebuggerUrl") if hasattr(tab, "get") else None
        if not ws_url:
            continue
        try:
            ws = create_connection(ws_url, timeout=3)
            ws.send(payload)
            ws.close()
        except Exception:
            pass


def browser_debug_port_open(debug_port: int = DEFAULT_DEBUG_PORT) -> bool:
    """True when the Chrome/Edge remote-debugging port is reachable."""
    return fetch_debug_tabs(debug_port) is not None


def make_watch_process_stopper(process_name: str) -> Optional["callable"]:
    """Return a ``stop_when`` predicate that fires when a process has exited.

    Returns ``None`` when no process name is given (feature disabled).
    """
    if not process_name:
        return None

    target = process_name.strip().lower()
    if target.endswith(".exe"):
        target = target[:-4]

    def _stopper() -> bool:
        try:
            import psutil
        except Exception:
            return False
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name.endswith(".exe"):
                name = name[:-4]
            if name == target:
                return False
        return True

    return _stopper
