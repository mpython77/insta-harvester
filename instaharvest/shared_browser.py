"""
Instagram Shared Browser Manager
Single browser instance shared across all operations
"""

import time
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from .config import ScraperConfig
from .logger import setup_logger
from .follow import FollowManager
from .message import MessageManager
from .followers import FollowersCollector
from .profile import ProfileScraper
from .post_links import PostLinksScraper
from .reel_links import ReelLinksScraper


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
        self.logger = setup_logger(
            name='SharedBrowser',
            log_file=self.config.log_file,
            level=self.config.log_level,
            log_to_console=self.config.log_to_console
        )

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

        # Launch browser
        self.browser = self.playwright.chromium.launch(
            channel=self.config.browser_channel,
            headless=headless
        )
        self.logger.info(f"🌐 Browser launched (headless={headless})")

        # Create context with session
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            user_agent=self.config.user_agent
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

        # Close browser resources
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

        self.logger.info("✅ Browser closed")

    def _update_session(self) -> None:
        """Update and save session"""
        try:
            import json
            storage_state = self.context.storage_state()

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

    # ==================== CONVENIENCE METHODS ====================

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

    # ==================== CONTEXT MANAGER ====================

    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        if exc_type:
            self.logger.error(f"Error during operations: {exc_val}")
