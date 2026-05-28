"""
HighlightScraper -- fetch highlight reels and their slides.

Two endpoints:

  * :meth:`list_highlights` -- list all highlight reels for a user
    via ``/api/v1/highlights/{user_id}/highlights_tray/``.
  * :meth:`get_highlight` -- fetch all slides within one highlight
    reel via ``/api/v1/feed/reels_media/`` (same endpoint as stories).
"""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Optional, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.core.models import Highlight, HighlightSlide, HighlightsList
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._feed import API_HEADERS


_HIGHLIGHTS_TRAY_URL = (
    "https://www.instagram.com/api/v1/highlights/{user_id}/highlights_tray/"
)
_REELS_MEDIA_URL = "https://www.instagram.com/api/v1/feed/reels_media/"


class HighlightScraper:
    """Fetch highlight metadata and slides for a user.

    Construct via :attr:`InstaHarvest.highlights`. Direct instantiation
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

    def list_highlights(self, user_id: str) -> HighlightsList:
        """List all highlight reels for a user.

        Uses GET to the highlights_tray endpoint.

        Raises:
            NetworkError: HTTP layer returned a non-2xx status.
            ParseError: Response was reachable but malformed.
        """
        self._logger.info(
            "highlights.list start",
            user_id=user_id,
        )

        url = _HIGHLIGHTS_TRAY_URL.format(user_id=user_id)
        try:
            resp = self._http.get(url, headers=API_HEADERS)
        except NetworkError:
            raise

        if resp.status_code >= 400:
            raise NetworkError(
                f"highlights tray returned {resp.status_code}",
                url=url,
            )

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                "highlights tray non-json",
                source="highlights.list",
            ) from exc

        highlights = _parse_tray(payload, self._logger)

        result = HighlightsList(
            user_id=user_id,
            highlights=tuple(highlights),
            total_returned=len(highlights),
        )

        self._logger.info(
            "highlights.list ok",
            user_id=user_id,
            count=result.total_returned,
        )
        return result

    def get_highlight(self, highlight_pk: str) -> Tuple[HighlightSlide, ...]:
        """Fetch all slides of a highlight reel.

        Uses POST to the reels_media endpoint. Adds "highlight:" prefix
        to the pk if not already present.

        Raises:
            NetworkError: HTTP layer returned a non-2xx status.
            ParseError: Response was reachable but malformed.
        """
        reel_id = highlight_pk if highlight_pk.startswith("highlight:") else f"highlight:{highlight_pk}"

        self._logger.info(
            "highlights.get start",
            highlight_pk=highlight_pk,
            reel_id=reel_id,
        )

        try:
            resp = self._http.post(
                _REELS_MEDIA_URL,
                data={"reel_ids": [reel_id]},
                headers=API_HEADERS,
            )
        except NetworkError:
            raise

        if resp.status_code >= 400:
            raise NetworkError(
                f"highlight reels_media returned {resp.status_code}",
                url=_REELS_MEDIA_URL,
            )

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                "highlight reels_media non-json",
                source="highlights.get",
            ) from exc

        slides = _parse_highlight_items(payload, highlight_pk, self._logger)

        self._logger.info(
            "highlights.get ok",
            highlight_pk=highlight_pk,
            count=len(slides),
        )
        return tuple(slides)


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _parse_tray(payload: Any, logger: Logger) -> List[Highlight]:
    """Parse the highlights_tray response into Highlight models."""
    if not isinstance(payload, Mapping):
        return []

    tray = payload.get("tray")
    if not isinstance(tray, list):
        return []

    highlights: List[Highlight] = []
    for entry in tray:
        if not isinstance(entry, Mapping):
            continue
        try:
            raw_id = str(entry.get("id") or "")
            # Strip "highlight:" prefix to get the PK
            pk = raw_id.replace("highlight:", "") if raw_id.startswith("highlight:") else raw_id
            if not pk:
                continue

            title = str(entry.get("title") or "Untitled")

            cover_url: Optional[str] = None
            cover_media = entry.get("cover_media")
            if isinstance(cover_media, Mapping):
                cropped = cover_media.get("cropped_image_version")
                if isinstance(cropped, Mapping):
                    cover_url = cropped.get("url")
                if not cover_url:
                    # Fallback to image_versions2
                    versions = cover_media.get("image_versions2")
                    if isinstance(versions, Mapping):
                        candidates = versions.get("candidates")
                        if isinstance(candidates, list) and candidates:
                            first = candidates[0]
                            if isinstance(first, Mapping):
                                cover_url = first.get("url")

            created_at = entry.get("created_at")
            media_count = int(entry.get("media_count") or 0)

            highlights.append(Highlight(
                pk=pk,
                title=title,
                cover_url=cover_url,
                created_at=created_at,
                media_count=media_count,
            ))
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "highlights.parse_tray skipped entry",
                entry_id=str(entry.get("id", "?")),
                error=str(exc),
            )

    return highlights


def _parse_highlight_items(
    payload: Any,
    highlight_pk: str,
    logger: Logger,
) -> List[HighlightSlide]:
    """Parse reels_media response into HighlightSlide models."""
    if not isinstance(payload, Mapping):
        return []

    slides: List[HighlightSlide] = []

    # Format 1: {"reels": {"highlight:PK": {"items": [...], "user": {...}}}}
    reels = payload.get("reels")
    if isinstance(reels, Mapping):
        for reel_id, reel_data in reels.items():
            if not isinstance(reel_data, Mapping):
                continue
            user_info = reel_data.get("user") or {}
            username = _extract_username(user_info)
            user_id = str(user_info.get("pk") or user_info.get("id") or "")
            items = reel_data.get("items") or []
            if isinstance(items, list):
                for item in items:
                    slide = _item_to_highlight_slide(
                        item, user_id, username, highlight_pk, logger
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
                    slide = _item_to_highlight_slide(
                        item, user_id, username, highlight_pk, logger
                    )
                    if slide is not None:
                        slides.append(slide)

    return slides


def _item_to_highlight_slide(
    item: Any,
    user_id: str,
    username: str,
    highlight_pk: str,
    logger: Logger,
) -> Optional[HighlightSlide]:
    """Convert a single item dict to a HighlightSlide model."""
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

        image_url = _extract_image_url(item)
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

        mentions = _extract_mentions(item)
        link_stickers = _extract_link_stickers(item)
        is_reel_mention = bool(item.get("is_reel_mention", False))

        # Use user info from item if present
        item_user = item.get("user")
        if isinstance(item_user, Mapping):
            user_id = str(item_user.get("pk") or item_user.get("id") or user_id)
            username = _extract_username(item_user) or username

        # Strip "highlight:" prefix for the pk field
        clean_pk = highlight_pk.replace("highlight:", "") if highlight_pk.startswith("highlight:") else highlight_pk

        return HighlightSlide(
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
            highlight_pk=clean_pk,
        )
    except (KeyError, TypeError, ValueError) as exc:
        logger.warning(
            "highlights.parse skipped item",
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

    reel_mentions = item.get("reel_mentions")
    if isinstance(reel_mentions, list):
        for mention in reel_mentions:
            if isinstance(mention, Mapping):
                user = mention.get("user")
                if isinstance(user, Mapping):
                    uname = user.get("username")
                    if isinstance(uname, str) and uname:
                        mentions.append(uname)

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


__all__ = ["HighlightScraper"]
