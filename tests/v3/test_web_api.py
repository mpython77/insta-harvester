"""Tests for the unified WebAPI client."""

from __future__ import annotations

import pytest

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.settings import Settings
from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.scrapers.web_api import WebAPI
from instaharvest._v3.facade import InstaHarvest

from .conftest import FakeHttpClient, FakeHttpResponse, FakeLogger


def _make_api(http: FakeHttpClient, logger: FakeLogger | None = None) -> WebAPI:
    return WebAPI(http=http, logger=logger or FakeLogger())


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------


class TestWebAPIReadEndpoints:
    def test_get_profile_success(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/users/web_profile_info/": FakeHttpResponse(
                status_code=200, json_data={"data": {"user": {"id": "123"}}}
            ),
        })
        api = _make_api(http)
        result = api.get_profile("testuser")
        assert result == {"data": {"user": {"id": "123"}}}

    def test_get_profile_404_raises_network_error(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/users/web_profile_info/": FakeHttpResponse(
                status_code=404, json_data=None, text="Not Found"
            ),
        })
        api = _make_api(http)
        with pytest.raises(NetworkError) as exc_info:
            api.get_profile("ghost")
        assert "404" in str(exc_info.value)

    def test_get_profile_non_json_raises_parse_error(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/users/web_profile_info/": FakeHttpResponse(
                status_code=200, json_data=None, text="<html>not json</html>"
            ),
        })
        api = _make_api(http)
        with pytest.raises(ParseError):
            api.get_profile("testuser")

    def test_get_media_info_success(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/media/ABC123/info/": FakeHttpResponse(
                status_code=200, json_data={"items": [{"id": "1"}]}
            ),
        })
        api = _make_api(http)
        result = api.get_media_info("ABC123")
        assert result == {"items": [{"id": "1"}]}

    def test_get_comments_success(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/media/999/comments/": FakeHttpResponse(
                status_code=200, json_data={"comments": [], "next_min_id": None}
            ),
        })
        api = _make_api(http)
        result = api.get_comments("999")
        assert result == {"comments": [], "next_min_id": None}

    def test_get_comments_with_cursor(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/media/999/comments/": FakeHttpResponse(
                status_code=200, json_data={"comments": [{"id": "c2"}]}
            ),
        })
        api = _make_api(http)
        result = api.get_comments("999", cursor="abc")
        assert result == {"comments": [{"id": "c2"}]}
        # Verify the params were sent
        call = http.calls[0]
        assert call["method"] == "GET"

    def test_get_followers_success(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/friendships/111/followers/": FakeHttpResponse(
                status_code=200, json_data={"users": [{"pk": "222"}]}
            ),
        })
        api = _make_api(http)
        result = api.get_followers("111")
        assert result == {"users": [{"pk": "222"}]}

    def test_get_following_success(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/friendships/111/following/": FakeHttpResponse(
                status_code=200, json_data={"users": [{"pk": "333"}]}
            ),
        })
        api = _make_api(http)
        result = api.get_following("111")
        assert result == {"users": [{"pk": "333"}]}

    def test_get_hashtag_info_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/tags/web_info/": FakeHttpResponse(
                status_code=200, json_data={"name": "python", "media_count": 5000}
            ),
        })
        api = _make_api(http)
        result = api.get_hashtag_info("python")
        assert result["name"] == "python"

    def test_get_hashtag_sections_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/tags/python/sections/": FakeHttpResponse(
                status_code=200, json_data={"sections": [], "next_max_id": None}
            ),
        })
        api = _make_api(http)
        result = api.get_hashtag_sections("python", tab="recent")
        assert result == {"sections": [], "next_max_id": None}

    def test_get_location_info_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/locations/web_info/": FakeHttpResponse(
                status_code=200, json_data={"native_location_data": {"pk": "12345"}}
            ),
        })
        api = _make_api(http)
        result = api.get_location_info("12345")
        assert result["native_location_data"]["pk"] == "12345"

    def test_get_location_sections_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/locations/12345/sections/": FakeHttpResponse(
                status_code=200, json_data={"sections": [{"items": []}]}
            ),
        })
        api = _make_api(http)
        result = api.get_location_sections("12345")
        assert "sections" in result

    def test_get_explore_grid_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/discover/web/explore_grid/": FakeHttpResponse(
                status_code=200, json_data={"sectional_items": [], "next_max_id": "x"}
            ),
        })
        api = _make_api(http)
        result = api.get_explore_grid()
        assert result["next_max_id"] == "x"

    def test_get_stories_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/feed/reels_media/": FakeHttpResponse(
                status_code=200, json_data={"reels": {"123": {"items": []}}}
            ),
        })
        api = _make_api(http)
        result = api.get_stories(["123"])
        assert "reels" in result

    def test_get_highlights_tray_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/highlights/123/highlights_tray/": FakeHttpResponse(
                status_code=200, json_data={"tray": [{"id": "h1"}]}
            ),
        })
        api = _make_api(http)
        result = api.get_highlights_tray("123")
        assert result["tray"][0]["id"] == "h1"

    def test_get_highlight_items_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/feed/reels_media/": FakeHttpResponse(
                status_code=200, json_data={"reels": {"highlight:99": {"items": [{"id": "s1"}]}}}
            ),
        })
        api = _make_api(http)
        result = api.get_highlight_items("99")
        assert "reels" in result

    def test_get_notifications_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/news/inbox/": FakeHttpResponse(
                status_code=200, json_data={"new_stories": [], "old_stories": []}
            ),
        })
        api = _make_api(http)
        result = api.get_notifications()
        assert "new_stories" in result

    def test_get_notifications_with_cursor(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/news/inbox/": FakeHttpResponse(
                status_code=200, json_data={"old_stories": [{"pk": "n1"}]}
            ),
        })
        api = _make_api(http)
        result = api.get_notifications(cursor="cursor123")
        assert "old_stories" in result

    def test_search_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/fbsearch/topsearch_flat/": FakeHttpResponse(
                status_code=200, json_data={"list": [{"user": {"username": "alice"}}]}
            ),
        })
        api = _make_api(http)
        result = api.search("alice")
        assert result["list"][0]["user"]["username"] == "alice"

    def test_friendship_status_success(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/friendships/show/456/": FakeHttpResponse(
                status_code=200, json_data={"following": True, "blocking": False}
            ),
        })
        api = _make_api(http)
        result = api.friendship_status("456")
        assert result["following"] is True


# ---------------------------------------------------------------------------
# Write endpoints
# ---------------------------------------------------------------------------


class TestWebAPIWriteEndpoints:
    def test_follow_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/friendships/create/789/": FakeHttpResponse(
                status_code=200, json_data={"result": "following", "status": "ok"}
            ),
        })
        api = _make_api(http)
        result = api.follow("789")
        assert result["result"] == "following"

    def test_unfollow_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/friendships/destroy/789/": FakeHttpResponse(
                status_code=200, json_data={"status": "ok"}
            ),
        })
        api = _make_api(http)
        result = api.unfollow("789")
        assert result["status"] == "ok"

    def test_send_message_success(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/": FakeHttpResponse(
                status_code=200, json_data={"status": "ok", "payload": {"thread_id": "t1"}}
            ),
        })
        api = _make_api(http)
        result = api.send_message("100", "Hello!")
        assert result["status"] == "ok"
        # Verify the data that was sent
        call = http.calls[0]
        assert call["data"]["text"] == "Hello!"
        assert call["data"]["recipient_users"] == "[[100]]"


# ---------------------------------------------------------------------------
# Headers
# ---------------------------------------------------------------------------


class TestWebAPIHeaders:
    def test_read_endpoints_include_app_id_header(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/users/web_profile_info/": FakeHttpResponse(
                status_code=200, json_data={"data": {}}
            ),
        })
        api = _make_api(http)
        api.get_profile("test")
        headers = http.calls[0]["headers"]
        assert headers["X-IG-App-ID"] == "936619743392459"
        assert headers["X-Requested-With"] == "XMLHttpRequest"

    def test_write_endpoints_include_csrf_token(self):
        """Write endpoints add X-CSRFToken when available."""

        class FakeHttpWithCsrf(FakeHttpClient):
            def csrf_token(self):
                return "test_csrf_token_abc"

        http = FakeHttpWithCsrf(responses={
            "https://www.instagram.com/api/v1/friendships/create/5/": FakeHttpResponse(
                status_code=200, json_data={"status": "ok"}
            ),
        })
        api = _make_api(http)
        api.follow("5")
        headers = http.calls[0]["headers"]
        assert headers["X-CSRFToken"] == "test_csrf_token_abc"

    def test_write_endpoints_include_origin_referer(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/friendships/create/5/": FakeHttpResponse(
                status_code=200, json_data={"status": "ok"}
            ),
        })
        api = _make_api(http)
        api.follow("5")
        headers = http.calls[0]["headers"]
        assert headers["Origin"] == "https://www.instagram.com"
        assert headers["Referer"] == "https://www.instagram.com/"

    def test_read_endpoints_do_not_include_origin(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/news/inbox/": FakeHttpResponse(
                status_code=200, json_data={}
            ),
        })
        api = _make_api(http)
        api.get_notifications()
        headers = http.calls[0]["headers"]
        assert "Origin" not in headers

    def test_write_without_csrf_token_logs_warning(self):
        """Write with a plain FakeHttpClient (no csrf_token, no _session) omits X-CSRFToken and logs a warning."""
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/friendships/create/5/": FakeHttpResponse(
                status_code=200, json_data={"result": "following", "status": "ok"}
            ),
        })
        logger = FakeLogger()
        api = WebAPI(http=http, logger=logger)
        result = api.follow("5")

        # Request was made successfully
        assert len(http.calls) == 1
        assert http.calls[0]["method"] == "POST"

        # X-CSRFToken is NOT in the headers
        headers = http.calls[0]["headers"]
        assert "X-CSRFToken" not in headers

        # Warning was logged about missing CSRF token
        warnings = logger.messages_at("warning")
        assert any("web_api write without csrf token" in msg for msg in warnings)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestWebAPIErrorHandling:
    def test_4xx_raises_network_error(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/users/web_profile_info/": FakeHttpResponse(
                status_code=429, json_data=None, text="Rate Limited"
            ),
        })
        api = _make_api(http)
        with pytest.raises(NetworkError) as exc_info:
            api.get_profile("x")
        assert "429" in str(exc_info.value)

    def test_5xx_raises_network_error(self):
        http = FakeHttpClient(responses={
            "https://i.instagram.com/api/v1/users/web_profile_info/": FakeHttpResponse(
                status_code=500, json_data=None, text="Server Error"
            ),
        })
        api = _make_api(http)
        with pytest.raises(NetworkError):
            api.get_profile("x")

    def test_non_json_response_raises_parse_error(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/news/inbox/": FakeHttpResponse(
                status_code=200, json_data=None, text="plain text"
            ),
        })
        api = _make_api(http)
        with pytest.raises(ParseError):
            api.get_notifications()

    def test_network_exception_propagates(self):
        http = FakeHttpClient(
            responses={},
            raise_for_url={
                "https://i.instagram.com/api/v1/users/web_profile_info/": NetworkError(
                    "connection reset", url="https://i.instagram.com/"
                ),
            },
        )
        api = _make_api(http)
        with pytest.raises(NetworkError, match="connection reset"):
            api.get_profile("x")

    def test_post_5xx_raises_network_error(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/friendships/create/1/": FakeHttpResponse(
                status_code=503, json_data=None, text="Unavailable"
            ),
        })
        api = _make_api(http)
        with pytest.raises(NetworkError) as exc_info:
            api.follow("1")
        assert "503" in str(exc_info.value)

    def test_post_non_json_raises_parse_error(self):
        http = FakeHttpClient(responses={
            "https://www.instagram.com/api/v1/friendships/create/1/": FakeHttpResponse(
                status_code=200, json_data=None, text="<html></html>"
            ),
        })
        api = _make_api(http)
        with pytest.raises(ParseError):
            api.follow("1")


# ---------------------------------------------------------------------------
# Facade integration
# ---------------------------------------------------------------------------


class TestWebAPIFacade:
    def test_facade_api_property_returns_web_api(self):
        http = FakeHttpClient()
        logger = FakeLogger()
        ih = InstaHarvest(
            Settings.default(),
            http=http,
            logger=logger,
            browser=None,
        )
        # InstaHarvest needs a browser; patch minimally
        ih._browser_started = True

        assert isinstance(ih.api, WebAPI)

    def test_facade_api_property_is_cached(self):
        http = FakeHttpClient()
        logger = FakeLogger()
        ih = InstaHarvest(
            Settings.default(),
            http=http,
            logger=logger,
            browser=None,
        )
        ih._browser_started = True

        api1 = ih.api
        api2 = ih.api
        assert api1 is api2
