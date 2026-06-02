"""Tests for keepalive.browser — M365 URL classification."""

from keepalive import browser


class TestIsM365Url:
    def test_matches_outlook(self):
        assert browser.is_m365_url("https://outlook.office365.com/mail/") is True

    def test_matches_teams(self):
        assert browser.is_m365_url("https://teams.microsoft.com/v2/") is True

    def test_matches_sharepoint(self):
        assert browser.is_m365_url("https://contoso.sharepoint.com/sites/hr") is True

    def test_matches_office(self):
        assert browser.is_m365_url("https://www.office.com") is True

    def test_rejects_non_m365(self):
        assert browser.is_m365_url("https://google.com") is False

    def test_rejects_empty(self):
        assert browser.is_m365_url("") is False

    def test_case_insensitive(self):
        assert browser.is_m365_url("https://OUTLOOK.OFFICE365.com") is True


class TestSelectM365Tabs:
    def test_filters_mixed_list(self):
        tabs = [
            {"url": "https://outlook.office365.com/mail/"},
            {"url": "https://google.com"},
            {"url": "https://contoso.sharepoint.com/sites/hr"},
        ]
        assert len(browser.select_m365_tabs(tabs)) == 2

    def test_none_input(self):
        assert browser.select_m365_tabs(None) == []

    def test_no_matches(self):
        assert browser.select_m365_tabs([{"url": "https://github.com"}]) == []

    def test_missing_url_key(self):
        assert browser.select_m365_tabs([{"title": "x"}]) == []


def test_patterns_exposed():
    assert "outlook\\.office" in browser.m365_url_patterns()
