"""Tests for LocationScraper."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.core.exceptions import NetworkError
from instaharvest.core.models import FeedSource
from instaharvest.scrapers.location import (
    LocationNotFoundError,
    LocationScraper,
)

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


def _make_scraper(http: FakeHttpClient) -> LocationScraper:
    return LocationScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
    )


_INFO_URL = "https://www.instagram.com/api/v1/locations/web_info/"
_SECTIONS_URL = "https://www.instagram.com/api/v1/locations/42/sections/"


# ---------------------------------------------------------------------------
# pk normalisation
# ---------------------------------------------------------------------------


class TestPkNormalisation:
    def test_int_accepted(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"location_info": {"pk": 42, "name": "Tashkent"}},
        )
        loc = _make_scraper(http).lookup(42)
        assert loc.pk == "42"

    def test_negative_int_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).lookup(-1)

    def test_non_numeric_string_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).lookup("abc")

    def test_empty_string_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).lookup("")

    def test_non_str_non_int_rejected(self):
        http = FakeHttpClient()
        with pytest.raises(ValueError):
            _make_scraper(http).lookup(12.5)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


class TestLookup:
    def test_native_data_shape(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(
            status_code=200,
            json_data={
                "native_location_data": {
                    "location_info": {
                        "pk": 42,
                        "name": "Tashkent",
                        "city": "Tashkent",
                        "lat": 41.2995,
                        "lng": 69.2401,
                    },
                    "location_section_data": {"media_count": 50000},
                },
            },
        )
        loc = _make_scraper(http).lookup("42")
        assert loc.pk == "42"
        assert loc.name == "Tashkent"
        assert loc.city == "Tashkent"
        assert loc.lat == 41.2995
        assert loc.lng == 69.2401
        assert loc.media_count == 50000

    def test_legacy_shape(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"location_info": {"pk": 42, "name": "Tashkent"}},
        )
        loc = _make_scraper(http).lookup("42")
        assert loc.name == "Tashkent"
        assert loc.media_count == 0

    def test_404_raises(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=404)
        with pytest.raises(LocationNotFoundError) as exc:
            _make_scraper(http).lookup("42")
        assert exc.value.pk == "42"

    def test_500_raises_network_error(self):
        http = FakeHttpClient()
        http.responses[_INFO_URL] = FakeHttpResponse(status_code=500)
        with pytest.raises(NetworkError):
            _make_scraper(http).lookup("42")


# ---------------------------------------------------------------------------
# Feed
# ---------------------------------------------------------------------------


class TestFeed:
    def _media_dict(self, shortcode: str) -> Dict[str, Any]:
        return {
            "code": shortcode,
            "media_type": 1,
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 1, "comment_count": 0,
            "image_versions2": {"candidates": [{"url": "https://cdn.example/x.jpg"}]},
        }

    def _section(self, codes):
        return {
            "layout_content": {
                "medias": [{"media": self._media_dict(c)} for c in codes],
            },
        }

    def test_recent_uses_recent_tab_and_returns_correct_source(self):
        http = FakeHttpClient()
        http.responses[_SECTIONS_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"sections": [self._section(["TASH01"])], "next_max_id": None},
        )
        feed = _make_scraper(http).recent("42")
        assert feed.source == FeedSource.LOCATION_RECENT
        assert feed.source_id == "42"

    def test_ranked_uses_ranked_tab(self):
        http = FakeHttpClient()
        http.responses[_SECTIONS_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"sections": [self._section(["TASH01"])], "next_max_id": None},
        )
        feed = _make_scraper(http).ranked("42")
        assert feed.source == FeedSource.LOCATION_RANKED
        # POST body specified tab=ranked
        assert any(
            c.get("data", {}).get("tab") == "ranked" for c in http.calls
        )

    def test_int_pk_accepted_for_feed(self):
        http = FakeHttpClient()
        http.responses[_SECTIONS_URL] = FakeHttpResponse(
            status_code=200,
            json_data={"sections": [self._section(["TASH01"])], "next_max_id": None},
        )
        feed = _make_scraper(http).recent(42)
        assert feed.source_id == "42"
