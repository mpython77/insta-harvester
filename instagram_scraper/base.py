"""
Instagram Scraper - Base scraper class
Professional base class with error handling, logging, and retry logic
"""

import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from .config import ScraperConfig
from .exceptions import (
    SessionNotFoundError,
    PageLoadError,
    HTMLStructureChangedError,
    LoginRequiredError
)
from .logger import setup_logger


class BaseScraper(ABC):
    """
    Base scraper class with common functionality

    Features:
    - Session management
    - Browser automation
    - Error handling with retries
    - Professional logging
    - HTML structure change detection
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize base scraper

        Args:
            config: Scraper configuration (uses defaults if None)
        """
        self.config = config or ScraperConfig()
        self.logger = setup_logger(
            name=self.__class__.__name__,
            log_file=self.config.log_file,
            level=self.config.log_level,
            log_to_console=self.config.log_to_console
        )

        # Browser state
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        self.logger.info(f"{self.__class__.__name__} initialized")

    def check_session_exists(self) -> None:
        """Check if session file exists"""
        session_path = Path(self.config.session_file)
        if not session_path.exists():
            self.logger.error(f"Session file not found: {self.config.session_file}")
            raise SessionNotFoundError(
                f"Session file '{self.config.session_file}' not found. "
                f"Run save_session.py first."
            )
        self.logger.debug(f"Session file found: {self.config.session_file}")

    def load_session(self) -> Dict[str, Any]:
        """
        Load session from file

        Returns:
            Session data dictionary
        """
        self.logger.info("Loading session...")
        self.check_session_exists()

        try:
            with open(self.config.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            self.logger.info(f"Session loaded: {len(session_data.get('cookies', []))} cookies")
            return session_data
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid session file format: {e}")
            raise SessionNotFoundError(f"Invalid session file: {e}")

    def setup_browser(self, session_data: Optional[Dict] = None) -> None:
        """
        Setup browser with Playwright

        Args:
            session_data: Optional session data for authenticated browsing
        """
        self.logger.info("Setting up browser...")

        if self.playwright is None:
            self.playwright = sync_playwright().start()

        # Launch browser with real Chrome
        self.browser = self.playwright.chromium.launch(
            channel='chrome',  # Use real Chrome instead of Chromium
            headless=self.config.headless,
            args=['--start-maximized'] if not self.config.headless else []
        )
        self.logger.debug(f"Browser launched (Chrome, headless={self.config.headless})")

        # Create context
        context_options = {
            'viewport': {
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            'user_agent': self.config.user_agent
        }

        if session_data:
            context_options['storage_state'] = session_data
            self.logger.debug("Context created with session data")

        self.context = self.browser.new_context(**context_options)

        # Create page
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config.default_timeout)
        self.logger.info("Browser setup complete")

    def goto_url(
        self,
        url: str,
        wait_until: str = 'domcontentloaded',
        delay: Optional[float] = None
    ) -> bool:
        """
        Navigate to URL with error handling

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation successful
            delay: Optional custom delay after navigation

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Navigating to: {url}")

        for attempt in range(self.config.max_retries):
            try:
                self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.config.navigation_timeout
                )

                # Delay after page load
                sleep_time = delay if delay is not None else self.config.page_load_delay
                self.logger.debug(f"Page loaded, waiting {sleep_time}s...")
                time.sleep(sleep_time)

                # Check if login required
                if self._is_login_page():
                    self.logger.error("Login page detected - session expired")
                    raise LoginRequiredError("Session expired, login required")

                self.logger.info(f"Successfully navigated to: {url}")
                return True

            except Exception as e:
                self.logger.warning(
                    f"Navigation attempt {attempt + 1}/{self.config.max_retries} failed: {e}"
                )
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay)
                else:
                    self.logger.error(f"Failed to navigate to {url} after {self.config.max_retries} attempts")
                    raise PageLoadError(f"Failed to load page: {url}")

        return False

    def _is_login_page(self) -> bool:
        """Check if current page is login page"""
        try:
            content = self.page.content()
            return 'loginForm' in content or 'login' in self.page.url
        except Exception:
            return False

    def safe_extract(
        self,
        extractor_func,
        element_name: str,
        selector: str,
        default: Any = None
    ) -> Any:
        """
        Safely extract data with error handling and logging

        Args:
            extractor_func: Function to extract data
            element_name: Name of element being extracted (for logging)
            selector: CSS selector used
            default: Default value if extraction fails

        Returns:
            Extracted data or default value
        """
        try:
            result = extractor_func()
            self.logger.debug(f"✓ Extracted {element_name}: {result}")
            return result
        except Exception as e:
            self.logger.warning(
                f"✗ Failed to extract {element_name} using selector '{selector}': {e}"
            )
            # Check if HTML structure changed
            if "TimeoutError" in str(type(e).__name__) or "not found" in str(e).lower():
                self.logger.error(
                    f"HTML structure may have changed for '{element_name}'. "
                    f"Selector '{selector}' no longer works."
                )
            return default

    def close(self) -> None:
        """Close browser and cleanup"""
        self.logger.info("Closing browser...")

        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

        self.logger.info("Browser closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
        if exc_type:
            self.logger.error(f"Error during scraping: {exc_val}")

    @abstractmethod
    def scrape(self, *args, **kwargs):
        """Abstract method - must be implemented by subclasses"""
        pass
