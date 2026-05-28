"""Tests for SearchScraper — topsearch API."""

from __future__ import annotations

import pytest

from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.scrapers.search import SearchScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


def _make_scraper(http: FakeHttpClient) -> SearchScraper:
    return SearchScraper(http=http, logger=FakeLogger())


_TOPSEARCH_URL = "https://www.instagram.com/api/v1/fbsearch/topsearch_flat/"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_query_rejected_before_io(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError, match="empty"):
            _make_scraper(http).search("")
        assert http.calls == []

    def test_whitespace_only_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError, match="empty"):
            _make_scraper(http).search("   ")

    def test_too_long_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError, match="too long"):
            _make_scraper(http).search("x" * 101)


# ---------------------------------------------------------------------------
# Flat-list response
# ---------------------------------------------------------------------------


class TestFlatList:
    def test_users_hashtags_places(self):
        http = FakeHttpClient()
        http.responses[_TOPSEARCH_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"list": [
                {"user": {
                    "pk": 1, "username": "alice", "full_name": "Alice",
                    "is_verified": True, "follower_count": 1000,
                }},
                {"hashtag": {
                    "name": "fashionweek", "media_count": 1234567,
                    "formatted_media_count": "1.2M",
                }},
                {"place": {"location": {
                    "pk": 42, "name": "Tashkent",
                }}},
            ]},
        )

        result = _make_scraper(http).search("fashion")
        assert result.query == "fashion"
        assert len(result.users) == 1
        assert result.users[0].username == "alice"
        assert result.users[0].is_verified is True
        assert len(result.hashtags) == 1
        assert result.hashtags[0].media_count == 1234567
        assert len(result.places) == 1
        assert result.places[0].name == "Tashkent"

    def test_dedupes_within_each_category(self):
        http = FakeHttpClient()
        http.responses[_TOPSEARCH_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"list": [
                {"user": {"pk": 1, "username": "alice"}},
                {"user": {"pk": 2, "username": "alice"}},  # duplicate username
            ]},
        )
        result = _make_scraper(http).search("alice")
        assert len(result.users) == 1


# ---------------------------------------------------------------------------
# Legacy category-keyed response
# ---------------------------------------------------------------------------


class TestCategoryKeyed:
    def test_users_under_users_key(self):
        http = FakeHttpClient()
        http.responses[_TOPSEARCH_URL] = FakeHttpResponse(
            status_code=200,
            json_data={
                "users": [
                    {"user": {"pk": 1, "username": "alice"}},
                ],
                "hashtags": [
                    {"hashtag": {"name": "fashion", "media_count": 100}},
                ],
                "places": [
                    {"place": {"location": {"pk": 1, "name": "Tashkent"}}},
                ],
            },
        )
        result = _make_scraper(http).search("fashion")
        assert len(result.users) == 1
        assert len(result.hashtags) == 1
        assert len(result.places) == 1


# ---------------------------------------------------------------------------
# Error mapping
# ---------------------------------------------------------------------------


class TestErrors:
    def test_5xx_raises_network_error(self):
        http = FakeHttpClient()
        http.responses[_TOPSEARCH_URL] = FakeHttpResponse(status_code=503)
        with pytest.raises(NetworkError):
            _make_scraper(http).search("fashion")

    def test_invalid_json_raises_parse_error(self):
        http = FakeHttpClient()
        http.responses[_TOPSEARCH_URL] = FakeHttpResponse(
            status_code=200, text="not json",
        )
        with pytest.raises(ParseError):
            _make_scraper(http).search("fashion")

    def test_empty_response_returns_empty_result(self):
        http = FakeHttpClient()
        http.responses[_TOPSEARCH_URL] = FakeHttpResponse(
            status_code=200, json_data={},
        )
        result = _make_scraper(http).search("fashion")
        assert result.users == ()
        assert result.hashtags == ()
        assert result.places == ()
