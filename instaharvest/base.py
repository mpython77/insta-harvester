"""
Instagram Scraper - Base scraper class
Professional base class with error handling, logging, and retry logic
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

from .config import ScraperConfig
from .exceptions import (
    InstagramScraperError,
    SessionNotFoundError,
    PageLoadError,
    ProfileNotFoundError,
    HTMLStructureChangedError,
    LoginRequiredError,
    RateLimitError,
    WebAPIError
)
from .security import SecurityManager
from .network_client import NetworkClient  # [NEW]
from .logging_config import get_logger
from .proxy import ProxyManager, create_proxy_manager_from_config


class BaseScraper(ABC):
    """
    Base scraper class with common functionality
    Handles Browser Management, Auth, and Hybrid Networking.
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """
        Initialize base scraper

        Args:
            config: Scraper configuration (uses defaults if None)
        """
        self.config = config or ScraperConfig()
        self.logger = get_logger(self.__class__.__name__)

        # Browser state
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Proxy Manager
        self.proxy_manager = create_proxy_manager_from_config(self.config, self.logger)
        
        # Hybrid Network Client (curl_cffi) - with proxy support
        proxy_for_client = self.proxy_manager.get_for_curl() if self.proxy_manager.has_proxies else None
        self.network_client = NetworkClient(proxy=proxy_for_client)
        
        # Interruption tracking
        self.interrupted = False

        # Web API client (lazy initialized)
        self._web_api = None

        self.logger.info(f"{self.__class__.__name__} initialized")

    def sync_network_client(self):
        """
        Synchronization: Browser Cookies -> Network Client
        Allows making high-speed requests using the authenticated session.
        """
        if self.context:
            cookies = self.context.cookies()
            self.network_client.set_cookies(cookies)
            self.logger.info("⚡ Synced Browser Cookies to Network Client")

    @property
    def web_api(self):
        """
        Instagram Web API client (lazy initialized).

        Provides JSON-first data extraction via Instagram's internal API.
        Automatically created when first accessed, requires browser page.

        Returns:
            InstagramWebAPI instance or None if page not available
        """
        if self._web_api is None and self.page is not None:
            from .web_api import InstagramWebAPI
            self._web_api = InstagramWebAPI(
                page=self.page,
                config=self.config,
                logger=self.logger
            )
            self.logger.debug("🔌 WebAPI client initialized")
        return self._web_api

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
        except (json.JSONDecodeError, IOError, OSError, PermissionError) as e:
            self.logger.error(f"Session file error: {e}")
            raise SessionNotFoundError(f"Failed to load session: {e}")

    def update_session(self) -> None:
        """
        Update and save current session to file

        This keeps the session fresh and prevents expiration.
        Should be called after successful browser setup with session.
        """
        if not self.context:
            self.logger.warning("Cannot update session: browser context not available")
            return

        try:
            import inspect
            # Get current storage state (cookies, localStorage, etc.)
            result = self.context.storage_state()
            
            # Handle case where storage_state returns a coroutine
            if inspect.iscoroutine(result):
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self.logger.debug("⚠ storage_state returned coroutine, skipping update")
                        result.close()
                        return
                    else:
                        result = loop.run_until_complete(result)
                except RuntimeError:
                    result.close()
                    return
            
            storage_state = result

            # Save to session file atomically to prevent corruption on SIGINT
            tmp_path = self.config.session_file + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f, indent=2)
            os.replace(tmp_path, self.config.session_file)

            cookies_count = len(storage_state.get('cookies', []))
            self.logger.info(f"✓ Session updated and saved: {cookies_count} cookies")

        except Exception as e:
            self.logger.warning(f"Failed to update session: {e}")

    def setup_browser(self, session_data: Optional[Dict] = None, auto_update_session: bool = True) -> None:
        """
        Setup browser with Playwright

        Args:
            session_data: Optional session data for authenticated browsing
            auto_update_session: If True, automatically update session after browser setup (default: True)
        """
        self.logger.info("Setting up browser...")

        try:
            if self.playwright is None:
                self.playwright = sync_playwright().start()

            # Launch browser
            # 'chromium' = use Playwright's bundled Chromium (most compatible)
            # 'chrome' = use system Chrome (may have compatibility issues with new versions)
            launch_options = {'headless': self.config.headless}

            # PROXY: Get proxy for Playwright from ProxyManager
            selected_proxy = None
            if self.proxy_manager.has_proxies:
                selected_proxy = self.proxy_manager.get_for_playwright()
                if selected_proxy:
                    self.logger.info(f"Using Proxy: {selected_proxy['server']}")

            try:
                # Standard Chromium launch (Proxy applied at Context level)
                self.browser = self.playwright.chromium.launch(**launch_options)
                    
            except Exception as launch_error:
                error_msg = str(launch_error)
                
                # RETRY LOGIC: If "Old Headless" error, try launching in NEW HEADLESS mode
                if "Old Headless mode" in error_msg:
                    self.logger.warning("System Chrome rejected 'Old Headless' mode. Retrying with 'new' Headless...")
                    launch_options['headless'] = 'new'
                    try:
                         self.browser = self.playwright.chromium.launch(**launch_options)
                    except Exception as retry_error:
                         # If New Headless also fails, try HEADFUL as last resort
                         self.logger.warning("New Headless also failed. Retrying in HEADFUL mode...")
                         launch_options['headless'] = False
                         self.browser = self.playwright.chromium.launch(**launch_options)
                
                # Specific handling for missing Chrome when channel='chrome'
                elif self.config.browser_channel == 'chrome':
                    self.logger.critical("\n\n" + "!"*60)
                    self.logger.critical("FAILED TO LAUNCH SYSTEM CHROME!")
                    self.logger.critical("!"*60)
                    self.logger.critical(f"Error: {launch_error}")
                    self.logger.critical("Possible solutions:")
                    self.logger.critical("1. Install Google Chrome on your system")
                    self.logger.critical("2. Or change config to use bundled Chromium: config.browser_channel = 'chromium'")
                    self.logger.critical("   (Note: Chromium may not play videos correctly due to missing codecs)")
                    self.logger.critical("!"*60 + "\n")
                    raise launch_error
                else:
                     raise launch_error

            browser_type = self.config.browser_channel or 'chromium'
            self.logger.debug(f"Browser launched ({browser_type}, headless={self.config.headless})")

            # SECURITY: User-Agent Rotation
            final_user_agent = self.config.user_agent
            if self.config.rotate_user_agent:
                final_user_agent = SecurityManager.get_random_user_agent(self.config.user_agents)
                self.logger.info(f"Rotated User-Agent: {final_user_agent[:30]}...")

            # Create context
            context_options = {
                'viewport': {
                    'width': self.config.viewport_width,
                    'height': self.config.viewport_height
                },
                'user_agent': final_user_agent,
                'locale': self.config.locale
            }
            
            
            # Apply Proxy at Context Level
            if selected_proxy:
                context_options['proxy'] = selected_proxy
                self.logger.info(f"Applied Proxy to Context: {selected_proxy['server']}")

            if session_data:
                context_options['storage_state'] = session_data
                self.logger.debug("Context created with session data")

            self.context = self.browser.new_context(**context_options)

            # Apply Stealth Mode at Context Level (BEFORE page creation)
            self.stealth_manager = None
            if self.config.enable_stealth:
                try:
                    from .stealth import StealthManager
                    self.stealth_manager = StealthManager(self.config, self.logger)
                    self.stealth_manager.apply_context_stealth(self.context)
                except Exception as e:
                    self.logger.warning(f"⚠️ Stealth context setup failed: {e}")

            # Create page
            self.page = self.context.new_page()
            self.page.set_default_timeout(self.config.default_timeout)
            
            # Apply Stealth Mode at Page Level
            if self.stealth_manager:
                try:
                    self.stealth_manager.apply_page_stealth(self.page)
                except Exception as e:
                    self.logger.warning(f"⚠️ Stealth page setup failed: {e}")
            
            self.logger.info("Browser setup complete")

            # Auto-update session to keep it fresh
            if session_data and auto_update_session:
                self.logger.debug("Auto-updating session to keep it fresh...")
                try:
                    # Visit Instagram to refresh session
                    self.page.goto(
                        self.config.instagram_base_url,
                        wait_until=self.config.page_load_wait_until,
                        timeout=self.config.session_activation_timeout
                    )
                    # Wait for page to fully load
                    time.sleep(self.config.page_stability_delay)

                    # Update and save session
                    self.update_session()
                except Exception as e:
                    self.logger.warning(f"Auto-update session failed: {e}")

        except Exception as e:
            # Cleanup partial initialization on failure
            self.logger.error(f"Browser setup failed: {e}")
            if self.context:
                try:
                    self.context.close()
                except Exception: pass
            if self.browser:
                try:
                    self.browser.close()
                except Exception: pass
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception: pass
            # Reset all to None
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            raise

    def goto_url(
        self,
        url: str,
        wait_until: str = 'domcontentloaded',
        delay: Optional[float] = None
    ) -> bool:
        """
        Navigate to URL with error handling and session recovery

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation successful
            delay: Optional custom delay after navigation

        Returns:
            True if successful, False otherwise
        """
        self.logger.info(f"Navigating to: {url}")

        rate_limit_retries = 0
        for attempt in range(self.config.max_retries):
            try:
                self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.config.navigation_timeout
                )

                # Delay after page load
                sleep_time = delay if delay is not None else self.config.page_load_delay
                self.logger.debug(f"⏱️ Page loaded, waiting {sleep_time}s...")
                time.sleep(sleep_time)

                # Check if rate limited (before login check)
                if self._is_rate_limited():
                    rate_limit_retries += 1
                    self.logger.warning(
                        f"⚠️ Rate limit detected! "
                        f"Auto-cooldown: {self.config.rate_limit_cooldown}s "
                        f"(attempt {rate_limit_retries}/{self.config.rate_limit_max_retries})"
                    )
                    if rate_limit_retries < self.config.rate_limit_max_retries:
                        self.logger.info(f"⏳ Waiting {self.config.rate_limit_cooldown}s before retry...")
                        time.sleep(self.config.rate_limit_cooldown)
                        continue
                    else:
                        raise RateLimitError(
                            f"Rate limited by Instagram after {self.config.rate_limit_max_retries} "
                            f"cooldown attempts ({self.config.rate_limit_cooldown}s each)"
                        )

                # Check if login required
                if self._is_login_page():
                    self.logger.warning("Login page detected on first load - attempting session recovery...")

                    # Try to recover by visiting Instagram home first
                    if attempt < self.config.max_retries - 1:
                        self.logger.info("Attempting to reactivate session by visiting Instagram home...")
                        try:
                            self.page.goto(
                                self.config.instagram_base_url,
                                wait_until='domcontentloaded',
                                timeout=self.config.navigation_timeout
                            )
                            time.sleep(self.config.page_stability_delay)

                            # Check if home page loaded successfully
                            if not self._is_login_page():
                                self.logger.info("Session reactivated, retrying target URL...")
                                # Retry the original URL
                                continue
                        except Exception as recovery_error:
                            self.logger.warning(f"Session recovery failed: {recovery_error}")

                    # If recovery failed or last attempt, raise error
                    self.logger.error("Login page detected - session expired or invalid")
                    raise LoginRequiredError("Session expired, login required")

                self.logger.info(f"Successfully navigated to: {url}")
                return True

            except (LoginRequiredError, RateLimitError):
                # Re-raise login and rate limit errors immediately
                raise
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
        """
        Check if current page is login page with multiple detection methods

        Uses multiple signals to reliably detect if login is required:
        1. URL check - if redirected to /accounts/login/
        2. Page title check - login pages have specific titles
        3. Login form detection - check for login form elements
        4. Logged-in UI detection - check for navigation elements that only appear when logged in

        Returns:
            True if login is required, False if already logged in
        """
        try:
            current_url = self.page.url

            # Method 1: URL-based detection (most reliable)
            if '/accounts/login' in current_url or '/accounts/emailsignup' in current_url:
                self.logger.debug("Login required: redirected to login URL")
                return True

            # Method 2: Check for password input — reliable login page signal.
            # This also catches cases where Instagram renders the login link as
            # span[role="link"] instead of <a>, which would otherwise fool the
            # nav-element check below into thinking the user is logged in.
            try:
                if self.page.locator('input[type="password"]').count() > 0:
                    self.logger.debug("Login required: found password input field")
                    return True
            except Exception as e:
                self.logger.debug(f"Could not check password input: {e}")

            # Method 3 (was 2): Check for logged-in UI elements (navigation bar, etc.)
            # If we can find the main navigation bar or user menu, we're logged in.
            # Note: span[role="link"] is intentionally excluded here because Instagram
            # also uses it on the login page itself, making it an unreliable logged-in signal.
            try:
                # Wait briefly for navigation elements to appear
                nav_selectors = [
                    'nav[role="navigation"]',  # Main navigation
                    'a[href*="/direct/"]',      # Direct messages link (only visible when logged in)
                    'svg[aria-label="Home"]',   # Home icon in nav
                ]

                for selector in nav_selectors:
                    if self.page.locator(selector).count() > 0:
                        self.logger.debug(f"Logged in: found navigation element '{selector}'")
                        return False  # Found logged-in UI element

            except Exception as e:
                self.logger.debug(f"Could not check navigation elements: {e}")

            # Method 3: Content-based detection (fallback)
            # Only use this if URL check and UI check didn't give clear answer
            content = self.page.content()

            # Check for login form elements
            login_indicators = [
                'name="username"',
                'name="password"',
                '"loginForm"',
                'Log in to Instagram',
            ]

            if any(indicator in content for indicator in login_indicators):
                self.logger.debug("Login required: found login form elements")
                return True

            # Check for config-based login detection strings
            if any(s in content for s in self.config.login_detection_strings):
                self.logger.debug("Login required: found login detection string")
                return True

            # Method 4: Check page title
            try:
                title = self.page.title()
                if 'login' in title.lower() or 'sign up' in title.lower():
                    self.logger.debug(f"Login required: page title indicates login page: '{title}'")
                    return True
            except Exception:
                pass

            # If none of the above detected login page, assume we're logged in
            self.logger.debug("Session appears valid: no login indicators found")
            return False

        except Exception as e:
            self.logger.warning(f"Error checking login status: {e}")
            # Conservative approach: if we can't tell, assume login required
            return True

    def _is_rate_limited(self) -> bool:
        """
        Check if current page shows a rate limit / action blocked page

        Detection methods:
        1. URL check - /challenge/, /action_blocked/, challenge_required
        2. Page content check - known Instagram block indicator strings

        Returns:
            True if rate limited, False otherwise
        """
        try:
            # Method 1: Check URL patterns
            current_url = self.page.url.lower()
            for pattern in self.config.rate_limit_url_patterns:
                if pattern in current_url:
                    self.logger.debug(f"Rate limit detected via URL pattern: {pattern}")
                    return True

            # Method 2: Check page content for block indicators
            try:
                body_text = self.page.locator('body').inner_text(timeout=3000)
                for indicator in self.config.rate_limit_indicators:
                    if indicator in body_text:
                        self.logger.debug(f"Rate limit detected via content: '{indicator}'")
                        return True
            except Exception:
                # Fallback: check raw HTML
                try:
                    content = self.page.content()
                    for indicator in self.config.rate_limit_indicators:
                        if indicator in content:
                            self.logger.debug(f"Rate limit detected via raw HTML: '{indicator}'")
                            return True
                except Exception:
                    pass

            return False

        except Exception as e:
            self.logger.debug(f"Rate limit check error: {e}")
            return False

    def safe_extract(
        self,
        extractor_func,
        element_name: str,
        selector: str,
        default: Any = None,
        snapshot_on_error: bool = True,
        critical: bool = False
    ) -> Any:
        """
        Safely extract data with error handling and optional HTML snapshot.

        Args:
            extractor_func: Callable that performs the extraction
            element_name: Human-readable name of the element being extracted
            selector: CSS selector being used (for diagnostics)
            default: Default value if extraction fails
            snapshot_on_error: Save HTML snapshot on failure for debugging
            critical: If True, raise HTMLStructureChangedError instead of
                      returning default. Use for essential fields (followers,
                      posts count) where a silent 0 would mislead the user.

        Returns:
            Extracted value, or default if extraction fails and critical=False

        Raises:
            HTMLStructureChangedError: If critical=True and extraction fails
        """
        try:
            result = extractor_func()
            self.logger.debug(f"✓ Extracted {element_name}: {result}")
            return result
        except Exception as e:
            self.logger.warning(
                f"✗ Failed to extract {element_name} using selector '{selector}': {e}"
            )
            
            snapshot_path = None
            # Detailed diagnostics for HTML structure changes
            if snapshot_on_error:
                try:
                    # check if page is available
                    if self.page:
                        timestamp = int(time.time())
                        debug_dir = Path("debug_snapshots")
                        debug_dir.mkdir(exist_ok=True)
                        
                        clean_name = element_name.lower().replace(" ", "_").replace("/", "_")
                        filename = debug_dir / f"fail_{clean_name}_{timestamp}.html"
                        
                        # Save HTML snapshot
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(self.page.content())

                        snapshot_path = str(filename)
                        self.logger.error(
                            f"\n{'!'*60}\n"
                            f"HTML STRUCTURE CHANGE DETECTED!\n"
                            f"Failed Element: {element_name}\n"
                            f"Selector Used: {selector}\n"
                            f"Snapshot Saved: {filename}\n"
                            f"{'!'*60}\n"
                        )
                except Exception as diag_e:
                    self.logger.error(f"Failed to save diagnostic snapshot: {diag_e}")

            # If critical — raise instead of silently returning default
            if critical:
                msg = (
                    f"HTML structure changed for '{element_name}'. "
                    f"Selector '{selector}' no longer works. "
                    f"Original error: {type(e).__name__}: {e}"
                )
                if snapshot_path:
                    msg += f" | Debug snapshot: {snapshot_path}"
                raise HTMLStructureChangedError(
                    element_name=element_name,
                    selector=selector,
                    message=msg
                ) from e

            return default

    def parse_number(self, text: str) -> int:
        """
        Parse number string with localization support (K, M, etc.)
        Uses config.number_suffixes and config.number_separators.

        Args:
            text: Raw text containing number (e.g. "1.5M", "10,5тыс.", "1 000")

        Returns:
            Parsed integer, or 0 if parsing failed
        """
        if not text:
            return 0

        clean_text = text.strip().upper()
        
        # 1. Check for suffixes
        multiplier = 1
        for suffix, mult in self.config.number_suffixes.items():
            if clean_text.endswith(suffix.upper()):
                multiplier = mult
                clean_text = clean_text[:-len(suffix)].strip()
                break
        
        # 2. Clean up separators
        # Replace all separators with dot if it looks like a decimal
        # Or remove them if they are thousands separators
        # Heuristic: If we have a multiplier, any separator is likely a decimal point
        # If no multiplier, it might be thousands separator or decimal
        
        try:
            # Remove spaces (always safe)
            clean_text = clean_text.replace(' ', '')
            
            # Handle comma vs dot
            if ',' in clean_text and '.' in clean_text:
                 # Both present? e.g. 1,000.50 -> remove comma
                 clean_text = clean_text.replace(',', '')
            elif ',' in clean_text:
                 # Only comma. If multiplier > 1, treat as decimal (1,5K -> 1.5K)
                 # If no multiplier, it's ambiguous, but usually thousands separator in 1,000
                 if multiplier > 1:
                     clean_text = clean_text.replace(',', '.')
                 else:
                     clean_text = clean_text.replace(',', '') # Assume 1,000 -> 1000
            
            # Parse
            value = float(clean_text)
            return int(value * multiplier)
            
        except ValueError:
            self.logger.warning(f"Failed to parse number: '{text}'")
            return 0

    def close(self, update_session_before_close: bool = True) -> None:
        """
        Close browser and cleanup

        Args:
            update_session_before_close: If True, update session before closing (default: True)
        """
        self.logger.info("Closing browser...")

        # Update session one last time before closing
        if update_session_before_close and self.context:
            try:
                self.logger.debug("Updating session before closing...")
                self.update_session()
            except Exception as e:
                self.logger.warning(f"Failed to update session before closing: {e}")

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

        # Null out all resources so accidental re-use doesn't crash
        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

        self.logger.info("Browser closed")

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit — always closes, never suppresses exceptions"""
        self.close()
        if exc_type:
            self.logger.error(f"Error during scraping: {exc_val}")
        return False  # Never suppress exceptions

    @abstractmethod
    def scrape(self, *args, **kwargs):
        """Abstract method - must be implemented by subclasses"""
        pass

    # ═══════════════════════════════════════════════════════════
    # DATE RANGE FILTERING HELPERS
    # ═══════════════════════════════════════════════════════════

    def _extract_post_date(self, post_url: str) -> Optional[str]:
        """
        Extract publication date from a post/reel page by reading <time datetime="...">

        Args:
            post_url: Full URL to the post/reel

        Returns:
            ISO date string 'YYYY-MM-DD' or None if extraction fails
        """
        try:
            self.goto_url(post_url)
            time.sleep(1.5)
            # Instagram posts have <time datetime="2025-03-07T12:00:00.000Z">
            time_el = self.page.locator('time[datetime]').first
            if time_el.count() > 0:
                dt_str = time_el.get_attribute('datetime')
                if dt_str:
                    # Parse ISO datetime → date only
                    from datetime import datetime as dt_cls
                    parsed = dt_cls.fromisoformat(dt_str.replace('Z', '+00:00'))
                    return parsed.strftime('%Y-%m-%d')
        except Exception as e:
            self.logger.debug(f"Date extraction failed for {post_url}: {e}")
        return None

    def _filter_by_date_range(
        self,
        links: list,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        url_key: str = 'url'
    ) -> list:
        """
        Filter collected links by date range.

        Instagram posts are displayed newest-first, so we can stop early
        when we encounter a post older than date_from.

        Args:
            links: List of link dicts (must have url_key) or list of URL strings
            date_from: Start date 'YYYY-MM-DD' (inclusive)
            date_to: End date 'YYYY-MM-DD' (inclusive)
            url_key: Key name for URL in dict (use None if links are strings)

        Returns:
            Filtered list of links within date range
        """
        if not date_from and not date_to:
            return links

        self.logger.info(
            f"📅 Date filter: {date_from or 'any'} → {date_to or 'any'} "
            f"({len(links)} links to check)"
        )

        filtered = []
        checked = 0
        skipped_future = 0
        stopped_early = False

        for item in links:
            # Get URL from dict, object attribute, or directly from string
            if url_key and isinstance(item, dict):
                url = item.get(url_key)
            elif url_key and hasattr(item, url_key):
                url = getattr(item, url_key)
            else:
                url = item

            # Extract date from the post page
            post_date = self._extract_post_date(url)
            checked += 1

            if post_date is None:
                # Can't extract date — include for safety
                self.logger.debug(f"  [{checked}] {url[:50]}... → date unknown, including")
                filtered.append(item)
                continue

            # Check date_to (future boundary) — skip posts newer than date_to
            if date_to and post_date > date_to:
                skipped_future += 1
                self.logger.debug(f"  [{checked}] {post_date} > {date_to} — skipping (too new)")
                continue

            # Check date_from (past boundary) — posts are newest-first,
            # so if this post is before date_from, ALL remaining are older → stop
            if date_from and post_date < date_from:
                # IMPORTANT: Pinned posts are at the top regardless of date.
                # If it's a pinned post, its old date shouldn't trigger an early stop
                # for the rest of the unpinned (and potentially newer) posts.
                is_pinned = False
                if isinstance(item, dict):
                    is_pinned = item.get('is_pinned', False)
                elif hasattr(item, 'is_pinned'):
                    is_pinned = getattr(item, 'is_pinned')
                if is_pinned:
                    self.logger.debug(
                        f"  [{checked}] {post_date} < {date_from} — "
                        f"skipping (too old) BUT NOT STOPPING because it's a PINNED post"
                    )
                    continue
                else:
                    self.logger.info(
                        f"  [{checked}] {post_date} < {date_from} — "
                        f"stopping (posts are chronological, rest are older)"
                    )
                    stopped_early = True
                    break

            # Within range
            self.logger.info(f"  [{checked}] ✅ {post_date} — in range")
            filtered.append(item)

        summary = (
            f"📅 Date filter complete: {len(filtered)} in range, "
            f"{skipped_future} too new, checked {checked}/{len(links)}"
        )
        if stopped_early:
            summary += f" (stopped early — remaining {len(links) - checked} are older)"
        self.logger.info(summary)

        return filtered

