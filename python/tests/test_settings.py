"""Tests for keepalive.settings — CLI/profile precedence."""

from keepalive.settings import Settings, resolve_settings


def _empty_cli(**overrides):
    base = {
        "interval_seconds": None,
        "minutes": None,
        "quiet": False,
        "system_only": False,
        "all_microsoft_apps": False,
        "browser_keep_alive": False,
        "tray": False,
    }
    base.update(overrides)
    return base


def test_defaults_when_nothing_set():
    s = resolve_settings(_empty_cli())
    assert s == Settings()
    assert s.interval_seconds == 60
    assert s.minutes == 0


def test_cli_values_applied():
    s = resolve_settings(_empty_cli(interval_seconds=30, minutes=90, quiet=True))
    assert s.interval_seconds == 30
    assert s.minutes == 90
    assert s.quiet is True


def test_profile_fills_unset_values():
    preset = {"Minutes": 120, "SystemOnly": True}
    s = resolve_settings(_empty_cli(), preset)
    assert s.minutes == 120
    assert s.system_only is True


def test_cli_overrides_profile():
    preset = {"Minutes": 120}
    s = resolve_settings(_empty_cli(minutes=60), preset)
    assert s.minutes == 60


def test_profile_enables_boolean_flag():
    preset = {"AllMicrosoftApps": True, "Quiet": True}
    s = resolve_settings(_empty_cli(), preset)
    assert s.all_microsoft_apps is True
    assert s.quiet is True


def test_tray_profile():
    preset = {"Tray": True}
    s = resolve_settings(_empty_cli(), preset)
    assert s.tray is True


def test_browser_keep_alive_profile():
    preset = {"BrowserKeepAlive": True}
    s = resolve_settings(_empty_cli(), preset)
    assert s.browser_keep_alive is True


def test_unknown_profile_keys_ignored():
    preset = {"Bogus": 1, "Minutes": 5}
    s = resolve_settings(_empty_cli(), preset)
    assert s.minutes == 5
