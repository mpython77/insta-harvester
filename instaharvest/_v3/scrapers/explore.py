"""
ExploreScraper — algorithmic ``/explore/`` feed.

Returns a single :class:`MediaFeed`. Pagination is supported via
``next_cursor`` (Instagram exposes ``max_id`` on the explore grid
endpoint), but explore feeds are bottomless, so users almost always
want to set a sensible ``max_items``.

Replaces legacy ``explore_scraper.ExploreScraper`` (~270 LOC of DOM
infinite-scroll) with ~80 LOC of API logic.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Tuple

from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.core.models import FeedSource, MediaFeed
from instaharvest._v3.core.protocols import HttpClient, Logger
from instaharvest._v3.scrapers._feed import API_HEADERS, paginate_feed


_EXPLORE_URL = "https://www.instagram.com/api/v1/discover/web/explore_grid/"


class ExploreScraper:
    """Read the algorithmic explore feed.

    Construct via :attr:`InstaHarvest.explore`. Direct instantiation
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

    def feed(self, *, max_items: Optional[int] = 50) -> MediaFeed:
        """Return up to ``max_items`` algorithmically-recommended media.

        ``max_items`` defaults to 50 (≈ 2 grid pages) because explore
        is unbounded and a missing cap is far more likely to be a bug
        than a feature.
        """

        def fetcher(cursor: Optional[str]):
            params = {"is_prefetch": "false"}
            if cursor:
                params["max_id"] = cursor
            return self._http.get(
                _EXPLORE_URL, params=params, headers=API_HEADERS,
            )

        return paginate_feed(
            http=self._http,
            logger=self._logger,
            source=FeedSource.EXPLORE,
            source_id="explore",
            fetcher=fetcher,
            parser=_parse_explore_page,
            max_items=max_items,
            log_prefix="explore",
        )


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _parse_explore_page(
    payload: Mapping[str, Any],
) -> Tuple[List[Mapping[str, Any]], Optional[str]]:
    """Pull media dicts and the next cursor from an explore payload.

    The explore grid returns ``sectional_items`` rather than
    ``sections``, with each entry having a ``media`` key.
    """
    if not isinstance(payload, Mapping):
        return [], None

    out: List[Mapping[str, Any]] = []
    items = payload.get("sectional_items") or payload.get("items") or []
    if isinstance(items, list):
        for entry in items:
            if not isinstance(entry, Mapping):
                continue
            media = entry.get("media")
            if isinstance(media, Mapping):
                out.append(media)
            elif "code" in entry or "shortcode" in entry:
                # Some payloads stash media at the top level.
                out.append(entry)

    next_cursor: Optional[str] = None
    nm = payload.get("next_max_id")
    if isinstance(nm, str) and nm:
        next_cursor = nm
    elif isinstance(nm, int):
        next_cursor = str(nm)
    return out, next_cursor


__all__ = ["ExploreScraper"]
