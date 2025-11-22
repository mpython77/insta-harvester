"""
Instagram Scraper - Professional Instagram scraping library

Features:
- Profile statistics (posts, followers, following)
- Post links collection with intelligent scrolling
- Reel links collection (SEPARATE from posts)
- Post data extraction (tags, likes, timestamps)
- Reel data extraction (SEPARATE from posts)
- Complete workflow orchestration
- **Parallel processing** - Scrape multiple posts simultaneously
- **Excel export** - Real-time data export to Excel
- **Follow/Unfollow management** - Professional follow operations with rate limiting
- HTML structure change detection
- Professional logging
- Modular design for library usage

Usage:
    # Simple usage
    from instagram_scraper import quick_scrape
    results = quick_scrape('username')

    # Advanced usage with parallel processing and Excel
    from instagram_scraper import InstagramOrchestrator, ScraperConfig

    config = ScraperConfig(headless=True)
    orchestrator = InstagramOrchestrator(config)

    results = orchestrator.scrape_complete_profile_advanced(
        'username',
        parallel=3,        # 3 parallel browser tabs
        save_excel=True    # Real-time Excel export
    )

    # Follow/Unfollow management
    from instagram_scraper import FollowManager

    manager = FollowManager()
    manager.setup_browser(session_data)
    result = manager.follow('username')

Author: AI Assistant
Version: 2.2.0 (Added Follow/Unfollow Management)
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
from .orchestrator import InstagramOrchestrator, quick_scrape

__version__ = '2.2.0'
__author__ = 'AI Assistant'

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
