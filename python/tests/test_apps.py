"""Tests for keepalive.apps — Microsoft app process matching."""

from keepalive import apps


class TestMicrosoftAppProcessNames:
    def test_non_empty(self):
        assert len(apps.microsoft_app_process_names()) > 0

    def test_includes_core_apps(self):
        names = apps.microsoft_app_process_names()
        assert "outlook" in names
        assert "teams" in names
        assert "excel" in names

    def test_returns_a_copy(self):
        names = apps.microsoft_app_process_names()
        names.append("tampered")
        assert "tampered" not in apps.microsoft_app_process_names()


class TestIsMicrosoftApp:
    def test_matches_regardless_of_case(self):
        assert apps.is_microsoft_app("OUTLOOK") is True

    def test_tolerates_exe_suffix(self):
        assert apps.is_microsoft_app("WINWORD.EXE") is True

    def test_matches_new_teams_client(self):
        assert apps.is_microsoft_app("ms-teams") is True

    def test_rejects_non_microsoft(self):
        assert apps.is_microsoft_app("notepad") is False

    def test_rejects_whitespace(self):
        assert apps.is_microsoft_app("   ") is False

    def test_rejects_none(self):
        assert apps.is_microsoft_app(None) is False
