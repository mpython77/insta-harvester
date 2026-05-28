"""Tests for the InstaHarvest facade — composition root behaviour."""

from __future__ import annotations

from instaharvest import InstaHarvest, Settings
from instaharvest.scrapers.profile import ProfileScraper

from .conftest import FakeBrowserSession, FakeHttpClient, FakeLogger, FakeSessionStore


def _injected(**overrides) -> InstaHarvest:
    """Build an InstaHarvest with all four infra deps faked."""
    defaults = dict(
        logger=FakeLogger(),
        session_store=FakeSessionStore(),
        http=FakeHttpClient(),
        browser=FakeBrowserSession(),
    )
    defaults.update(overrides)
    return InstaHarvest(Settings.default(), **defaults)


class TestComposition:
    def test_lazy_profile_scraper_is_cached(self):
        ih = _injected()
        scraper1 = ih.profile
        scraper2 = ih.profile
        assert isinstance(scraper1, ProfileScraper)
        assert scraper1 is scraper2

    def test_browser_property_returns_injected_browser(self):
        browser = FakeBrowserSession()
        ih = _injected(browser=browser)
        assert ih.browser is browser

    def test_settings_exposed(self):
        s = Settings.default()
        ih = InstaHarvest(
            s,
            logger=FakeLogger(),
            session_store=FakeSessionStore(),
            http=FakeHttpClient(),
            browser=FakeBrowserSession(),
        )
        assert ih.settings is s


class TestLifecycle:
    def test_close_closes_http_and_browser(self):
        http = FakeHttpClient()
        browser = FakeBrowserSession()
        ih = _injected(http=http, browser=browser)
        ih.close()
        assert http.closed is True
        assert browser.closed is True

    def test_close_is_idempotent(self):
        http = FakeHttpClient()
        browser = FakeBrowserSession()
        ih = _injected(http=http, browser=browser)
        ih.close()
        ih.close()  # second call must not error
        assert http.closed is True

    def test_close_swallows_component_failures_with_warning(self):
        logger = FakeLogger()
        http = FakeHttpClient()
        browser = FakeBrowserSession()

        def boom() -> None:
            raise RuntimeError("close failed")

        http.close = boom  # type: ignore[assignment]

        ih = _injected(logger=logger, http=http, browser=browser)
        ih.close()  # must not propagate

        # The failure was logged, not silently swallowed.
        warnings = [(msg, ctx) for lvl, msg, ctx in logger.records if lvl == "warning"]
        assert any("close error" in msg for msg, _ in warnings)

    def test_context_manager_calls_close(self):
        http = FakeHttpClient()
        with _injected(http=http) as ih:
            assert isinstance(ih, InstaHarvest)
        assert http.closed is True
