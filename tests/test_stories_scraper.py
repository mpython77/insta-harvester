"""Tests for StoryScraper."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.core.exceptions import NetworkError, ParseError
from instaharvest.core.models import StoryFeed, StorySlide
from instaharvest.scrapers.stories import StoryScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


_REELS_MEDIA_URL = "https://www.instagram.com/api/v1/feed/reels_media/"


def _make_scraper(http: FakeHttpClient, logger: FakeLogger | None = None) -> StoryScraper:
    return StoryScraper(
        http=http,
        logger=logger or FakeLogger(),
        rate_limit=RateLimitConfig(
            request_delay_min=0.0,
            request_delay_max=0.0,
            cooldown_seconds=0.0,
            cooldown_max_retries=0,
        ),
    )


def _item(
    item_id: str = "story_1",
    media_type: int = 1,
    taken_at: int = 1700000000,
    expiring_at: int = 1700086400,
    image_url: str = "https://cdn.example/img.jpg",
    video_url: str | None = None,
    mentions: list | None = None,
    link_stickers: list | None = None,
    user: dict | None = None,
    has_audio: bool = False,
):
    d = {
        "id": item_id,
        "taken_at": taken_at,
        "expiring_at": expiring_at,
        "media_type": media_type,
        "original_width": 1080,
        "original_height": 1920,
        "has_audio": has_audio,
        "image_versions2": {
            "candidates": [{"url": image_url, "width": 1080, "height": 1920}]
        },
    }
    if video_url is not None:
        d["video_versions"] = [{"url": video_url, "width": 1080, "height": 1920}]
    if mentions is not None:
        d["reel_mentions"] = mentions
    if link_stickers is not None:
        d["story_link_stickers"] = link_stickers
    if user is not None:
        d["user"] = user
    return d


def _reels_response(user_id: str = "12345", username: str = "alice", items=None):
    """Build a reels-format response."""
    return {
        "reels": {
            user_id: {
                "user": {"pk": int(user_id), "username": username},
                "items": items or [],
            }
        }
    }


class TestStoryScraper:
    def test_single_user_single_slide(self):
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=[_item()])
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert isinstance(feed, StoryFeed)
        assert feed.user_id == "12345"
        assert feed.username == "alice"
        assert feed.total_returned == 1
        assert len(feed.slides) == 1

    def test_multiple_slides(self):
        items = [_item(item_id="s1"), _item(item_id="s2"), _item(item_id="s3")]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert len(feed.slides) == 3
        assert feed.slides[0].id == "s1"
        assert feed.slides[1].id == "s2"
        assert feed.slides[2].id == "s3"

    def test_video_slide(self):
        items = [_item(media_type=2, video_url="https://cdn.example/vid.mp4")]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        slide = feed.slides[0]
        assert slide.media_type == "video"
        assert str(slide.video_url) == "https://cdn.example/vid.mp4"

    def test_image_slide(self):
        items = [_item(media_type=1)]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        slide = feed.slides[0]
        assert slide.media_type == "image"
        assert slide.video_url is None

    def test_mentions_extracted(self):
        mentions = [
            {"user": {"username": "bob"}},
            {"user": {"username": "carol"}},
        ]
        items = [_item(mentions=mentions)]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.slides[0].mentions == ("bob", "carol")

    def test_link_stickers_extracted(self):
        stickers = [
            {"story_link": {"url": "https://example.com"}},
            {"story_link": {"url": "https://other.com"}},
        ]
        items = [_item(link_stickers=stickers)]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.slides[0].link_stickers == ("https://example.com", "https://other.com")

    def test_reels_media_format(self):
        """Response in reels_media list format also parses correctly."""
        payload = {
            "reels_media": [
                {
                    "user": {"pk": 99, "username": "dave"},
                    "items": [_item(item_id="rm_1")],
                }
            ]
        }
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).get_stories(["99"])
        assert feed.total_returned == 1
        assert feed.slides[0].id == "rm_1"
        assert feed.slides[0].username == "dave"

    def test_empty_response(self):
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=[])
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.total_returned == 0
        assert feed.slides == ()

    def test_no_stories_for_user(self):
        """User has empty items list."""
        payload = {"reels": {"12345": {"user": {"pk": 12345, "username": "alice"}, "items": []}}}
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.total_returned == 0
        assert feed.slides == ()

    def test_http_error_raises_network_error(self):
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(status_code=403, json_data={})
        })
        with pytest.raises(NetworkError):
            _make_scraper(http).get_stories(["12345"])

    def test_invalid_json_raises_parse_error(self):
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(status_code=200, json_data=None, text="not json")
        })
        with pytest.raises(ParseError):
            _make_scraper(http).get_stories(["12345"])

    def test_malformed_item_skipped(self):
        """Item missing id is skipped, warning logged."""
        items = [{"media_type": 1, "taken_at": 100}]  # missing "id"
        logger = FakeLogger()
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http, logger=logger).get_stories(["12345"])
        assert feed.total_returned == 0

    def test_expiring_at_parsed(self):
        items = [_item(expiring_at=1700086400)]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        slide = feed.slides[0]
        assert isinstance(slide.expiring_at, datetime)
        assert slide.expiring_at == datetime.fromtimestamp(1700086400, tz=timezone.utc)

    def test_taken_at_parsed(self):
        items = [_item(taken_at=1700000000)]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        slide = feed.slides[0]
        assert isinstance(slide.taken_at, datetime)
        assert slide.taken_at == datetime.fromtimestamp(1700000000, tz=timezone.utc)

    def test_user_info_from_item(self):
        """Item has its own user dict which overrides parent."""
        items = [_item(user={"pk": 999, "username": "override_user"})]
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(user_id="12345", username="alice", items=items)
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        slide = feed.slides[0]
        assert slide.user_id == "999"
        assert slide.username == "override_user"

    def test_video_duration_extracted(self):
        """video_duration is parsed from API response for video items."""
        item = _item(media_type=2, video_url="https://cdn.example/vid.mp4")
        item["video_duration"] = 14.567
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=[item])
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.slides[0].video_duration == 14.567

    def test_video_duration_zero_is_none(self):
        """video_duration of 0.0 is treated as unknown and set to None."""
        item = _item(media_type=2, video_url="https://cdn.example/vid.mp4")
        item["video_duration"] = 0
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=[item])
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.slides[0].video_duration is None

    def test_video_duration_none_for_images(self):
        """video_duration is None for image slides."""
        item = _item(media_type=1)
        item["video_duration"] = 10.0  # should be ignored for images
        http = FakeHttpClient(responses={
            _REELS_MEDIA_URL: FakeHttpResponse(
                json_data=_reels_response(items=[item])
            )
        })
        feed = _make_scraper(http).get_stories(["12345"])
        assert feed.slides[0].video_duration is None
