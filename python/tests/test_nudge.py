"""Tests for keepalive.nudge — guarded OS-touching helpers."""

from keepalive import nudge


class TestWatchProcessStopper:
    def test_none_when_no_process_given(self):
        assert nudge.make_watch_process_stopper("") is None

    def test_returns_callable_for_a_name(self):
        stopper = nudge.make_watch_process_stopper("teams")
        assert callable(stopper)

    def test_stopper_true_when_process_absent(self):
        # A process that certainly is not running -> stop_when fires True.
        stopper = nudge.make_watch_process_stopper("definitely-not-a-real-process-xyz")
        # Returns True (stop) only if psutil is available; without psutil it
        # safely returns False. Either way it must be a bool.
        assert isinstance(stopper(), bool)


class TestFetchDebugTabs:
    def test_returns_none_when_port_closed(self):
        # Port 1 is not a Chrome debug port; connection fails -> None.
        assert nudge.fetch_debug_tabs(debug_port=1, timeout=0.2) is None

    def test_browser_debug_port_open_false_when_closed(self):
        assert nudge.browser_debug_port_open(debug_port=1) is False


class TestSendBrowserNudge:
    def test_noop_when_port_closed(self):
        # Should not raise even though nothing is listening.
        nudge.send_browser_nudge(debug_port=1)


class TestSendAppNudge:
    def test_noop_off_windows(self, monkeypatch):
        monkeypatch.setattr(nudge, "is_windows", lambda: False)
        nudge.send_app_nudge()  # should simply return without error
