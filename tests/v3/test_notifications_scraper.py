"""Tests for NotificationsScraper."""

from __future__ import annotations

import pytest

from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.core.models import (
    Notification,
    NotificationFeed,
    NotificationType,
)
from instaharvest._v3.scrapers.notifications import NotificationsScraper

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


_INBOX_URL = "https://www.instagram.com/api/v1/news/inbox/"


def _make_scraper(http: FakeHttpClient) -> NotificationsScraper:
    return NotificationsScraper(
        http=http,
        logger=FakeLogger(),
    )


def _notif_item(
    pk: str = "notif_1",
    notif_type: int | None = 12,
    text: str = "alice liked your post",
    timestamp: int = 1700000000,
    usernames: list | None = None,
    is_grouped: bool = False,
    group_count: int = 0,
):
    args = {
        "text": text,
        "timestamp": timestamp,
        "profile_image": "https://cdn.example/pic.jpg",
        "links": [{"type": "user", "id": u} for u in (usernames or ["alice"])],
    }
    if is_grouped:
        args["is_grouped"] = True
        args["group_count"] = group_count
    item = {"pk": pk, "args": args}
    if notif_type is not None:
        item["type"] = notif_type
    return item


def _inbox_response(stories=None, more_available=False, next_cursor=None):
    return {
        "stories": stories or [],
        "old_stories": [],
        "more_available": more_available,
        "next_cursor": next_cursor,
    }


class TestNotificationsScraper:
    def test_basic_like_notification(self):
        payload = _inbox_response(stories=[_notif_item(notif_type=12)])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert isinstance(feed, NotificationFeed)
        assert feed.total_returned == 1
        n = feed.notifications[0]
        assert n.notification_type == NotificationType.LIKE

    def test_comment_notification(self):
        payload = _inbox_response(stories=[
            _notif_item(notif_type=14, text="bob commented on your post")
        ])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.notifications[0].notification_type == NotificationType.COMMENT

    def test_follow_notification(self):
        payload = _inbox_response(stories=[
            _notif_item(notif_type=101, text="carol started following you")
        ])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.notifications[0].notification_type == NotificationType.FOLLOW

    def test_mention_notification(self):
        payload = _inbox_response(stories=[
            _notif_item(notif_type=102, text="dave mentioned you")
        ])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.notifications[0].notification_type == NotificationType.MENTION

    def test_text_classification_fallback(self):
        """No type code, text='liked your photo' -> LIKE."""
        payload = _inbox_response(stories=[
            _notif_item(notif_type=None, text="alice liked your photo")
        ])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.notifications[0].notification_type == NotificationType.LIKE

    def test_comment_like_text_pattern(self):
        """text='liked your comment' -> COMMENT_LIKE."""
        payload = _inbox_response(stories=[
            _notif_item(notif_type=None, text="bob liked your comment")
        ])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.notifications[0].notification_type == NotificationType.COMMENT_LIKE

    def test_multiple_notifications(self):
        stories = [
            _notif_item(pk="n1", notif_type=12, text="liked"),
            _notif_item(pk="n2", notif_type=14, text="commented"),
            _notif_item(pk="n3", notif_type=101, text="followed"),
        ]
        payload = _inbox_response(stories=stories)
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.total_returned == 3

    def test_pagination(self):
        """Multiple pages with cursor are collected from both."""
        page1 = _inbox_response(
            stories=[_notif_item(pk="n1")],
            more_available=True,
            next_cursor="cursor_abc",
        )
        page2 = _inbox_response(
            stories=[_notif_item(pk="n2")],
            more_available=False,
            next_cursor=None,
        )

        call_count = [0]
        original_get = None

        http = FakeHttpClient()

        def paginated_get(url, *, params=None, headers=None):
            http.calls.append({"method": "GET", "url": url, "headers": headers})
            if call_count[0] == 0:
                call_count[0] += 1
                return FakeHttpResponse(json_data=page1)
            else:
                return FakeHttpResponse(json_data=page2)

        http.get = paginated_get  # type: ignore[assignment]

        feed = _make_scraper(http).feed(max_items=None)
        assert feed.total_returned == 2
        assert feed.notifications[0].id == "n1"
        assert feed.notifications[1].id == "n2"

    def test_max_items_caps_result(self):
        """max_items=2 with 5 available -> only 2 returned."""
        stories = [_notif_item(pk=f"n{i}") for i in range(5)]
        payload = _inbox_response(stories=stories)
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed(max_items=2)
        assert feed.total_returned == 2
        assert feed.has_more is True

    def test_empty_inbox(self):
        payload = _inbox_response(stories=[])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        assert feed.total_returned == 0
        assert feed.notifications == ()

    def test_http_error(self):
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(status_code=429, json_data={})
        })
        with pytest.raises(NetworkError):
            _make_scraper(http).feed()

    def test_grouped_notification(self):
        """is_grouped=True, group_count=5 -> fields set."""
        payload = _inbox_response(stories=[
            _notif_item(is_grouped=True, group_count=5)
        ])
        http = FakeHttpClient(responses={
            _INBOX_URL: FakeHttpResponse(json_data=payload)
        })
        feed = _make_scraper(http).feed()
        n = feed.notifications[0]
        assert n.is_grouped is True
        assert n.group_count == 5
