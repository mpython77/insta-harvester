"""Tests for ProfileScraper — both API and DOM strategies."""

from __future__ import annotations

import pytest

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.selectors import ProfileSelectors
from instaharvest._v3.core.exceptions import (
    HtmlStructureChangedError,
    ProfileNotFoundError,
)
from instaharvest._v3.scrapers.profile import ProfileScraper, _parse_count

from .conftest import FakeBrowserSession, FakeHttpClient, FakeHttpResponse, FakeLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scraper(
    *,
    browser: FakeBrowserSession | None = None,
    http: FakeHttpClient | None = None,
) -> ProfileScraper:
    return ProfileScraper(
        browser=browser or FakeBrowserSession(),
        http=http or FakeHttpClient(),
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
        selectors=ProfileSelectors(),
    )


def _api_response(user_data: dict) -> FakeHttpResponse:
    return FakeHttpResponse(
        status_code=200,
        json_data={"data": {"user": user_data}},
    )


# ---------------------------------------------------------------------------
# Pure helper: _parse_count
# ---------------------------------------------------------------------------


class TestParseCount:
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("1234", 1234),
            ("12,345", 12345),
            ("1.2K", 1200),
            ("1.2k", 1200),
            ("3M", 3_000_000),
            ("2B", 2_000_000_000),
            (" 100 ", 100),
            ("", 0),
            ("not a number", 0),
        ],
    )
    def test_parses(self, raw: str, expected: int):
        assert _parse_count(raw) == expected


# ---------------------------------------------------------------------------
# API path
# ---------------------------------------------------------------------------


class TestApiPath:
    def test_happy_returns_api_profile(self):
        http = FakeHttpClient()
        http.responses["https://i.instagram.com/api/v1/users/web_profile_info/"] = (
            _api_response({
                "id": "12345",
                "username": "alice",
                "full_name": "Alice Smith",
                "biography": "hello",
                "is_verified": True,
                "is_private": False,
                "is_business_account": False,
                "is_professional_account": False,
                "edge_followed_by": {"count": 10000},
                "edge_follow": {"count": 200},
                "edge_owner_to_timeline_media": {"count": 50},
                "bio_links": [{"url": "https://example.com/", "title": "Site"}],
                "profile_pic_url_hd": "https://cdn.example.com/pic.jpg",
                "category_name": "Photographer",
            })
        )
        scraper = _make_scraper(http=http)
        profile = scraper.scrape("alice")

        assert profile.username == "alice"
        assert profile.user_id == "12345"
        assert profile.followers == 10000
        assert profile.following == 200
        assert profile.posts == 50
        assert profile.is_verified is True
        assert profile.data_source == "api"
        assert len(profile.bio_links) == 1
        assert str(profile.bio_links[0].url).startswith("https://example.com/")

    def test_404_raises_profile_not_found(self):
        http = FakeHttpClient()
        http.responses["https://i.instagram.com/api/v1/users/web_profile_info/"] = (
            FakeHttpResponse(status_code=404)
        )
        scraper = _make_scraper(http=http)
        with pytest.raises(ProfileNotFoundError) as exc:
            scraper.scrape("ghost")
        assert exc.value.username == "ghost"

    def test_api_failure_falls_back_to_dom(self):
        # API returns 500 → scraper should attempt DOM
        http = FakeHttpClient()
        http.responses["https://i.instagram.com/api/v1/users/web_profile_info/"] = (
            FakeHttpResponse(status_code=500)
        )
        browser = FakeBrowserSession(
            url="https://www.instagram.com/alice/",
            content="<html>ok</html>",
            elements={
                "header section ul li:nth-child(1)": {"text": "42 posts"},
                'a[href$="/followers/"]': {"text": "1,234", "attrs": {"title": "1,234"}},
                'a[href$="/following/"]': {"text": "100"},
            },
        )
        scraper = _make_scraper(http=http, browser=browser)
        profile = scraper.scrape("alice")
        assert profile.data_source == "dom"
        assert profile.followers == 1234

    def test_invalid_username_rejected_before_io(self):
        http = FakeHttpClient()  # no responses programmed
        scraper = _make_scraper(http=http)
        with pytest.raises(ValueError, match="invalid Instagram username"):
            scraper.scrape("not a username!")
        # No HTTP call should have been made.
        assert http.calls == []

    def test_skips_api_when_prefer_api_false(self):
        http = FakeHttpClient()  # would fail if queried
        browser = FakeBrowserSession(
            url="https://www.instagram.com/alice/",
            content="<html>ok</html>",
            elements={
                "header section ul li:nth-child(1)": {"text": "1"},
                'a[href$="/followers/"]': {"text": "1"},
                'a[href$="/following/"]': {"text": "1"},
            },
        )
        scraper = _make_scraper(http=http, browser=browser)
        profile = scraper.scrape("alice", prefer_api=False)
        assert profile.data_source == "dom"
        assert http.calls == []


# ---------------------------------------------------------------------------
# DOM path
# ---------------------------------------------------------------------------


class TestDomPath:
    def _dom_browser(self, **overrides) -> FakeBrowserSession:
        browser = FakeBrowserSession(
            url="https://www.instagram.com/alice/",
            content="<html>profile content</html>",
            elements={
                "header section ul li:nth-child(1)": {"text": "42 posts"},
                'a[href$="/followers/"]': {"text": "1.2K", "attrs": {"title": "1,234"}},
                'a[href$="/following/"]': {"text": "100"},
                'svg[aria-label="Verified"]': {"text": ""},
            },
        )
        for k, v in overrides.items():
            setattr(browser, k, v)
        return browser

    def test_uses_title_attribute_for_precise_count(self):
        browser = self._dom_browser()
        scraper = _make_scraper(http=FakeHttpClient(), browser=browser)
        profile = scraper.scrape("alice", prefer_api=False)
        # ``title`` attr ("1,234") is preferred over inner text ("1.2K")
        assert profile.followers == 1234

    def test_falls_back_to_inner_text(self):
        browser = self._dom_browser()
        # Drop the title attribute
        browser.elements['a[href$="/followers/"]'] = {"text": "999"}
        scraper = _make_scraper(http=FakeHttpClient(), browser=browser)
        profile = scraper.scrape("alice", prefer_api=False)
        assert profile.followers == 999

    def test_missing_count_selector_raises_structure_changed(self):
        browser = self._dom_browser()
        del browser.elements["header section ul li:nth-child(1)"]
        scraper = _make_scraper(http=FakeHttpClient(), browser=browser)
        with pytest.raises(HtmlStructureChangedError) as exc:
            scraper.scrape("alice", prefer_api=False)
        assert exc.value.element == "posts"

    def test_not_found_marker_raises(self):
        browser = self._dom_browser(
            content="<html>Sorry, this page isn't available.</html>"
        )
        scraper = _make_scraper(http=FakeHttpClient(), browser=browser)
        with pytest.raises(ProfileNotFoundError):
            scraper.scrape("alice", prefer_api=False)
