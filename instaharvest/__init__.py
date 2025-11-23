"""
InstaHarvest 🌾 - Professional Instagram Data Collection Toolkit

A powerful and efficient Instagram automation library for data collection,
engagement management, and analytics.

Features:
- 📊 Profile statistics (posts, followers, following)
- 🔗 Post & Reel links collection with intelligent scrolling
- 🏷️ Tagged accounts extraction (posts & reels)
- 👥 Followers/Following collection with real-time output
- 💬 Direct messaging with smart rate limiting
- 🤝 Follow/Unfollow management
- ⚡ Parallel processing - Scrape multiple posts simultaneously
- 📑 Real-time Excel export
- 🌐 Shared browser sessions - Single browser for all operations
- 🔍 HTML structure change detection
- 📝 Professional logging
- 🧩 Modular design for library usage

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

Author: Artem
Version: 2.5.0
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
from .post_links import PostLinksScraper
from .post_data import PostDataScraper, PostData
from .reel_links import ReelLinksScraper
from .reel_data import ReelDataScraper, ReelData
from .parallel_scraper import ParallelPostDataScraper
from .excel_export import ExcelExporter
from .follow import FollowManager
from .message import MessageManager
from .followers import FollowersCollector
from .shared_browser import SharedBrowser
from .orchestrator import InstagramOrchestrator, quick_scrape

__version__ = '2.5.0'
__author__ = 'Artem'
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
    'PostDataScraper',
    'ReelLinksScraper',
    'ReelDataScraper',
    'ParallelPostDataScraper',
    'FollowManager',
    'MessageManager',
    'FollowersCollector',
    'SharedBrowser',

    # Data structures
    'ProfileData',
    'PostData',
    'ReelData',

    # Export
    'ExcelExporter',

    # Orchestrator
    'InstagramOrchestrator',
    'quick_scrape',
]
