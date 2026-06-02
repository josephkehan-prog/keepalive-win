"""Tests for the Windows side-effect modules using injected fakes.

These exercise the Windows code paths on any platform by monkeypatching the
``is_windows`` guard and the lazily-resolved ctypes / subprocess handles, so
the bodies are covered without a real Windows host.
"""

import subprocess

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
