"""
Unified low-level Instagram Web API client.

Consolidates all API endpoint wrappers into one place. Each method:

- Constructs the correct URL
- Sends the request with standard IG headers (X-IG-App-ID etc.)
- Adds CSRF token for write operations
- Checks response status, raises NetworkError on 4xx/5xx
- Parses JSON, raises ParseError on decode failure
- Returns the raw JSON dict (parsing into Pydantic models is the scraper's job)

Write operations do NOT enforce enabled/dry-run here -- that is the
Actions layer's job. This class is purely about HTTP transport and
response validation.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional

from instaharvest.core.exceptions import NetworkError, ParseError
from instaharvest.core.protocols import HttpClient, Logger


_HEADERS: Dict[str, str] = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

_WRITE_HEADERS: Dict[str, str] = {
    **_HEADERS,
    "Origin": "https://www.instagram.com",
    "Referer": "https://www.instagram.com/",
}


class WebAPI:
    """Unified low-level Instagram Web API client.

    Consolidates all API endpoint wrappers into one place. Each method
    constructs the correct URL, sends the request with standard IG headers,
    checks response status, parses JSON, and returns the raw dict.

    This is a raw transport layer without built-in pacing or rate limiting.
    Users calling methods directly should throttle their own requests to
    avoid 429 responses and potential account restrictions.

    Usage::

        from instaharvest import InstaHarvest, Settings

        with InstaHarvest(Settings.default()) as ih:
            data = ih.api.get_profile("instagram")
            # data is a raw JSON dict
    """

    def __init__(self, *, http: HttpClient, logger: Logger) -> None:
        self._http = http
        self._logger = logger

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _csrf_token(self) -> Optional[str]:
        """Extract the csrftoken cookie from the underlying HTTP session."""
        getter = getattr(self._http, "csrf_token", None)
        if callable(getter):
            return getter()
        session = getattr(self._http, "_session", None)
        cookies = getattr(session, "cookies", None) if session is not None else None
        if cookies is not None:
            try:
                return cookies.get("csrftoken")
            except Exception:
                return None
        return None

    def _get(
        self,
        url: str,
        params: Optional[Mapping[str, Any]] = None,
    ) -> dict:
        """GET with standard read headers, status check, JSON parse."""
        self._logger.debug("web_api GET", url=url)
        try:
            resp = self._http.get(url, params=params, headers=_HEADERS)
        except NetworkError:
            raise

        if resp.status_code >= 400:
            raise NetworkError(
                f"GET {url} returned {resp.status_code}",
                url=url,
            )

        try:
            return resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"GET {url} returned non-JSON response",
                source="web_api",
            ) from exc

    def _post(
        self,
        url: str,
        data: Any = None,
        json_body: Any = None,
        *,
        write: bool = False,
    ) -> dict:
        """POST with headers, optional CSRF for writes, status check, JSON parse."""
        self._logger.debug("web_api POST", url=url, write=write)
        headers: Dict[str, str] = dict(_WRITE_HEADERS if write else _HEADERS)
        if write:
            token = self._csrf_token()
            if token:
                headers["X-CSRFToken"] = token
            else:
                self._logger.warning("web_api write without csrf token", url=url)

        try:
            resp = self._http.post(url, data=data, json=json_body, headers=headers)
        except NetworkError:
            raise

        if resp.status_code >= 400:
            raise NetworkError(
                f"POST {url} returned {resp.status_code}",
                url=url,
            )

        try:
            return resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"POST {url} returned non-JSON response",
                source="web_api",
            ) from exc

    # ------------------------------------------------------------------
    # Read endpoints
    # ------------------------------------------------------------------

    def get_profile(self, username: str) -> dict:
        """Fetch profile info for a username."""
        url = "https://i.instagram.com/api/v1/users/web_profile_info/"
        return self._get(url, params={"username": username})

    def get_media_info(self, shortcode: str) -> dict:
        """Fetch media info for a shortcode."""
        url = f"https://i.instagram.com/api/v1/media/{shortcode}/info/"
        return self._get(url)

    def get_comments(
        self, media_id: str, *, cursor: Optional[str] = None
    ) -> dict:
        """Fetch comments for a media item."""
        url = f"https://i.instagram.com/api/v1/media/{media_id}/comments/"
        params: Dict[str, str] = {}
        if cursor:
            params["min_id"] = cursor
        return self._get(url, params=params or None)

    def get_followers(
        self, user_id: str, *, cursor: Optional[str] = None, count: int = 50
    ) -> dict:
        """Fetch followers for a user."""
        url = f"https://i.instagram.com/api/v1/friendships/{user_id}/followers/"
        params: Dict[str, Any] = {"count": str(count)}
        if cursor:
            params["max_id"] = cursor
        return self._get(url, params=params)

    def get_following(
        self, user_id: str, *, cursor: Optional[str] = None, count: int = 50
    ) -> dict:
        """Fetch following list for a user."""
        url = f"https://i.instagram.com/api/v1/friendships/{user_id}/following/"
        params: Dict[str, Any] = {"count": str(count)}
        if cursor:
            params["max_id"] = cursor
        return self._get(url, params=params)

    def get_hashtag_info(self, tag: str) -> dict:
        """Fetch hashtag metadata."""
        url = "https://www.instagram.com/api/v1/tags/web_info/"
        return self._get(url, params={"tag_name": tag})

    def get_hashtag_sections(
        self,
        tag: str,
        *,
        tab: str = "recent",
        cursor: Optional[str] = None,
    ) -> dict:
        """Fetch one page of hashtag media sections."""
        url = f"https://www.instagram.com/api/v1/tags/{tag}/sections/"
        form: Dict[str, Any] = {
            "tab": tab,
            "surface": "grid",
            "include_persistent": "0",
        }
        if cursor:
            form["max_id"] = cursor
        return self._post(url, data=form)

    def get_location_info(self, pk: str) -> dict:
        """Fetch location metadata."""
        url = "https://www.instagram.com/api/v1/locations/web_info/"
        return self._get(url, params={"location_id": pk})

    def get_location_sections(
        self,
        pk: str,
        *,
        tab: str = "recent",
        cursor: Optional[str] = None,
    ) -> dict:
        """Fetch one page of location media sections."""
        url = f"https://www.instagram.com/api/v1/locations/{pk}/sections/"
        form: Dict[str, Any] = {
            "tab": tab,
            "surface": "grid",
            "include_persistent": "0",
        }
        if cursor:
            form["max_id"] = cursor
        return self._post(url, data=form)

    def get_explore_grid(self, *, cursor: Optional[str] = None) -> dict:
        """Fetch explore grid page."""
        url = "https://www.instagram.com/api/v1/discover/web/explore_grid/"
        params: Dict[str, str] = {"is_prefetch": "false"}
        if cursor:
            params["max_id"] = cursor
        return self._get(url, params=params)

    def get_stories(self, user_ids: List[str]) -> dict:
        """Fetch active stories for given user IDs."""
        url = "https://www.instagram.com/api/v1/feed/reels_media/"
        return self._post(url, data={"reel_ids": user_ids})

    def get_highlights_tray(self, user_id: str) -> dict:
        """Fetch the highlights tray for a user."""
        url = f"https://www.instagram.com/api/v1/highlights/{user_id}/highlights_tray/"
        return self._get(url)

    def get_highlight_items(self, highlight_pk: str) -> dict:
        """Fetch items for a single highlight reel."""
        url = "https://www.instagram.com/api/v1/feed/reels_media/"
        return self._post(url, data={"reel_ids": [f"highlight:{highlight_pk}"]})

    def get_notifications(self, *, cursor: Optional[str] = None) -> dict:
        """Fetch the activity/notifications inbox."""
        url = "https://www.instagram.com/api/v1/news/inbox/"
        params: Optional[Dict[str, str]] = None
        if cursor:
            params = {"cursor": cursor}
        return self._get(url, params=params)

    def search(self, query: str) -> dict:
        """Run a top-search query."""
        url = "https://www.instagram.com/api/v1/fbsearch/topsearch_flat/"
        params = {
            "query": query,
            "context": "blended",
            "search_surface": "web_top_search",
        }
        return self._get(url, params=params)

    def friendship_status(self, user_id: str) -> dict:
        """Check friendship status with a user."""
        url = f"https://i.instagram.com/api/v1/friendships/show/{user_id}/"
        return self._get(url)

    # ------------------------------------------------------------------
    # Write endpoints
    # ------------------------------------------------------------------

    def follow(self, user_id: str) -> dict:
        """Follow a user (write operation)."""
        url = f"https://www.instagram.com/api/v1/friendships/create/{user_id}/"
        return self._post(url, write=True)

    def unfollow(self, user_id: str) -> dict:
        """Unfollow a user (write operation)."""
        url = f"https://www.instagram.com/api/v1/friendships/destroy/{user_id}/"
        return self._post(url, write=True)

    def send_message(self, user_id: str, text: str) -> dict:
        """Send a direct message (write operation)."""
        url = "https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/"
        form = {
            "recipient_users": f"[[{user_id}]]",
            "action": "send_item",
            "text": text,
        }
        return self._post(url, data=form, write=True)


__all__ = ["WebAPI"]
