"""Tests for Phase 5 facade integration (stories, highlights, notifications, evasion)."""

from __future__ import annotations

from instaharvest._v3 import InstaHarvest, Settings
from instaharvest._v3.evasion.facade import EvasionManager
from instaharvest._v3.scrapers.highlights import HighlightScraper
from instaharvest._v3.scrapers.notifications import NotificationsScraper
from instaharvest._v3.scrapers.stories import StoryScraper

from .conftest import FakeBrowserSession, FakeHttpClient, FakeLogger, FakeSessionStore


def _make_ih() -> InstaHarvest:
    return InstaHarvest(
        Settings.default(),
        logger=FakeLogger(),
        session_store=FakeSessionStore(data={"cookies": []}),
        http=FakeHttpClient(),
        browser=FakeBrowserSession(),
    )


class TestFacadePhase5:
    def test_stories_property_returns_scraper(self):
        ih = _make_ih()
        assert isinstance(ih.stories, StoryScraper)

    def test_highlights_property_returns_scraper(self):
        ih = _make_ih()
        assert isinstance(ih.highlights, HighlightScraper)

    def test_notifications_property_returns_scraper(self):
        ih = _make_ih()
        assert isinstance(ih.notifications, NotificationsScraper)

    def test_evasion_property_returns_manager(self):
        ih = _make_ih()
        assert isinstance(ih.evasion, EvasionManager)

    def test_stories_property_cached(self):
        ih = _make_ih()
        assert ih.stories is ih.stories

    def test_highlights_property_cached(self):
        ih = _make_ih()
        assert ih.highlights is ih.highlights

    def test_notifications_property_cached(self):
        ih = _make_ih()
        assert ih.notifications is ih.notifications

    def test_evasion_property_cached(self):
        ih = _make_ih()
        assert ih.evasion is ih.evasion
