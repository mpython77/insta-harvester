"""
CommentScraper — pull comments and replies from a post or reel.

Pure API path. Comments are paginated via ``min_id`` cursors; this
scraper resolves pagination internally and returns one consolidated
:class:`CommentsPage`. Replies are fetched per-comment (only when
:attr:`include_replies` is True and a comment has ``reply_count > 0``)
to keep the network footprint proportional to what the caller asked
for.

Replaces legacy ``comment_scraper.CommentScraper`` (~700 LOC, mixed
DOM-scrolling and API-mocking) with ~250 LOC of explicit API logic.
DOM scrolling is intentionally not part of v3 — it produced ordering
inconsistencies and never recovered the engagement counts that the
API exposes for free.
"""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Optional, Sequence, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.selectors import CommentSelectors
from instaharvest._v3.core.exceptions import (
    NetworkError,
    ParseError,
)
from instaharvest._v3.core.models import (
    Comment,
    CommentAuthor,
    CommentsPage,
    Media,
)
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._parsing import extract_shortcode


_INFO_URL = "https://i.instagram.com/api/v1/media/{shortcode}/info/"
_COMMENTS_URL = "https://i.instagram.com/api/v1/media/{media_id}/comments/"
_REPLIES_URL = (
    "https://i.instagram.com/api/v1/media/{media_id}/comments/{comment_id}/child_comments/"
)

_API_HEADERS = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

# Instagram's comments endpoint refuses unbounded pagination. We cap our
# walk well below their internal soft-limits so a buggy caller cannot
# silently DOS themselves on a single popular post.
_MAX_PAGES = 200
_REPLIES_PER_COMMENT_CAP = 1_000


class CommentScraper:
    """Scrape comments (and optionally replies) for a media item.

    Construct via :attr:`InstaHarvest.comments`. Direct instantiation is
    supported for testing.
    """

    def __init__(
        self,
        *,
        http: HttpClient,
        logger: Logger,
        rate_limit: RateLimitConfig,
        selectors: CommentSelectors,
    ) -> None:
        self._http = http
        self._logger = logger
        self._rate_limit = rate_limit
        self._selectors = selectors  # currently unused; kept for parity

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scrape(
        self,
        media_or_shortcode: "str | Media",
        *,
        max_comments: Optional[int] = None,
        include_replies: bool = True,
    ) -> CommentsPage:
        """Return up to ``max_comments`` comments for the given media.

        ``media_or_shortcode`` may be:

          * a :class:`Media` previously returned by ``MediaScraper`` —
            we use its ``shortcode`` directly,
          * a shortcode string,
          * a full instagram.com URL.

        Args:
            max_comments: Hard cap. ``None`` means "fetch every page
                Instagram returns (up to the safety cap of
                ``_MAX_PAGES`` × per-page size)".
            include_replies: When True (default) we make one extra call
                per comment that has replies, to populate
                :attr:`Comment.replies`.

        Raises:
            NetworkError: HTTP layer kept failing after retries.
            ParseError: response was reachable but malformed.
        """
        shortcode = self._resolve_shortcode(media_or_shortcode)
        if max_comments is not None and max_comments < 0:
            raise ValueError("max_comments must be >= 0")

        media_id = self._lookup_media_id(media_or_shortcode, shortcode)
        self._logger.info(
            "comments scrape start",
            shortcode=shortcode,
            media_id=media_id,
            max_comments=max_comments,
            include_replies=include_replies,
        )

        comments, has_more, cursor = self._fetch_top_level(
            media_id=media_id,
            max_comments=max_comments,
        )

        if include_replies:
            comments = self._populate_replies(media_id, comments)

        page = CommentsPage(
            media_shortcode=shortcode,
            comments=tuple(comments),
            total_returned=len(comments),
            has_more=has_more,
            next_cursor=cursor,
        )
        self._logger.info(
            "comments scrape ok",
            shortcode=shortcode,
            count=page.total_returned,
            has_more=page.has_more,
        )
        return page

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_shortcode(media_or_shortcode: "str | Media") -> str:
        if isinstance(media_or_shortcode, Media):
            return media_or_shortcode.shortcode
        if isinstance(media_or_shortcode, str):
            return extract_shortcode(media_or_shortcode)
        raise TypeError(
            "expected Media, shortcode, or URL; got "
            f"{type(media_or_shortcode).__name__}"
        )

    def _lookup_media_id(
        self,
        media_or_shortcode: "str | Media",
        shortcode: str,
    ) -> str:
        """Resolve the numeric ``media_id`` Instagram uses for comments.

        If the caller passed a :class:`Media` whose owner has a known
        user id we still need a media_id, not a user id — Instagram
        keeps the two distinct. We always do one ``/media/<code>/info``
        call to fetch it. (Future optimisation: thread media_id through
        Media itself; out of scope for this PR.)
        """
        url = _INFO_URL.format(shortcode=shortcode)
        try:
            resp = self._http.get(url, headers=_API_HEADERS)
        except NetworkError:
            raise
        if resp.status_code >= 400:
            raise NetworkError(
                f"media info lookup failed with status {resp.status_code}",
                url=url,
            )
        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"media info returned non-json for {shortcode!r}",
                source="comments.lookup",
            ) from exc

        items = payload.get("items") if isinstance(payload, Mapping) else None
        if not (isinstance(items, list) and items and isinstance(items[0], Mapping)):
            raise ParseError(
                f"media info has no items for {shortcode!r}",
                source="comments.lookup",
            )
        first = items[0]
        media_id = first.get("pk") or first.get("id")
        if not media_id:
            raise ParseError(
                f"media info has no pk/id for {shortcode!r}",
                source="comments.lookup",
            )
        return str(media_id)

    def _fetch_top_level(
        self,
        *,
        media_id: str,
        max_comments: Optional[int],
    ) -> Tuple[List[Comment], bool, Optional[str]]:
        url = _COMMENTS_URL.format(media_id=media_id)
        collected: List[Comment] = []
        cursor: Optional[str] = None
        has_more = False

        for page_index in range(_MAX_PAGES):
            params: dict = {}
            if cursor:
                params["min_id"] = cursor

            try:
                resp = self._http.get(url, params=params, headers=_API_HEADERS)
            except NetworkError:
                raise
            if resp.status_code >= 400:
                self._logger.warning(
                    "comments page non-2xx",
                    media_id=media_id,
                    page=page_index,
                    status=resp.status_code,
                )
                # Partial results are useful; surface them with has_more=True
                # so the caller can inspect ``next_cursor`` and retry.
                return collected, True, cursor

            try:
                payload = resp.json()
            except (ValueError, json.JSONDecodeError) as exc:
                raise ParseError(
                    f"comments page returned non-json (page={page_index})",
                    source="comments.page",
                ) from exc

            page_comments, next_cursor = _parse_top_level_page(payload)
            collected.extend(page_comments)

            if max_comments is not None and len(collected) >= max_comments:
                collected = collected[:max_comments]
                # ``has_more`` is True if Instagram has more, regardless
                # of whether the cap clipped us.
                has_more = bool(next_cursor) or len(page_comments) > 0
                cursor = next_cursor
                break

            if not next_cursor:
                break

            cursor = next_cursor
        else:
            # Loop exhausted the safety cap without Instagram saying "done".
            self._logger.warning(
                "comments pagination cap hit",
                media_id=media_id,
                pages=_MAX_PAGES,
            )
            has_more = True

        return collected, has_more, cursor

    def _populate_replies(
        self,
        media_id: str,
        comments: Sequence[Comment],
    ) -> List[Comment]:
        out: List[Comment] = []
        for comment in comments:
            if comment.reply_count <= 0:
                out.append(comment)
                continue
            try:
                replies = self._fetch_replies(media_id, comment)
            except NetworkError as exc:
                # Reply fetching is best-effort; log and keep the parent.
                self._logger.warning(
                    "replies fetch failed",
                    comment_id=comment.id,
                    error=str(exc),
                )
                out.append(comment)
                continue
            out.append(comment.model_copy(update={"replies": tuple(replies)}))
        return out

    def _fetch_replies(self, media_id: str, parent: Comment) -> List[Comment]:
        url = _REPLIES_URL.format(media_id=media_id, comment_id=parent.id)
        replies: List[Comment] = []
        cursor: Optional[str] = None

        for _ in range(_MAX_PAGES):
            params: dict = {}
            if cursor:
                params["min_id"] = cursor
            resp = self._http.get(url, params=params, headers=_API_HEADERS)
            if resp.status_code >= 400:
                break
            try:
                payload = resp.json()
            except (ValueError, json.JSONDecodeError):
                break

            page_replies, next_cursor = _parse_replies_page(payload, parent_id=parent.id)
            replies.extend(page_replies)

            if len(replies) >= _REPLIES_PER_COMMENT_CAP:
                replies = replies[:_REPLIES_PER_COMMENT_CAP]
                break
            if not next_cursor:
                break
            cursor = next_cursor

        return replies


# ---------------------------------------------------------------------------
# Parsers (pure)
# ---------------------------------------------------------------------------


def _parse_top_level_page(
    payload: Mapping[str, Any],
) -> Tuple[List[Comment], Optional[str]]:
    items = payload.get("comments") if isinstance(payload, Mapping) else None
    if items is None and isinstance(payload, Mapping):
        items = payload.get("items")
    out: List[Comment] = []
    if isinstance(items, list):
        for raw in items:
            comment = _comment_from_api(raw, parent_id=None)
            if comment is not None:
                out.append(comment)
    next_cursor = None
    if isinstance(payload, Mapping):
        nm = payload.get("next_min_id") or payload.get("next_max_id")
        if isinstance(nm, str) and nm:
            next_cursor = nm
        elif payload.get("has_more_comments") and items:
            # Some payload variants put the cursor on the last comment.
            last = items[-1]
            if isinstance(last, Mapping) and last.get("pk"):
                next_cursor = str(last["pk"])
    return out, next_cursor


def _parse_replies_page(
    payload: Mapping[str, Any],
    *,
    parent_id: str,
) -> Tuple[List[Comment], Optional[str]]:
    items = payload.get("child_comments") if isinstance(payload, Mapping) else None
    if items is None and isinstance(payload, Mapping):
        items = payload.get("comments") or payload.get("items")
    out: List[Comment] = []
    if isinstance(items, list):
        for raw in items:
            comment = _comment_from_api(raw, parent_id=parent_id)
            if comment is not None:
                out.append(comment)
    next_cursor = None
    if isinstance(payload, Mapping):
        nm = payload.get("next_min_id") or payload.get("next_max_id")
        if isinstance(nm, str) and nm:
            next_cursor = nm
    return out, next_cursor


def _comment_from_api(
    raw: Any,
    *,
    parent_id: Optional[str],
) -> Optional[Comment]:
    if not isinstance(raw, Mapping):
        return None
    pk = raw.get("pk") or raw.get("id")
    if pk is None:
        return None
    user = raw.get("user") or {}
    if not isinstance(user, Mapping):
        return None
    username = user.get("username")
    if not isinstance(username, str) or not username:
        return None
    try:
        return Comment(
            id=str(pk),
            text=str(raw.get("text") or ""),
            author=CommentAuthor(
                username=username,
                user_id=str(user["pk"]) if user.get("pk") is not None else None,
                full_name=user.get("full_name") or None,
                is_verified=bool(user.get("is_verified", False)),
                profile_pic_url=user.get("profile_pic_url") or None,
            ),
            created_at=raw.get("created_at") or raw.get("created_at_utc") or 0,
            like_count=int(raw.get("comment_like_count") or raw.get("like_count") or 0),
            reply_count=int(raw.get("child_comment_count") or raw.get("reply_count") or 0),
            parent_id=parent_id,
        )
    except (TypeError, ValueError):
        return None


__all__ = ["CommentScraper"]
