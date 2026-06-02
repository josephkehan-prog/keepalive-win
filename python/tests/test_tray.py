"""Tests for keepalive.tray — the system-tray icon presentation logic."""

import sys
import types
from unittest.mock import MagicMock

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

    def test_returns_true_when_deps_importable(self, monkeypatch):
        fake_pystray = types.ModuleType("pystray")
        fake_pil = types.ModuleType("PIL")
        fake_pil_image = types.ModuleType("PIL.Image")
        fake_pil.Image = fake_pil_image
        monkeypatch.setitem(sys.modules, "pystray", fake_pystray)
        monkeypatch.setitem(sys.modules, "PIL", fake_pil)
        monkeypatch.setitem(sys.modules, "PIL.Image", fake_pil_image)
        assert tray.tray_available() is True

    def test_returns_false_when_pystray_missing(self, monkeypatch):
        monkeypatch.delitem(sys.modules, "pystray", raising=False)
        assert tray.tray_available() is False


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

    def test_renders_with_mocked_pillow(self, monkeypatch):
        fake_img = MagicMock()
        fake_draw = MagicMock()

        fake_image_mod = types.ModuleType("PIL.Image")
        fake_image_mod.new = MagicMock(return_value=fake_img)
        fake_imagedraw_mod = types.ModuleType("PIL.ImageDraw")
        fake_imagedraw_mod.Draw = MagicMock(return_value=fake_draw)

        fake_pil = types.ModuleType("PIL")
        fake_pil.Image = fake_image_mod
        fake_pil.ImageDraw = fake_imagedraw_mod

        monkeypatch.setitem(sys.modules, "PIL", fake_pil)
        monkeypatch.setitem(sys.modules, "PIL.Image", fake_image_mod)
        monkeypatch.setitem(sys.modules, "PIL.ImageDraw", fake_imagedraw_mod)

        result = tray.build_icon_image(running=True, tick=0, size=64)
        assert result is fake_img
        fake_image_mod.new.assert_called_once_with("RGBA", (64, 64), (0, 0, 0, 0))

    def test_renders_blink_frame_with_mocked_pillow(self, monkeypatch):
        fake_img = MagicMock()
        fake_draw = MagicMock()

        fake_image_mod = types.ModuleType("PIL.Image")
        fake_image_mod.new = MagicMock(return_value=fake_img)
        fake_imagedraw_mod = types.ModuleType("PIL.ImageDraw")
        fake_imagedraw_mod.Draw = MagicMock(return_value=fake_draw)

        fake_pil = types.ModuleType("PIL")
        fake_pil.Image = fake_image_mod
        fake_pil.ImageDraw = fake_imagedraw_mod

        monkeypatch.setitem(sys.modules, "PIL", fake_pil)
        monkeypatch.setitem(sys.modules, "PIL.Image", fake_image_mod)
        monkeypatch.setitem(sys.modules, "PIL.ImageDraw", fake_imagedraw_mod)

        # Odd tick → blink (closed eyes rendered via draw.line)
        result = tray.build_icon_image(running=True, tick=1, size=64)
        assert result is fake_img
        assert fake_draw.line.call_count == 2

    def test_renders_paused_state_with_mocked_pillow(self, monkeypatch):
        fake_img = MagicMock()
        fake_draw = MagicMock()

        fake_image_mod = types.ModuleType("PIL.Image")
        fake_image_mod.new = MagicMock(return_value=fake_img)
        fake_imagedraw_mod = types.ModuleType("PIL.ImageDraw")
        fake_imagedraw_mod.Draw = MagicMock(return_value=fake_draw)

        fake_pil = types.ModuleType("PIL")
        fake_pil.Image = fake_image_mod
        fake_pil.ImageDraw = fake_imagedraw_mod

        monkeypatch.setitem(sys.modules, "PIL", fake_pil)
        monkeypatch.setitem(sys.modules, "PIL.Image", fake_image_mod)
        monkeypatch.setitem(sys.modules, "PIL.ImageDraw", fake_imagedraw_mod)

        # Paused (running=False) → amber, open eyes, no blink
        result = tray.build_icon_image(running=False, tick=0, size=64)
        assert result is fake_img
        # Open eyes are drawn with ellipse, not line
        assert fake_draw.ellipse.call_count == 2
        assert fake_draw.line.call_count == 0


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

    def test_refresh_swallows_exception_from_broken_icon(self):
        class _BrokenIcon:
            def __setattr__(self, name, value):
                raise RuntimeError(f"broken icon: {name}")

        c = TrayController()
        # Bypass our __setattr__ guard: assign the broken icon via object.__setattr__.
        object.__setattr__(c, "_icon", _BrokenIcon())
        c.refresh()  # must not propagate the RuntimeError
