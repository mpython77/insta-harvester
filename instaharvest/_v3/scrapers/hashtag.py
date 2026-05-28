"""
HashtagScraper — read hashtag metadata and media feeds.

Two surfaces, separated as separate methods because they cost
different things on the wire:

  * :meth:`lookup` — single GET to ``tags/web_info``. Cheap,
    metadata only.
  * :meth:`recent` / :meth:`top` — paginated ``tags/sections``.
    Iterates pages until ``max_items`` or natural end. Reuses
    :func:`paginate_feed` so behaviour around partial results,
    cursor handling, and safety caps is shared with location and
    explore.

Replaces legacy ``hashtag_scraper.HashtagScraper`` (DOM-scrolling,
~280 LOC of brittle infinite-scroll heuristics) with ~190 LOC of
explicit API logic.
"""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Optional, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.exceptions import (
    NetworkError,
    ParseError,
    ProfileNotFoundError,  # used as the base for HashtagNotFoundError
)
from instaharvest._v3.core.models import FeedSource, Hashtag, MediaFeed
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._feed import API_HEADERS, paginate_feed


_INFO_URL = "https://www.instagram.com/api/v1/tags/web_info/?tag_name={tag}"
_SECTIONS_URL = "https://www.instagram.com/api/v1/tags/{tag}/sections/"

# Hashtag names use the same character class as usernames + a few
# extras (Instagram allows underscores and full-width Unicode in some
# locales). We are deliberately permissive — Instagram is the source
# of truth for what counts as a valid tag.
_HASHTAG_MAX_LEN = 100


class HashtagNotFoundError(ProfileNotFoundError):
    """The requested hashtag has no metadata on Instagram.

    Subclasses :class:`ProfileNotFoundError` so callers can catch
    "this thing doesn't exist on Instagram" generically while still
    being able to dispatch on the specific subclass.
    """

    def __init__(self, tag: str):
        Exception.__init__(self, f"Hashtag not found: #{tag}")
        self.username = tag        # legacy compat with ProfileNotFoundError
        self.tag = tag


class HashtagScraper:
    """Read hashtag metadata and media feeds.

    Construct via :attr:`InstaHarvest.hashtag`. Direct instantiation
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
        self._rate_limit = rate_limit

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def lookup(self, tag: str) -> Hashtag:
        """Return :class:`Hashtag` metadata (no media feed).

        Raises:
            HashtagNotFoundError: tag has no presence on Instagram.
            NetworkError: HTTP layer kept failing after retries.
            ParseError: response was reachable but malformed.
        """
        tag = _normalise_tag(tag)
        url = _INFO_URL.format(tag=tag)
        try:
            resp = self._http.get(url, headers=API_HEADERS)
        except NetworkError:
            raise
        if resp.status_code == 404:
            raise HashtagNotFoundError(tag)
        if resp.status_code >= 400:
            raise NetworkError(
                f"hashtag lookup returned {resp.status_code}",
                url=url,
            )
        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"hashtag lookup non-json for {tag!r}",
                source="hashtag.lookup",
            ) from exc

        return _hashtag_from_api(tag, payload)

    def recent(
        self,
        tag: str,
        *,
        max_items: Optional[int] = None,
    ) -> MediaFeed:
        """Recent media for ``#tag``."""
        return self._sections_feed(
            tag=tag, source=FeedSource.HASHTAG_RECENT, tab="recent",
            max_items=max_items,
        )

    def top(
        self,
        tag: str,
        *,
        max_items: Optional[int] = None,
    ) -> MediaFeed:
        """Top (Instagram-curated) media for ``#tag``."""
        return self._sections_feed(
            tag=tag, source=FeedSource.HASHTAG_TOP, tab="top",
            max_items=max_items,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sections_feed(
        self,
        *,
        tag: str,
        source: FeedSource,
        tab: str,
        max_items: Optional[int],
    ) -> MediaFeed:
        tag = _normalise_tag(tag)
        url = _SECTIONS_URL.format(tag=tag)

        def fetcher(cursor: Optional[str]):
            body = {"tab": tab, "surface": "grid", "include_persistent": "false"}
            if cursor:
                body["max_id"] = cursor
            return self._http.post(url, data=body, headers=API_HEADERS)

        return paginate_feed(
            http=self._http,
            logger=self._logger,
            source=source,
            source_id=tag,
            fetcher=fetcher,
            parser=_parse_sections_page,
            max_items=max_items,
            log_prefix=f"hashtag.{tab}",
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _normalise_tag(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"tag must be str, got {type(raw).__name__}")
    cleaned = raw.strip().lstrip("#")
    if not cleaned:
        raise ValueError("empty hashtag")
    if len(cleaned) > _HASHTAG_MAX_LEN:
        raise ValueError(
            f"hashtag too long ({len(cleaned)} chars; max {_HASHTAG_MAX_LEN})"
        )
    if any(ch.isspace() for ch in cleaned):
        raise ValueError(f"hashtag may not contain whitespace: {raw!r}")
    return cleaned


def _hashtag_from_api(tag: str, payload: Any) -> Hashtag:
    """Build a :class:`Hashtag` from the ``tags/web_info`` response."""
    data = (
        payload.get("data") if isinstance(payload, Mapping) else None
    ) or payload
    if not isinstance(data, Mapping):
        return Hashtag(name=tag)
    return Hashtag(
        name=str(data.get("name") or tag),
        media_count=int(data.get("media_count") or 0),
        formatted_media_count=data.get("formatted_media_count") or None,
        profile_pic_url=data.get("profile_pic_url") or None,
        is_top_media_only=bool(data.get("is_top_media_only", False)),
        allow_following=bool(data.get("allow_following", True)),
        is_following=bool(data.get("following", False)),
    )


def _parse_sections_page(
    payload: Mapping[str, Any],
) -> Tuple[List[Mapping[str, Any]], Optional[str]]:
    """Pull media dicts and the next cursor from a sections payload."""
    if not isinstance(payload, Mapping):
        return [], None

    sections = payload.get("sections") or []
    out: List[Mapping[str, Any]] = []
    if isinstance(sections, list):
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            layout = section.get("layout_content") or {}
            if not isinstance(layout, Mapping):
                continue
            medias = layout.get("medias") or layout.get("fill_items") or []
            if not isinstance(medias, list):
                continue
            for entry in medias:
                if isinstance(entry, Mapping):
                    out.append(entry)

    next_cursor: Optional[str] = None
    nm = payload.get("next_max_id")
    if isinstance(nm, str) and nm:
        next_cursor = nm
    elif isinstance(nm, int):
        next_cursor = str(nm)
    return out, next_cursor


__all__ = ["HashtagScraper", "HashtagNotFoundError"]
