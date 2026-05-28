"""
LocationScraper — read location metadata and media feeds.

Same shape as :class:`HashtagScraper`:

  * :meth:`lookup` — single GET, metadata only.
  * :meth:`recent` / :meth:`ranked` — paginated feed, reuses
    :func:`paginate_feed`.

Locations differ from hashtags in two ways that surface in this
module:

  1. Identified by numeric ``pk`` rather than a name string. We
     accept ``int`` or ``str`` and normalise to ``str``.
  2. Top-tab is called "ranked" in Instagram's API, not "top".
"""

from __future__ import annotations

import json
from typing import Any, List, Mapping, Optional, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.exceptions import (
    NetworkError,
    ParseError,
    ProfileNotFoundError,
)
from instaharvest._v3.core.models import FeedSource, Location, MediaFeed
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._feed import API_HEADERS, paginate_feed
from instaharvest._v3.scrapers.hashtag import _parse_sections_page


_INFO_URL = "https://www.instagram.com/api/v1/locations/web_info/?location_id={pk}"
_SECTIONS_URL = "https://www.instagram.com/api/v1/locations/{pk}/sections/"


class LocationNotFoundError(ProfileNotFoundError):
    """The requested location pk does not exist on Instagram."""

    def __init__(self, pk: str):
        Exception.__init__(self, f"Location not found: pk={pk}")
        self.username = pk
        self.pk = pk


class LocationScraper:
    """Read location metadata and media feeds.

    Construct via :attr:`InstaHarvest.location`. Direct instantiation
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

    def lookup(self, pk) -> Location:
        """Return :class:`Location` metadata (no media feed)."""
        pk_str = _normalise_pk(pk)
        url = _INFO_URL.format(pk=pk_str)
        try:
            resp = self._http.get(url, headers=API_HEADERS)
        except NetworkError:
            raise
        if resp.status_code == 404:
            raise LocationNotFoundError(pk_str)
        if resp.status_code >= 400:
            raise NetworkError(
                f"location lookup returned {resp.status_code}",
                url=url,
            )
        try:
            payload = resp.json()
        except (ValueError, json.JSONDecodeError) as exc:
            raise ParseError(
                f"location lookup non-json for pk={pk_str}",
                source="location.lookup",
            ) from exc

        return _location_from_api(pk_str, payload)

    def recent(self, pk, *, max_items: Optional[int] = None) -> MediaFeed:
        """Recent media tagged at this location."""
        return self._sections_feed(
            pk=pk, source=FeedSource.LOCATION_RECENT, tab="recent",
            max_items=max_items,
        )

    def ranked(self, pk, *, max_items: Optional[int] = None) -> MediaFeed:
        """Top (Instagram-ranked) media tagged at this location.

        Note that Instagram calls this tab "ranked" in the location
        API, not "top" as it does for hashtags. We expose the same
        terminology so log lines and callers stay accurate.
        """
        return self._sections_feed(
            pk=pk, source=FeedSource.LOCATION_RANKED, tab="ranked",
            max_items=max_items,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _sections_feed(
        self,
        *,
        pk,
        source: FeedSource,
        tab: str,
        max_items: Optional[int],
    ) -> MediaFeed:
        pk_str = _normalise_pk(pk)
        url = _SECTIONS_URL.format(pk=pk_str)

        def fetcher(cursor: Optional[str]):
            body = {"tab": tab, "surface": "grid", "include_persistent": "false"}
            if cursor:
                body["max_id"] = cursor
            return self._http.post(url, data=body, headers=API_HEADERS)

        return paginate_feed(
            http=self._http,
            logger=self._logger,
            source=source,
            source_id=pk_str,
            fetcher=fetcher,
            # Location sections payload mirrors hashtag sections.
            parser=_parse_sections_page,
            max_items=max_items,
            log_prefix=f"location.{tab}",
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _normalise_pk(raw) -> str:
    if isinstance(raw, int):
        if raw < 0:
            raise ValueError(f"location pk must be non-negative: {raw}")
        return str(raw)
    if isinstance(raw, str):
        cleaned = raw.strip()
        if not cleaned:
            raise ValueError("empty location pk")
        if not cleaned.isdigit():
            raise ValueError(f"location pk must be numeric: {raw!r}")
        return cleaned
    raise ValueError(
        f"location pk must be int or str, got {type(raw).__name__}"
    )


def _location_from_api(pk: str, payload: Any) -> Location:
    """Build a :class:`Location` from the ``locations/web_info`` payload.

    The endpoint returns one of two shapes depending on edge:
      * ``{"native_location_data": {"location_info": {...}}}``  (most common)
      * ``{"location_info": {...}}``                            (legacy)

    Both are unwrapped here so callers see the same model regardless.
    """
    if not isinstance(payload, Mapping):
        return Location(pk=pk, name=f"location-{pk}")

    info = (
        payload.get("native_location_data", {}).get("location_info")
        if isinstance(payload.get("native_location_data"), Mapping)
        else None
    )
    if info is None:
        info = payload.get("location_info") or payload.get("location") or {}
    if not isinstance(info, Mapping):
        return Location(pk=pk, name=f"location-{pk}")

    return Location(
        pk=str(info.get("pk") or info.get("id") or pk),
        name=str(info.get("name") or f"location-{pk}"),
        slug=info.get("slug") or None,
        address=info.get("address") or None,
        city=info.get("city") or None,
        short_name=info.get("short_name") or None,
        lat=_optional_float(info.get("lat") or info.get("latitude")),
        lng=_optional_float(info.get("lng") or info.get("longitude")),
        media_count=int(
            payload.get("native_location_data", {}).get("location_section_data", {}).get("media_count")
            if isinstance(payload.get("native_location_data"), Mapping)
            else 0
        ) or 0,
    )


def _optional_float(value):
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["LocationScraper", "LocationNotFoundError"]
