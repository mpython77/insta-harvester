"""Tests for HighlightScraper."""

from __future__ import annotations

import pytest

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.core.exceptions import NetworkError, ParseError
from instaharvest.core.models import Highlight, HighlightSlide, HighlightsList
from instaharvest.scrapers.highlights import HighlightScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


_HIGHLIGHTS_TRAY_URL = "https://www.instagram.com/api/v1/highlights/"
_REELS_MEDIA_URL = "https://www.instagram.com/api/v1/feed/reels_media/"


def _make_scraper(http: FakeHttpClient) -> HighlightScraper:
    return HighlightScraper(
        http=http,
        logger=FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
    )


def _tray_entry(
    entry_id: str = "highlight:123",
    title: str = "Travel",
    cover_url: str = "https://cdn.example/cover.jpg",
    media_count: int = 5,
    created_at: int = 1700000000,
    use_fallback_cover: bool = False,
):
    entry = {
        "id": entry_id,
        "title": title,
        "media_count": media_count,
        "created_at": created_at,
    }
    if use_fallback_cover:
        entry["cover_media"] = {
            "image_versions2": {
                "candidates": [{"url": cover_url, "width": 150, "height": 150}]
            }
        }
    else:
        entry["cover_media"] = {
            "cropped_image_version": {"url": cover_url}
        }
    return entry


def _slide_item(
    item_id: str = "slide_1",
    media_type: int = 1,
    taken_at: int = 1700000000,
    expiring_at: int = 1700086400,
    image_url: str = "https://cdn.example/img.jpg",
    video_url: str | None = None,
):
    d = {
        "id": item_id,
        "taken_at": taken_at,
        "expiring_at": expiring_at,
        "media_type": media_type,
        "original_width": 1080,
        "original_height": 1920,
        "has_audio": False,
        "image_versions2": {
            "candidates": [{"url": image_url, "width": 1080, "height": 1920}]
        },
    }
    if video_url is not None:
        d["video_versions"] = [{"url": video_url, "width": 1080, "height": 1920}]
    return d


class TestListHighlights:
    def test_list_highlights_basic(self):
        payload = {"tray": [_tray_entry()]}
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(json_data=payload)
        })
        result = _make_scraper(http).list_highlights("12345")
        assert isinstance(result, HighlightsList)
        assert result.user_id == "12345"
        assert result.total_returned == 1
        h = result.highlights[0]
        assert h.pk == "123"
        assert h.title == "Travel"

    def test_list_highlights_multiple(self):
        payload = {"tray": [
            _tray_entry(entry_id="highlight:1", title="Food"),
            _tray_entry(entry_id="highlight:2", title="Nature"),
            _tray_entry(entry_id="highlight:3", title="Travel"),
        ]}
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(json_data=payload)
        })
        result = _make_scraper(http).list_highlights("12345")
        assert result.total_returned == 3
        assert result.highlights[0].title == "Food"
        assert result.highlights[1].title == "Nature"
        assert result.highlights[2].title == "Travel"

    def test_list_highlights_empty(self):
        payload = {"tray": []}
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(json_data=payload)
        })
        result = _make_scraper(http).list_highlights("12345")
        assert result.total_returned == 0
        assert result.highlights == ()

    def test_list_highlights_cover_url_from_cropped(self):
        payload = {"tray": [_tray_entry(cover_url="https://cdn.example/cropped.jpg")]}
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(json_data=payload)
        })
        result = _make_scraper(http).list_highlights("12345")
        assert str(result.highlights[0].cover_url) == "https://cdn.example/cropped.jpg"

    def test_list_highlights_cover_url_fallback(self):
        """Fallback to image_versions2.candidates[0].url."""
        payload = {"tray": [_tray_entry(
            cover_url="https://cdn.example/fallback.jpg",
            use_fallback_cover=True,
        )]}
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(json_data=payload)
        })
        result = _make_scraper(http).list_highlights("12345")
        assert str(result.highlights[0].cover_url) == "https://cdn.example/fallback.jpg"

    def test_list_highlights_strip_highlight_prefix(self):
        """'highlight:123' id becomes pk='123'."""
        payload = {"tray": [_tray_entry(entry_id="highlight:456")]}
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(json_data=payload)
        })
        result = _make_scraper(http).list_highlights("12345")
        assert result.highlights[0].pk == "456"

    def test_list_highlights_http_error(self):
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(status_code=404, json_data={})
        })
        with pytest.raises(NetworkError):
            _make_scraper(http).list_highlights("12345")

    def test_list_highlights_bad_json(self):
        http = FakeHttpClient(responses={
            _HIGHLIGHTS_TRAY_URL: FakeHttpResponse(status_code=200, json_data=None, text="<html>")
        })
        with pytest.raises(ParseError):
            _make_scraper(http).list_highlights("12345")


class TestGetHighlight:
    def test_get_highlight_basic(self):
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [_slide_item()],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert len(slides) == 1
        assert isinstance(slides[0], HighlightSlide)
        assert slides[0].id == "slide_1"
        assert slides[0].highlight_pk == "123"

    def test_get_highlight_multiple_slides(self):
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [
                        _slide_item(item_id="s1"),
                        _slide_item(item_id="s2"),
                        _slide_item(item_id="s3"),
                    ],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert len(slides) == 3
        assert slides[0].id == "s1"
        assert slides[2].id == "s3"

    def test_get_highlight_video_slide(self):
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [_slide_item(media_type=2, video_url="https://cdn.example/vid.mp4")],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert slides[0].media_type == "video"
        assert str(slides[0].video_url) == "https://cdn.example/vid.mp4"

    def test_get_highlight_adds_prefix(self):
        """If highlight_pk doesn't have 'highlight:' prefix, adds it in request."""
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [_slide_item()],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        _make_scraper(http).get_highlight("123")
        # Verify the POST data includes "highlight:" prefix
        call = http.calls[0]
        assert call["method"] == "POST"
        assert call["data"]["reel_ids"] == ["highlight:123"]

    def test_get_highlight_already_prefixed(self):
        """'highlight:123' sent as-is."""
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [_slide_item()],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        _make_scraper(http).get_highlight("highlight:123")
        call = http.calls[0]
        assert call["data"]["reel_ids"] == ["highlight:123"]

    def test_get_highlight_http_error(self):
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(status_code=500, json_data={})
        })
        with pytest.raises(NetworkError):
            _make_scraper(http).get_highlight("123")

    def test_get_highlight_empty(self):
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert slides == ()

    def test_get_highlight_video_duration_extracted(self):
        """video_duration is parsed from API response for video slides."""
        item = _slide_item(media_type=2, video_url="https://cdn.example/vid.mp4")
        item["video_duration"] = 22.5
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [item],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert slides[0].video_duration == 22.5

    def test_get_highlight_video_duration_zero_is_none(self):
        """video_duration of 0.0 is treated as unknown and set to None."""
        item = _slide_item(media_type=2, video_url="https://cdn.example/vid.mp4")
        item["video_duration"] = 0
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [item],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert slides[0].video_duration is None

    def test_get_highlight_video_duration_none_for_images(self):
        """video_duration is None for image slides."""
        item = _slide_item(media_type=1)
        item["video_duration"] = 10.0  # should be ignored for images
        payload = {
            "reels": {
                "highlight:123": {
                    "user": {"pk": 12345, "username": "alice"},
                    "items": [item],
                }
            }
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        slides = _make_scraper(http).get_highlight("123")
        assert slides[0].video_duration is None
