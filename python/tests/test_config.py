"""Tests for keepalive.config — profile loading and paths."""

import json

from keepalive import config


class TestStartupTaskName:
    def test_stable_name(self):
        assert config.startup_task_name() == "KeepAlive"


class TestPidFilePath:
    def test_ends_with_pid(self):
        assert config.pid_file_path().endswith("keepalive.pid")


class TestReadProfileConfig:
    def test_none_when_missing(self, tmp_path):
        assert config.read_profile_config(str(tmp_path / "nope.json")) is None

    def test_none_for_malformed_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("NOT JSON", encoding="utf-8")
        assert config.read_profile_config(str(bad)) is None

    def test_none_for_empty_path(self):
        assert config.read_profile_config("") is None

    def test_parses_valid_config(self, tmp_path):
        good = tmp_path / "keepalive.json"
        good.write_text(json.dumps({"profiles": {"meeting": {"Minutes": 120}}}), encoding="utf-8")
        profiles = config.read_profile_config(str(good))
        assert profiles is not None
        assert profiles["meeting"]["Minutes"] == 120

    def test_none_when_profiles_key_missing(self, tmp_path):
        f = tmp_path / "keepalive.json"
        f.write_text(json.dumps({"other": {}}), encoding="utf-8")
        assert config.read_profile_config(str(f)) is None

    def test_none_when_top_level_not_object(self, tmp_path):
        f = tmp_path / "keepalive.json"
        f.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        assert config.read_profile_config(str(f)) is None


class TestProfileSettings:
    profiles = {"meeting": {"Minutes": 120}, "focus": {"Quiet": True}}

    def test_returns_known_profile(self):
        assert config.profile_settings(self.profiles, "meeting")["Minutes"] == 120

    def test_none_for_unknown(self):
        assert config.profile_settings(self.profiles, "unknown") is None

    def test_none_when_profiles_none(self):
        assert config.profile_settings(None, "meeting") is None

    def test_none_for_empty_name(self):
        assert config.profile_settings(self.profiles, "") is None
