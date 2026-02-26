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
        max_comments=100,
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

Author: Muydinov Doston
Version: 2.8.0
License: MIT
"""

from .config import ScraperConfig
from .exceptions import (
    InstagramScraperError,
    SessionNotFoundError,
    ProfileNotFoundError,
    HTMLStructureChangedError,
    PageLoadError,
    RateLimitError,
    LoginRequiredError
)
from .base import BaseScraper
from .profile import ProfileScraper, ProfileData
from .post_links import InstagramPostLinksScraper, PostLinksScraper
from .post_data import PostDataScraper, PostData
from .reel_links import ReelLinksScraper
from .reel_data import ReelDataScraper, ReelData
from .parallel_scraper import ParallelPostDataScraper

from .comment_scraper import CommentScraper, PostCommentsData
from .models import CommentData, CommentAuthor, Collaborator, Comment
from .exporters import CommentsExporter, RealTimeCommentsExporter, export_comments_to_json, export_comments_to_excel, ExcelExporter
from .follow import FollowManager
from .message import MessageManager
from .followers import FollowersCollector
from .shared_browser import SharedBrowser
from .orchestrator import InstagramOrchestrator, quick_scrape
from .session_utils import (
    save_session, 
    check_session_exists, 
    load_session_data, 
    get_default_session_path,
    find_session_file,
    get_session_save_path,
    SESSION_FILENAME
)
from .stealth import StealthManager
from .proxy import ProxyManager
from .logging_config import SmartLogger, get_logger
from .core import InstaHarvest
from .notifications import NotificationReader, NotificationItem
from .webhooks import EventEmitter, FollowerWatcher, Event, EventTypes
from .batch_downloader import BatchDownloader, DownloadTask, DownloadResult, BatchResult, ProgressTracker
from .async_engine import AsyncBaseScraper, AsyncProfileScraper, AsyncBatchScraper


__version__ = '2.8.0'
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

    # Data structures
    'ProfileData',
    'PostData',
    'ReelData',
    'CommentData',
    'CommentAuthor',
    'PostCommentsData',
    'Collaborator',

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
]

