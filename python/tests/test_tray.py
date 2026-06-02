"""Tests for keepalive.tray — the system-tray icon presentation logic."""

import pytest

from keepalive import tray
from keepalive.tray import TrayController


class TestTooltip:
    def test_running_tooltip(self):
        text = tray.tray_tooltip(True, 60)
        assert "awake" in text
        assert "60s" in text

    def test_running_with_mode_suffix(self):
        text = tray.tray_tooltip(True, 30, " (display may sleep)")
        assert "display may sleep" in text

    def test_paused_tooltip(self):
        assert tray.tray_tooltip(False, 60) == "KeepAlive - paused"


class TestMenuLabels:
    def test_running_shows_pause(self):
        assert tray.tray_menu_labels(True) == ["Pause", "Quit"]

    def test_paused_shows_resume(self):
        assert tray.tray_menu_labels(False) == ["Resume", "Quit"]


class TestIconColor:
    def test_paused_is_amber(self):
        assert tray.icon_color(False) == tray.COLOR_PAUSED

    def test_running_blinks_between_two_colors(self):
        assert tray.icon_color(True, 0) == tray.COLOR_AWAKE_BRIGHT
        assert tray.icon_color(True, 1) == tray.COLOR_AWAKE_DIM
        assert tray.icon_color(True, 2) == tray.COLOR_AWAKE_BRIGHT


class TestTrayAvailable:
    def test_returns_bool(self):
        assert isinstance(tray.tray_available(), bool)


class TestBuildIconImage:
    def test_builds_image_or_raises_without_pillow(self):
        try:
            from PIL import Image  # noqa: F401
        except Exception:
            with pytest.raises(RuntimeError):
                tray.build_icon_image()
            return
        img = tray.build_icon_image(True, 0, size=64)
        assert img.size == (64, 64)
        # Closed-eye frame still renders.
        assert tray.build_icon_image(True, 1).size == (64, 64)
        assert tray.build_icon_image(False, 0).size == (64, 64)


class TestTrayController:
    def test_initial_state_not_stopped_not_paused(self):
        c = TrayController(interval_seconds=45)
        assert c.should_stop() is False
        assert c.paused() is False

    def test_request_stop(self):
        c = TrayController()
        c.request_stop()
        assert c.should_stop() is True

    def test_toggle_pause(self):
        c = TrayController()
        c.toggle_pause()
        assert c.paused() is True
        c.toggle_pause()
        assert c.paused() is False

    def test_tooltip_reflects_pause(self):
        c = TrayController(interval_seconds=45, mode_suffix=" (display may sleep)")
        assert "awake" in c.tooltip()
        c.toggle_pause()
        assert c.tooltip() == "KeepAlive - paused"

    def test_on_status_updates_tick_without_icon(self):
        c = TrayController()
        # No live pystray icon, so this just records the tick and no-ops refresh.
        c.on_status(7, "=^-^=", None)
        assert c._tick == 7

    def test_refresh_without_icon_is_noop(self):
        c = TrayController()
        c.refresh()  # should not raise
