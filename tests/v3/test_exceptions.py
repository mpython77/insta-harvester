"""Tests for v3 exception hierarchy and structured context."""

from __future__ import annotations

import pytest

from instaharvest._v3 import (
    HtmlStructureChangedError,
    InstaHarvestError,
    NetworkError,
    ProfileNotFoundError,
    RateLimitedError,
    SessionExpiredError,
    SessionNotFoundError,
)


class TestHierarchy:
    def test_all_subclass_base(self):
        for cls in [
            NetworkError,
            RateLimitedError,
            ProfileNotFoundError,
            HtmlStructureChangedError,
            SessionExpiredError,
            SessionNotFoundError,
        ]:
            assert issubclass(cls, InstaHarvestError)

    def test_session_subclass(self):
        from instaharvest._v3.core.exceptions import SessionError
        assert issubclass(SessionNotFoundError, SessionError)
        assert issubclass(SessionExpiredError, SessionError)


class TestStructuredContext:
    def test_profile_not_found_carries_username(self):
        exc = ProfileNotFoundError("alice")
        assert exc.username == "alice"
        assert "@alice" in str(exc)

    def test_rate_limited_carries_cooldown(self):
        exc = RateLimitedError("blocked", cooldown_seconds=120.0)
        assert exc.cooldown_seconds == 120.0

    def test_network_error_carries_url(self):
        exc = NetworkError("timeout", url="https://example.com")
        assert exc.url == "https://example.com"

    def test_html_structure_changed_carries_all_context(self):
        exc = HtmlStructureChangedError(
            element="followers",
            selector="a[href$='/followers/']",
            url="https://www.instagram.com/x/",
            snapshot_path="/tmp/snap.html",
        )
        assert exc.element == "followers"
        assert exc.selector == "a[href$='/followers/']"
        assert exc.url == "https://www.instagram.com/x/"
        assert exc.snapshot_path == "/tmp/snap.html"
        assert "followers" in str(exc)
        assert "selector" in str(exc)


class TestSessionNotFound:
    def test_carries_path_in_attribute_and_message(self):
        exc = SessionNotFoundError("/no/such/session.json")
        assert exc.path == "/no/such/session.json"
        assert "/no/such/session.json" in str(exc)


class TestExceptionChaining:
    def test_raise_from_preserves_cause(self):
        # Document the convention: scrapers raise typed exceptions ``from exc``
        # so the original cause is available on ``__cause__``.
        original = ValueError("boom")
        try:
            try:
                raise original
            except ValueError as e:
                raise NetworkError("failed", url="x") from e
        except NetworkError as exc:
            assert exc.__cause__ is original
        else:
            pytest.fail("expected NetworkError to propagate")
