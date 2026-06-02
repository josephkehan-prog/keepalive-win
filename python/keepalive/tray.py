"""System-tray icon for the keep-alive (the new Python-only feature).

Runs a small notification-area icon so the keep-alive can sit quietly in the
tray instead of holding a console window. The icon animates the same blinking
ASCII cat the CLI prints, the tooltip shows live status, and a right-click menu
exposes Pause/Resume and Quit.

The pure presentation logic (tooltip text, menu labels, palette, blink frame)
is fully testable here. The actual ``pystray``/``Pillow`` drawing and event
loop are imported lazily so the rest of the package — and its tests — run on
any platform without those optional dependencies installed.
"""

from __future__ import annotations

import threading
from typing import Callable, List, Optional, Tuple

# Accent palette for the tray glyph. "Awake" frames pulse between a bright and
# a dim green so the icon visibly blinks like the CLI cat; "paused" is amber.
COLOR_AWAKE_BRIGHT: Tuple[int, int, int] = (46, 204, 113)
COLOR_AWAKE_DIM: Tuple[int, int, int] = (33, 150, 83)
COLOR_PAUSED: Tuple[int, int, int] = (243, 156, 18)
COLOR_FACE: Tuple[int, int, int] = (24, 26, 32)


def tray_available() -> bool:
    """True when the optional tray dependencies (pystray + Pillow) import."""
    try:
        import pystray  # noqa: F401
        from PIL import Image  # noqa: F401
    except Exception:
        return False
    return True


def tray_tooltip(running: bool, interval_seconds: int, mode_suffix: str = "") -> str:
    """Build the hover tooltip text for the tray icon."""
    if not running:
        return "KeepAlive - paused"
    return f"KeepAlive - awake{mode_suffix} (nudge every {interval_seconds}s)"


def tray_menu_labels(running: bool) -> List[str]:
    """Return the right-click menu labels for the current state.

    The first item toggles between Pause and Resume depending on whether the
    keep-alive loop is currently running.
    """
    toggle = "Pause" if running else "Resume"
    return [toggle, "Quit"]


def icon_color(running: bool, tick: int = 0) -> Tuple[int, int, int]:
    """Pick the glyph accent colour for the current state and blink tick.

    While running the colour alternates each tick (the blink); while paused it
    stays amber.
    """
    if not running:
        return COLOR_PAUSED
    return COLOR_AWAKE_BRIGHT if tick % 2 == 0 else COLOR_AWAKE_DIM


def build_icon_image(running: bool = True, tick: int = 0, size: int = 64):
    """Draw the tray glyph as a PIL ``Image`` (lazy import).

    A rounded square in the state colour with two cat ears and two eyes that
    "close" on odd ticks while awake, echoing the ``=^.^=`` / ``=^-^=`` blink.
    Raises ``RuntimeError`` if Pillow is unavailable.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception as exc:  # pragma: no cover - exercised only without Pillow
        raise RuntimeError("Pillow is required to render the tray icon") from exc

    accent = icon_color(running, tick)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    pad = size // 8
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad], radius=size // 6, fill=accent
    )

    # Two triangular ears on top of the rounded face.
    ear = size // 6
    draw.polygon([(pad, pad + ear), (pad + ear, pad - ear // 2), (pad + 2 * ear, pad + ear)], fill=accent)
    draw.polygon(
        [(size - pad - 2 * ear, pad + ear), (size - pad - ear, pad - ear // 2), (size - pad, pad + ear)],
        fill=accent,
    )

    eye_y = size // 2
    left_x = size // 2 - size // 6
    right_x = size // 2 + size // 6
    blink = running and (tick % 2 == 1)
    if blink:
        # Closed eyes: short horizontal lines.
        draw.line([(left_x - 5, eye_y), (left_x + 5, eye_y)], fill=COLOR_FACE, width=3)
        draw.line([(right_x - 5, eye_y), (right_x + 5, eye_y)], fill=COLOR_FACE, width=3)
    else:
        r = size // 14
        draw.ellipse([left_x - r, eye_y - r, left_x + r, eye_y + r], fill=COLOR_FACE)
        draw.ellipse([right_x - r, eye_y - r, right_x + r, eye_y + r], fill=COLOR_FACE)
    return img


class TrayController:
    """Drive a ``pystray`` icon that reflects and controls the keep-alive loop.

    The keep-alive loop runs on a worker thread; the tray icon owns the main
    thread (required by some platforms). State changes from menu clicks flip
    threading flags the loop polls via :meth:`should_stop` / :meth:`paused`.
    """

    def __init__(self, interval_seconds: int = 60, mode_suffix: str = "") -> None:
        self._interval_seconds = interval_seconds
        self._mode_suffix = mode_suffix
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._tick = 0
        self._icon = None  # set in run()

    # --- state queried by the run loop -------------------------------------
    def should_stop(self) -> bool:
        """True once the user picked Quit (wired to the loop's ``stop_when``)."""
        return self._stop.is_set()

    def paused(self) -> bool:
        return self._paused.is_set()

    def request_stop(self) -> None:
        self._stop.set()

    def toggle_pause(self) -> None:
        if self._paused.is_set():
            self._paused.clear()
        else:
            self._paused.set()
        self.refresh()

    def on_status(self, tick: int, frame: str, now) -> None:
        """Hook passed to the runner so the icon blinks in step with the CLI."""
        self._tick = tick
        self.refresh()

    # --- presentation ------------------------------------------------------
    def tooltip(self) -> str:
        return tray_tooltip(not self.paused(), self._interval_seconds, self._mode_suffix)

    def refresh(self) -> None:
        """Re-render the icon image + tooltip if a live pystray icon exists."""
        if self._icon is None:
            return
        try:  # pragma: no cover - requires a live pystray icon
            self._icon.icon = build_icon_image(not self.paused(), self._tick)
            self._icon.title = self.tooltip()
            self._icon.update_menu()
        except Exception:
            pass

    def run(self, run_loop: Callable[[], None]) -> None:  # pragma: no cover - needs display
        """Start ``run_loop`` on a worker thread and block on the tray icon."""
        import pystray

        worker = threading.Thread(target=run_loop, daemon=True)

        def _toggle(icon, item):
            self.toggle_pause()

        def _quit(icon, item):
            self.request_stop()
            icon.stop()

        menu = pystray.Menu(
            pystray.MenuItem(
                lambda item: "Resume" if self.paused() else "Pause", _toggle
            ),
            pystray.MenuItem("Quit", _quit),
        )
        self._icon = pystray.Icon(
            "keepalive",
            icon=build_icon_image(True, 0),
            title=self.tooltip(),
            menu=menu,
        )
        worker.start()
        self._icon.run()
        # Tray closed: make sure the loop is asked to stop and drained.
        self.request_stop()
        worker.join(timeout=5)
