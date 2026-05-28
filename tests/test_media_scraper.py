"""Tests for MediaScraper — API path, DOM fallback, error mapping."""

from __future__ import annotations

import json

import pytest

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.config.selectors import MediaSelectors
from instaharvest.core.exceptions import ParseError
from instaharvest.core.models import MediaKind
from instaharvest.scrapers.media import (
    MediaNotFoundError,
    MediaScraper,
)

from .conftest import FakeBrowserSession, FakeHttpClient, FakeHttpResponse, FakeLogger


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def _make_scraper(
    *,
    http: FakeHttpClient | None = None,
    browser: FakeBrowserSession | None = None,
) -> MediaScraper:
    return MediaScraper(
        browser=browser or FakeBrowserSession(),
        http=http or FakeHttpClient(),
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
        selectors=MediaSelectors(),
    )


def _api_response(item: dict) -> FakeHttpResponse:
    return FakeHttpResponse(
        status_code=200,
        json_data={"items": [item]},
    )


_BASE_API_URL = "https://i.instagram.com/api/v1/media/"


# ---------------------------------------------------------------------------
# API path
# ---------------------------------------------------------------------------


class TestApiPath:
    def test_image_post(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = _api_response({
            "media_type": 1,
            "user": {"pk": 99, "username": "alice", "is_verified": True},
            "taken_at": 1_700_000_000,
            "like_count": 250,
            "comment_count": 17,
            "caption": {"text": "hello world"},
            "image_versions2": {
                "candidates": [{"url": "https://cdn.example/img.jpg", "width": 1080, "height": 1080}],
            },
            "original_width": 1080,
            "original_height": 1080,
            "accessibility_caption": "A photo of a sunset.",
        })
        scraper = _make_scraper(http=http)
        media = scraper.scrape("ABC1234")

        assert media.kind == MediaKind.IMAGE
        assert media.shortcode == "ABC1234"
        assert media.owner.username == "alice"
        assert media.owner.user_id == "99"
        assert media.owner.is_verified is True
        assert media.like_count == 250
        assert media.comment_count == 17
        assert media.caption == "hello world"
        assert media.width == 1080
        assert str(media.image_url).startswith("https://cdn.example/")
        assert media.video_url is None
        assert media.data_source == "api"

    def test_reel_classified_correctly(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = _api_response({
            "media_type": 2,
            "product_type": "clips",
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 1, "comment_count": 0,
            "video_versions": [{"url": "https://cdn.example/v.mp4"}],
            "video_duration": 12.5,
            "has_audio": True,
        })
        media = _make_scraper(http=http).scrape("XYZ12345")
        assert media.kind == MediaKind.REEL
        assert media.video_duration == 12.5
        assert media.has_audio is True
        # URL uses /reel/ for reels, not /p/.
        assert "/reel/" in str(media.url)

    def test_carousel_with_slides(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = _api_response({
            "media_type": 8,
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 1, "comment_count": 0,
            "carousel_media": [
                {
                    "media_type": 1, "original_width": 1080, "original_height": 1080,
                    "image_versions2": {"candidates": [{"url": "https://cdn.example/1.jpg"}]},
                },
                {
                    "media_type": 2, "original_width": 1080, "original_height": 1920,
                    "video_versions": [{"url": "https://cdn.example/2.mp4"}],
                    "video_duration": 5.0,
                    "has_audio": True,
                },
            ],
        })
        media = _make_scraper(http=http).scrape("ABCDE12")
        assert media.kind == MediaKind.CAROUSEL
        assert len(media.carousel) == 2
        assert media.carousel[0].kind == MediaKind.IMAGE
        assert media.carousel[1].kind == MediaKind.VIDEO
        assert media.carousel[1].has_audio is True

    def test_carousel_media_type_8_without_children_is_parse_error(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = _api_response({
            "media_type": 8,
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 0, "comment_count": 0,
            # No carousel_media!
        })
        with pytest.raises(ParseError):
            _make_scraper(http=http).scrape("ABCDE12")

    def test_404_raises_media_not_found(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = FakeHttpResponse(status_code=404)
        with pytest.raises(MediaNotFoundError) as exc:
            _make_scraper(http=http).scrape("ABC1234")
        assert exc.value.shortcode == "ABC1234"

    def test_url_input_accepted(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = _api_response({
            "media_type": 1,
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 1, "comment_count": 0,
            "image_versions2": {"candidates": [{"url": "https://cdn.example/x.jpg"}]},
        })
        media = _make_scraper(http=http).scrape("https://www.instagram.com/p/ABC1234/")
        assert media.shortcode == "ABC1234"

    def test_invalid_input_rejected_before_io(self):
        http = FakeHttpClient()  # would assert on any unmatched URL
        scraper = _make_scraper(http=http)
        with pytest.raises(ValueError):
            scraper.scrape("not a url")
        assert http.calls == []

    def test_skips_api_when_prefer_api_false(self):
        http = FakeHttpClient()
        # DOM fallback gets a tiny embedded payload
        json_blob = json.dumps({
            "media_type": 1,
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 1, "comment_count": 0,
            "image_versions2": {"candidates": [{"url": "https://cdn.example/x.jpg"}]},
        })
        page = (
            '<html><script>window._sharedData={"shortcode_media":'
            + json_blob
            + ',"foo":1}</script></html>'
        )
        browser = FakeBrowserSession(
            url="https://www.instagram.com/p/ABC1234/",
            content=page,
        )
        media = _make_scraper(http=http, browser=browser).scrape(
            "ABC1234", prefer_api=False
        )
        assert media.data_source == "dom"
        assert http.calls == []  # API was skipped


# ---------------------------------------------------------------------------
# DOM path (as fallback)
# ---------------------------------------------------------------------------


class TestDomFallback:
    def test_used_when_api_returns_5xx(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = FakeHttpResponse(status_code=500)
        json_blob = json.dumps({
            "media_type": 1,
            "user": {"pk": 1, "username": "alice"},
            "taken_at": 1_700_000_000,
            "like_count": 99, "comment_count": 1,
            "image_versions2": {"candidates": [{"url": "https://cdn.example/x.jpg"}]},
        })
        page = (
            '<html><script>{"shortcode_media":'
            + json_blob
            + ',"viewer":null}</script></html>'
        )
        browser = FakeBrowserSession(
            url="https://www.instagram.com/p/ABC1234/",
            content=page,
        )
        media = _make_scraper(http=http, browser=browser).scrape("ABC1234")
        assert media.data_source == "dom"
        assert media.like_count == 99

    def test_dom_not_found_marker_raises(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = FakeHttpResponse(status_code=500)
        browser = FakeBrowserSession(
            url="https://www.instagram.com/p/ABC1234/",
            content="<html>Sorry, this page isn't available.</html>",
        )
        with pytest.raises(MediaNotFoundError):
            _make_scraper(http=http, browser=browser).scrape("ABC1234")

    def test_dom_without_embedded_json_raises_parse_error(self):
        http = FakeHttpClient()
        http.responses[_BASE_API_URL] = FakeHttpResponse(status_code=500)
        browser = FakeBrowserSession(
            url="https://www.instagram.com/p/ABC1234/",
            content="<html><body>just text, no script</body></html>",
        )
        with pytest.raises(ParseError):
            _make_scraper(http=http, browser=browser).scrape("ABC1234")
