"""
InstaHarvest v3 — clean architecture (in progress).

This namespace contains the supported, refactored API.
Legacy code at ``instaharvest/*.py`` continues to work but is
not maintained for new features.

See ``ARCHITECTURE.md`` at the repository root for the full design.

Public API (stable from this point):

    from instaharvest._v3 import InstaHarvest, Settings

    with InstaHarvest(Settings.default()) as ih:
        profile = ih.profile.scrape("instagram")
"""

from instaharvest._v3.config import Settings
from instaharvest._v3.config.actions import ActionsConfig
from instaharvest._v3.config.browser import BrowserConfig
from instaharvest._v3.config.network import NetworkConfig
from instaharvest._v3.config.stealth import StealthConfig
from instaharvest._v3.config.rate_limit import RateLimitConfig
from instaharvest._v3.config.output import OutputConfig
from instaharvest._v3.config.selectors import SelectorConfig

from instaharvest._v3.core.exceptions import (
    InstaHarvestError,
    ConfigError,
    SessionError,
    SessionNotFoundError,
    SessionExpiredError,
    NetworkError,
    RateLimitedError,
    ProfileNotFoundError,
    HtmlStructureChangedError,
    ParseError,
)
from instaharvest._v3.core.models import (
    Profile,
    BioLink,
    BusinessInfo,
    Media,
    MediaKind,
    MediaOwner,
    MediaLocation,
    CarouselItem,
    Comment,
    CommentAuthor,
    CommentsPage,
    FollowEntry,
    FollowList,
    FriendshipStatus,
    ActionResult,
    ActionStatus,
    Hashtag,
    Location,
    MediaFeed,
    FeedSource,
    SearchResult,
    SearchUserHit,
    SearchHashtagHit,
    SearchPlaceHit,
)
from instaharvest._v3.core.protocols import (
    HttpClient,
    BrowserSession,
    SessionStore,
    Logger,
)

from instaharvest._v3.facade import InstaHarvest
from instaharvest._v3.scrapers.hashtag import HashtagNotFoundError
from instaharvest._v3.scrapers.location import LocationNotFoundError
from instaharvest._v3.scrapers.media import MediaNotFoundError

__all__ = [
    # Facade
    "InstaHarvest",
    # Config
    "Settings",
    "BrowserConfig",
    "NetworkConfig",
    "StealthConfig",
    "RateLimitConfig",
    "OutputConfig",
    "SelectorConfig",
    "ActionsConfig",
    # Exceptions
    "InstaHarvestError",
    "ConfigError",
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "NetworkError",
    "RateLimitedError",
    "ProfileNotFoundError",
    "MediaNotFoundError",
    "HashtagNotFoundError",
    "LocationNotFoundError",
    "HtmlStructureChangedError",
    "ParseError",
    # Models
    "Profile",
    "BioLink",
    "BusinessInfo",
    "Media",
    "MediaKind",
    "MediaOwner",
    "MediaLocation",
    "CarouselItem",
    "Comment",
    "CommentAuthor",
    "CommentsPage",
    "FollowEntry",
    "FollowList",
    "FriendshipStatus",
    "ActionResult",
    "ActionStatus",
    "Hashtag",
    "Location",
    "MediaFeed",
    "FeedSource",
    "SearchResult",
    "SearchUserHit",
    "SearchHashtagHit",
    "SearchPlaceHit",
    # Protocols
    "HttpClient",
    "BrowserSession",
    "SessionStore",
    "Logger",
]
