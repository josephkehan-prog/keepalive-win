"""Tests for keepalive.core — the pure keep-alive logic."""

from datetime import datetime

import pytest

from keepalive import core


class TestIntervalValid:
    def test_accepts_minimum_interval(self):
        assert core.interval_valid(10) is True

    def test_accepts_normal_interval(self):
        assert core.interval_valid(60) is True

    def test_rejects_below_minimum(self):
        assert core.interval_valid(5) is False

    def test_rejects_zero(self):
        assert core.interval_valid(0) is False


class TestEndTime:
    start = datetime(2026, 5, 31, 12, 0, 0)

    def test_none_when_minutes_zero(self):
        assert core.end_time(self.start, 0) is None

    def test_none_when_minutes_negative(self):
        assert core.end_time(self.start, -5) is None

    def test_start_plus_minutes(self):
        assert core.end_time(self.start, 30) == datetime(2026, 5, 31, 12, 30, 0)


class TestAwakeFlags:
    def test_default_is_continuous_system_display(self):
        # 0x80000000 | 0x1 | 0x2 = 2147483651
        assert core.awake_flags() == 2147483651

    def test_result_is_unsigned(self):
        assert core.awake_flags() > 0

    def test_system_only_clears_display(self):
        # ES_CONTINUOUS | ES_SYSTEM_REQUIRED = 2147483649
        assert core.awake_flags(keep_display_on=False) == 2147483649

    def test_display_only(self):
        assert core.awake_flags(keep_system_awake=False) == 2147483650

    def test_both_cleared_is_just_continuous(self):
        assert core.awake_flags(keep_system_awake=False, keep_display_on=False) == 2147483648

    def test_release_flags_is_continuous(self):
        assert core.release_flags() == 2147483648


class TestCatFrame:
    def test_eyes_open_for_tick_zero(self):
        assert core.cat_frame(0) == "=^.^="

    def test_blink_for_tick_one(self):
        assert core.cat_frame(1) == "=^-^="

    def test_wraps_after_last(self):
        assert core.cat_frame(2) == "=^.^="

    def test_alternates(self):
        assert core.cat_frame(3) == "=^-^="

    def test_default_is_eyes_open(self):
        assert core.cat_frame() == "=^.^="

    def test_negative_counter(self):
        assert core.cat_frame(-1) == "=^-^="

    def test_ascii_only(self):
        assert all(ord(ch) <= 127 for ch in core.cat_frame(0))


class TestShouldStop:
    now = datetime(2026, 5, 31, 12, 0, 0)

    def test_never_when_end_none(self):
        assert core.should_stop(self.now, None) is False

    def test_not_before_end(self):
        assert core.should_stop(self.now, datetime(2026, 5, 31, 12, 30, 0)) is False

    def test_stops_at_end(self):
        assert core.should_stop(self.now, self.now) is True

    def test_stops_after_end(self):
        assert core.should_stop(self.now, datetime(2026, 5, 31, 11, 59, 0)) is True
