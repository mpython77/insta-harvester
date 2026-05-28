"""
InstaHarvest - Professional Instagram Data Collection Toolkit

Version 4.0.0 - Clean architecture release.
Legacy modules have been removed. The v3 API is now the only API.

Quick Start:
    from instaharvest import InstaHarvest, Settings

    with InstaHarvest(Settings.default()) as ih:
        profile = ih.profile.scrape("instagram")
        print(profile.followers, profile.is_verified)

Author: Muydinov Doston
License: MIT
"""

from instaharvest.facade import InstaHarvest
from instaharvest.config import Settings
from instaharvest.config.actions import ActionsConfig
from instaharvest.config.browser import BrowserConfig
from instaharvest.config.network import NetworkConfig
from instaharvest.config.stealth import StealthConfig
from instaharvest.config.rate_limit import RateLimitConfig
from instaharvest.config.output import OutputConfig
from instaharvest.config.selectors import SelectorConfig
from instaharvest.evasion.config import EvasionConfig

from instaharvest.core.exceptions import (
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
from instaharvest.scrapers.media import MediaNotFoundError
from instaharvest.scrapers.hashtag import HashtagNotFoundError
from instaharvest.scrapers.location import LocationNotFoundError

from instaharvest.core.models import (
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
    StorySlide,
    StoryFeed,
    Highlight,
    HighlightSlide,
    HighlightsList,
    NotificationType,
    Notification,
    NotificationFeed,
)
from instaharvest.core.protocols import (
    HttpClient,
    BrowserSession,
    SessionStore,
    Logger,
)
from instaharvest.scrapers.web_api import WebAPI

from instaharvest.session_utils import (
    save_session,
    check_session_exists,
    load_session_data,
    get_default_session_path,
    find_session_file,
    get_session_save_path,
    SESSION_FILENAME,
)

__version__ = "4.0.0"
__author__ = "Muydinov Doston"
__email__ = "kelajak054@gmail.com"
__url__ = "https://github.com/mpython77/insta-harvester"

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
    "EvasionConfig",
    # Exceptions
    "InstaHarvestError",
    "ConfigError",
    "SessionError",
    "SessionNotFoundError",
    "SessionExpiredError",
    "NetworkError",
    "RateLimitedError",
    "ProfileNotFoundError",
    "HtmlStructureChangedError",
    "ParseError",
    "MediaNotFoundError",
    "HashtagNotFoundError",
    "LocationNotFoundError",
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
    "StorySlide",
    "StoryFeed",
    "Highlight",
    "HighlightSlide",
    "HighlightsList",
    "NotificationType",
    "Notification",
    "NotificationFeed",
    # Protocols
    "HttpClient",
    "BrowserSession",
    "SessionStore",
    "Logger",
    # Web API
    "WebAPI",
    # Session utilities
    "save_session",
    "check_session_exists",
    "load_session_data",
    "get_default_session_path",
    "find_session_file",
    "get_session_save_path",
    "SESSION_FILENAME",
]
