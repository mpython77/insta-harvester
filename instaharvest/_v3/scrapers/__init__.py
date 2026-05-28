"""
v3 scrapers.

Each scraper has exactly one job (one Instagram surface). All
shared concerns — navigation, login detection, rate-limit handling,
pacing — live in :class:`AbstractScraper`. Concrete scrapers only
own their parsing and their domain checks.
"""

from instaharvest._v3.scrapers.base import AbstractScraper, NavigationOutcome
from instaharvest._v3.scrapers.comments import CommentScraper
from instaharvest._v3.scrapers.explore import ExploreScraper
from instaharvest._v3.scrapers.followers import FollowersScraper
from instaharvest._v3.scrapers.hashtag import HashtagNotFoundError, HashtagScraper
from instaharvest._v3.scrapers.location import (
    LocationNotFoundError,
    LocationScraper,
)
from instaharvest._v3.scrapers.media import MediaNotFoundError, MediaScraper
from instaharvest._v3.scrapers.profile import ProfileScraper
from instaharvest._v3.scrapers.search import SearchScraper

__all__ = [
    "AbstractScraper",
    "NavigationOutcome",
    "ProfileScraper",
    "MediaScraper",
    "MediaNotFoundError",
    "CommentScraper",
    "FollowersScraper",
    "HashtagScraper",
    "HashtagNotFoundError",
    "LocationScraper",
    "LocationNotFoundError",
    "SearchScraper",
    "ExploreScraper",
]
