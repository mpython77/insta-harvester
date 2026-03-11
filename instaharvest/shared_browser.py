"""
Instagram Shared Browser Manager
Single browser instance shared across all operations
"""

import time
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from .config import ScraperConfig
from .logging_config import get_logger
from .follow import FollowManager
from .message import MessageManager
from .followers import FollowersCollector
from .profile import ProfileScraper
from .post_links import PostLinksScraper
from .reel_links import ReelLinksScraper
from .downloader import MediaDownloader
from .post_data import PostDataScraper, PostData
from .reel_data import ReelDataScraper, ReelData
from .story_scraper import StoryScraper, StoryResult
from .comment_scraper import CommentScraper
from .search_api import SearchAPI
from .hashtag_scraper import HashtagScraper
from .location_scraper import LocationScraper
from .explore_scraper import ExploreScraper
from .notifications import NotificationReader
from .web_api import (
    InstagramWebAPI, WebProfileData, WebSearchResult, SearchUserResult,
    FollowUserItem, FollowListResult, FriendshipStatus,
    FeedPost, UserFeedResult, MediaInfo, CommentItem, CommentsResult,
    LikerItem, LikersResult, StoryMediaItem, StoriesTrayResult,
    HighlightInfo, HighlightsResult, ReelItem, ReelsResult,
    HashtagSection, LocationSection
)


class SharedBrowser:
    """
    Shared Browser Manager - Single browser for all operations

    Opens browser once and reuses it for all operations:
    - Follow/Unfollow
    - Send messages
    - Collect followers/following
    - Scrape profiles
    - Collect links
    - etc.

    Example:
        >>> with SharedBrowser() as browser:
        ...     browser.follow("username")
        ...     browser.send_message("username", "Hello!")
        ...     followers = browser.get_followers("username", limit=50)
        ...     browser.scrape_profile("username")

    Or manual usage:
        >>> browser = SharedBrowser()
        >>> browser.start()
        >>> browser.follow("username")
        >>> browser.send_message("username", "Hello!")
        >>> followers = browser.get_followers("username", limit=100)
        >>> browser.close()
    """

    def __init__(self, config: Optional[ScraperConfig] = None, session_file: Optional[str] = None):
        """
        Initialize Shared Browser

        Args:
            config: Scraper configuration (optional)
            session_file: Path to session file
        """
        self.config = config or ScraperConfig()
        self.session_file = session_file if session_file is not None else self.config.session_file
        self.logger = get_logger('SharedBrowser')

        # Browser components
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Manager instances (will be created after browser starts)
        self._follow_manager: Optional[FollowManager] = None
        self._message_manager: Optional[MessageManager] = None
        self._followers_collector: Optional[FollowersCollector] = None
        self._profile_scraper: Optional[ProfileScraper] = None
        self._post_links_scraper: Optional[PostLinksScraper] = None
        self._reel_links_scraper: Optional[ReelLinksScraper] = None
        self._downloader: Optional[MediaDownloader] = None
        # Phase 2: New scrapers
        self._post_data_scraper: Optional[PostDataScraper] = None
        self._reel_data_scraper: Optional[ReelDataScraper] = None
        self._story_scraper: Optional[StoryScraper] = None
        self._comment_scraper: Optional[CommentScraper] = None
        self._search_api: Optional[SearchAPI] = None
        self._hashtag_scraper: Optional[HashtagScraper] = None
        self._location_scraper: Optional[LocationScraper] = None
        self._explore_scraper: Optional[ExploreScraper] = None
        self._notification_reader: Optional[NotificationReader] = None
        self._web_api: Optional[InstagramWebAPI] = None

        self.logger.info("✨ SharedBrowser initialized")

    def start(self, headless: bool = None) -> None:
        """
        Start browser session

        Args:
            headless: Run browser in headless mode (default: use config.headless)

        This opens browser once and loads the session.
        All subsequent operations will reuse this browser.
        """
        # Use provided headless value, or fall back to config
        if headless is None:
            headless = self.config.headless
        self.logger.info("🚀 Starting shared browser session...")

        # Load session
        import json
        from pathlib import Path

        session_path = Path(self.session_file)
        if not session_path.exists():
            raise FileNotFoundError(
                f"Session file '{self.session_file}' not found. "
                f"Run save_session.py first."
            )

        with open(self.session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        self.logger.info(f"📂 Session loaded: {len(session_data.get('cookies', []))} cookies")

        # Start Playwright
        self.playwright = sync_playwright().start()

        # Prepare launch options
        launch_options = {'headless': headless}
        if self.config.browser_channel and self.config.browser_channel != 'chromium':
            launch_options['channel'] = self.config.browser_channel

        # Launch browser with retry logic for headless mode
        try:
            self.browser = self.playwright.chromium.launch(**launch_options)
        except Exception as launch_error:
            error_msg = str(launch_error)
            
            # RETRY LOGIC: If "Old Headless" error, try launching in NEW HEADLESS mode
            if "Old Headless mode" in error_msg or "Old Headless" in error_msg:
                self.logger.warning("System Chrome rejected 'Old Headless' mode. Retrying with 'new' Headless...")
                launch_options['headless'] = 'new'
                try:
                    self.browser = self.playwright.chromium.launch(**launch_options)
                except Exception as retry_error:
                    # If New Headless also fails, try HEADFUL as last resort
                    self.logger.warning("New Headless also failed. Retrying in HEADFUL mode...")
                    launch_options['headless'] = False
                    self.browser = self.playwright.chromium.launch(**launch_options)
            else:
                raise launch_error
        
        self.logger.info(f"🌐 Browser launched (headless={launch_options.get('headless', headless)})")

        # Create context with session
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            user_agent=self.config.user_agent,
            locale=self.config.locale
        )

        # Create page
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config.default_timeout)

        # Visit Instagram to activate session
        self.logger.info("🔄 Activating session...")
        self.page.goto(self.config.instagram_base_url, wait_until='domcontentloaded', timeout=self.config.session_activation_timeout)
        time.sleep(self.config.page_stability_delay)

        # Update session
        self._update_session()

        self.logger.info("✅ Shared browser ready! All operations will use this browser.")

    def close(self) -> None:
        """Close browser and cleanup"""
        self.logger.info("🔒 Closing shared browser...")

        # Update session before closing
        if self.context:
            self._update_session()

        # Clean up manager instances
        if self._follow_manager:
            self._follow_manager.playwright = None
            self._follow_manager.browser = None
            self._follow_manager.context = None
            self._follow_manager.page = None
            self._follow_manager = None

        if self._message_manager:
            self._message_manager.playwright = None
            self._message_manager.browser = None
            self._message_manager.context = None
            self._message_manager.page = None
            self._message_manager = None

        if self._followers_collector:
            self._followers_collector.playwright = None
            self._followers_collector.browser = None
            self._followers_collector.context = None
            self._followers_collector.page = None
            self._followers_collector = None

        if self._profile_scraper:
            self._profile_scraper.playwright = None
            self._profile_scraper.browser = None
            self._profile_scraper.context = None
            self._profile_scraper.page = None
            self._profile_scraper = None

        if self._post_links_scraper:
            self._post_links_scraper.playwright = None
            self._post_links_scraper.browser = None
            self._post_links_scraper.context = None
            self._post_links_scraper.page = None
            self._post_links_scraper = None

        if self._reel_links_scraper:
            self._reel_links_scraper.playwright = None
            self._reel_links_scraper.browser = None
            self._reel_links_scraper.context = None
            self._reel_links_scraper.page = None
            self._reel_links_scraper = None

        if self._downloader:
            self._downloader = None

        # Phase 2 scrapers cleanup
        for attr in [
            '_post_data_scraper', '_reel_data_scraper', '_story_scraper',
            '_comment_scraper', '_search_api', '_hashtag_scraper',
            '_location_scraper', '_explore_scraper', '_notification_reader'
        ]:
            instance = getattr(self, attr, None)
            if instance:
                for component in ['playwright', 'browser', 'context', 'page']:
                    if hasattr(instance, component):
                        setattr(instance, component, None)
                setattr(self, attr, None)


        # Close browser resources
        # Close browser resources — each in its own try/except
        # so a failure in one doesn't prevent cleanup of others
        for resource, action, name in [
            (self.page, lambda r: r.close(), 'page'),
            (self.context, lambda r: r.close(), 'context'),
            (self.browser, lambda r: r.close(), 'browser'),
            (self.playwright, lambda r: r.stop(), 'playwright'),
        ]:
            if resource:
                try:
                    action(resource)
                except Exception as e:
                    self.logger.warning(f"Error closing {name}: {e}")

        self.logger.info("✅ Browser closed")

    def _update_session(self) -> None:
        """Update and save session"""
        try:
            import json
            import inspect
            
            result = self.context.storage_state()
            
            # Handle case where storage_state returns a coroutine
            # (can happen with certain Playwright versions)
            if inspect.iscoroutine(result):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # Can't await in sync context with running loop
                        # Fall back to reading existing session file
                        self.logger.debug("⚠ storage_state returned coroutine, skipping update")
                        result.close()  # Prevent "was never awaited" warning
                        return
                    else:
                        result = loop.run_until_complete(result)
                except RuntimeError:
                    result.close()
                    return
            
            storage_state = result

            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f, indent=2)

            self.logger.debug(f"✓ Session updated: {len(storage_state.get('cookies', []))} cookies")
        except Exception as e:
            self.logger.warning(f"Failed to update session: {e}")

    # ==================== MANAGER PROPERTIES ====================

    @property
    def follow_manager(self) -> FollowManager:
        """Get FollowManager instance (lazy loading)"""
        if self._follow_manager is None:
            manager = FollowManager(self.config)
            # Inject existing browser components
            manager.playwright = self.playwright
            manager.browser = self.browser
            manager.context = self.context
            manager.page = self.page
            self._follow_manager = manager
        return self._follow_manager

    @property
    def message_manager(self) -> MessageManager:
        """Get MessageManager instance (lazy loading)"""
        if self._message_manager is None:
            manager = MessageManager(self.config)
            # Inject existing browser components
            manager.playwright = self.playwright
            manager.browser = self.browser
            manager.context = self.context
            manager.page = self.page
            self._message_manager = manager
        return self._message_manager

    @property
    def followers_collector(self) -> FollowersCollector:
        """Get FollowersCollector instance (lazy loading)"""
        if self._followers_collector is None:
            collector = FollowersCollector(self.config)
            # Inject existing browser components
            collector.playwright = self.playwright
            collector.browser = self.browser
            collector.context = self.context
            collector.page = self.page
            self._followers_collector = collector
        return self._followers_collector

    @property
    def profile_scraper(self) -> ProfileScraper:
        """Get ProfileScraper instance (lazy loading)"""
        if self._profile_scraper is None:
            scraper = ProfileScraper(self.config)
            # Inject existing browser components
            scraper.playwright = self.playwright
            scraper.browser = self.browser
            scraper.context = self.context
            scraper.page = self.page
            self._profile_scraper = scraper
        return self._profile_scraper

    @property
    def post_links_scraper(self) -> PostLinksScraper:
        """Get PostLinksScraper instance (lazy loading)"""
        if self._post_links_scraper is None:
            scraper = PostLinksScraper(self.config)
            # Inject existing browser components
            scraper.playwright = self.playwright
            scraper.browser = self.browser
            scraper.context = self.context
            scraper.page = self.page
            self._post_links_scraper = scraper
        return self._post_links_scraper

    @property
    def reel_links_scraper(self) -> ReelLinksScraper:
        """Get ReelLinksScraper instance (lazy loading)"""
        if self._reel_links_scraper is None:
            scraper = ReelLinksScraper(self.config)
            # Inject existing browser components
            scraper.playwright = self.playwright
            scraper.browser = self.browser
            scraper.context = self.context
            scraper.page = self.page
            self._reel_links_scraper = scraper
        return self._reel_links_scraper

    @property
    def downloader(self) -> MediaDownloader:
        """Get MediaDownloader instance"""
        if self._downloader is None:
            self._downloader = MediaDownloader()
        return self._downloader

    # ==================== PHASE 2: NEW SCRAPER PROPERTIES ====================

    def _inject_browser(self, scraper):
        """Inject shared browser components into any scraper instance"""
        scraper.playwright = self.playwright
        scraper.browser = self.browser
        scraper.context = self.context
        scraper.page = self.page
        return scraper

    @property
    def post_data_scraper(self) -> PostDataScraper:
        """Get PostDataScraper instance (lazy loading)"""
        if self._post_data_scraper is None:
            self._post_data_scraper = self._inject_browser(PostDataScraper(self.config))
        return self._post_data_scraper

    @property
    def reel_data_scraper(self) -> ReelDataScraper:
        """Get ReelDataScraper instance (lazy loading)"""
        if self._reel_data_scraper is None:
            self._reel_data_scraper = self._inject_browser(ReelDataScraper(self.config))
        return self._reel_data_scraper

    @property
    def story_scraper(self) -> StoryScraper:
        """Get StoryScraper instance (lazy loading)"""
        if self._story_scraper is None:
            self._story_scraper = self._inject_browser(StoryScraper(self.config))
        return self._story_scraper

    @property
    def comment_scraper(self) -> CommentScraper:
        """Get CommentScraper instance (lazy loading)"""
        if self._comment_scraper is None:
            self._comment_scraper = self._inject_browser(CommentScraper(self.config))
        return self._comment_scraper

    @property
    def search_api(self) -> SearchAPI:
        """Get SearchAPI instance (lazy loading)"""
        if self._search_api is None:
            self._search_api = self._inject_browser(SearchAPI(self.config))
        return self._search_api

    @property
    def hashtag_scraper(self) -> HashtagScraper:
        """Get HashtagScraper instance (lazy loading)"""
        if self._hashtag_scraper is None:
            self._hashtag_scraper = self._inject_browser(HashtagScraper(self.config))
        return self._hashtag_scraper

    @property
    def location_scraper(self) -> LocationScraper:
        """Get LocationScraper instance (lazy loading)"""
        if self._location_scraper is None:
            self._location_scraper = self._inject_browser(LocationScraper(self.config))
        return self._location_scraper

    @property
    def explore_scraper(self) -> ExploreScraper:
        """Get ExploreScraper instance (lazy loading)"""
        if self._explore_scraper is None:
            self._explore_scraper = self._inject_browser(ExploreScraper(self.config))
        return self._explore_scraper

    @property
    def notification_reader(self) -> NotificationReader:
        """Get NotificationReader instance (lazy loading)"""
        if self._notification_reader is None:
            self._notification_reader = self._inject_browser(NotificationReader(self.config))
        return self._notification_reader

    @property
    def web_api(self) -> InstagramWebAPI:
        """Get InstagramWebAPI instance (lazy loading)"""
        if self._web_api is None:
            self._web_api = InstagramWebAPI(
                page=self.page,
                config=self.config,
                logger=self.logger
            )
        return self._web_api

    # ==================== CONVENIENCE METHODS ====================

    def get_profile_json(self, username: str) -> Optional[WebProfileData]:
        """
        Get complete profile data via Instagram Web API (JSON).

        Returns exact follower counts, business info, bio links etc.
        Much faster and more accurate than DOM scraping.

        Args:
            username: Instagram username (without @)

        Returns:
            WebProfileData object or None if failed

        Example:
            >>> with SharedBrowser() as browser:
            ...     profile = browser.get_profile_json('mondayswimwear')
            ...     print(f"{profile.full_name}: {profile.follower_count:,}")
            Monday Swimwear: 1,069,117
        """
        return self.web_api.get_profile(username)

    def get_user_info(self, user_id: str) -> Optional[WebProfileData]:
        """
        Get profile data by user ID via Web API.

        Args:
            user_id: Instagram numeric user ID

        Returns:
            WebProfileData object or None
        """
        return self.web_api.get_user_info(user_id)

    def search_users(self, query: str, limit: int = 20) -> WebSearchResult:
        """
        Search for Instagram users via Web API.

        Args:
            query: Search query string
            limit: Max results

        Returns:
            WebSearchResult with matched users

        Example:
            >>> with SharedBrowser() as browser:
            ...     results = browser.search_users('swimwear brand')
            ...     for user in results.users:
            ...         print(f"@{user.username}")
        """
        return self.web_api.search(query, limit=limit)

    def fetch_raw_api(self, endpoint: str, params: dict = None, method: str = 'GET', body: dict = None) -> Optional[dict]:
        """Make raw API call to any Instagram endpoint (GET or POST)."""
        return self.web_api.fetch_raw(endpoint, params, method=method, body=body)

    def get_followers_api(self, user_id: str, count: int = 50, max_id: str = None) -> FollowListResult:
        """Get followers list via Web API (paginated)."""
        return self.web_api.get_followers(user_id, count, max_id)

    def get_following_api(self, user_id: str, count: int = 50, max_id: str = None) -> FollowListResult:
        """Get following list via Web API (paginated)."""
        return self.web_api.get_following(user_id, count, max_id)

    def get_friendship_status(self, user_id: str) -> FriendshipStatus:
        """Check friendship status with user."""
        return self.web_api.get_friendship_status(user_id)

    def get_user_feed_api(self, user_id: str, count: int = 12) -> UserFeedResult:
        """Get user's posts via Web API."""
        return self.web_api.get_user_feed(user_id, count)

    def get_media_info_api(self, media_id: str) -> Optional[MediaInfo]:
        """Get detailed post info via Web API."""
        return self.web_api.get_media_info(media_id)

    def get_media_comments_api(self, media_id: str) -> CommentsResult:
        """Get post comments via Web API."""
        return self.web_api.get_media_comments(media_id)

    def get_media_likers_api(self, media_id: str) -> LikersResult:
        """Get post likers via Web API."""
        return self.web_api.get_media_likers(media_id)

    def get_stories_api(self, user_id: str) -> list:
        """Get user's active stories via Web API."""
        return self.web_api.get_stories(user_id)

    def get_highlights_api(self, user_id: str) -> HighlightsResult:
        """Get user's highlights via Web API."""
        return self.web_api.get_highlights(user_id)

    def get_reels_api(self, user_id: str) -> ReelsResult:
        """Get user's reels via Web API."""
        return self.web_api.get_reels(user_id)

    def get_hashtag_feed_api(self, tag: str) -> HashtagSection:
        """Get hashtag posts via Web API."""
        return self.web_api.get_hashtag_feed(tag)

    def get_location_feed_api(self, location_id: str) -> LocationSection:
        """Get location posts via Web API."""
        return self.web_api.get_location_feed(location_id)

    def get_tagged_posts_api(self, user_id: str) -> UserFeedResult:
        """Get tagged posts via Web API."""
        return self.web_api.get_tagged_posts(user_id)

    def follow(self, username: str, check_status: bool = True) -> dict:
        """
        Follow a user

        Args:
            username: Instagram username
            check_status: Check if already following

        Returns:
            Result dict
        """
        return self.follow_manager.follow(username, check_status=check_status)

    def unfollow(self, username: str, confirm: bool = True) -> dict:
        """
        Unfollow a user

        Args:
            username: Instagram username
            confirm: Confirm unfollow in popup

        Returns:
            Result dict
        """
        return self.follow_manager.unfollow(username, confirm=confirm)

    def is_following(self, username: str) -> dict:
        """
        Check if following a user

        Args:
            username: Instagram username

        Returns:
            Result dict with 'following' key
        """
        return self.follow_manager.is_following(username)

    def send_message(self, username: str, message: str) -> dict:
        """
        Send direct message

        Args:
            username: Instagram username
            message: Message text

        Returns:
            Result dict
        """
        return self.message_manager.send_message(username, message)

    def batch_follow(self, usernames: list, delay_between: tuple = (2, 4)) -> dict:
        """
        Follow multiple users

        Args:
            usernames: List of usernames
            delay_between: Delay range (min, max)

        Returns:
            Summary dict
        """
        return self.follow_manager.batch_follow(usernames, delay_between=delay_between)

    def batch_send(self, usernames: list, message: str, delay_between: tuple = (3, 5)) -> dict:
        """
        Send message to multiple users

        Args:
            usernames: List of usernames
            message: Message text
            delay_between: Delay range (min, max)

        Returns:
            Summary dict
        """
        return self.message_manager.batch_send(usernames, message, delay_between=delay_between)

    def scrape_profile(self, username: str) -> dict:
        """
        Scrape profile statistics

        Args:
            username: Instagram username
        
        Returns:
            Profile data dict
        """
        from .profile import ProfileData
        data = self.profile_scraper.scrape(username)
        if isinstance(data, ProfileData):
            return data.to_dict()
        return data

    def get_followers(self, username: str, limit: Optional[int] = None, print_realtime: bool = True) -> list:
        """
        Collect followers from a profile

        Args:
            username: Instagram username
            limit: Maximum number of followers to collect (None = all)
            print_realtime: Print followers in real-time as discovered

        Returns:
            List of follower usernames
        """
        return self.followers_collector.get_followers(username, limit=limit, print_realtime=print_realtime)

    def get_following(self, username: str, limit: Optional[int] = None, print_realtime: bool = True) -> list:
        """
        Collect following list from a profile

        Args:
            username: Instagram username
            limit: Maximum number to collect (None = all)
            print_realtime: Print in real-time as discovered

        Returns:
            List of following usernames
        """
        return self.followers_collector.get_following(username, limit=limit, print_realtime=print_realtime)

    def scrape_post_links(self, username: str, target_count: Optional[int] = None, save_to_file: bool = True) -> list:
        """
        Scrape post and reel links from a profile

        Args:
            username: Instagram username
            target_count: Target number of links (None = scrape all)
            save_to_file: Save links to file

        Returns:
            List of dictionaries with 'url' and 'type' keys
        """
        return self.post_links_scraper.scrape(username, target_count=target_count, save_to_file=save_to_file)

    def scrape_reel_links(self, username: str, save_to_file: bool = True) -> list:
        """
        Scrape reel links from a profile

        Args:
            username: Instagram username
            save_to_file: Save links to file

        Returns:
            List of reel URLs
        """
        return self.reel_links_scraper.scrape(username, save_to_file=save_to_file)

    # ==================== PHASE 2: NEW CONVENIENCE METHODS ====================

    def scrape_post(self, url: str, **kwargs) -> PostData:
        """
        Scrape data from a single post

        Args:
            url: Post URL
            **kwargs: Additional args (get_tags, get_likes, get_timestamp)

        Returns:
            PostData object with all extracted data
        """
        self._ensure_started()
        return self.post_data_scraper.scrape(url, **kwargs)

    def scrape_posts(self, urls: list, **kwargs) -> list:
        """
        Scrape data from multiple posts sequentially

        Args:
            urls: List of post URLs
            **kwargs: Additional args

        Returns:
            List of PostData objects
        """
        self._ensure_started()
        return self.post_data_scraper.scrape_multiple(urls, **kwargs)

    def scrape_reel(self, url: str, **kwargs) -> ReelData:
        """
        Scrape data from a single reel

        Args:
            url: Reel URL
            **kwargs: Additional args

        Returns:
            ReelData object
        """
        self._ensure_started()
        return self.reel_data_scraper.scrape(url, **kwargs)

    def scrape_reels(self, urls: list, **kwargs) -> list:
        """
        Scrape data from multiple reels

        Args:
            urls: List of reel URLs
            **kwargs: Additional args

        Returns:
            List of ReelData objects
        """
        self._ensure_started()
        return self.reel_data_scraper.scrape_multiple(urls, **kwargs)

    def scrape_stories(self, username: str, **kwargs) -> StoryResult:
        """
        Scrape stories from a user

        Args:
            username: Instagram username
            **kwargs: Additional args (extract_tags, challenge_delay)

        Returns:
            StoryResult object
        """
        self._ensure_started()
        return self.story_scraper.scrape(username, **kwargs)

    def scrape_comments(self, post_url: str, **kwargs):
        """
        Scrape comments from a post

        Args:
            post_url: Post URL
            **kwargs: Additional args (target_count, etc.)

        Returns:
            Comment data
        """
        self._ensure_started()
        return self.comment_scraper.scrape(post_url, **kwargs)

    def search(self, query: str, search_type: str = 'all'):
        """
        Search Instagram

        Args:
            query: Search query
            search_type: Type of search (all, users, hashtags, places)

        Returns:
            SearchResult object
        """
        self._ensure_started()
        return self.search_api.scrape(query, search_type=search_type)

    def scrape_hashtag(self, hashtag: str, **kwargs):
        """
        Scrape posts from a hashtag

        Args:
            hashtag: Hashtag name (without #)
            **kwargs: Additional args

        Returns:
            HashtagResult object
        """
        self._ensure_started()
        return self.hashtag_scraper.scrape(hashtag, **kwargs)

    def read_notifications(self, **kwargs):
        """
        Read Instagram notifications

        Returns:
            List of NotificationItem objects
        """
        self._ensure_started()
        return self.notification_reader.scrape(**kwargs)

    def download_post(self, url: str) -> list:
        """
        Download all media (images/videos) from a post URL.
        Handles Carousels automatically.
        
        Args:
            url: Post URL
        
        Returns:
            List of saved file paths
        """
        self.logger.info(f"📥 Starting download for: {url}")
        self._ensure_started()
        
        # Use the shared PostDataScraper
        post_data = self.post_data_scraper.scrape(url, get_media=True)
        
        username = "unknown"
        if hasattr(post_data, 'owner') and post_data.owner:
            username = post_data.owner.username or "unknown"
        
        return self.downloader.download_post(post_data, username=username)

    def scrape_tagged_posts(self, username: str, target_count: int = 50) -> 'TaggedPostsResult':
        """
        Scrape posts where a user has been tagged by others.

        Args:
            username: Instagram username
            target_count: Maximum posts to collect

        Returns:
            TaggedPostsResult with tagged posts
        """
        from .tagged_posts import TaggedPostsScraper, TaggedPostsResult
        self._ensure_started()
        
        scraper = self._inject_browser(TaggedPostsScraper(config=self.config))
        
        result = scraper.scrape(username, target_count=target_count)
        self.logger.info(
            f"🏷️ Tagged: {result.total_found} posts, "
            f"{len(result.unique_taggers)} unique taggers"
        )
        return result

    def scrape_highlight(self, highlight_id: str, max_slides: int = 500) -> 'HighlightResult':
        """
        Scrape all slides from an Instagram highlight.

        Args:
            highlight_id: Highlight ID or full URL
            max_slides: Maximum slides to collect

        Returns:
            HighlightResult with slides, stickers, music, etc.
        """
        from .highlight_scraper import HighlightsScraper, HighlightResult
        self._ensure_started()
        
        scraper = HighlightsScraper(config=self.config)
        scraper.page = self.page
        scraper.browser = self.browser
        scraper.context = self.context
        
        result = scraper.scrape(highlight_id, max_slides=max_slides)
        self.logger.info(
            f"🌟 Highlight: {result.slide_count} slides, "
            f"{len(result.all_mentions)} mentions"
        )
        return result

    def list_highlights(self, username: str) -> list:
        """List all highlights for a user. Returns List[HighlightInfo]."""
        from .highlight_scraper import HighlightsScraper
        self._ensure_started()
        scraper = HighlightsScraper(config=self.config)
        scraper.page = self.page
        scraper.browser = self.browser
        scraper.context = self.context
        return scraper.list_highlights(username)

    def scrape_all_highlights(self, username: str, max_slides_per: int = 200) -> 'HighlightsListResult':
        """Scrape ALL highlights for a user sequentially."""
        from .highlight_scraper import HighlightsScraper, HighlightsListResult
        self._ensure_started()
        scraper = HighlightsScraper(config=self.config)
        scraper.page = self.page
        scraper.browser = self.browser
        scraper.context = self.context
        return scraper.scrape_all(username, max_slides_per=max_slides_per)

    # ==================== AUTO-START GUARD ====================

    def _ensure_started(self) -> None:
        """
        Ensure browser is started before performing operations.

        If the browser is not running, automatically calls start().
        This makes the library automation-friendly — users can call
        any method without manually calling start() first.

        Raises:
            RuntimeError: If browser cannot be started
        """
        if self.page is None or self.browser is None:
            self.logger.info("🔄 Browser not started yet, auto-starting...")
            try:
                self.start()
            except Exception as e:
                raise RuntimeError(
                    f"Failed to auto-start browser: {e}. "
                    f"Make sure session file exists at '{self.session_file}'. "
                    f"Run save_session.py first."
                ) from e

    # ==================== CONTEXT MANAGER ====================

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit — always closes browser, never suppresses exceptions"""
        self.close()
        if exc_type:
            self.logger.error(f"Error during operations: {exc_val}")
        return False  # Never suppress exceptions — let them propagate
