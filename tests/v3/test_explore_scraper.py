"""Tests for ExploreScraper."""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.models import FeedSource
from instaharvest._v3.scrapers.explore import ExploreScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


def _make_scraper(http: FakeHttpClient) -> ExploreScraper:
    return ExploreScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
    )


_EXPLORE_URL = "https://www.instagram.com/api/v1/discover/web/explore_grid/"


def _media_dict(shortcode: str) -> Dict[str, Any]:
    return {
        "code": shortcode,
        "media_type": 1,
        "user": {"pk": 1, "username": "alice"},
        "taken_at": 1_700_000_000,
        "like_count": 1,
        "comment_count": 0,
        "image_versions2": {"candidates": [{"url": "https://cdn.example/x.jpg"}]},
    }


class _Pager:
    def __init__(self, pages: List[Dict[str, Any]]) -> None:
        self._pages = pages
        self._next = 0

    def __call__(self):
        if self._next >= len(self._pages):
            return FakeHttpResponse(status_code=200, json_data={"sectional_items": []})
        page = self._pages[self._next]
        self._next += 1
        return FakeHttpResponse(status_code=200, json_data=page)


def _install_pager(http: FakeHttpClient, pages):
    pager = _Pager(pages)
    original_get = http.get

    def get(url: str, *, params=None, headers=None):
        if url.startswith(_EXPLORE_URL):
            http.calls.append({
                "method": "GET", "url": url,
                "params": dict(params) if params else None,
            })
            return pager()
        return original_get(url, params=params, headers=headers)

    http.get = get  # type: ignore[assignment]


class TestExploreFeed:
    def test_single_page(self):
        http = FakeHttpClient()
        _install_pager(http, [
            {"sectional_items": [
                {"media": _media_dict("ABCXY1")},
                {"media": _media_dict("ABCXY2")},
            ], "next_max_id": None},
        ])
        feed = _make_scraper(http).feed()
        assert feed.source == FeedSource.EXPLORE
        assert feed.source_id == "explore"
        assert [m.shortcode for m in feed.media] == ["ABCXY1", "ABCXY2"]

    def test_pagination(self):
        http = FakeHttpClient()
        _install_pager(http, [
            {"sectional_items": [{"media": _media_dict("ABCXY1")}], "next_max_id": "k1"},
            {"sectional_items": [{"media": _media_dict("ABCXY2")}], "next_max_id": None},
        ])
        feed = _make_scraper(http).feed()
        assert [m.shortcode for m in feed.media] == ["ABCXY1", "ABCXY2"]
        assert feed.has_more is False

    def test_max_items_default_caps_collection(self):
        # Default max_items=50 — explore is bottomless, so the
        # default cap is non-None to prevent runaway calls.
        http = FakeHttpClient()
        _install_pager(http, [
            {"sectional_items": [{"media": _media_dict(f"AB{i:04d}")} for i in range(40)],
             "next_max_id": "k1"},
            {"sectional_items": [{"media": _media_dict(f"CD{i:04d}")} for i in range(40)],
             "next_max_id": "k2"},
            {"sectional_items": [{"media": _media_dict(f"EF{i:04d}")} for i in range(40)],
             "next_max_id": None},
        ])
        feed = _make_scraper(http).feed()
        assert feed.total_returned == 50
        assert feed.has_more is True

    def test_explicit_none_max_items_walks_until_done(self):
        http = FakeHttpClient()
        _install_pager(http, [
            {"sectional_items": [{"media": _media_dict("ABCXY1")}], "next_max_id": "k"},
            {"sectional_items": [{"media": _media_dict("ABCXY2")}], "next_max_id": None},
        ])
        feed = _make_scraper(http).feed(max_items=None)
        assert feed.total_returned == 2
        assert feed.has_more is False

    def test_empty_response(self):
        http = FakeHttpClient()
        _install_pager(http, [
            {"sectional_items": [], "next_max_id": None},
        ])
        feed = _make_scraper(http).feed()
        assert feed.total_returned == 0
        assert feed.media == ()
