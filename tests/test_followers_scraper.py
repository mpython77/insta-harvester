"""Tests for FollowersScraper — pagination, partial results, friendship status."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.core.exceptions import NetworkError, ParseError
from instaharvest.scrapers.followers import FollowersScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scraper(http: FakeHttpClient) -> FollowersScraper:
    return FollowersScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
    )


_FOLLOWERS_URL = "https://i.instagram.com/api/v1/friendships/123/followers/"
_FOLLOWING_URL = "https://i.instagram.com/api/v1/friendships/123/following/"
_FRIENDSHIP_URL = "https://i.instagram.com/api/v1/friendships/show/123/"


def _user(pk: int, username: str | None = None) -> Dict[str, Any]:
    return {
        "pk": pk,
        "username": username or f"user{pk}",
        "full_name": "",
        "is_verified": False,
        "is_private": False,
    }


class _Paginator:
    """Returns one configured response per call to a URL prefix."""

    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self._pages = pages
        self._next = 0

    def __call__(self) -> FakeHttpResponse:
        if self._next >= len(self._pages):
            return FakeHttpResponse(status_code=200, json_data={"users": []})
        page = self._pages[self._next]
        self._next += 1
        return FakeHttpResponse(status_code=200, json_data=page)


def _install_paginator(
    http: FakeHttpClient,
    url_prefix: str,
    pages: List[Dict[str, Any]],
) -> None:
    paginator = _Paginator(pages)
    original_get = http.get

    def get(url: str, *, params=None, headers=None):
        if url.startswith(url_prefix):
            http.calls.append({"method": "GET", "url": url, "params": dict(params) if params else None})
            return paginator()
        return original_get(url, params=params, headers=headers)

    http.get = get  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# list_followers / list_following
# ---------------------------------------------------------------------------


class TestListFollowers:
    def test_single_page(self):
        http = FakeHttpClient()
        _install_paginator(http, _FOLLOWERS_URL, [
            {"users": [_user(1), _user(2)], "next_max_id": None},
        ])

        result = _make_scraper(http).list_followers("123")
        assert result.kind == "followers"
        assert result.target_user_id == "123"
        assert result.total_returned == 2
        assert [u.username for u in result.users] == ["user1", "user2"]
        assert result.has_more is False

    def test_pagination_walks_until_cursor_none(self):
        http = FakeHttpClient()
        _install_paginator(http, _FOLLOWERS_URL, [
            {"users": [_user(1), _user(2)], "next_max_id": "cursor1"},
            {"users": [_user(3)], "next_max_id": "cursor2"},
            {"users": [_user(4)], "next_max_id": None},
        ])

        result = _make_scraper(http).list_followers("123")
        assert [u.username for u in result.users] == [
            "user1", "user2", "user3", "user4",
        ]
        assert result.has_more is False

    def test_max_users_caps_collection(self):
        http = FakeHttpClient()
        _install_paginator(http, _FOLLOWERS_URL, [
            {"users": [_user(i) for i in range(50)], "next_max_id": "k"},
            {"users": [_user(i) for i in range(50, 100)], "next_max_id": None},
        ])

        result = _make_scraper(http).list_followers("123", max_users=30)
        assert result.total_returned == 30
        assert result.has_more is True

    def test_int_cursor_normalised_to_string(self):
        # Instagram has been known to return next_max_id as either str
        # or int. Both must end up as a string ``next_cursor``.
        http = FakeHttpClient()
        _install_paginator(http, _FOLLOWERS_URL, [
            {"users": [_user(1)], "next_max_id": 12345},
            {"users": [_user(2)], "next_max_id": None},
        ])

        result = _make_scraper(http).list_followers("123")
        assert isinstance(result.next_cursor, type(None))  # finished
        # Mid-walk we issued a request; check params
        max_id_calls = [c for c in http.calls if c.get("params", {}) and "max_id" in c["params"]]
        assert max_id_calls and max_id_calls[0]["params"]["max_id"] == "12345"

    def test_negative_max_users_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).list_followers("123", max_users=-1)

    def test_zero_page_size_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).list_followers("123", page_size=0)


class TestListFollowing:
    def test_returns_following_kind(self):
        http = FakeHttpClient()
        _install_paginator(http, _FOLLOWING_URL, [
            {"users": [_user(1)], "next_max_id": None},
        ])
        result = _make_scraper(http).list_following("123")
        assert result.kind == "following"
        assert result.total_returned == 1


class TestPartialResults:
    def test_mid_walk_5xx_returns_partial(self):
        """Mirrors CommentScraper's behaviour: a mid-walk 5xx surfaces what
        we have so far with has_more=True, NOT an exception."""
        http = FakeHttpClient()

        responses = [
            FakeHttpResponse(
                status_code=200,
                json_data={"users": [_user(1), _user(2)], "next_max_id": "next"},
            ),
            FakeHttpResponse(status_code=503),
        ]
        idx = [0]
        original_get = http.get

        def get(url: str, *, params=None, headers=None):
            if url.startswith(_FOLLOWERS_URL):
                http.calls.append({"method": "GET", "url": url, "params": params})
                resp = responses[idx[0]]
                idx[0] += 1
                return resp
            return original_get(url, params=params, headers=headers)

        http.get = get  # type: ignore[assignment]

        result = _make_scraper(http).list_followers("123")
        assert result.total_returned == 2
        assert result.has_more is True
        assert result.next_cursor == "next"


# ---------------------------------------------------------------------------
# friendship_status
# ---------------------------------------------------------------------------


class TestFriendshipStatus:
    def test_happy(self):
        http = FakeHttpClient()
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"following": True, "followed_by": False, "blocking": False},
        )
        status = _make_scraper(http).friendship_status("123")
        assert status.user_id == "123"
        assert status.is_following is True
        assert status.is_followed_by is False

    def test_500_raises_network_error(self):
        http = FakeHttpClient()
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(status_code=500)
        with pytest.raises(NetworkError):
            _make_scraper(http).friendship_status("123")

    def test_invalid_json_raises_parse_error(self):
        http = FakeHttpClient()
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, text="not json",
        )
        with pytest.raises(ParseError):
            _make_scraper(http).friendship_status("123")

    def test_missing_fields_default_to_false(self):
        http = FakeHttpClient()
        http.responses[_FRIENDSHIP_URL] = FakeHttpResponse(
            status_code=200, json_data={},
        )
        status = _make_scraper(http).friendship_status("123")
        assert status.is_following is False
        assert status.is_followed_by is False
