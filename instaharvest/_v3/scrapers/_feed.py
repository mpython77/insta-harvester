"""
Shared infrastructure for paginated media feeds.

Hashtag, location, and explore endpoints all return the same
"paginated grid of media" shape: an outer envelope with ``sections``
or ``items`` and a ``next_max_id`` cursor, where each item is a
standard Instagram media dict that :func:`_media_from_api` already
knows how to parse.

This module exposes :func:`paginate_feed`, which any scraper can call
with a callable that returns one page at a time. It handles:

  * the safety cap on pages,
  * partial-result behaviour on mid-walk 5xx,
  * ``max_items`` clipping with correct ``has_more`` semantics,
  * the standard set of ``MediaFeed`` fields.

Scrapers do NOT call :func:`paginate_feed` directly. They wrap it in
their own ``recent()`` / ``top()`` etc. methods so the public API
stays explicit about which surface is being read.
"""

from __future__ import annotations

import json
from typing import Any, Callable, List, Mapping, Optional, Tuple

from instaharvest._v3.core.exceptions import NetworkError, ParseError
from instaharvest._v3.core.models import FeedSource, Media, MediaFeed
from instaharvest._v3.core.protocols import HttpClient, HttpResponse, Logger
from instaharvest._v3.scrapers.media import _media_from_api


# Safety ceiling: 200 pages × ~33 media/page ≈ 6.6k items max walk.
# Hashtag/location feeds in the wild can be far longer than that, so
# callers that genuinely need to paginate further must use
# ``next_cursor`` from the returned :class:`MediaFeed` to resume.
MAX_PAGES = 200

API_HEADERS = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}


# A "page fetcher" takes a cursor and returns the raw response. The
# scraper wires the URL + method (GET vs POST) inside this callable;
# the helper stays generic.
PageFetcher = Callable[[Optional[str]], HttpResponse]

# A "page parser" pulls (list-of-media-dicts, next-cursor) out of a
# decoded JSON payload. Endpoints differ in whether they nest media
# under ``sections[*].layout_content.medias[*].media`` or under
# ``items`` directly; this lets each scraper own that detail.
PageParser = Callable[[Mapping[str, Any]], Tuple[List[Mapping[str, Any]], Optional[str]]]


def paginate_feed(
    *,
    http: HttpClient,
    logger: Logger,
    source: FeedSource,
    source_id: str,
    fetcher: PageFetcher,
    parser: PageParser,
    max_items: Optional[int],
    log_prefix: str = "feed",
) -> MediaFeed:
    """Walk a paginated feed endpoint and assemble a :class:`MediaFeed`.

    Args:
        http: Unused at this layer — :class:`HttpClient` only matters
            inside ``fetcher``. Kept in the signature so subclasses
            could inject retries or instrumentation around the call.
        logger: Structured logger.
        source: Which surface this feed represents
            (e.g. :attr:`FeedSource.HASHTAG_RECENT`).
        source_id: Tag name, location pk, or ``"explore"`` etc.
        fetcher: Returns one page given an optional ``max_id`` cursor.
        parser: Pulls ``(media_dicts, next_cursor)`` out of one page.
        max_items: Hard cap; ``None`` means "walk every page Instagram
            returns up to ``MAX_PAGES``".
        log_prefix: Tag included in every log line for readability.

    Raises:
        NetworkError: HTTP layer kept failing after retries.
        ParseError: response was reachable but malformed.
    """
    if max_items is not None and max_items < 0:
        raise ValueError("max_items must be >= 0")

    logger.info(
        f"{log_prefix} start",
        source=source.value,
        source_id=source_id,
        max_items=max_items,
    )

    collected: List[Media] = []
    cursor: Optional[str] = None
    has_more = False

    for page_index in range(MAX_PAGES):
        try:
            resp = fetcher(cursor)
        except NetworkError:
            raise

        status = resp.status_code
        if status >= 400:
            logger.warning(
                f"{log_prefix} page non-2xx",
                source=source.value,
                source_id=source_id,
                page=page_index,
                status=status,
            )
            return MediaFeed(
                source=source,
                source_id=source_id,
                media=tuple(collected),
                total_returned=len(collected),
                has_more=True,
                next_cursor=cursor,
            )

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"{log_prefix} page returned non-json (page={page_index})",
                source=log_prefix,
            ) from exc

        try:
            raw_items, next_cursor = parser(payload)
        except (KeyError, TypeError, ValueError) as exc:
            raise ParseError(
                f"{log_prefix} page parse error (page={page_index})",
                source=log_prefix,
            ) from exc

        for item in raw_items:
            media_dict, shortcode = _unwrap_media(item)
            if shortcode is None or media_dict is None:
                continue
            try:
                collected.append(_media_from_api(shortcode, media_dict, source="api"))
            except (KeyError, TypeError, ValueError) as exc:
                # Skip individual malformed items rather than failing
                # the whole feed; log so operators can spot drift.
                logger.debug(
                    f"{log_prefix} skipped item",
                    shortcode=shortcode,
                    error=str(exc),
                )

        cursor = next_cursor

        if max_items is not None and len(collected) >= max_items:
            collected = collected[:max_items]
            has_more = bool(next_cursor) or len(raw_items) > 0
            break

        if not next_cursor:
            break
    else:
        logger.warning(
            f"{log_prefix} pagination cap hit",
            source=source.value,
            source_id=source_id,
            pages=MAX_PAGES,
        )
        has_more = True

    feed = MediaFeed(
        source=source,
        source_id=source_id,
        media=tuple(collected),
        total_returned=len(collected),
        has_more=has_more,
        next_cursor=cursor,
    )
    logger.info(
        f"{log_prefix} ok",
        source=source.value,
        source_id=source_id,
        count=feed.total_returned,
        has_more=feed.has_more,
    )
    return feed


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _unwrap_media(item: Mapping[str, Any]):
    """Find the actual media dict and its shortcode.

    Different endpoints stash the media at different nesting levels:

      * ``{"code": "...", "media_type": ...}``                  — flat
      * ``{"media": {"code": "...", "media_type": ...}}``       — wrapped
      * ``{"media": {"media": {...}}}``                          — doubly wrapped (rare)

    Returns ``(media_dict, shortcode)`` for whichever level holds the
    shortcode, or ``(None, None)`` if no shortcode is found anywhere.
    Always returns the dict that ``_media_from_api`` should parse — i.e.
    the one with ``media_type``, not the wrapper.
    """
    if not isinstance(item, Mapping):
        return None, None
    sc = item.get("code") or item.get("shortcode")
    if isinstance(sc, str) and sc:
        return item, sc
    nested = item.get("media")
    if isinstance(nested, Mapping):
        return _unwrap_media(nested)
    return None, None


__all__ = ["paginate_feed", "MAX_PAGES", "API_HEADERS"]
