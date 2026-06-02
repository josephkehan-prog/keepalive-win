"""Tests for keepalive.runner — the injectable run loop."""

from datetime import datetime

from keepalive.runner import run_keepalive


def _noop_emit(_line):
    pass


def test_calls_enable_at_loop_start():
    state = {"enabled": False}
    run_keepalive(
        stop_when=lambda: True,
        enable=lambda: state.__setitem__("enabled", True),
        restore=lambda: None,
        tick=lambda: None,
        emit=_noop_emit,
    )
    assert state["enabled"] is True


def test_calls_restore_even_when_enable_raises():
    state = {"restored": False}

    def boom():
        raise RuntimeError("simulated error")

    try:
        run_keepalive(
            enable=boom,
            restore=lambda: state.__setitem__("restored", True),
            tick=lambda: None,
            emit=_noop_emit,
        )
    except RuntimeError:
        pass
    assert state["restored"] is True


def test_calls_restore_on_normal_exit():
    state = {"restored": False}
    run_keepalive(
        stop_when=lambda: True,
        enable=lambda: None,
        restore=lambda: state.__setitem__("restored", True),
        tick=lambda: None,
        emit=_noop_emit,
    )
    assert state["restored"] is True


def test_no_nudge_when_stop_immediately():
    state = {"nudged": False}
    run_keepalive(
        stop_when=lambda: True,
        nudge=lambda: state.__setitem__("nudged", True),
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: None,
        emit=_noop_emit,
    )
    assert state["nudged"] is False


def test_nudge_once_before_auto_stop():
    clocks = iter([
        datetime(2026, 1, 1, 12, 0, 0),   # start
        datetime(2026, 1, 1, 12, 0, 30),  # first should_stop check
        datetime(2026, 1, 1, 12, 0, 30),  # status emit
        datetime(2026, 1, 1, 12, 2, 0),   # inner-loop should_stop -> break
        datetime(2026, 1, 1, 12, 2, 0),   # next outer should_stop -> break
        datetime(2026, 1, 1, 12, 2, 0),
        datetime(2026, 1, 1, 12, 2, 0),
    ])
    state = {"nudges": 0}
    run_keepalive(
        minutes=1,
        clock=lambda: next(clocks),
        nudge=lambda: state.__setitem__("nudges", state["nudges"] + 1),
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: None,
        emit=_noop_emit,
    )
    assert state["nudges"] == 1


def test_quiet_suppresses_status_lines():
    lines = []
    run_keepalive(
        quiet=True,
        stop_when=lambda: True,
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: None,
        emit=lines.append,
    )
    # Only banner + stopped line; no "awake - next nudge" status lines.
    assert not any("next nudge" in line for line in lines)


def test_app_nudge_called_when_provided():
    clocks = iter([
        datetime(2026, 1, 1, 12, 0, 0),
        datetime(2026, 1, 1, 12, 0, 30),
        datetime(2026, 1, 1, 12, 0, 30),
        datetime(2026, 1, 1, 12, 2, 0),
        datetime(2026, 1, 1, 12, 2, 0),
        datetime(2026, 1, 1, 12, 2, 0),
    ])
    state = {"app": False}
    run_keepalive(
        minutes=1,
        clock=lambda: next(clocks),
        nudge=lambda: None,
        app_nudge=lambda: state.__setitem__("app", True),
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: None,
        emit=_noop_emit,
    )
    assert state["app"] is True


def test_banner_shows_end_time_when_minutes_set():
    lines = []
    clocks = iter([
        datetime(2026, 1, 1, 12, 0, 0),
        datetime(2026, 1, 1, 12, 5, 0),  # already past end -> stop
        datetime(2026, 1, 1, 12, 5, 0),
    ])
    run_keepalive(
        minutes=1,
        clock=lambda: next(clocks),
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: None,
        emit=lines.append,
    )
    assert any("until" in line for line in lines)


def test_on_status_invoked():
    seen = []
    clocks = iter([
        datetime(2026, 1, 1, 12, 0, 0),
        datetime(2026, 1, 1, 12, 0, 30),
        datetime(2026, 1, 1, 12, 0, 30),
        datetime(2026, 1, 1, 12, 2, 0),
        datetime(2026, 1, 1, 12, 2, 0),
        datetime(2026, 1, 1, 12, 2, 0),
    ])
    run_keepalive(
        minutes=1,
        clock=lambda: next(clocks),
        enable=lambda: None,
        restore=lambda: None,
        nudge=lambda: None,
        tick=lambda: None,
        emit=_noop_emit,
        on_status=lambda tick, frame, now: seen.append((tick, frame)),
    )
    assert seen and seen[0][0] == 0


def test_next_interval_overrides_sleep_count():
    # When a next_interval provider is given (used by --jitter), the inner
    # sleep loop should run that many ticks per cycle instead of interval_seconds.
    ticks = {"count": 0}
    intervals = iter([3])  # one cycle then stop
    run_keepalive(
        interval_seconds=60,
        stop_when=lambda: ticks["count"] >= 3,  # stop after 3 ticks
        next_interval=lambda: next(intervals),
        nudge=lambda: None,
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: ticks.__setitem__("count", ticks["count"] + 1),
        emit=_noop_emit,
        quiet=True,
    )
    # 3 ticks consumed from the single jittered interval of 3.
    assert ticks["count"] == 3


def test_status_line_reflects_jittered_interval():
    lines = []
    run_keepalive(
        interval_seconds=60,
        next_interval=lambda: 42,
        stop_when=lambda: len(lines) > 1,  # stop after first status line
        enable=lambda: None,
        restore=lambda: None,
        nudge=lambda: None,
        tick=lambda: None,
        emit=lines.append,
    )
    assert any("next nudge in 42s" in line for line in lines)


def test_browser_nudge_called_when_provided():
    state = {"browser": False}
    run_keepalive(
        stop_when=lambda: state["browser"],  # stop once the browser nudge fired
        browser_nudge=lambda: state.__setitem__("browser", True),
        enable=lambda: None,
        restore=lambda: None,
        nudge=lambda: None,
        tick=lambda: None,
        emit=_noop_emit,
    )
    assert state["browser"] is True


def test_default_emit_prints_to_stdout(capsys):
    # No emit injected → the default _default_emit(print) path is exercised.
    run_keepalive(
        stop_when=lambda: True,
        enable=lambda: None,
        restore=lambda: None,
        tick=lambda: None,
    )
    out = capsys.readouterr().out
    assert "Keeping awake" in out
    assert "normal power behavior restored" in out
