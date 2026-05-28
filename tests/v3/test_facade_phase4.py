"""Phase 4 integration tests for the InstaHarvest facade."""

from __future__ import annotations

from instaharvest._v3 import InstaHarvest, Settings
from instaharvest._v3.scrapers.explore import ExploreScraper
from instaharvest._v3.scrapers.hashtag import HashtagScraper
from instaharvest._v3.scrapers.location import LocationScraper
from instaharvest._v3.scrapers.search import SearchScraper

from .conftest import FakeBrowserSession, FakeHttpClient, FakeLogger, FakeSessionStore


def _injected(**overrides) -> InstaHarvest:
    defaults = dict(
        logger=FakeLogger(),
        session_store=FakeSessionStore(),
        http=FakeHttpClient(),
        browser=FakeBrowserSession(),
    )
    defaults.update(overrides)
    return InstaHarvest(Settings.default(), **defaults)


class TestFacadeProperties:
    def test_hashtag_lazy_and_cached(self):
        ih = _injected()
        a = ih.hashtag
        b = ih.hashtag
        assert isinstance(a, HashtagScraper)
        assert a is b

    def test_location_lazy_and_cached(self):
        ih = _injected()
        a = ih.location
        b = ih.location
        assert isinstance(a, LocationScraper)
        assert a is b

    def test_search_lazy_and_cached(self):
        ih = _injected()
        a = ih.search
        b = ih.search
        assert isinstance(a, SearchScraper)
        assert a is b

    def test_explore_lazy_and_cached(self):
        ih = _injected()
        a = ih.explore
        b = ih.explore
        assert isinstance(a, ExploreScraper)
        assert a is b


class TestNoBrowserNeededForApiOnly:
    """All Phase-4 scrapers are API-only. Accessing them should never
    trigger the lazy browser-start path that a profile/media DOM fallback
    would need."""

    def test_hashtag_does_not_start_browser(self):
        browser = FakeBrowserSession()
        ih = _injected(browser=browser)
        # Accessing the property must not call browser.start (we'd see
        # ``visited`` being non-empty in our fake if it did).
        _ = ih.hashtag
        _ = ih.location
        _ = ih.search
        _ = ih.explore
        assert browser.visited == []
