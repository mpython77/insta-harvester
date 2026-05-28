"""
v3 scrapers.

Each scraper has exactly one job (one Instagram surface). All
shared concerns — navigation, login detection, rate-limit handling,
pacing — live in :class:`AbstractScraper`. Concrete scrapers only
own their parsing and their domain checks.
"""

from instaharvest._v3.scrapers.base import AbstractScraper, NavigationOutcome
from instaharvest._v3.scrapers.profile import ProfileScraper

__all__ = [
    "AbstractScraper",
    "NavigationOutcome",
    "ProfileScraper",
]
