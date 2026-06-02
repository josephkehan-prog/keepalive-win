"""Tests for the --jitter and --max-idle features (pure logic).

Written test-first: these target functions that don't exist yet (RED), then
drive the minimal implementation in keepalive.core / keepalive.win32.
"""

import pytest

from keepalive import core


class _FakeRng:
    """A deterministic stand-in for random.Random with a fixed randint result."""

    def __init__(self, value):
        self.value = value
        self.calls = []

    def randint(self, low, high):
        self.calls.append((low, high))
        return self.value


class TestApplyJitter:
    def test_zero_jitter_returns_interval_unchanged(self):
        assert core.apply_jitter(60, 0) == 60

    def test_negative_jitter_treated_as_disabled(self):
        assert core.apply_jitter(60, -5) == 60

    def test_adds_positive_delta(self):
        rng = _FakeRng(7)
        assert core.apply_jitter(60, 10, rng=rng) == 67

    def test_subtracts_negative_delta(self):
        rng = _FakeRng(-8)
        assert core.apply_jitter(60, 10, rng=rng) == 52

    def test_samples_symmetric_range(self):
        rng = _FakeRng(0)
        core.apply_jitter(60, 15, rng=rng)
        assert rng.calls == [(-15, 15)]

    def test_clamps_to_at_least_one_second(self):
        rng = _FakeRng(-100)
        assert core.apply_jitter(10, 100, rng=rng) == 1


class TestIdleExceeded:
    def test_disabled_when_max_idle_zero(self):
        assert core.idle_exceeded(99999, 0) is False

    def test_disabled_when_max_idle_negative(self):
        assert core.idle_exceeded(99999, -1) is False

    def test_false_below_threshold(self):
        # 5 minutes idle, threshold 10 minutes.
        assert core.idle_exceeded(5 * 60, 10) is False

    def test_true_at_threshold(self):
        assert core.idle_exceeded(10 * 60, 10) is True

    def test_true_above_threshold(self):
        assert core.idle_exceeded(11 * 60, 10) is True


class TestIdleSecondsFromTicks:
    def test_simple_difference(self):
        assert core.idle_seconds_from_ticks(2000, 5000) == 3.0

    def test_handles_32bit_wraparound(self):
        # GetTickCount wraps at 2**32 ms; last just before wrap, now just after.
        last = 0xFFFFFFF0
        now = 0x00000010
        assert core.idle_seconds_from_ticks(last, now) == pytest.approx(0.032)

    def test_zero_when_equal(self):
        assert core.idle_seconds_from_ticks(1234, 1234) == 0.0
