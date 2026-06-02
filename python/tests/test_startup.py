"""Tests for keepalive.startup — relaunch argument assembly."""

from keepalive import startup


def test_plain_relaunch_is_empty():
    assert startup.startup_arguments() == []


def test_interval_only_when_non_default():
    assert startup.startup_arguments(interval_seconds=30) == ["--interval-seconds", "30"]


def test_interval_omitted_when_default():
    assert startup.startup_arguments(interval_seconds=60) == []


def test_minutes_only_when_non_zero():
    assert startup.startup_arguments(minutes=90) == ["--minutes", "90"]


def test_quiet_flag():
    assert startup.startup_arguments(quiet=True) == ["--quiet"]


def test_system_only_flag():
    assert startup.startup_arguments(system_only=True) == ["--system-only"]


def test_all_microsoft_apps_flag():
    assert startup.startup_arguments(all_microsoft_apps=True) == ["--all-microsoft-apps"]


def test_tray_flag():
    assert startup.startup_arguments(tray=True) == ["--tray"]


def test_composes_every_option_in_order():
    assert startup.startup_arguments(
        interval_seconds=30,
        minutes=90,
        quiet=True,
        system_only=True,
        all_microsoft_apps=True,
        tray=True,
    ) == [
        "--interval-seconds", "30",
        "--minutes", "90",
        "--quiet",
        "--system-only",
        "--all-microsoft-apps",
        "--tray",
    ]
