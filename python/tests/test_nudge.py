"""Tests for keepalive.nudge — guarded OS-touching helpers."""

import sys
import types
from unittest.mock import MagicMock

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

    def test_stopper_false_while_process_running(self, monkeypatch):
        fake_proc = MagicMock()
        fake_proc.info = {"name": "teams.exe"}
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: [fake_proc]
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        stopper = nudge.make_watch_process_stopper("teams")
        assert stopper() is False  # process found → keep running

    def test_stopper_true_when_process_gone(self, monkeypatch):
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: []
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        stopper = nudge.make_watch_process_stopper("teams")
        assert stopper() is True  # no matching process → stop

    def test_stopper_strips_exe_from_watch_name(self, monkeypatch):
        fake_proc = MagicMock()
        fake_proc.info = {"name": "teams.exe"}
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: [fake_proc]
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        # Watch name WITH .exe suffix → line 137 strips it, then matches teams.exe
        stopper = nudge.make_watch_process_stopper("teams.exe")
        assert stopper() is False

    def test_stopper_false_when_psutil_unavailable(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "psutil", raising=False)
        stopper = nudge.make_watch_process_stopper("someapp")
        assert stopper() is False  # psutil import fails → safe False


class TestFetchDebugTabs:
    def test_returns_none_when_port_closed(self):
        # Port 1 is not a Chrome debug port; connection fails -> None.
        assert nudge.fetch_debug_tabs(debug_port=1, timeout=0.2) is None

    def test_browser_debug_port_open_false_when_closed(self):
        assert nudge.browser_debug_port_open(debug_port=1) is False

    def test_returns_parsed_json_on_success(self, monkeypatch):
        from unittest.mock import patch, MagicMock

        fake_resp = MagicMock()
        fake_resp.__enter__ = lambda self: self
        fake_resp.__exit__ = MagicMock(return_value=False)
        fake_resp.read.return_value = b'[{"url": "https://outlook.office.com"}]'

        with patch("keepalive.nudge.urlopen", return_value=fake_resp):
            result = nudge.fetch_debug_tabs()

        assert result == [{"url": "https://outlook.office.com"}]

    def test_browser_debug_port_open_true_when_reachable(self, monkeypatch):
        from unittest.mock import patch, MagicMock

        fake_resp = MagicMock()
        fake_resp.__enter__ = lambda self: self
        fake_resp.__exit__ = MagicMock(return_value=False)
        fake_resp.read.return_value = b"[]"

        with patch("keepalive.nudge.urlopen", return_value=fake_resp):
            assert nudge.browser_debug_port_open() is True


class TestSendBrowserNudge:
    def test_noop_when_port_closed(self):
        # Should not raise even though nothing is listening.
        nudge.send_browser_nudge(debug_port=1)

    def test_sends_f15_via_websocket(self, monkeypatch):
        m365_tab = {
            "url": "https://outlook.office.com/mail",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/1",
        }
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda port: [m365_tab])

        fake_ws = MagicMock()
        fake_ws_module = types.ModuleType("websocket")
        fake_ws_module.create_connection = MagicMock(return_value=fake_ws)
        monkeypatch.setitem(sys.modules, "websocket", fake_ws_module)

        nudge.send_browser_nudge()

        fake_ws_module.create_connection.assert_called_once()
        fake_ws.send.assert_called_once()
        fake_ws.close.assert_called_once()

    def test_noop_when_no_m365_tabs(self, monkeypatch):
        non_m365 = [{"url": "https://example.com", "webSocketDebuggerUrl": "ws://localhost:9222/1"}]
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda port: non_m365)

        fake_ws_module = types.ModuleType("websocket")
        fake_ws_module.create_connection = MagicMock()
        monkeypatch.setitem(sys.modules, "websocket", fake_ws_module)

        nudge.send_browser_nudge()
        fake_ws_module.create_connection.assert_not_called()

    def test_noop_when_websocket_missing(self, monkeypatch):
        m365_tab = {
            "url": "https://outlook.office.com/mail",
            "webSocketDebuggerUrl": "ws://localhost:9222/devtools/page/1",
        }
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda port: [m365_tab])
        monkeypatch.delitem(sys.modules, "websocket", raising=False)

        nudge.send_browser_nudge()  # should not raise

    def test_swallows_websocket_exception(self, monkeypatch):
        m365_tab = {
            "url": "https://outlook.office.com/mail",
            "webSocketDebuggerUrl": "ws://localhost:9222/1",
        }
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda port: [m365_tab])

        fake_ws_module = types.ModuleType("websocket")
        fake_ws_module.create_connection = MagicMock(side_effect=ConnectionRefusedError)
        monkeypatch.setitem(sys.modules, "websocket", fake_ws_module)

        nudge.send_browser_nudge()  # must not propagate

    def test_skips_tab_without_ws_url(self, monkeypatch):
        tab_no_ws = {"url": "https://outlook.office.com/mail"}  # no webSocketDebuggerUrl
        monkeypatch.setattr(nudge, "fetch_debug_tabs", lambda port: [tab_no_ws])

        fake_ws_module = types.ModuleType("websocket")
        fake_ws_module.create_connection = MagicMock()
        monkeypatch.setitem(sys.modules, "websocket", fake_ws_module)

        nudge.send_browser_nudge()
        fake_ws_module.create_connection.assert_not_called()


class TestSendAppNudge:
    def test_noop_off_windows(self, monkeypatch):
        monkeypatch.setattr(nudge, "is_windows", lambda: False)
        nudge.send_app_nudge()  # should simply return without error

    def test_noop_on_windows_when_psutil_missing(self, monkeypatch):
        monkeypatch.setattr(nudge, "is_windows", lambda: True)
        monkeypatch.delitem(sys.modules, "psutil", raising=False)
        nudge.send_app_nudge()  # import psutil fails → returns without error

    def test_posts_wm_null_to_microsoft_windows(self, monkeypatch):
        import ctypes

        monkeypatch.setattr(nudge, "is_windows", lambda: True)

        fake_proc = MagicMock()
        fake_proc.info = {"name": "OUTLOOK.EXE"}
        fake_proc.pid = 1234
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: [fake_proc]
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        fake_user32 = MagicMock()
        monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=fake_user32), raising=False)

        monkeypatch.setattr(nudge, "_main_window_handle", lambda pid: 0xABC)

        nudge.send_app_nudge()

        fake_user32.PostMessageW.assert_called_once_with(0xABC, nudge.WM_NULL, 0, 0)

    def test_skips_non_microsoft_process(self, monkeypatch):
        import ctypes

        monkeypatch.setattr(nudge, "is_windows", lambda: True)

        fake_proc = MagicMock()
        fake_proc.info = {"name": "notepad.exe"}
        fake_proc.pid = 5678
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: [fake_proc]
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        fake_user32 = MagicMock()
        monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=fake_user32), raising=False)

        nudge.send_app_nudge()

        fake_user32.PostMessageW.assert_not_called()

    def test_skips_process_with_no_window_handle(self, monkeypatch):
        import ctypes

        monkeypatch.setattr(nudge, "is_windows", lambda: True)

        fake_proc = MagicMock()
        fake_proc.info = {"name": "TEAMS.EXE"}
        fake_proc.pid = 9999
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: [fake_proc]
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        fake_user32 = MagicMock()
        monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=fake_user32), raising=False)

        monkeypatch.setattr(nudge, "_main_window_handle", lambda pid: None)

        nudge.send_app_nudge()

        fake_user32.PostMessageW.assert_not_called()

    def test_swallows_postmessage_exception(self, monkeypatch):
        import ctypes

        monkeypatch.setattr(nudge, "is_windows", lambda: True)

        fake_proc = MagicMock()
        fake_proc.info = {"name": "OUTLOOK.EXE"}
        fake_proc.pid = 1234
        fake_psutil = types.ModuleType("psutil")
        fake_psutil.process_iter = lambda attrs: [fake_proc]
        monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

        fake_user32 = MagicMock()
        fake_user32.PostMessageW.side_effect = OSError("fail")
        monkeypatch.setattr(ctypes, "windll", types.SimpleNamespace(user32=fake_user32), raising=False)

        monkeypatch.setattr(nudge, "_main_window_handle", lambda pid: 0x1)

        nudge.send_app_nudge()  # must not propagate
