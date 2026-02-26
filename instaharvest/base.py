"""
Instagram Scraper - Base scraper class
Professional base class with error handling, logging, and retry logic
"""

import json
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
    RateLimitError
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

    def sync_network_client(self):
        """
        Synchronization: Browser Cookies -> Network Client
        Allows making high-speed requests using the authenticated session.
        """
        if self.context:
            cookies = self.context.cookies()
            self.network_client.set_cookies(cookies)
            self.logger.info("⚡ Synced Browser Cookies to Network Client")

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
            # Get current storage state (cookies, localStorage, etc.)
            storage_state = self.context.storage_state()

            # Save to session file
            with open(self.config.session_file, 'w', encoding='utf-8') as f:
                json.dump(storage_state, f, indent=2)

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
                    self.logger.warning(
                        f"⚠️ Rate limit detected! "
                        f"Auto-cooldown: {self.config.rate_limit_cooldown}s "
                        f"(attempt {attempt + 1}/{self.config.rate_limit_max_retries})"
                    )
                    if attempt < self.config.rate_limit_max_retries:
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

            # Method 2: Check for logged-in UI elements (navigation bar, etc.)
            # If we can find the main navigation bar or user menu, we're logged in
            try:
                # Wait briefly for navigation elements to appear
                nav_selectors = [
                    'nav[role="navigation"]',  # Main navigation
                    'a[href*="/direct/"]',      # Direct messages link (only visible when logged in)
                    'svg[aria-label="Home"]',   # Home icon in nav
                    'span[role="link"]',        # User profile link in nav
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
        snapshot_on_error: bool = True
    ) -> Any:
        try:
            result = extractor_func()
            self.logger.debug(f"✓ Extracted {element_name}: {result}")
            return result
        except Exception as e:
            self.logger.warning(
                f"✗ Failed to extract {element_name} using selector '{selector}': {e}"
            )
            
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
                            
                        self.logger.error(
                            f"\n{'!'*60}\n"
                            f"HTML STRUCTURE CHANGED DETECTED!\n"
                            f"Failed Element: {element_name}\n"
                            f"Selector Used: {selector}\n"
                            f"Snapshot Saved: {filename}\n"
                            f"{'!'*60}\n"
                        )
                except Exception as diag_e:
                    self.logger.error(f"Failed to save diagnostic snapshot: {diag_e}")

            return default

    def parse_number(self, text: str) -> Optional[int]:
        """
        Parse number string with localization support (K, M, etc.)
        Uses config.number_suffixes and config.number_separators.

        Args:
            text: Raw text containing number (e.g. "1.5M", "10,5тыс.", "1 000")

        Returns:
            Parsed integer or None if parsing failed
        """
        if not text:
            return None

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
            return None

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
