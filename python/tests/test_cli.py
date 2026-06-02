"""Tests for keepalive.cli — argument parsing and command dispatch."""

import pytest

from keepalive import cli
from keepalive.settings import Settings


class TestBuildParser:
    def test_defaults(self):
        args = cli.build_parser().parse_args([])
        assert args.interval_seconds is None
        assert args.minutes is None
        assert args.quiet is False
        assert args.tray is False

    def test_parses_flags(self):
        args = cli.build_parser().parse_args(
            ["--interval-seconds", "30", "--minutes", "90", "--quiet", "--tray"]
        )
        assert args.interval_seconds == 30
        assert args.minutes == 90
        assert args.quiet is True
        assert args.tray is True

    def test_version_exits(self):
        with pytest.raises(SystemExit):
            cli.build_parser().parse_args(["--version"])


class TestCliToSettings:
    def test_plain_defaults(self):
        args = cli.build_parser().parse_args([])
        settings = cli.cli_to_settings(args)
        assert settings == Settings()

    def test_applies_profile(self, tmp_path):
        config = tmp_path / "keepalive.json"
        config.write_text('{"profiles": {"meeting": {"Minutes": 120, "SystemOnly": true}}}', encoding="utf-8")
        args = cli.build_parser().parse_args(["--profile", "meeting"])
        settings = cli.cli_to_settings(args, config_path=str(config))
        assert settings.minutes == 120
        assert settings.system_only is True

    def test_unknown_profile_raises(self, tmp_path):
        config = tmp_path / "keepalive.json"
        config.write_text('{"profiles": {}}', encoding="utf-8")
        args = cli.build_parser().parse_args(["--profile", "ghost"])
        with pytest.raises(SystemExit):
            cli.cli_to_settings(args, config_path=str(config))


class TestLifecycleDispatch:
    def test_install_and_uninstall_conflict(self, capsys):
        args = cli.build_parser().parse_args(["--install", "--uninstall"])
        code = cli._handle_lifecycle(args, Settings())
        assert code == 1

    def test_status_returns_zero(self, capsys):
        args = cli.build_parser().parse_args(["--status"])
        code = cli._handle_lifecycle(args, Settings())
        assert code == 0
        out = capsys.readouterr().out
        assert "logon task" in out.lower()

    def test_uninstall_off_windows_returns_zero(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "uninstall_logon_task", lambda: False)
        args = cli.build_parser().parse_args(["--uninstall"])
        assert cli._handle_lifecycle(args, Settings()) == 0

    def test_no_lifecycle_returns_none(self):
        args = cli.build_parser().parse_args([])
        assert cli._handle_lifecycle(args, Settings()) is None


class TestRun:
    def test_rejects_invalid_interval(self, capsys):
        args = cli.build_parser().parse_args([])
        settings = Settings(interval_seconds=5)
        code = cli.run(args, settings)
        assert code == 1
        assert "interval-seconds" in capsys.readouterr().err

    def test_run_completes_with_stub_loop(self, monkeypatch):
        # Replace the real loop with a no-op so we exercise run() wiring without
        # blocking. Stub the Win32 calls too (they no-op off Windows anyway).
        called = {}

        def fake_loop(**kwargs):
            called.update(kwargs)

        monkeypatch.setattr(cli, "run_keepalive", fake_loop)
        args = cli.build_parser().parse_args([])
        code = cli.run(args, Settings(minutes=0))
        assert code == 0
        assert "nudge" in called

    def test_tray_falls_back_when_unavailable(self, monkeypatch):
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: None)
        # Force the tray to be unavailable so run() uses the console fallback.
        import keepalive.tray as tray_mod

        monkeypatch.setattr(tray_mod, "tray_available", lambda: False)
        args = cli.build_parser().parse_args(["--tray"])
        code = cli.run(args, Settings(tray=True))
        assert code == 0


class TestMoreLifecycleDispatch:
    def test_headless_dispatch(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "start_headless", lambda flags: 4242)
        args = cli.build_parser().parse_args(["--headless"])
        assert cli._handle_lifecycle(args, Settings()) == 0
        assert "4242" in capsys.readouterr().out

    def test_install_dispatch(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "install_logon_task", lambda flags: True)
        args = cli.build_parser().parse_args(["--install"])
        assert cli._handle_lifecycle(args, Settings()) == 0
        assert "Installed" in capsys.readouterr().out

    def test_stop_dispatch(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "stop_headless", lambda: True)
        args = cli.build_parser().parse_args(["--stop"])
        assert cli._handle_lifecycle(args, Settings()) == 0
        assert "Stopped" in capsys.readouterr().out


class TestProfileFromDefaultConfig:
    def test_meeting_profile_from_bundled_config(self):
        # No explicit config_path -> uses python/keepalive.json next to the pkg.
        args = cli.build_parser().parse_args(["--profile", "meeting"])
        settings = cli.cli_to_settings(args)
        assert settings.minutes == 120
        assert settings.system_only is True

    def test_tray_profile_from_bundled_config(self):
        args = cli.build_parser().parse_args(["--profile", "tray"])
        settings = cli.cli_to_settings(args)
        assert settings.tray is True


class TestRunWarnings:
    def test_browser_keep_alive_warns_when_port_closed(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: None)
        monkeypatch.setattr(cli, "browser_debug_port_open", lambda: False)
        args = cli.build_parser().parse_args([])
        code = cli.run(args, Settings(browser_keep_alive=True))
        assert code == 0
        assert "9222" in capsys.readouterr().err

    def test_system_only_sets_mode_suffix(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: captured.update(kw))
        args = cli.build_parser().parse_args([])
        cli.run(args, Settings(system_only=True))
        assert "display may sleep" in captured["mode_suffix"]

    def test_console_fallback_runs(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: captured.update(kw))
        code = cli.run_console_fallback(
            Settings(), "", lambda: None, None, None, None
        )
        assert code == 0
        assert "nudge" in captured


class TestMain:
    def test_main_status(self, capsys):
        code = cli.main(["--status"])
        assert code == 0

    def test_main_invalid_interval(self, capsys):
        code = cli.main(["--interval-seconds", "3"])
        assert code == 1

    def test_main_runs_loop(self, monkeypatch):
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: None)
        assert cli.main([]) == 0


class TestJitterAndMaxIdle:
    def test_parses_jitter_and_max_idle(self):
        args = cli.build_parser().parse_args(["--jitter", "10", "--max-idle", "30"])
        assert args.jitter == 10
        assert args.max_idle == 30

    def test_jitter_defaults_none(self):
        args = cli.build_parser().parse_args([])
        assert args.jitter is None
        assert args.max_idle is None

    def test_run_passes_next_interval_when_jitter_set(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: captured.update(kw))
        args = cli.build_parser().parse_args([])
        cli.run(args, Settings(jitter=10))
        assert captured.get("next_interval") is not None
        # The provider returns an int near the base interval.
        assert isinstance(captured["next_interval"](), int)

    def test_run_no_next_interval_without_jitter(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: captured.update(kw))
        args = cli.build_parser().parse_args([])
        cli.run(args, Settings())
        assert captured.get("next_interval") is None

    def test_max_idle_composes_stop_when(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: captured.update(kw))
        # Force the idle reading above the threshold so stop_when() fires True.
        monkeypatch.setattr(cli, "get_idle_seconds", lambda: 9999.0)
        args = cli.build_parser().parse_args([])
        cli.run(args, Settings(max_idle=1))
        stop_when = captured.get("stop_when")
        assert stop_when is not None
        assert stop_when() is True

    def test_no_stop_when_without_watch_or_idle(self, monkeypatch):
        captured = {}
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: captured.update(kw))
        args = cli.build_parser().parse_args([])
        cli.run(args, Settings())
        assert captured.get("stop_when") is None
