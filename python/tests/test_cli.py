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


class TestEnableClosureAndKeyboardInterrupt:
    def test_enable_closure_calls_stay_awake(self, monkeypatch):
        enable_called = {}

        def fake_loop(**kwargs):
            kwargs["enable"]()

        monkeypatch.setattr(cli, "run_keepalive", fake_loop)
        monkeypatch.setattr(
            cli,
            "enable_stay_awake",
            lambda keep_display_on: enable_called.update({"kdo": keep_display_on}),
        )

        args = cli.build_parser().parse_args([])
        cli.run(args, Settings())

        assert enable_called["kdo"] is True  # not system_only → keep display on

    def test_run_catches_keyboard_interrupt(self, monkeypatch):
        def _raise(**kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(cli, "run_keepalive", _raise)
        args = cli.build_parser().parse_args([])
        code = cli.run(args, Settings())
        assert code == 0

    def test_run_console_fallback_catches_keyboard_interrupt(self, monkeypatch):
        def _raise(**kwargs):
            raise KeyboardInterrupt

        monkeypatch.setattr(cli, "run_keepalive", _raise)
        code = cli.run_console_fallback(Settings(), "", lambda: None, None, None, None)
        assert code == 0


class TestPrintStatusBranches:
    def test_logon_task_installed_shows_installed(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "logon_task_installed", lambda: True)
        monkeypatch.setattr(cli, "read_pid", lambda: None)
        monkeypatch.setattr(cli, "pid_running", lambda pid: False)
        cli._print_status()
        assert "installed" in capsys.readouterr().out

    def test_headless_process_running_shows_pid(self, monkeypatch, capsys):
        monkeypatch.setattr(cli, "logon_task_installed", lambda: False)
        monkeypatch.setattr(cli, "read_pid", lambda: 9999)
        monkeypatch.setattr(cli, "pid_running", lambda pid: True)
        cli._print_status()
        assert "9999" in capsys.readouterr().out


class TestMainBadProfile:
    def test_bad_profile_returns_1(self, monkeypatch, tmp_path):
        config = tmp_path / "keepalive.json"
        config.write_text('{"profiles": {}}', encoding="utf-8")
        monkeypatch.setattr(cli, "_default_config_path", lambda: str(config))
        code = cli.main(["--profile", "ghost"])
        assert code == 1

    def test_main_reraises_non_string_systemexit(self, monkeypatch):
        monkeypatch.setattr(
            cli,
            "cli_to_settings",
            lambda a: (_ for _ in ()).throw(SystemExit(2)),
        )
        with pytest.raises(SystemExit) as exc_info:
            cli.main([])
        assert exc_info.value.code == 2


class TestRunWithTrayAvailable:
    def test_routes_through_tray_controller(self, monkeypatch):
        import keepalive.tray as tray_mod

        loop_captured = {}

        class FakeController:
            def __init__(self, **kwargs):
                pass

            def should_stop(self):
                return True

            def paused(self):
                return False

            def on_status(self, *a):
                pass

            def run(self, loop):
                loop_captured["ran"] = True
                loop()

        monkeypatch.setattr(tray_mod, "tray_available", lambda: True)
        monkeypatch.setattr(tray_mod, "TrayController", FakeController)
        monkeypatch.setattr(cli, "run_keepalive", lambda **kw: None)

        code = cli.run(cli.build_parser().parse_args(["--tray"]), Settings(tray=True))
        assert code == 0
        assert loop_captured.get("ran") is True

    def test_gated_nudge_passes_none_through(self, monkeypatch):
        import keepalive.tray as tray_mod

        nudges_captured = {}

        class FakeController:
            def __init__(self, **kwargs):
                pass

            def should_stop(self):
                return True

            def paused(self):
                return False

            def on_status(self, *a):
                pass

            def run(self, loop):
                loop()

        def fake_run_keepalive(**kwargs):
            nudges_captured["app_nudge"] = kwargs.get("app_nudge")
            nudges_captured["browser_nudge"] = kwargs.get("browser_nudge")

        monkeypatch.setattr(tray_mod, "tray_available", lambda: True)
        monkeypatch.setattr(tray_mod, "TrayController", FakeController)
        monkeypatch.setattr(cli, "run_keepalive", fake_run_keepalive)

        # No app/browser nudge → gated_nudge(None) returns None
        cli.run(cli.build_parser().parse_args(["--tray"]), Settings(tray=True))
        assert nudges_captured["app_nudge"] is None
        assert nudges_captured["browser_nudge"] is None

    def test_gated_nudge_skips_while_paused(self, monkeypatch):
        import keepalive.tray as tray_mod

        called = []

        class FakeController:
            def __init__(self, **kwargs):
                pass

            def should_stop(self):
                return True

            def paused(self):
                return True  # paused → gated nudge should skip

            def on_status(self, *a):
                pass

            def run(self, loop):
                loop()

        def fake_run_keepalive(**kwargs):
            if kwargs.get("nudge"):
                kwargs["nudge"]()  # invoke the gated nudge

        monkeypatch.setattr(tray_mod, "tray_available", lambda: True)
        monkeypatch.setattr(tray_mod, "TrayController", FakeController)
        monkeypatch.setattr(cli, "run_keepalive", fake_run_keepalive)
        monkeypatch.setattr(cli, "send_idle_nudge", lambda: called.append(1))

        cli.run(cli.build_parser().parse_args(["--tray"]), Settings(tray=True))
        assert called == []  # nudge skipped because paused

    def test_gated_nudge_fires_when_not_paused(self, monkeypatch):
        import keepalive.tray as tray_mod

        called = []

        class FakeController:
            def __init__(self, **kwargs):
                pass

            def should_stop(self):
                return True

            def paused(self):
                return False  # running → gated nudge should fire

            def on_status(self, *a):
                pass

            def run(self, loop):
                loop()

        def fake_run_keepalive(**kwargs):
            if kwargs.get("nudge"):
                kwargs["nudge"]()

        monkeypatch.setattr(tray_mod, "tray_available", lambda: True)
        monkeypatch.setattr(tray_mod, "TrayController", FakeController)
        monkeypatch.setattr(cli, "run_keepalive", fake_run_keepalive)
        monkeypatch.setattr(cli, "send_idle_nudge", lambda: called.append(1))

        cli.run(cli.build_parser().parse_args(["--tray"]), Settings(tray=True))
        assert called == [1]  # nudge fired because not paused

    def test_combined_stop_fires_from_outer_stop_when(self, monkeypatch):
        import keepalive.tray as tray_mod

        combined_stop_result = {}

        class FakeController:
            def __init__(self, **kwargs):
                pass

            def should_stop(self):
                return False  # controller itself not stopping

            def paused(self):
                return False

            def on_status(self, *a):
                pass

            def run(self, loop):
                loop()

        def fake_run_keepalive(**kwargs):
            # Invoke combined_stop (line 252) via stop_when
            result = kwargs["stop_when"]()
            combined_stop_result["fired"] = result

        monkeypatch.setattr(tray_mod, "tray_available", lambda: True)
        monkeypatch.setattr(tray_mod, "TrayController", FakeController)
        monkeypatch.setattr(cli, "run_keepalive", fake_run_keepalive)

        # Pass an outer stop_when that returns True so combined_stop returns True
        args = cli.build_parser().parse_args(["--tray"])
        settings = Settings(tray=True, max_idle=1)
        monkeypatch.setattr(cli, "get_idle_seconds", lambda: 9999.0)

        cli.run(args, settings)
        assert combined_stop_result["fired"] is True


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
