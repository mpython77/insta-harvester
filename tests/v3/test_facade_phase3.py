"""Phase 3 integration tests for the InstaHarvest facade."""

from __future__ import annotations

from instaharvest._v3 import InstaHarvest, Settings
from instaharvest._v3.actions import Actions
from instaharvest._v3.scrapers.followers import FollowersScraper

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


class TestFollowersFacadeProperty:
    def test_lazy_followers_is_cached(self):
        ih = _injected()
        a = ih.followers
        b = ih.followers
        assert isinstance(a, FollowersScraper)
        assert a is b

    def test_followers_does_not_require_actions_enabled(self):
        # Read-only scraping must work regardless of the actions config.
        ih = _injected()
        assert ih.settings.actions.enabled is False
        # Just access — no exception means the gating didn't leak.
        scraper = ih.followers
        assert scraper is not None


class TestActionsFacadeProperty:
    def test_lazy_actions_is_cached(self):
        ih = _injected()
        a = ih.actions
        b = ih.actions
        assert isinstance(a, Actions)
        assert a is b

    def test_actions_namespace_accessible_when_disabled(self):
        # Accessing the namespace itself never raises — only calling
        # methods on it raises (with a clear message).
        ih = _injected()
        actions = ih.actions
        assert actions.enabled is False
        assert actions.dry_run is True
        # Sub-namespaces also accessible
        assert actions.social is not None
        assert actions.messaging is not None

    def test_actions_shares_followers_for_pre_checks(self):
        # SocialActions uses FollowersScraper for friendship_status
        # pre-checks. Verify the facade wires the *same* instance, so
        # caching the user-id-to-friendship lookup actually works.
        ih = _injected()
        # Touch followers first so it's cached.
        scraper = ih.followers
        # Now touch actions; the underlying SocialActions should
        # have been built with the same scraper object.
        social = ih.actions.social
        assert social._followers is scraper  # private but stable
