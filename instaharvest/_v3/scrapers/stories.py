"""
StoryScraper -- fetch active Instagram stories.

Uses the private API endpoint ``/api/v1/feed/reels_media/`` to load
story slides for one or more user IDs. Returns a :class:`StoryFeed`
containing parsed :class:`StorySlide` models.

Replaces the legacy DOM-scraping approach with direct API calls.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.core.models import StoryFeed, StorySlide
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._feed import API_HEADERS


_REELS_MEDIA_URL = "https://www.instagram.com/api/v1/feed/reels_media/"


class StoryScraper:
    """Fetch active stories for given user IDs.

    Construct via :attr:`InstaHarvest.stories`. Direct instantiation
    is supported for tests.
    """

    def __init__(
        self,
        *,
        http: HttpClient,
        logger: Logger,
        rate_limit: RateLimitConfig,
    ) -> None:
        self._http = http
        self._logger = logger
        # rate_limit config is stored for future use; enforcement is not
        # yet implemented in v3 scrapers.
        self._rate_limit = rate_limit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_stories(self, user_ids: List[str]) -> StoryFeed:
        """Fetch active stories for given user IDs.

        Uses POST to the reels_media endpoint with body
        ``{"reel_ids": user_ids}``.

        Returns StoryFeed with slides from all requested users.

        Raises:
            NetworkError: HTTP layer returned a non-2xx status.
            ParseError: Response was reachable but malformed.
        """
        self._logger.info(
            "stories.get_stories start",
            user_ids=user_ids,
        )

        try:
            resp = self._http.post(
                _REELS_MEDIA_URL,
                data={"reel_ids": user_ids},
                headers=API_HEADERS,
            )
        except NetworkError:
            raise

        if resp.status_code >= 400:
            raise NetworkError(
                f"stories request returned {resp.status_code}",
                url=_REELS_MEDIA_URL,
            )

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                "stories response non-json",
                source="stories.get_stories",
            ) from exc

        slides = _parse_stories_response(payload, self._logger)

        # Determine user info from first slide or from user_ids list
        user_id = user_ids[0] if user_ids else ""
        username = ""
        if slides:
            user_id = slides[0].user_id
            username = slides[0].username

        feed = StoryFeed(
            user_id=user_id or "unknown",
            username=username or "unknown",
            slides=tuple(slides),
            total_returned=len(slides),
        )

        self._logger.info(
            "stories.get_stories ok",
            user_id=feed.user_id,
            count=feed.total_returned,
        )
        return feed


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _parse_stories_response(
    payload: Any,
    logger: Logger,
) -> List[StorySlide]:
    """Parse the reels_media response into StorySlide models.

    Instagram returns either:
      - {"reels": {"USER_ID": {"items": [...]}}}
      - {"reels_media": [{"items": [...], "user": {...}}]}
    """
    if not isinstance(payload, Mapping):
        return []

    slides: List[StorySlide] = []

    # Format 1: {"reels": {"USER_ID": {"items": [...], "user": {...}}}}
    reels = payload.get("reels")
    if isinstance(reels, Mapping):
        for reel_user_id, reel_data in reels.items():
            if not isinstance(reel_data, Mapping):
                continue
            user_info = reel_data.get("user") or {}
            username = _extract_username(user_info)
            items = reel_data.get("items") or []
            if isinstance(items, list):
                for item in items:
                    slide = _item_to_story_slide(
                        item, str(reel_user_id), username, logger
                    )
                    if slide is not None:
                        slides.append(slide)
        return slides

    # Format 2: {"reels_media": [{"items": [...], "user": {...}}]}
    reels_media = payload.get("reels_media")
    if isinstance(reels_media, list):
        for reel in reels_media:
            if not isinstance(reel, Mapping):
                continue
            user_info = reel.get("user") or {}
            user_id = str(user_info.get("pk") or user_info.get("id") or "")
            username = _extract_username(user_info)
            items = reel.get("items") or []
            if isinstance(items, list):
                for item in items:
                    slide = _item_to_story_slide(item, user_id, username, logger)
                    if slide is not None:
                        slides.append(slide)

    return slides


def _item_to_story_slide(
    item: Any,
    user_id: str,
    username: str,
    logger: Logger,
) -> Optional[StorySlide]:
    """Convert a single story item dict to a StorySlide model."""
    if not isinstance(item, Mapping):
        return None

    try:
        item_id = str(item.get("id") or "")
        if not item_id:
            return None

        taken_at = item.get("taken_at", 0)
        expiring_at = item.get("expiring_at", 0)

        # media_type: 1=image, 2=video
        raw_media_type = item.get("media_type", 1)
        media_type = "video" if raw_media_type == 2 else "image"

        # Image URL from image_versions2.candidates[0].url
        image_url = _extract_image_url(item)

        # Video URL from video_versions[0].url
        video_url = _extract_video_url(item) if media_type == "video" else None

        # Video duration (only for video items)
        video_duration: Optional[float] = None
        if media_type == "video":
            raw_duration = item.get("video_duration")
            if raw_duration is not None:
                dur = float(raw_duration)
                video_duration = dur if dur > 0.0 else None

        width = int(item.get("original_width") or 0)
        height = int(item.get("original_height") or 0)
        has_audio = bool(item.get("has_audio", False))

        # Extract mentions
        mentions = _extract_mentions(item)

        # Extract link stickers
        link_stickers = _extract_link_stickers(item)

        # Determine if from reel mention
        is_reel_mention = bool(item.get("is_reel_mention", False))

        # Use user info from item if present
        item_user = item.get("user")
        if isinstance(item_user, Mapping):
            user_id = str(item_user.get("pk") or item_user.get("id") or user_id)
            username = _extract_username(item_user) or username

        return StorySlide(
            id=item_id,
            user_id=user_id or "unknown",
            username=username or "unknown",
            taken_at=taken_at,
            expiring_at=expiring_at,
            media_type=media_type,
            image_url=image_url,
            video_url=video_url,
            video_duration=video_duration,
            width=width,
            height=height,
            has_audio=has_audio,
            mentions=tuple(mentions),
            link_stickers=tuple(link_stickers),
            is_reel_mention=is_reel_mention,
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "stories.parse skipped item",
            item_id=str(item.get("id", "?")),
            error=str(exc),
        )
        return None


def _extract_username(user_info: Any) -> str:
    """Get username from a user info dict."""
    if isinstance(user_info, Mapping):
        return str(user_info.get("username") or "")
    return ""


def _extract_image_url(item: Mapping[str, Any]) -> Optional[str]:
    """Extract best image URL from image_versions2."""
    versions = item.get("image_versions2")
    if not isinstance(versions, Mapping):
        return None
    candidates = versions.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    first = candidates[0]
    if isinstance(first, Mapping):
        url = first.get("url")
        if isinstance(url, str) and url:
            return url
    return None


def _extract_video_url(item: Mapping[str, Any]) -> Optional[str]:
    """Extract first video URL from video_versions."""
    versions = item.get("video_versions")
    if not isinstance(versions, list) or not versions:
        return None
    first = versions[0]
    if isinstance(first, Mapping):
        url = first.get("url")
        if isinstance(url, str) and url:
            return url
    return None


def _extract_mentions(item: Mapping[str, Any]) -> List[str]:
    """Extract mentions from reel_mentions or story_bloks_stickers."""
    mentions: List[str] = []

    # From reel_mentions
    reel_mentions = item.get("reel_mentions")
    if isinstance(reel_mentions, list):
        for mention in reel_mentions:
            if isinstance(mention, Mapping):
                user = mention.get("user")
                if isinstance(user, Mapping):
                    uname = user.get("username")
                    if isinstance(uname, str) and uname:
                        mentions.append(uname)

    # From story_bloks_stickers (mention stickers)
    stickers = item.get("story_bloks_stickers")
    if isinstance(stickers, list):
        for sticker in stickers:
            if isinstance(sticker, Mapping):
                bloks_data = sticker.get("bloks_sticker")
                if isinstance(bloks_data, Mapping):
                    sticker_data = bloks_data.get("sticker_data")
                    if isinstance(sticker_data, Mapping):
                        ig_mention = sticker_data.get("ig_mention")
                        if isinstance(ig_mention, Mapping):
                            uname = ig_mention.get("username")
                            if isinstance(uname, str) and uname:
                                mentions.append(uname)

    return mentions


def _extract_link_stickers(item: Mapping[str, Any]) -> List[str]:
    """Extract URLs from story_link_stickers."""
    links: List[str] = []

    link_stickers = item.get("story_link_stickers")
    if isinstance(link_stickers, list):
        for sticker in link_stickers:
            if isinstance(sticker, Mapping):
                story_link = sticker.get("story_link")
                if isinstance(story_link, Mapping):
                    url = story_link.get("url")
                    if isinstance(url, str) and url:
                        links.append(url)

    return links


__all__ = ["StoryScraper"]
