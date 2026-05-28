"""
v3 scrapers.

Each scraper has exactly one job (one Instagram surface). All
shared concerns — navigation, login detection, rate-limit handling,
pacing — live in :class:`AbstractScraper`. Concrete scrapers only
own their parsing and their domain checks.
"""

from instaharvest.scrapers.base import AbstractScraper, NavigationOutcome
from instaharvest.scrapers.comments import CommentScraper
from instaharvest.scrapers.explore import ExploreScraper
from instaharvest.scrapers.followers import FollowersScraper
from instaharvest.scrapers.hashtag import HashtagNotFoundError, HashtagScraper
from instaharvest.scrapers.highlights import HighlightScraper
from instaharvest.scrapers.location import (
    LocationNotFoundError,
    LocationScraper,
)
from instaharvest.scrapers.media import MediaNotFoundError, MediaScraper
from instaharvest.scrapers.notifications import NotificationsScraper
from instaharvest.scrapers.profile import ProfileScraper
from instaharvest.scrapers.search import SearchScraper
from instaharvest.scrapers.stories import StoryScraper
from instaharvest.scrapers.web_api import WebAPI

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
    "HighlightScraper",
    "LocationScraper",
    "LocationNotFoundError",
    "NotificationsScraper",
    "SearchScraper",
    "StoryScraper",
    "ExploreScraper",
    "WebAPI",
]
