"""
NotificationsScraper -- read the activity/notifications inbox.

Uses ``/api/v1/news/inbox/`` with cursor-based pagination. Each
notification is classified by type and returned in a
:class:`NotificationFeed` model.
"""

from __future__ import annotations

import json
import re
from typing import Any, List, Mapping, Optional

from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.core.models import (
    Notification,
    NotificationFeed,
    NotificationType,
)
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._feed import API_HEADERS


_INBOX_URL = "https://www.instagram.com/api/v1/news/inbox/"

# Maximum pages to prevent infinite pagination loops.
_MAX_PAGES = 50

# Type code to NotificationType mapping.
_TYPE_CODE_MAP = {
    12: NotificationType.LIKE,
    13: NotificationType.LIKE,
    14: NotificationType.COMMENT,
    101: NotificationType.FOLLOW,
    102: NotificationType.MENTION,
    26: NotificationType.COMMENT_LIKE,
    75: NotificationType.FOLLOW_REQUEST,
}

# Text-based classification patterns (fallback when type code is missing).
_TEXT_PATTERNS = [
    (re.compile(r"liked your comment", re.IGNORECASE), NotificationType.COMMENT_LIKE),
    (re.compile(r"liked", re.IGNORECASE), NotificationType.LIKE),
    (re.compile(r"commented", re.IGNORECASE), NotificationType.COMMENT),
    (re.compile(r"started following", re.IGNORECASE), NotificationType.FOLLOW),
    (re.compile(r"mentioned|tagged", re.IGNORECASE), NotificationType.MENTION),
    (re.compile(r"requested", re.IGNORECASE), NotificationType.FOLLOW_REQUEST),
]


class NotificationsScraper:
    """Read the activity/notifications inbox.

    Construct via :attr:`InstaHarvest.notifications`. Direct
    instantiation is supported for tests.
    """

    def __init__(
        self,
        *,
        http: HttpClient,
        logger: Logger,
    ) -> None:
        self._http = http
        self._logger = logger
        # Note: rate_limit config is not accepted here. Enforcement of
        # request delays is not yet implemented in v3 scrapers.

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def feed(self, *, max_items: Optional[int] = 50) -> NotificationFeed:
        """Read the activity/notifications inbox.

        Paginates via cursor until max_items is reached or no more
        pages are available.

        Raises:
            NetworkError: HTTP layer returned a non-2xx status.
            ParseError: Response was reachable but malformed.
        """
        self._logger.info(
            "notifications.feed start",
            max_items=max_items,
        )

        collected: List[Notification] = []
        cursor: Optional[str] = None
        has_more = False

        for page_index in range(_MAX_PAGES):
            params = {}
            if cursor:
                params["cursor"] = cursor

            try:
                resp = self._http.get(
                    _INBOX_URL,
                    params=params if params else None,
                    headers=API_HEADERS,
                )
            except NetworkError:
                raise

            if resp.status_code >= 400:
                raise NetworkError(
                    f"notifications inbox returned {resp.status_code}",
                    url=_INBOX_URL,
                )

            try:
                payload = resp.json()
            except (ValueError, json.JSONDecodeError) as exc:
                raise ParseError(
                    "notifications inbox non-json",
                    source="notifications.feed",
                ) from exc

            page_items = _parse_inbox_page(payload, self._logger)
            collected.extend(page_items)

            # Check if we have enough
            if max_items is not None and len(collected) >= max_items:
                collected = collected[:max_items]
                has_more = True
                break

            # Check for next page
            next_cursor = _extract_cursor(payload)
            more_available = payload.get("more_available", False)

            if not next_cursor or not more_available:
                break

            cursor = next_cursor
        else:
            self._logger.warning(
                "notifications.feed pagination cap hit",
                pages=_MAX_PAGES,
            )
            has_more = True

        result = NotificationFeed(
            notifications=tuple(collected),
            total_returned=len(collected),
            has_more=has_more,
            next_cursor=cursor,
        )

        self._logger.info(
            "notifications.feed ok",
            count=result.total_returned,
            has_more=result.has_more,
        )
        return result


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _parse_inbox_page(
    payload: Any,
    logger: Logger,
) -> List[Notification]:
    """Parse one page of the inbox response."""
    if not isinstance(payload, Mapping):
        return []

    notifications: List[Notification] = []

    # Instagram returns notifications in "stories" and "old_stories"
    for key in ("stories", "old_stories", "new_stories"):
        items = payload.get(key)
        if not isinstance(items, list):
            continue
        for item in items:
            notif = _item_to_notification(item, logger)
            if notif is not None:
                notifications.append(notif)

    return notifications


def _item_to_notification(
    item: Any,
    logger: Logger,
) -> Optional[Notification]:
    """Convert a single notification item to a Notification model."""
    if not isinstance(item, Mapping):
        return None

    try:
        args = item.get("args") or {}
        if not isinstance(args, Mapping):
            args = {}

        # Build notification ID
        notif_id = str(item.get("pk") or item.get("id") or args.get("tuuid") or "")
        if not notif_id:
            return None

        # Get text
        text = str(args.get("text") or "")

        # Get timestamp
        timestamp = args.get("timestamp") or item.get("timestamp") or 0

        # Classify type
        raw_type = item.get("type")
        notification_type = _classify_type(raw_type, text)

        # Extract profile pic
        profile_pic = args.get("profile_image") or args.get("profile_image_url")
        profile_pic_url = str(profile_pic) if profile_pic else None

        # Extract usernames from links
        usernames = _extract_usernames(args)

        # Extract media shortcode
        media_shortcode: Optional[str] = None
        links = args.get("links")
        if isinstance(links, list):
            for link in links:
                if isinstance(link, Mapping):
                    link_type = link.get("type")
                    link_id = link.get("id")
                    if link_type == "media" and isinstance(link_id, str):
                        media_shortcode = link_id
                        break

        # Check if grouped
        is_grouped = bool(args.get("is_grouped", False))
        group_count = int(args.get("group_count") or 0)

        return Notification(
            id=notif_id,
            notification_type=notification_type,
            text=text,
            timestamp=timestamp,
            usernames=tuple(usernames),
            profile_pic_url=profile_pic_url if profile_pic_url else None,
            media_shortcode=media_shortcode,
            is_grouped=is_grouped,
            group_count=group_count,
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "notifications.parse skipped item",
            item_pk=str(item.get("pk", "?")),
            error=str(exc),
        )
        return None


def _classify_type(raw_type: Any, text: str) -> NotificationType:
    """Classify notification type from type code or text content."""
    # Try type code first
    if isinstance(raw_type, int) and raw_type in _TYPE_CODE_MAP:
        return _TYPE_CODE_MAP[raw_type]

    # Fallback to text pattern matching
    for pattern, ntype in _TEXT_PATTERNS:
        if pattern.search(text):
            return ntype

    return NotificationType.OTHER


def _extract_usernames(args: Mapping[str, Any]) -> List[str]:
    """Extract usernames from links[*].id or from inline_follow args."""
    usernames: List[str] = []

    links = args.get("links")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, Mapping):
                link_type = link.get("type")
                link_id = link.get("id")
                if link_type == "user" and isinstance(link_id, str) and link_id:
                    usernames.append(link_id)

    # Also check inline_follow for username
    inline = args.get("inline_follow")
    if isinstance(inline, Mapping):
        user_info = inline.get("user_info")
        if isinstance(user_info, Mapping):
            uname = user_info.get("username")
            if isinstance(uname, str) and uname and uname not in usernames:
                usernames.append(uname)

    return usernames


def _extract_cursor(payload: Mapping[str, Any]) -> Optional[str]:
    """Get the next pagination cursor from the response."""
    cursor = payload.get("next_cursor") or payload.get("cursor")
    if isinstance(cursor, str) and cursor:
        return cursor
    if isinstance(cursor, int):
        return str(cursor)
    return None


__all__ = ["NotificationsScraper"]
