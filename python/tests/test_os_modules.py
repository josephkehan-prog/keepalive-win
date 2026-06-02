"""Tests for the Windows side-effect modules using injected fakes.

These exercise the Windows code paths on any platform by monkeypatching the
``is_windows`` guard and the lazily-resolved ctypes / subprocess handles, so
the bodies are covered without a real Windows host.
"""

import ctypes
import subprocess
import sys
import types

from keepalive import lifecycle, nudge, win32


class _FakeKernel:
    def __init__(self):
        self.calls = []

    def SetThreadExecutionState(self, flags):
        self.calls.append(flags)


class _FakeUser:
    def __init__(self):
        self.events = []

    def keybd_event(self, vk, scan, flags, extra):
        self.events.append((vk, flags))


class TestWin32Windows:
    def test_enable_stay_awake_sets_flags(self, monkeypatch):
        kernel = _FakeKernel()
        monkeypatch.setattr(win32, "is_windows", lambda: True)
        monkeypatch.setattr(win32, "_kernel32", lambda: kernel)
        win32.enable_stay_awake(keep_display_on=True)
        assert kernel.calls == [win32.awake_flags(keep_display_on=True)]

    def test_enable_stay_awake_system_only(self, monkeypatch):
        kernel = _FakeKernel()
        monkeypatch.setattr(win32, "is_windows", lambda: True)
        monkeypatch.setattr(win32, "_kernel32", lambda: kernel)
        win32.enable_stay_awake(keep_display_on=False)
        assert kernel.calls == [win32.awake_flags(keep_display_on=False)]

    def test_restore_power_clears(self, monkeypatch):
        kernel = _FakeKernel()
        monkeypatch.setattr(win32, "is_windows", lambda: True)
        monkeypatch.setattr(win32, "_kernel32", lambda: kernel)
        win32.restore_power()
        assert kernel.calls == [win32.release_flags()]

    def test_send_idle_nudge_keydown_keyup(self, monkeypatch):
        user = _FakeUser()
        monkeypatch.setattr(win32, "is_windows", lambda: True)
        monkeypatch.setattr(win32, "_user32", lambda: user)
        win32.send_idle_nudge()
        assert user.events == [(win32.VK_F15, 0), (win32.VK_F15, win32.KEYEVENTF_KEYUP)]

    def test_all_noop_off_windows(self, monkeypatch):
        monkeypatch.setattr(win32, "is_windows", lambda: False)
        # None of these should raise or touch ctypes off Windows.
        win32.enable_stay_awake()
        win32.restore_power()
        win32.send_idle_nudge()


class _Result:
    def __init__(self, returncode):
        self.returncode = returncode


class TestLifecycleWindows:
    def test_install_logon_task_success(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: True)
        monkeypatch.setattr(lifecycle.subprocess, "run", lambda *a, **k: _Result(0))
        assert lifecycle.install_logon_task(["--quiet"]) is True

    def test_install_logon_task_failure(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: True)
        monkeypatch.setattr(lifecycle.subprocess, "run", lambda *a, **k: _Result(1))
        assert lifecycle.install_logon_task([]) is False

    def test_uninstall_logon_task_success(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: True)
        monkeypatch.setattr(lifecycle.subprocess, "run", lambda *a, **k: _Result(0))
        assert lifecycle.uninstall_logon_task() is True

    def test_logon_task_installed_true(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: True)
        monkeypatch.setattr(lifecycle.subprocess, "run", lambda *a, **k: _Result(0))
        assert lifecycle.logon_task_installed() is True

    def test_start_headless_records_pid(self, monkeypatch, tmp_path):
        pid_path = tmp_path / "keepalive.pid"
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(pid_path))

        class _Proc:
            pid = 9999

        monkeypatch.setattr(lifecycle.subprocess, "Popen", lambda *a, **k: _Proc())
        monkeypatch.setattr(lifecycle, "is_windows", lambda: False)
        pid = lifecycle.start_headless(["--minutes", "5"])
        assert pid == 9999
        assert lifecycle.read_pid() == 9999

    def test_stop_headless_with_pid_file(self, monkeypatch, tmp_path):
        pid_path = tmp_path / "keepalive.pid"
        pid_path.write_text("123456", encoding="ascii")
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(pid_path))
        # No such process: terminate path is a safe no-op, file is cleared.
        assert lifecycle.stop_headless() is True
        assert not pid_path.exists()


class TestNudgeBrowserPaths:
    def test_send_browser_nudge_selects_m365_then_handles_no_ws_lib(self, monkeypatch):
        tabs = [
            {"url": "https://outlook.office.com", "webSocketDebuggerUrl": "ws://x"},
            {"url": "https://google.com"},
        ]
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda debug_port=9222: tabs)
        # websocket-client is not installed here, so the import fails gracefully.
        nudge.send_browser_nudge()  # must not raise

    def test_send_browser_nudge_no_m365_tabs(self, monkeypatch):
        monkeypatch.setattr(
            nudge, "fetch_debug_tabs", lambda debug_port=9222: [{"url": "https://github.com"}]
        )
        nudge.send_browser_nudge()  # returns early, no error

    def test_browser_debug_port_open_true(self, monkeypatch):
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda debug_port=9222: [])
        # An empty list is still a reachable port -> falsy list though.
        # Use a non-empty list to assert the True branch.
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda debug_port=9222: [{"url": "x"}])
        assert nudge.browser_debug_port_open() is True


class TestWin32Idle:
    def test_get_idle_seconds_zero_off_windows(self, monkeypatch):
        monkeypatch.setattr(win32, "is_windows", lambda: False)
        assert win32.get_idle_seconds() == 0.0


class TestWin32HandleResolvers:
    """Cover the lazy ctypes.windll resolvers by faking ctypes.windll."""

    def test_user32_returns_windll_user32(self, monkeypatch):
        sentinel = object()
        fake_windll = types.SimpleNamespace(user32=sentinel, kernel32=object())
        monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
        assert win32._user32() is sentinel

    def test_kernel32_returns_windll_kernel32(self, monkeypatch):
        sentinel = object()
        fake_windll = types.SimpleNamespace(user32=object(), kernel32=sentinel)
        monkeypatch.setattr(ctypes, "windll", fake_windll, raising=False)
        assert win32._kernel32() is sentinel


class _FakeIdleUser:
    """Fake user32 whose GetLastInputInfo writes a dwTime via the byref obj."""

    def __init__(self, last_input_ms, ok=True):
        self._last_input_ms = last_input_ms
        self._ok = ok

    def GetLastInputInfo(self, ref):
        if self._ok:
            ref._obj.dwTime = self._last_input_ms
        return 1 if self._ok else 0


class _FakeTickKernel:
    def __init__(self, now_ms):
        self._now_ms = now_ms

    def GetTickCount(self):
        return self._now_ms


class TestQueryIdleSeconds:
    def test_idle_seconds_from_real_ctypes_structure(self, monkeypatch):
        # Real ctypes.Structure/sizeof/byref work on Linux; only the Win32
        # handles are faked, so the Windows query body is genuinely exercised.
        monkeypatch.setattr(win32, "is_windows", lambda: True)
        monkeypatch.setattr(win32, "_user32", lambda: _FakeIdleUser(1_000))
        monkeypatch.setattr(win32, "_kernel32", lambda: _FakeTickKernel(5_000))
        # (5000 - 1000) ms = 4.0 s idle.
        assert win32.get_idle_seconds() == 4.0

    def test_idle_seconds_zero_when_getlastinputinfo_fails(self, monkeypatch):
        monkeypatch.setattr(win32, "is_windows", lambda: True)
        monkeypatch.setattr(win32, "_user32", lambda: _FakeIdleUser(0, ok=False))
        monkeypatch.setattr(win32, "_kernel32", lambda: _FakeTickKernel(5_000))
        assert win32.get_idle_seconds() == 0.0


class _FakeWinKernel:
    """Fake kernel32 for the Win32 OpenProcess/GetExitCodeProcess pid check."""

    STILL_ACTIVE = 259

    def __init__(self, handle, exit_code=STILL_ACTIVE, get_exit_ok=True):
        self._handle = handle
        self._exit_code = exit_code
        self._get_exit_ok = get_exit_ok
        self.closed = False

    def OpenProcess(self, access, inherit, pid):
        return self._handle

    def GetExitCodeProcess(self, handle, ref):
        ref._obj.value = self._exit_code
        return 1 if self._get_exit_ok else 0

    def CloseHandle(self, handle):
        self.closed = True


def _patch_winapi(monkeypatch, kernel, last_error=0):
    monkeypatch.setattr(ctypes, "WinDLL", lambda name, use_last_error=False: kernel, raising=False)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: last_error, raising=False)


class TestPidExistsWindows:
    def _force_windows_no_psutil(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: True)
        # Ensure the psutil fast-path is skipped so the Win32 branch runs.
        monkeypatch.setitem(sys.modules, "psutil", None)

    def test_running_when_still_active(self, monkeypatch):
        self._force_windows_no_psutil(monkeypatch)
        kernel = _FakeWinKernel(handle=0x100, exit_code=259)
        _patch_winapi(monkeypatch, kernel)
        assert lifecycle.pid_running(1234) is True
        assert kernel.closed is True  # handle always closed

    def test_not_running_when_exit_code_set(self, monkeypatch):
        self._force_windows_no_psutil(monkeypatch)
        kernel = _FakeWinKernel(handle=0x100, exit_code=0)
        _patch_winapi(monkeypatch, kernel)
        assert lifecycle.pid_running(1234) is False
        assert kernel.closed is True

    def test_running_when_getexitcode_fails(self, monkeypatch):
        self._force_windows_no_psutil(monkeypatch)
        kernel = _FakeWinKernel(handle=0x100, get_exit_ok=False)
        _patch_winapi(monkeypatch, kernel)
        # GetExitCodeProcess failing is treated as "still exists".
        assert lifecycle.pid_running(1234) is True

    def test_access_denied_counts_as_running(self, monkeypatch):
        self._force_windows_no_psutil(monkeypatch)
        kernel = _FakeWinKernel(handle=0)  # OpenProcess failed
        _patch_winapi(monkeypatch, kernel, last_error=5)  # ERROR_ACCESS_DENIED
        assert lifecycle.pid_running(1234) is True

    def test_no_handle_other_error_not_running(self, monkeypatch):
        self._force_windows_no_psutil(monkeypatch)
        kernel = _FakeWinKernel(handle=0)
        _patch_winapi(monkeypatch, kernel, last_error=87)  # some other error
        assert lifecycle.pid_running(1234) is False


class TestPidRunningBranches:
    def test_zero_pid_is_not_running(self):
        assert lifecycle.pid_running(0) is False
        assert lifecycle.pid_running(None) is False

    def test_psutil_fast_path(self, monkeypatch):
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.pid_exists = lambda pid: True
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
        assert lifecycle.pid_running(4321) is True

    def test_posix_os_kill_alive(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: False)
        monkeypatch.setitem(sys.modules, "psutil", None)
        monkeypatch.setattr(lifecycle.os, "kill", lambda pid, sig: None)
        assert lifecycle.pid_running(1234) is True

    def test_posix_os_kill_dead(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: False)
        monkeypatch.setitem(sys.modules, "psutil", None)

        def _raise(pid, sig):
            raise OSError("no such process")

        monkeypatch.setattr(lifecycle.os, "kill", _raise)
        assert lifecycle.pid_running(1234) is False


class TestHeadlessWindowsPaths:
    def test_start_headless_sets_windows_creationflags(self, monkeypatch, tmp_path):
        pid_path = tmp_path / "keepalive.pid"
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(pid_path))
        monkeypatch.setattr(lifecycle, "is_windows", lambda: True)
        # Provide the Windows-only flags so the OR expression resolves.
        monkeypatch.setattr(lifecycle.subprocess, "CREATE_NO_WINDOW", 0x08000000, raising=False)
        monkeypatch.setattr(lifecycle.subprocess, "DETACHED_PROCESS", 0x00000008, raising=False)

        captured = {}

        class _Proc:
            pid = 7777

        def _popen(cmd, **kwargs):
            captured.update(kwargs)
            return _Proc()

        monkeypatch.setattr(lifecycle.subprocess, "Popen", _popen)
        pid = lifecycle.start_headless(["--minutes", "5"])
        assert pid == 7777
        # Windows branch OR-combines the two detach flags into creationflags.
        assert captured["creationflags"] == (0x08000000 | 0x00000008)

    def test_stop_headless_terminates_via_psutil(self, monkeypatch, tmp_path):
        pid_path = tmp_path / "keepalive.pid"
        pid_path.write_text("4242", encoding="ascii")
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(pid_path))

        terminated = {}

        class _FakeProcess:
            def __init__(self, pid):
                terminated["pid"] = pid

            def terminate(self):
                terminated["terminated"] = True

        fake_psutil = types.ModuleType("psutil")
        fake_psutil.pid_exists = lambda pid: True
        fake_psutil.Process = _FakeProcess
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        assert lifecycle.stop_headless() is True
        assert terminated == {"pid": 4242, "terminated": True}
        assert not pid_path.exists()
