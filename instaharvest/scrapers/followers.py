"""
FollowersScraper — paginated read-only access to followers / following.

Replaces legacy ``followers.py`` (``FollowersCollector``, ~507 LOC)
which scrolled the followers dialog in the DOM and produced order-
dependent, deduplication-prone results. v3 takes the same approach
as :class:`CommentScraper`: API-only, full pagination, single
:class:`FollowList` returned to the caller.

The scraper does not own a browser session — followers/following are
fetched purely through :class:`HttpClient`. Cookies must already be
imported into the client (the facade does this when the browser is
started, but a test can call ``http.import_cookies`` directly).

Design notes:

  * One safety cap (``_MAX_PAGES`` × ~50/page = 10 000 entries) above
    which the scraper stops and reports ``has_more=True`` so a buggy
    caller cannot DOS itself or Instagram on a megafollow account.
  * Mid-walk 5xx returns partial results with ``has_more=True`` and
    a usable ``next_cursor``, mirroring :class:`CommentScraper`.
  * The returned :class:`FollowList`'s :attr:`kind` is one of
    ``"followers"`` or ``"following"`` so users can keep both lists
    in the same data pipeline without losing track.
"""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Optional, Tuple

from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.core.exceptions import (
    NetworkError,
    ParseError,
)
from instaharvest.core.models import (
    FollowEntry,
    FollowList,
    FriendshipStatus,
)
from instaharvest.core.protocols import HttpClient, Logger


_FOLLOWERS_URL = "https://i.instagram.com/api/v1/friendships/{user_id}/followers/"
_FOLLOWING_URL = "https://i.instagram.com/api/v1/friendships/{user_id}/following/"
_FRIENDSHIP_URL = "https://i.instagram.com/api/v1/friendships/show/{user_id}/"

_API_HEADERS = {
    "X-IG-App-ID": "936619743392459",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json",
}

# Instagram's default page size is 25-50 entries; we cap pagination at
# 200 pages to keep the worst case bounded.
_MAX_PAGES = 200
_DEFAULT_PAGE_SIZE = 50


class FollowersScraper:
    """Read followers / following lists and friendship status.

    Construct via :attr:`InstaHarvest.followers`. Direct instantiation
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

    def list_followers(
        self,
        user_id: str,
        *,
        max_users: Optional[int] = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> FollowList:
        """List who follows ``user_id``.

        Args:
            user_id: Numeric Instagram user id (string form).
            max_users: Hard cap on returned users. ``None`` means
                "fetch every page Instagram returns up to the safety
                ceiling".
            page_size: Per-request page size hint sent as
                ``count``. Instagram may ignore this.

        Returns:
            One :class:`FollowList` with ``kind="followers"``.

        Raises:
            NetworkError: HTTP layer kept failing after retries.
            ParseError: response was reachable but malformed.
        """
        return self._paginated(
            url_template=_FOLLOWERS_URL,
            user_id=user_id,
            kind="followers",
            max_users=max_users,
            page_size=page_size,
        )

    def list_following(
        self,
        user_id: str,
        *,
        max_users: Optional[int] = None,
        page_size: int = _DEFAULT_PAGE_SIZE,
    ) -> FollowList:
        """List who ``user_id`` follows.

        Same shape and semantics as :meth:`list_followers`; only the
        endpoint and the returned ``kind`` differ.
        """
        return self._paginated(
            url_template=_FOLLOWING_URL,
            user_id=user_id,
            kind="following",
            max_users=max_users,
            page_size=page_size,
        )

    def friendship_status(self, user_id: str) -> FriendshipStatus:
        """Return the viewer's relationship with ``user_id``.

        Useful as a pre-check before calling
        :meth:`SocialActions.follow` so we can short-circuit on
        ``ALREADY_DONE`` without making the mutation request.
        """
        url = _FRIENDSHIP_URL.format(user_id=user_id)
        try:
            resp = self._http.get(url, headers=_API_HEADERS)
        except NetworkError:
            raise
        if resp.status_code >= 400:
            raise NetworkError(
                f"friendship status returned {resp.status_code}",
                url=url,
            )
        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"friendship status non-json for user_id={user_id}",
                source="followers.friendship",
            ) from exc

        return _friendship_from_api(user_id, payload)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _paginated(
        self,
        *,
        url_template: str,
        user_id: str,
        kind: str,
        max_users: Optional[int],
        page_size: int,
    ) -> FollowList:
        if max_users is not None and max_users < 0:
            raise ValueError("max_users must be >= 0")
        if page_size <= 0:
            raise ValueError("page_size must be > 0")

        url = url_template.format(user_id=user_id)
        self._logger.info(
            "follow list start",
            user_id=user_id,
            kind=kind,
            max_users=max_users,
        )

        collected: List[FollowEntry] = []
        cursor: Optional[str] = None
        has_more = False

        for page_index in range(_MAX_PAGES):
            params: dict = {"count": page_size}
            if cursor:
                params["max_id"] = cursor

            try:
                resp = self._http.get(url, params=params, headers=_API_HEADERS)
            except NetworkError:
                raise
            if resp.status_code >= 400:
                self._logger.warning(
                    "follow list page non-2xx",
                    user_id=user_id,
                    kind=kind,
                    page=page_index,
                    status=resp.status_code,
                )
                # Surface partial results, mirroring CommentScraper.
                return _build_list(
                    user_id=user_id,
                    kind=kind,
                    users=collected,
                    has_more=True,
                    cursor=cursor,
                )

            try:
                payload = resp.json()
            except (ValueError, json.JSONDecodeError) as exc:
                raise ParseError(
                    f"{kind} page returned non-json (page={page_index})",
                    source=f"followers.{kind}",
                ) from exc

            page_users, next_cursor = _parse_follow_page(payload)
            collected.extend(page_users)
            # Always advertise the latest cursor — including the
            # ``None`` we get on the natural end of pagination —
            # so the caller's next_cursor reflects reality.
            cursor = next_cursor

            if max_users is not None and len(collected) >= max_users:
                collected = collected[:max_users]
                has_more = bool(next_cursor) or len(page_users) > 0
                break

            if not next_cursor:
                break
        else:
            # Loop exhausted the safety cap without Instagram saying done.
            self._logger.warning(
                "follow list pagination cap hit",
                user_id=user_id,
                kind=kind,
                pages=_MAX_PAGES,
            )
            has_more = True

        result = _build_list(
            user_id=user_id,
            kind=kind,
            users=collected,
            has_more=has_more,
            cursor=cursor,
        )
        self._logger.info(
            "follow list ok",
            user_id=user_id,
            kind=kind,
            count=result.total_returned,
            has_more=result.has_more,
        )
        return result


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _build_list(
    *,
    user_id: str,
    kind: str,
    users: List[FollowEntry],
    has_more: bool,
    cursor: Optional[str],
) -> FollowList:
    return FollowList(
        target_user_id=user_id,
        kind=kind,
        users=tuple(users),
        total_returned=len(users),
        has_more=has_more,
        next_cursor=cursor,
    )


def _parse_follow_page(
    payload: Mapping[str, Any],
) -> Tuple[List[FollowEntry], Optional[str]]:
    if not isinstance(payload, Mapping):
        return [], None
    raw_users = payload.get("users") or []
    out: List[FollowEntry] = []
    if isinstance(raw_users, list):
        for raw in raw_users:
            entry = _follow_entry_from_api(raw)
            if entry is not None:
                out.append(entry)

    next_cursor: Optional[str] = None
    nm = payload.get("next_max_id")
    if isinstance(nm, str) and nm:
        next_cursor = nm
    elif isinstance(nm, int):
        # Sometimes Instagram returns it as an int; normalise to str.
        next_cursor = str(nm)
    return out, next_cursor


def _follow_entry_from_api(raw: Any) -> Optional[FollowEntry]:
    if not isinstance(raw, Mapping):
        return None
    username = raw.get("username")
    if not isinstance(username, str) or not username:
        return None
    pk = raw.get("pk") or raw.get("id")
    try:
        return FollowEntry(
            username=username,
            user_id=str(pk) if pk is not None else None,
            full_name=raw.get("full_name") or None,
            is_verified=bool(raw.get("is_verified", False)),
            is_private=bool(raw.get("is_private", False)),
            profile_pic_url=raw.get("profile_pic_url") or None,
        )
    except (TypeError, ValueError):
        return None


def _friendship_from_api(user_id: str, payload: Any) -> FriendshipStatus:
    """Build :class:`FriendshipStatus` from the show endpoint response.

    The endpoint returns a flat dict. Some fields are missing on
    private or restricted accounts; we default everything to ``False``
    so callers do not have to special-case missing keys.
    """
    if not isinstance(payload, Mapping):
        return FriendshipStatus(user_id=user_id)
    return FriendshipStatus(
        user_id=user_id,
        is_following=bool(payload.get("following", False)),
        is_followed_by=bool(payload.get("followed_by", False)),
        is_blocking=bool(payload.get("blocking", False)),
        is_muting=bool(payload.get("is_muting_reel") or payload.get("muting", False)),
        has_outgoing_request=bool(payload.get("outgoing_request", False)),
        has_incoming_request=bool(payload.get("incoming_request", False)),
    )


__all__ = ["FollowersScraper"]
