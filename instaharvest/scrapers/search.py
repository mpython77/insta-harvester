"""
SearchScraper — Instagram top-search.

Single endpoint (``fbsearch/topsearch_flat``), single result type
(:class:`SearchResult`). No pagination — Instagram returns one batch
per query.

Replaces legacy ``search_api.SearchAPI`` (~140 LOC, mixed DOM and
API code paths) with ~120 LOC of API-only logic.
"""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Optional

from instaharvest.core.exceptions import NetworkError, ParseError
from instaharvest.core.models import (
    SearchHashtagHit,
    SearchPlaceHit,
    SearchResult,
    SearchUserHit,
)
from instaharvest.core.protocols import HttpClient, Logger
from instaharvest.scrapers._feed import API_HEADERS


_TOPSEARCH_URL = "https://www.instagram.com/api/v1/fbsearch/topsearch_flat/"

_QUERY_MAX_LEN = 100


class SearchScraper:
    """Search users, hashtags, and places via Instagram's top-search.

    Construct via :attr:`InstaHarvest.search`. Direct instantiation is
    supported for tests.
    """

    def __init__(
        self,
        *,
        http: HttpClient,
        logger: Logger,
    ) -> None:
        self._http = http
        self._logger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(self, query: str) -> SearchResult:
        """Return one batch of search hits for ``query``.

        Raises:
            ValueError: ``query`` is empty or unreasonably long.
            NetworkError: HTTP layer kept failing.
            ParseError: response was reachable but malformed.
        """
        query = _normalise_query(query)
        self._logger.info("search start", query=query)

        params = {
            "query": query,
            "context": "blended",
            "search_surface": "web_top_search",
        }
        try:
            resp = self._http.get(
                _TOPSEARCH_URL, params=params, headers=API_HEADERS,
            )
        except NetworkError:
            raise
        if resp.status_code >= 400:
            raise NetworkError(
                f"search returned {resp.status_code}",
                url=_TOPSEARCH_URL,
            )

        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"search non-json for query={query!r}",
                source="search",
            ) from exc

        result = _result_from_api(query, payload)
        self._logger.info(
            "search ok",
            query=query,
            users=len(result.users),
            hashtags=len(result.hashtags),
            places=len(result.places),
        )
        return result


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _normalise_query(raw: str) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"query must be str, got {type(raw).__name__}")
    cleaned = raw.strip()
    if not cleaned:
        raise ValueError("empty query")
    if len(cleaned) > _QUERY_MAX_LEN:
        raise ValueError(
            f"query too long ({len(cleaned)} chars; max {_QUERY_MAX_LEN})"
        )
    return cleaned


def _result_from_api(query: str, payload: Any) -> SearchResult:
    """Build a :class:`SearchResult` from the ``topsearch_flat`` payload."""
    if not isinstance(payload, Mapping):
        return SearchResult(query=query)

    # ``topsearch_flat`` returns a flat list under ``list``, with each
    # entry tagged by ``user``/``hashtag``/``place`` payload. Older
    # endpoints split these into separate keys; we accept both.
    flat = payload.get("list")
    users: list = []
    hashtags: list = []
    places: list = []

    if isinstance(flat, list):
        for entry in flat:
            if not isinstance(entry, Mapping):
                continue
            if entry.get("user"):
                hit = _user_hit(entry["user"])
                if hit is not None:
                    users.append(hit)
            elif entry.get("hashtag"):
                hit = _hashtag_hit(entry["hashtag"])
                if hit is not None:
                    hashtags.append(hit)
            elif entry.get("place"):
                hit = _place_hit(entry["place"])
                if hit is not None:
                    places.append(hit)

    # Older endpoints expose category-keyed lists.
    for raw in payload.get("users", []) or []:
        # ``users`` can be either ``[{"user": {...}}]`` or ``[{...}]``
        user_dict = raw.get("user") if isinstance(raw, Mapping) and "user" in raw else raw
        hit = _user_hit(user_dict)
        if hit is not None:
            users.append(hit)
    for raw in payload.get("hashtags", []) or []:
        tag_dict = raw.get("hashtag") if isinstance(raw, Mapping) and "hashtag" in raw else raw
        hit = _hashtag_hit(tag_dict)
        if hit is not None:
            hashtags.append(hit)
    for raw in payload.get("places", []) or []:
        place_dict = raw.get("place") if isinstance(raw, Mapping) and "place" in raw else raw
        hit = _place_hit(place_dict)
        if hit is not None:
            places.append(hit)

    return SearchResult(
        query=query,
        users=tuple(_dedupe(users, key=lambda u: u.username)),
        hashtags=tuple(_dedupe(hashtags, key=lambda h: h.name)),
        places=tuple(_dedupe(places, key=lambda p: p.pk)),
    )


def _user_hit(raw) -> Optional[SearchUserHit]:
    if not isinstance(raw, Mapping):
        return None
    username = raw.get("username")
    if not isinstance(username, str) or not username:
        return None
    pk = raw.get("pk") or raw.get("id")
    try:
        return SearchUserHit(
            username=username,
            user_id=str(pk) if pk is not None else None,
            full_name=raw.get("full_name") or None,
            is_verified=bool(raw.get("is_verified", False)),
            is_private=bool(raw.get("is_private", False)),
            profile_pic_url=raw.get("profile_pic_url") or None,
            follower_count=int(raw.get("follower_count") or 0),
        )
    except (TypeError, ValueError):
        return None


def _hashtag_hit(raw) -> Optional[SearchHashtagHit]:
    if not isinstance(raw, Mapping):
        return None
    name = raw.get("name")
    if not isinstance(name, str) or not name:
        return None
    try:
        return SearchHashtagHit(
            name=name,
            media_count=int(raw.get("media_count") or 0),
            formatted_media_count=raw.get("formatted_media_count") or None,
        )
    except (TypeError, ValueError):
        return None


def _place_hit(raw) -> Optional[SearchPlaceHit]:
    if not isinstance(raw, Mapping):
        return None
    location = raw.get("location") if isinstance(raw.get("location"), Mapping) else raw
    pk = location.get("pk") if isinstance(location, Mapping) else None
    name = location.get("name") if isinstance(location, Mapping) else None
    if pk is None or not isinstance(name, str) or not name:
        return None
    try:
        return SearchPlaceHit(
            pk=str(pk),
            name=name,
            short_name=location.get("short_name") or None,
            city=location.get("city") or None,
            address=location.get("address") or None,
            lat=_optional_float(location.get("lat") or location.get("latitude")),
            lng=_optional_float(location.get("lng") or location.get("longitude")),
        )
    except (TypeError, ValueError):
        return None


def _optional_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(items, *, key):
    seen: set = set()
    out: list = []
    for item in items:
        k = key(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


__all__ = ["SearchScraper"]
