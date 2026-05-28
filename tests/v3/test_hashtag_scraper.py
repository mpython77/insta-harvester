"""Tests for HashtagScraper — lookup, recent / top feeds, validation."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.core.models import FeedSource
from instaharvest._v3.scrapers.hashtag import HashtagNotFoundError, HashtagScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_scraper(http: FakeHttpClient) -> HashtagScraper:
    return HashtagScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
    )


_INFO_URL = "https://www.instagram.com/api/v1/tags/web_info/"
_SECTIONS_URL = "https://www.instagram.com/api/v1/tags/fashionweek/sections/"


def _media_dict(shortcode: str) -> Dict[str, Any]:
    return {
        "code": shortcode,
        "media_type": 1,
        "user": {"pk": 1, "username": "alice"},
        "taken_at": 1_700_000_000,
        "like_count": 10,
        "comment_count": 2,
        "image_versions2": {"candidates": [{"url": "https://cdn.example/x.jpg"}]},
    }


def _section(shortcodes: List[str]) -> Dict[str, Any]:
    return {
        "layout_content": {
            "medias": [{"media": _media_dict(sc)} for sc in shortcodes],
        },
    }


# Reusable valid Instagram-style shortcodes (>=5 chars).
SC_A = "ABC123"
SC_B = "DEF456"
SC_C = "GHI789"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_tag_rejected(self):
        scraper = _make_scraper(FakeHttpClient())
        with pytest.raises(ValueError, match="empty hashtag"):
            scraper.lookup("")

    def test_whitespace_in_tag_rejected(self):
        scraper = _make_scraper(FakeHttpClient())
        with pytest.raises(ValueError, match="whitespace"):
            scraper.lookup("fashion week")

    def test_hash_prefix_stripped(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"data": {"name": "fashionweek", "media_count": 100}},
        )
        scraper = _make_scraper(http)
        h = scraper.lookup("#fashionweek")
        assert h.name == "fashionweek"


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


class TestLookup:
    def test_happy(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"data": {
                "name": "fashionweek",
                "media_count": 1234567,
                "formatted_media_count": "1.2M",
                "allow_following": True,
                "following": False,
            }},
        )
        h = _make_scraper(http).lookup("fashionweek")
        assert h.name == "fashionweek"
        assert h.media_count == 1234567
        assert h.formatted_media_count == "1.2M"
        assert h.allow_following is True
        assert h.is_following is False

    def test_404_raises(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=404)
        with pytest.raises(HashtagNotFoundError) as exc:
            _make_scraper(http).lookup("nope")
        assert exc.value.tag == "nope"

    def test_500_raises_network_error(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=500)
        with pytest.raises(NetworkError):
            _make_scraper(http).lookup("fashion")

    def test_invalid_json_raises_parse_error(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=200, text="bad")
        with pytest.raises(ParseError):
            _make_scraper(http).lookup("fashion")


# ---------------------------------------------------------------------------
# Feed (recent / top)
# ---------------------------------------------------------------------------


class _Pager:
    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self._pages = pages
        self._next = 0

    def __call__(self) -> FakeHttpResponse:
        if self._next >= len(self._pages):
            return FakeHttpResponse(status_code=200, json_data={"sections": []})
        page = self._pages[self._next]
        self._next += 1
        return FakeHttpResponse(status_code=200, json_data=page)


def _install_paginator(
    http: FakeHttpClient,
    url_prefix: str,
    pages: List[Dict[str, Any]],
) -> None:
    pager = _Pager(pages)
    original_post = http.post

    def post(url: str, *, data=None, json=None, headers=None):
        if url.startswith(url_prefix):
            http.calls.append({
                "method": "POST", "url": url,
                "data": dict(data) if data else None,
            })
            return pager()
        return original_post(url, data=data, json=json, headers=headers)

    http.post = post  # type: ignore[assignment]


class TestRecentFeed:
    def test_single_page(self):
        http = FakeHttpClient()
        _install_paginator(http, _SECTIONS_URL, [
            {"sections": [_section([SC_A, SC_B])], "next_max_id": None},
        ])
        feed = _make_scraper(http).recent("fashionweek")
        assert feed.source == FeedSource.HASHTAG_RECENT
        assert feed.source_id == "fashionweek"
        assert feed.total_returned == 2
        assert [m.shortcode for m in feed.media] == [SC_A, SC_B]
        assert feed.has_more is False

    def test_pagination_walks(self):
        http = FakeHttpClient()
        _install_paginator(http, _SECTIONS_URL, [
            {"sections": [_section([SC_A])], "next_max_id": "cursor1"},
            {"sections": [_section([SC_B])], "next_max_id": "cursor2"},
            {"sections": [_section([SC_C])], "next_max_id": None},
        ])
        feed = _make_scraper(http).recent("fashionweek")
        assert [m.shortcode for m in feed.media] == [SC_A, SC_B, SC_C]
        assert feed.next_cursor is None

    def test_max_items_caps_collection(self):
        http = FakeHttpClient()
        codes = [f"AB{i:04d}" for i in range(10)]
        _install_paginator(http, _SECTIONS_URL, [
            {"sections": [_section(codes)], "next_max_id": "k"},
            {"sections": [_section(codes)], "next_max_id": None},
        ])
        feed = _make_scraper(http).recent("fashionweek", max_items=5)
        assert feed.total_returned == 5
        assert feed.has_more is True

    def test_top_feed_uses_top_tab(self):
        http = FakeHttpClient()
        _install_paginator(http, _SECTIONS_URL, [
            {"sections": [_section([SC_A])], "next_max_id": None},
        ])
        feed = _make_scraper(http).top("fashionweek")
        assert feed.source == FeedSource.HASHTAG_TOP
        # Check that the request body specified ``tab=top``.
        assert any(
            c.get("data", {}).get("tab") == "top" for c in http.calls
        )

    def test_mid_walk_5xx_returns_partial(self):
        http = FakeHttpClient()
        responses = [
            FakeHttpResponse(
                status_code=200,
                json_data={"sections": [_section([SC_A])], "next_max_id": "next"},
            ),
            FakeHttpResponse(status_code=503),
        ]
        idx = [0]
        original_post = http.post

        def post(url: str, *, data=None, json=None, headers=None):
            if url.startswith(_SECTIONS_URL):
                http.calls.append({"method": "POST", "url": url})
                resp = responses[idx[0]]
                idx[0] += 1
                return resp
            return original_post(url, data=data, json=json, headers=headers)

        http.post = post  # type: ignore[assignment]

        feed = _make_scraper(http).recent("fashionweek")
        assert feed.total_returned == 1
        assert feed.has_more is True
        assert feed.next_cursor == "next"

    def test_int_cursor_normalised_to_str(self):
        http = FakeHttpClient()
        _install_paginator(http, _SECTIONS_URL, [
            {"sections": [_section([SC_A])], "next_max_id": 12345},
            {"sections": [_section([SC_B])], "next_max_id": None},
        ])
        feed = _make_scraper(http).recent("fashionweek")
        assert feed.next_cursor is None
        # Mid-walk we issued a POST with max_id="12345"
        cursored = [c for c in http.calls if c.get("data", {}).get("max_id")]
        assert cursored and cursored[0]["data"]["max_id"] == "12345"

    def test_negative_max_items_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).recent("fashionweek", max_items=-1)
