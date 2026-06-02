"""Tests for keepalive.lifecycle — PID file + run-at-logon helpers."""

import os

from keepalive import lifecycle


class TestPidFile:
    def test_write_read_clear_roundtrip(self, monkeypatch, tmp_path):
        pid_path = tmp_path / "keepalive.pid"
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(pid_path))

        assert lifecycle.read_pid() is None  # nothing yet
        lifecycle.write_pid(4321)
        assert lifecycle.read_pid() == 4321
        lifecycle.clear_pid()
        assert lifecycle.read_pid() is None

    def test_read_pid_handles_garbage(self, monkeypatch, tmp_path):
        pid_path = tmp_path / "keepalive.pid"
        pid_path.write_text("not-a-number", encoding="ascii")
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(pid_path))
        assert lifecycle.read_pid() is None

    def test_clear_pid_when_absent_is_silent(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(tmp_path / "missing.pid"))
        lifecycle.clear_pid()  # no error


class TestPidRunning:
    def test_none_is_false(self):
        assert lifecycle.pid_running(None) is False

    def test_zero_is_false(self):
        assert lifecycle.pid_running(0) is False

    def test_current_process_is_running(self):
        assert lifecycle.pid_running(os.getpid()) is True


class TestLogonTaskOffWindows:
    def test_install_false_off_windows(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: False)
        assert lifecycle.install_logon_task([]) is False

    def test_uninstall_false_off_windows(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: False)
        assert lifecycle.uninstall_logon_task() is False

    def test_query_false_off_windows(self, monkeypatch):
        monkeypatch.setattr(lifecycle, "is_windows", lambda: False)
        assert lifecycle.logon_task_installed() is False


class TestStopHeadless:
    def test_false_when_no_pid_file(self, monkeypatch, tmp_path):
        monkeypatch.setattr(lifecycle, "pid_file_path", lambda: str(tmp_path / "none.pid"))
        assert lifecycle.stop_headless() is False
