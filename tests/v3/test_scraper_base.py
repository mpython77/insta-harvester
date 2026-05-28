"""Tests for AbstractScraper.navigate — pacing, login, rate-limit handling."""

from __future__ import annotations

import time

import pytest

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.selectors import ProfileSelectors
from instaharvest._v3.core.exceptions import (
    NetworkError,
    RateLimitedError,
    SessionExpiredError,
)
from instaharvest._v3.scrapers.base import AbstractScraper, NavigationOutcome

from .conftest import FakeBrowserSession, FakeLogger


class _Concrete(AbstractScraper):
    """Minimal concrete subclass — the base is abstract by intent only."""


def _make_scraper(
    *,
    browser: FakeBrowserSession,
    rate_limit: RateLimitConfig | None = None,
) -> _Concrete:
    rate_limit = rate_limit or RateLimitConfig(
        request_delay_min=0.0,
        request_delay_max=0.0,
        cooldown_seconds=0.0,
        cooldown_max_retries=2,
    )
    return _Concrete(
        browser=browser,
        logger=FakeLogger(),
        rate_limit=rate_limit,
        selectors=ProfileSelectors(),
    )


class TestNavigateHappyPath:
    def test_returns_ok_outcome(self):
        browser = FakeBrowserSession(
            url="https://www.instagram.com/alice/",
            content="<html>profile</html>",
        )
        scraper = _make_scraper(browser=browser)
        result = scraper.navigate("https://www.instagram.com/alice/")
        assert result.outcome == NavigationOutcome.OK
        assert result.url == "https://www.instagram.com/alice/"
        assert browser.visited == ["https://www.instagram.com/alice/"]


class TestRateLimitDetection:
    def test_url_indicator_triggers_cooldown(self):
        browser = FakeBrowserSession(content="")
        # First two navigations land on action_blocked, third succeeds
        browser.goto_sequence = [
            {"url": "https://www.instagram.com/challenge/action_blocked/", "content": ""},
            {"url": "https://www.instagram.com/challenge/action_blocked/", "content": ""},
            {"url": "https://www.instagram.com/alice/", "content": "<html>ok</html>"},
        ]
        scraper = _make_scraper(browser=browser)
        result = scraper.navigate("https://www.instagram.com/alice/")
        assert result.outcome == NavigationOutcome.OK
        assert len(browser.visited) == 3

    def test_content_indicator_triggers_cooldown(self):
        browser = FakeBrowserSession()
        browser.goto_sequence = [
            {"url": "https://www.instagram.com/alice/", "content": "Try Again Later"},
            {"url": "https://www.instagram.com/alice/", "content": "<html>ok</html>"},
        ]
        scraper = _make_scraper(browser=browser)
        result = scraper.navigate("https://www.instagram.com/alice/")
        assert result.outcome == NavigationOutcome.OK

    def test_exhausted_retries_raises(self):
        browser = FakeBrowserSession()
        # Always rate-limited
        browser.goto_sequence = [
            {"url": "https://www.instagram.com/challenge/", "content": ""},
        ] * 10
        scraper = _make_scraper(
            browser=browser,
            rate_limit=RateLimitConfig(
                request_delay_min=0.0,
                request_delay_max=0.0,
                cooldown_seconds=0.0,
                cooldown_max_retries=1,
            ),
        )
        with pytest.raises(RateLimitedError) as exc_info:
            scraper.navigate("https://www.instagram.com/alice/")
        assert exc_info.value.cooldown_seconds == 0.0


class TestLoginDetection:
    def test_login_url_raises_session_expired(self):
        # Simulate Instagram redirecting our request to the login page.
        browser = FakeBrowserSession()
        browser.goto_sequence = [
            {"url": "https://www.instagram.com/accounts/login/", "content": ""},
        ]
        scraper = _make_scraper(browser=browser)
        with pytest.raises(SessionExpiredError):
            scraper.navigate("https://www.instagram.com/alice/")

    def test_password_field_in_content_raises(self):
        browser = FakeBrowserSession()
        browser.goto_sequence = [
            {
                "url": "https://www.instagram.com/alice/",
                "content": '<form><input type="password"></form>',
            },
        ]
        scraper = _make_scraper(browser=browser)
        with pytest.raises(SessionExpiredError):
            scraper.navigate("https://www.instagram.com/alice/")


class TestTransportError:
    def test_browser_failure_wrapped_in_network_error(self):
        browser = FakeBrowserSession(raise_on_goto=RuntimeError("boom"))
        scraper = _make_scraper(browser=browser)
        with pytest.raises(NetworkError) as exc_info:
            scraper.navigate("https://www.instagram.com/alice/")
        assert exc_info.value.url == "https://www.instagram.com/alice/"
        assert isinstance(exc_info.value.__cause__, RuntimeError)


class TestPacing:
    def test_jitter_delays_subsequent_requests(self, monkeypatch):
        """If request_delay_min > 0, the second navigate must wait."""
        sleeps: list[float] = []
        monkeypatch.setattr("instaharvest._v3.scrapers.base.time.sleep", sleeps.append)
        # Force ``random.uniform`` to return its lower bound for determinism.
        monkeypatch.setattr(
            "instaharvest._v3.scrapers.base.random.uniform",
            lambda lo, hi: lo,
        )

        browser = FakeBrowserSession(
            url="https://www.instagram.com/alice/",
            content="<html>ok</html>",
        )
        scraper = _make_scraper(
            browser=browser,
            rate_limit=RateLimitConfig(
                request_delay_min=0.5,
                request_delay_max=0.5,
                cooldown_seconds=0.0,
                cooldown_max_retries=0,
            ),
        )

        # First call: no prior request → minimal/no sleep
        scraper.navigate("https://www.instagram.com/alice/")
        # Second call: we expect _respect_pacing to call time.sleep
        scraper.navigate("https://www.instagram.com/alice/")

        # At least one sleep was issued and it was at most the configured delay.
        assert any(s > 0 for s in sleeps), f"expected pacing delay, got sleeps={sleeps}"
        assert all(s <= 0.5 + 1e-6 for s in sleeps)
