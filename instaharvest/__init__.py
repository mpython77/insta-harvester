"""
InstaHarvest - Professional Instagram Data Collection Toolkit

A powerful and efficient Instagram automation library for data collection,
engagement management, and analytics.

Features:
- Profile statistics (posts, followers, following)
- Verified badge detection - Check if account is verified
- Profile category extraction - Detect Actor, Model, Photographer, etc.
- Complete bio extraction - All text, links, emails, mentions, contact info
- Post & Reel links collection with intelligent scrolling
- Tagged accounts extraction (posts & reels)
- FULL COMMENT SCRAPING (NEW!) - Extract all comments with:
  - Comment text, likes count, timestamp
  - Author info (username, profile pic, verified status)
  - Collaborators extraction (post co-authors)
  - Reply extraction (nested comments)
  - Real-time JSON & Excel export
- Followers/Following collection with real-time output
- Direct messaging with smart rate limiting
- Follow/Unfollow management
- Parallel processing - Scrape multiple posts simultaneously
- Real-time Excel export
- Shared browser sessions - Single browser for all operations
- HTML structure change detection
- Professional logging
- Modular design for library usage
- Notification reader for activity feed

Quick Start:
    # Simple usage
    from instaharvest import quick_scrape
    results = quick_scrape('username')

    # Advanced usage with parallel processing
    from instaharvest import InstagramOrchestrator, ScraperConfig

    config = ScraperConfig(headless=True)
    orchestrator = InstagramOrchestrator(config)

    results = orchestrator.scrape_complete_profile_advanced(
        'username',
        parallel=3,        # 3 parallel browser tabs
        save_excel=True    # Real-time Excel export
    )

    # Full comment scraping (NEW!)
    from instaharvest import InstagramOrchestrator, ScraperConfig

    config = ScraperConfig()
    orchestrator = InstagramOrchestrator(config)

    # Option 1: Scrape everything including comments
    results = orchestrator.scrape_complete_profile_advanced(
        'username',
        parallel=3,
        save_excel=True,
        scrape_comments=True,         # Enable comment scraping
        max_comments_per_post=100,    # Limit per post (None = all)
        include_replies=True          # Include reply threads
    )

    # Option 2: Scrape only comments
    results = orchestrator.scrape_comments_only(
        'username',
        max_comments_per_post=50,
        include_replies=True,
        save_excel=True,
        export_json=True
    )

    # Option 3: Low-level comment scraping
    from instaharvest import CommentScraper

    scraper = CommentScraper()
    scraper.setup_browser(session_data)
    comments = scraper.scrape(
        'https://www.instagram.com/p/ABC123/',
        target_count=100,
        include_replies=True
    )
    # comments.total_comments_scraped
    # comments.comments[0].author.username
    # comments.comments[0].text
    # comments.comments[0].likes_count
    # comments.comments[0].replies

    # Follow/Unfollow management
    from instaharvest import FollowManager
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    manager = FollowManager(config=config)
    manager.setup_browser(session_data)
    result = manager.follow('username')

    # Direct messaging
    from instaharvest import MessageManager
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    messenger = MessageManager(config=config)
    messenger.setup_browser(session_data)
    result = messenger.send_message('username', 'Hello!')

    # Shared browser - all operations in one browser! (RECOMMENDED)
    from instaharvest import SharedBrowser
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    with SharedBrowser(config=config) as browser:
        browser.follow('user1')
        browser.send_message('user1', 'Hello!')
        followers = browser.get_followers('user1', limit=100)
        browser.scrape_profile('user1')

    # Collect followers with real-time output
    from instaharvest import FollowersCollector
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    collector = FollowersCollector(config=config)
    collector.setup_browser(session_data)
    followers = collector.get_followers('username', limit=100)

    # Save session (first-time setup)
    from instaharvest import save_session
    save_session()  # Opens browser for manual login

    # Check if session exists
    from instaharvest import check_session_exists
    if not check_session_exists():
        save_session()

    # Story scraping with per-slide tag mapping
    from instaharvest import StoryScraper, StorySlideInfo
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    scraper = StoryScraper(config=config)
    result = scraper.scrape('username', extract_tags=True)
    print(result.all_tagged_accounts)
    for slide in result.slides:
        print(f"Slide {slide.slide_index + 1}: {slide.timestamp} → {slide.tagged_accounts}")

    # Tagged Posts scraping — who tags this account
    from instaharvest import TaggedPostsScraper
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    scraper = TaggedPostsScraper(config=config)
    result = scraper.scrape('mondayswimwear', target_count=100)
    for post in result.tagged_posts:
        print(f"{post.owner} tagged @mondayswimwear → {post.url}")

    # Highlights scraping — full slide data with stickers
    from instaharvest import HighlightsScraper
    from instaharvest.config import ScraperConfig

    config = ScraperConfig()
    scraper = HighlightsScraper(config=config)

    # Single highlight
    result = scraper.scrape('18092082532805201')
    print(f"{result.highlight_title}: {result.slide_count} slides")
    print(f"Mentions: {result.all_mentions}")
    print(f"Music: {[m.title for m in result.all_music]}")

    # List all highlights for a user
    highlights = scraper.list_highlights('mondayswimwear')

    # Scrape ALL highlights sequentially
    full = scraper.scrape_all('mondayswimwear', max_slides_per=100)
    for r in full.full_results:
        print(f"  {r.highlight_title}: {r.slide_count} slides")

Author: Muydinov Doston
Version: 3.0.0-alpha
License: MIT
"""

import warnings as _warnings
import importlib as _importlib

# ---------------------------------------------------------------------------
# Legacy import mapping: name -> (module_path, attribute_name)
# These are loaded lazily via __getattr__ with a deprecation warning.
# ---------------------------------------------------------------------------

_LEGACY_IMPORTS = {
    # config
    'ScraperConfig': ('.config', 'ScraperConfig'),
    # exceptions
    'InstagramScraperError': ('.exceptions', 'InstagramScraperError'),
    'SessionNotFoundError': ('.exceptions', 'SessionNotFoundError'),
    'ProfileNotFoundError': ('.exceptions', 'ProfileNotFoundError'),
    'HTMLStructureChangedError': ('.exceptions', 'HTMLStructureChangedError'),
    'PageLoadError': ('.exceptions', 'PageLoadError'),
    'RateLimitError': ('.exceptions', 'RateLimitError'),
    'LoginRequiredError': ('.exceptions', 'LoginRequiredError'),
    'WebAPIError': ('.exceptions', 'WebAPIError'),
    # base
    'BaseScraper': ('.base', 'BaseScraper'),
    # profile
    'ProfileScraper': ('.profile', 'ProfileScraper'),
    'ProfileData': ('.profile', 'ProfileData'),
    # post_links
    'InstagramPostLinksScraper': ('.post_links', 'InstagramPostLinksScraper'),
    'PostLinksScraper': ('.post_links', 'PostLinksScraper'),
    # post_data
    'PostDataScraper': ('.post_data', 'PostDataScraper'),
    'PostData': ('.post_data', 'PostData'),
    'PostLocation': ('.post_data', 'PostLocation'),
    'PostOwner': ('.post_data', 'PostOwner'),
    'CarouselSlide': ('.post_data', 'CarouselSlide'),
    # reel_links
    'ReelLinksScraper': ('.reel_links', 'ReelLinksScraper'),
    # reel_data
    'ReelDataScraper': ('.reel_data', 'ReelDataScraper'),
    'ReelData': ('.reel_data', 'ReelData'),
    # parallel_scraper
    'ParallelPostDataScraper': ('.parallel_scraper', 'ParallelPostDataScraper'),
    # comment_scraper
    'CommentScraper': ('.comment_scraper', 'CommentScraper'),
    'PostCommentsData': ('.comment_scraper', 'PostCommentsData'),
    # models
    'CommentData': ('.models', 'CommentData'),
    'CommentAuthor': ('.models', 'CommentAuthor'),
    'Collaborator': ('.models', 'Collaborator'),
    'Comment': ('.models', 'Comment'),
    # exporters
    'CommentsExporter': ('.exporters', 'CommentsExporter'),
    'RealTimeCommentsExporter': ('.exporters', 'RealTimeCommentsExporter'),
    'export_comments_to_json': ('.exporters', 'export_comments_to_json'),
    'export_comments_to_excel': ('.exporters', 'export_comments_to_excel'),
    'ExcelExporter': ('.exporters', 'ExcelExporter'),
    # follow
    'FollowManager': ('.follow', 'FollowManager'),
    # message
    'MessageManager': ('.message', 'MessageManager'),
    # followers
    'FollowersCollector': ('.followers', 'FollowersCollector'),
    # shared_browser
    'SharedBrowser': ('.shared_browser', 'SharedBrowser'),
    # orchestrator
    'InstagramOrchestrator': ('.orchestrator', 'InstagramOrchestrator'),
    'quick_scrape': ('.orchestrator', 'quick_scrape'),
    # session_utils
    'save_session': ('.session_utils', 'save_session'),
    'check_session_exists': ('.session_utils', 'check_session_exists'),
    'load_session_data': ('.session_utils', 'load_session_data'),
    'get_default_session_path': ('.session_utils', 'get_default_session_path'),
    'find_session_file': ('.session_utils', 'find_session_file'),
    'get_session_save_path': ('.session_utils', 'get_session_save_path'),
    'SESSION_FILENAME': ('.session_utils', 'SESSION_FILENAME'),
    # stealth
    'StealthManager': ('.stealth', 'StealthManager'),
    # proxy
    'ProxyManager': ('.proxy', 'ProxyManager'),
    # logging_config
    'SmartLogger': ('.logging_config', 'SmartLogger'),
    'get_logger': ('.logging_config', 'get_logger'),
    # core
    'InstaHarvest': ('.core', 'InstaHarvest'),
    # notifications
    'NotificationReader': ('.notifications', 'NotificationReader'),
    'NotificationItem': ('.notifications', 'NotificationItem'),
    # webhooks
    'EventEmitter': ('.webhooks', 'EventEmitter'),
    'FollowerWatcher': ('.webhooks', 'FollowerWatcher'),
    'Event': ('.webhooks', 'Event'),
    'EventTypes': ('.webhooks', 'EventTypes'),
    # batch_downloader
    'BatchDownloader': ('.batch_downloader', 'BatchDownloader'),
    'DownloadTask': ('.batch_downloader', 'DownloadTask'),
    'DownloadResult': ('.batch_downloader', 'DownloadResult'),
    'BatchResult': ('.batch_downloader', 'BatchResult'),
    'ProgressTracker': ('.batch_downloader', 'ProgressTracker'),
    # async_engine
    'AsyncBaseScraper': ('.async_engine', 'AsyncBaseScraper'),
    'AsyncProfileScraper': ('.async_engine', 'AsyncProfileScraper'),
    'AsyncBatchScraper': ('.async_engine', 'AsyncBatchScraper'),
    # hashtag_scraper
    'HashtagScraper': ('.hashtag_scraper', 'HashtagScraper'),
    'HashtagResult': ('.hashtag_scraper', 'HashtagResult'),
    # story_scraper
    'StoryScraper': ('.story_scraper', 'StoryScraper'),
    'StoryResult': ('.story_scraper', 'StoryResult'),
    'StoryItem': ('.story_scraper', 'StoryItem'),
    'StorySlideInfo': ('.story_scraper', 'StorySlideInfo'),
    # location_scraper
    'LocationScraper': ('.location_scraper', 'LocationScraper'),
    'LocationResult': ('.location_scraper', 'LocationResult'),
    # search_api
    'SearchAPI': ('.search_api', 'SearchAPI'),
    'SearchResult': ('.search_api', 'SearchResult'),
    # explore_scraper
    'ExploreScraper': ('.explore_scraper', 'ExploreScraper'),
    'ExploreResult': ('.explore_scraper', 'ExploreResult'),
    # data_export
    'DataExporter': ('.data_export', 'DataExporter'),
    # tagged_posts
    'TaggedPostsScraper': ('.tagged_posts', 'TaggedPostsScraper'),
    'TaggedPostData': ('.tagged_posts', 'TaggedPostData'),
    'TaggedPostsResult': ('.tagged_posts', 'TaggedPostsResult'),
    # highlight_scraper
    'HighlightsScraper': ('.highlight_scraper', 'HighlightsScraper'),
    'HighlightResult': ('.highlight_scraper', 'HighlightResult'),
    'HighlightSlide': ('.highlight_scraper', 'HighlightSlide'),
    'HighlightSticker': ('.highlight_scraper', 'HighlightSticker'),
    'HighlightMusic': ('.highlight_scraper', 'HighlightMusic'),
    'HighlightInfo': ('.highlight_scraper', 'HighlightInfo'),
    'HighlightsListResult': ('.highlight_scraper', 'HighlightsListResult'),
    # session_manager
    'SessionManager': ('.session_manager', 'SessionManager'),
    'SessionRotationStrategy': ('.session_manager', 'SessionRotationStrategy'),
    # captcha_solver
    'CaptchaSolver': ('.captcha_solver', 'CaptchaSolver'),
    'CaptchaProvider': ('.captcha_solver', 'CaptchaProvider'),
    # web_api (legacy)
    'InstagramWebAPI': ('.web_api', 'InstagramWebAPI'),
    'WebProfileData': ('.web_api', 'WebProfileData'),
    'WebSearchResult': ('.web_api', 'WebSearchResult'),
    'SearchUserResult': ('.web_api', 'SearchUserResult'),
    'FollowUserItem': ('.web_api', 'FollowUserItem'),
    'FollowListResult': ('.web_api', 'FollowListResult'),
    'FriendshipStatus': ('.web_api', 'FriendshipStatus'),
    'FeedPost': ('.web_api', 'FeedPost'),
    'UserFeedResult': ('.web_api', 'UserFeedResult'),
    'MediaInfo': ('.web_api', 'MediaInfo'),
    'CommentItem': ('.web_api', 'CommentItem'),
    'CommentsResult': ('.web_api', 'CommentsResult'),
    'LikerItem': ('.web_api', 'LikerItem'),
    'LikersResult': ('.web_api', 'LikersResult'),
    'StoryMediaItem': ('.web_api', 'StoryMediaItem'),
    'StoriesTrayResult': ('.web_api', 'StoriesTrayResult'),
    'WebHighlightInfo': ('.web_api', 'HighlightInfo'),
    'HighlightsResult': ('.web_api', 'HighlightsResult'),
    'ReelItem': ('.web_api', 'ReelItem'),
    'ReelsResult': ('.web_api', 'ReelsResult'),
    'HashtagSection': ('.web_api', 'HashtagSection'),
    'LocationSection': ('.web_api', 'LocationSection'),
}


def __getattr__(name):
    if name in _LEGACY_IMPORTS:
        module_path, attr_name = _LEGACY_IMPORTS[name]
        mod = _importlib.import_module(module_path, package=__name__)
        value = getattr(mod, attr_name)
        _warnings.warn(
            f"Importing '{name}' directly from 'instaharvest' is deprecated. "
            f"Use 'from instaharvest.v3 import ...' for the v3 API or "
            f"'from instaharvest{module_path} import {attr_name}' for legacy code. "
            f"Legacy imports will be removed in 4.0.",
            PendingDeprecationWarning,
            stacklevel=2,
        )
        # Cache in module namespace so __getattr__ is not called again
        globals()[name] = value
        return value
    raise AttributeError(f"module 'instaharvest' has no attribute {name!r}")


__version__ = '3.0.0-alpha'
__author__ = 'Muydinov Doston'
__email__ = 'kelajak054@gmail.com'
__url__ = 'https://github.com/mpython77/insta-harvester'

__all__ = [
    # Configuration
    'ScraperConfig',

    # Exceptions
    'InstagramScraperError',
    'SessionNotFoundError',
    'ProfileNotFoundError',
    'HTMLStructureChangedError',
    'PageLoadError',
    'RateLimitError',
    'LoginRequiredError',

    # Base
    'BaseScraper',

    # Scrapers
    'ProfileScraper',
    'PostLinksScraper',
    'InstagramPostLinksScraper',
    'PostDataScraper',
    'ReelLinksScraper',
    'ReelDataScraper',
    'ParallelPostDataScraper',
    'CommentScraper',
    'FollowManager',
    'MessageManager',
    'FollowersCollector',
    'SharedBrowser',
    'TaggedPostsScraper',
    'HighlightsScraper',

    # Data structures
    'ProfileData',
    'PostData',
    'PostLocation',
    'PostOwner',
    'CarouselSlide',
    'ReelData',
    'CommentData',
    'CommentAuthor',
    'PostCommentsData',
    'Collaborator',
    'TaggedPostData',
    'TaggedPostsResult',
    'HighlightResult',
    'HighlightSlide',
    'HighlightSticker',
    'HighlightMusic',
    'HighlightInfo',
    'HighlightsListResult',

    # Export
    'ExcelExporter',
    'CommentsExporter',
    'RealTimeCommentsExporter',
    'export_comments_to_json',
    'export_comments_to_excel',

    # Orchestrator
    'InstagramOrchestrator',
    'quick_scrape',

    # Session utilities
    'save_session',
    'check_session_exists',
    'load_session_data',
    'get_default_session_path',
    'find_session_file',
    'get_session_save_path',
    'SESSION_FILENAME',
    
    # Stealth / Anti-Detection
    'StealthManager',
    
    # Proxy Management
    'ProxyManager',
    
    # Smart Logging
    'SmartLogger',
    'get_logger',
    
    # Central Hub
    'InstaHarvest',
    
    # Notifications
    'NotificationReader',
    'NotificationItem',

    # Webhooks / Events
    'EventEmitter',
    'FollowerWatcher',
    'Event',
    'EventTypes',

    # Batch Downloader
    'BatchDownloader',
    'DownloadTask',
    'DownloadResult',
    'BatchResult',
    'ProgressTracker',

    # Async Engine
    'AsyncBaseScraper',
    'AsyncProfileScraper',
    'AsyncBatchScraper',

    # Hashtag Scraper
    'HashtagScraper',
    'HashtagResult',

    # Story Scraper
    'StoryScraper',
    'StoryResult',
    'StoryItem',
    'StorySlideInfo',

    # Location Scraper
    'LocationScraper',
    'LocationResult',

    # Search API
    'SearchAPI',
    'SearchResult',

    # Explore Scraper
    'ExploreScraper',
    'ExploreResult',

    # Data Export
    'DataExporter',

    # Session Management
    'SessionManager',
    'SessionRotationStrategy',

    # Captcha Solver
    'CaptchaSolver',
    'CaptchaProvider',

    # Web API (JSON-first) — 16+ endpoints
    'InstagramWebAPI',
    'WebProfileData',
    'WebSearchResult',
    'SearchUserResult',
    'WebAPIError',
    'FollowUserItem',
    'FollowListResult',
    'FriendshipStatus',
    'FeedPost',
    'UserFeedResult',
    'MediaInfo',
    'Comment',
    'CommentItem',
    'CommentsResult',
    'LikerItem',
    'LikersResult',
    'StoryMediaItem',
    'StoriesTrayResult',
    'WebHighlightInfo',
    'HighlightsResult',
    'ReelItem',
    'ReelsResult',
    'HashtagSection',
    'LocationSection',
]




# ---------------------------------------------------------------------------
# v3 namespace alias
# ---------------------------------------------------------------------------
#
# v3 is the supported, refactored API. Legacy symbols above continue to
# work for backwards compatibility but are not maintained for new
# features. See ARCHITECTURE.md for the design and migration plan.
#
# Recommended new code::
#
#     from instaharvest.v3 import InstaHarvest, Settings
#
#     with InstaHarvest(Settings.default()) as ih:
#         profile = ih.profile.scrape("instagram")
#
# The leading-underscore module ``instaharvest._v3`` remains the
# canonical location of the implementation; ``instaharvest.v3`` is a
# clean public alias provided here.

from instaharvest import _v3 as v3  # noqa: E402  (alias must follow legacy imports)

# Register the alias in sys.modules so ``from instaharvest.v3 import X`` works
# (a plain attribute alias only supports ``instaharvest.v3.X``, not the
# ``from`` form, because Python's import machinery looks up sub-modules in
# ``sys.modules``, not in the parent module's namespace).
import sys as _sys  # noqa: E402

_sys.modules.setdefault("instaharvest.v3", v3)

__all__.append("v3")
