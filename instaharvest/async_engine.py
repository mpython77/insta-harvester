"""
Instagram Async Engine
Full async scraping engine built on async_playwright.
Provides the same API as sync scrapers but with async/await and concurrent execution.

Usage:
    import asyncio
    from instaharvest import AsyncProfileScraper, AsyncBatchScraper, ScraperConfig

    # Single profile (async)
    async def main():
        async with AsyncProfileScraper() as scraper:
            profile = await scraper.scrape("instagram")
            print(profile.to_dict())

    asyncio.run(main())

    # Batch scrape (concurrent)
    async def batch():
        scraper = AsyncBatchScraper(max_concurrent=5)
        results = await scraper.scrape_profiles(["user1", "user2", "user3"])
        for profile in results:
            print(f"{profile.username}: {profile.followers} followers")

    asyncio.run(batch())
"""

import asyncio
import json
import time
from pathlib import Path
from typing import AsyncIterator, Dict, List, Optional, Any

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Playwright

from .config import ScraperConfig
from .profile import ProfileData
from .exceptions import (
    InstagramScraperError,
    SessionNotFoundError,
    PageLoadError,
    ProfileNotFoundError,
    LoginRequiredError,
    RateLimitError,
)
from .security import SecurityManager
from .logging_config import get_logger
from .proxy import create_proxy_manager_from_config


# ==================== Async Base Scraper ====================

class AsyncBaseScraper:
    """
    Async base scraper using async_playwright.

    Provides browser management, navigation, session handling,
    and rate limit detection — all async.

    Supports async context manager:
        async with AsyncBaseScraper(config) as scraper:
            await scraper.goto_url("https://instagram.com/...")
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        self.config = config or ScraperConfig()
        self.logger = get_logger(self.__class__.__name__)

        # Browser state
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        # Proxy
        self.proxy_manager = create_proxy_manager_from_config(self.config, self.logger)

    async def setup_browser(self, session_data: Optional[Dict] = None) -> None:
        """
        Setup browser with async_playwright.

        Args:
            session_data: Optional session data for authenticated browsing
        """
        self.logger.info("Setting up async browser...")

        try:
            self.playwright = await async_playwright().start()

            # Browser launch args
            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
            ]

            # Proxy config
            proxy_config = None
            if self.proxy_manager and self.proxy_manager.has_proxies:
                proxy_config = self.proxy_manager.get_for_playwright()

            self.browser = await self.playwright.chromium.launch(
                headless=self.config.headless,
                args=launch_args,
                proxy=proxy_config,
            )

            # Context with session cookies
            context_opts = {
                'viewport': {'width': self.config.viewport_width, 'height': self.config.viewport_height},
                'user_agent': SecurityManager.get_random_user_agent(),
                'locale': 'en-US',
            }

            if session_data and 'cookies' in session_data:
                self.context = await self.browser.new_context(**context_opts)
                await self.context.add_cookies(session_data['cookies'])
                self.logger.info(f"Loaded {len(session_data['cookies'])} session cookies")
            else:
                self.context = await self.browser.new_context(**context_opts)

            self.page = await self.context.new_page()
            await self.page.set_default_timeout(self.config.default_timeout)

            self.logger.info("Async browser setup complete")

        except Exception as e:
            self.logger.error(f"Async browser setup failed: {e}")
            await self.close()
            raise

    async def load_session(self) -> Dict:
        """Load session from file"""
        session_file = Path(self.config.session_file)
        if not session_file.exists():
            raise SessionNotFoundError(f"Session file not found: {session_file}")

        with open(session_file, 'r') as f:
            return json.load(f)

    async def update_session(self) -> None:
        """Update and save current session cookies"""
        if not self.context:
            return
        try:
            cookies = await self.context.cookies()
            session_file = Path(self.config.session_file)
            session_data = {}
            if session_file.exists():
                with open(session_file, 'r') as f:
                    session_data = json.load(f)
            session_data['cookies'] = cookies
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            self.logger.debug(f"Session updated: {len(cookies)} cookies")
        except Exception as e:
            self.logger.warning(f"Session update failed: {e}")

    async def goto_url(
        self,
        url: str,
        wait_until: str = 'domcontentloaded',
        delay: Optional[float] = None,
    ) -> bool:
        """
        Navigate to URL with rate limit detection and retry.

        Args:
            url: URL to navigate to
            wait_until: Page load event to wait for
            delay: Custom delay after navigation

        Returns:
            True if successful
        """
        self.logger.info(f"Navigating to: {url}")

        for attempt in range(self.config.max_retries):
            try:
                await self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=self.config.navigation_timeout,
                )

                sleep_time = delay if delay is not None else self.config.page_load_delay
                await asyncio.sleep(sleep_time)

                # Rate limit detection
                if await self._is_rate_limited():
                    self.logger.warning(
                        f"⚠️ Rate limit detected! "
                        f"Cooldown: {self.config.rate_limit_cooldown}s "
                        f"(attempt {attempt + 1}/{self.config.rate_limit_max_retries})"
                    )
                    if attempt < self.config.rate_limit_max_retries:
                        await asyncio.sleep(self.config.rate_limit_cooldown)
                        continue
                    else:
                        raise RateLimitError("Rate limited by Instagram")

                # Login detection
                if await self._is_login_page():
                    if attempt < self.config.max_retries - 1:
                        self.logger.info("Attempting session recovery...")
                        await self.page.goto(
                            self.config.instagram_base_url,
                            wait_until='domcontentloaded',
                            timeout=self.config.navigation_timeout,
                        )
                        await asyncio.sleep(self.config.page_stability_delay)
                        if not await self._is_login_page():
                            continue
                    raise LoginRequiredError("Session expired")

                self.logger.info(f"Successfully navigated to: {url}")
                return True

            except (LoginRequiredError, RateLimitError):
                raise
            except Exception as e:
                self.logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay)
                else:
                    raise PageLoadError(f"Failed to load: {url}")

        return False

    async def _is_rate_limited(self) -> bool:
        """Check if current page shows rate limit / action blocked"""
        try:
            current_url = self.page.url.lower()
            for pattern in self.config.rate_limit_url_patterns:
                if pattern in current_url:
                    return True

            try:
                body_text = await self.page.locator('body').inner_text(timeout=3000)
                for indicator in self.config.rate_limit_indicators:
                    if indicator in body_text:
                        return True
            except Exception:
                content = await self.page.content()
                for indicator in self.config.rate_limit_indicators:
                    if indicator in content:
                        return True

            return False
        except Exception:
            return False

    async def _is_login_page(self) -> bool:
        """Check if current page requires login"""
        try:
            url = self.page.url.lower()
            if '/accounts/login' in url:
                return True

            content = await self.page.content()
            login_indicators = ['Log in to Instagram', 'Log In', 'Sign up']
            for indicator in login_indicators:
                if indicator in content:
                    return True

            return False
        except Exception:
            return True

    async def close(self) -> None:
        """Close browser and cleanup"""
        try:
            if self.context:
                await self.context.close()
        except Exception:
            pass
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass

        self.page = None
        self.context = None
        self.browser = None
        self.playwright = None

    async def __aenter__(self):
        """Async context manager entry"""
        session_data = await self.load_session()
        await self.setup_browser(session_data)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        try:
            await self.update_session()
        except Exception:
            pass
        await self.close()


# ==================== Async Profile Scraper ====================

class AsyncProfileScraper(AsyncBaseScraper):
    """
    Async profile scraper.

    Usage:
        async with AsyncProfileScraper(config) as scraper:
            profile = await scraper.scrape("instagram")
    """

    async def scrape(self, username: str) -> ProfileData:
        """
        Scrape profile data asynchronously.

        Args:
            username: Instagram username (without @)

        Returns:
            ProfileData object
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"Async scraping profile: @{username}")

        profile_url = self.config.profile_url_pattern.format(username=username)
        await self.goto_url(profile_url)

        # Check profile exists
        content = await self.page.content()
        for not_found in self.config.profile_not_found_strings:
            if not_found in content:
                raise ProfileNotFoundError(f"Profile @{username} not found")

        # Wait for stats
        try:
            await self.page.wait_for_selector(
                self.config.selector_posts_count,
                timeout=self.config.posts_count_timeout,
            )
            await asyncio.sleep(self.config.ui_stability_delay)
        except Exception:
            await asyncio.sleep(self.config.page_stability_delay)

        # Extract stats
        posts = await self._get_stat_count(self.config.selector_posts_count)
        followers = await self._get_followers_count()
        following = await self._get_stat_count(self.config.selector_following_link)

        # Check verified
        is_verified = await self._check_verified()

        # Check private
        is_private = await self._is_private()

        # Get category
        category = await self._get_category()

        data = ProfileData(
            username=username,
            posts=posts,
            followers=followers,
            following=following,
            is_verified=is_verified,
            is_private=is_private,
            category=category,
        )

        self.logger.info(
            f"Profile complete: {posts} posts, "
            f"{followers} followers, {following} following"
        )
        return data

    async def _get_stat_count(self, selector: str) -> int:
        """Extract count from a stats element"""
        try:
            element = self.page.locator(selector).first
            span = element.locator(self.config.selector_html_span).first
            text = await span.inner_text()
            return self._parse_number(text)
        except Exception:
            return 0

    async def _get_followers_count(self) -> int:
        """Extract followers count (with title attribute priority)"""
        try:
            link = self.page.locator(self.config.selector_followers_link).first
            title_span = link.locator('span[title]').first
            if await title_span.count() > 0:
                text = await title_span.get_attribute('title')
                return self._parse_number(text)
            span = link.locator(self.config.selector_html_span).first
            text = await span.inner_text()
            return self._parse_number(text)
        except Exception:
            return 0

    async def _check_verified(self) -> bool:
        """Check verified badge"""
        try:
            badge = self.page.locator(self.config.selector_verified_badge).first
            return await badge.count() > 0
        except Exception:
            return False

    async def _is_private(self) -> bool:
        """Check if account is private"""
        try:
            icon = self.page.locator(self.config.selector_private_icon).first
            if await icon.count() > 0:
                return True
            body_text = await self.page.locator('body').inner_text()
            for indicator in self.config.selector_private_text_indicators:
                if indicator in body_text:
                    return True
            return False
        except Exception:
            return False

    async def _get_category(self) -> Optional[str]:
        """Extract profile category"""
        try:
            element = self.page.locator(self.config.selector_profile_category).first
            if await element.count() > 0:
                return (await element.inner_text()).strip() or None
            return None
        except Exception:
            return None

    def _parse_number(self, text: str) -> int:
        """Parse number string with K/M support"""
        if not text:
            return 0
        text = text.strip().replace(',', '').replace(' ', '')
        try:
            if text.upper().endswith('M'):
                return int(float(text[:-1]) * 1_000_000)
            elif text.upper().endswith('K'):
                return int(float(text[:-1]) * 1_000)
            return int(float(text))
        except (ValueError, TypeError):
            return 0


# ==================== Async Batch Scraper ====================

class AsyncBatchScraper:
    """
    Scrape multiple profiles concurrently with semaphore control.

    Features:
    - Configurable concurrency (default: 5 browsers)
    - Semaphore-based rate control
    - Graceful error handling per worker
    - Results streaming via async generator
    - Progress callback support

    Usage:
        scraper = AsyncBatchScraper(max_concurrent=5)

        # Collect all results
        results = await scraper.scrape_profiles(["user1", "user2", ...])

        # Stream results
        async for profile in scraper.scrape_stream(usernames):
            print(f"Got: {profile.username}")
    """

    def __init__(
        self,
        config: Optional[ScraperConfig] = None,
        max_concurrent: int = 5,
        on_result: Optional[Any] = None,
        on_error: Optional[Any] = None,
    ):
        """
        Args:
            config: ScraperConfig for each worker
            max_concurrent: Max concurrent browser instances
            on_result: Optional callback(ProfileData) called for each result
            on_error: Optional callback(username, error) called on failure
        """
        self.config = config or ScraperConfig()
        self.max_concurrent = max_concurrent
        self.on_result = on_result
        self.on_error = on_error
        self.logger = get_logger('AsyncBatchScraper')

        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._results: List[ProfileData] = []
        self._errors: Dict[str, str] = {}

    async def scrape_profiles(self, usernames: List[str]) -> List[ProfileData]:
        """
        Scrape multiple profiles concurrently.

        Args:
            usernames: List of Instagram usernames

        Returns:
            List of ProfileData (only successful scrapes)
        """
        self.logger.info(
            f"🚀 Batch scrape: {len(usernames)} profiles "
            f"(max {self.max_concurrent} concurrent)"
        )

        self._results = []
        self._errors = {}

        tasks = [
            self._worker(username)
            for username in usernames
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

        # Summary
        self.logger.info(
            f"✅ Batch complete: {len(self._results)}/{len(usernames)} profiles "
            f"({len(self._errors)} errors)"
        )

        return self._results

    async def scrape_stream(self, usernames: List[str]) -> AsyncIterator[ProfileData]:
        """
        Stream profile results as they become available.

        Usage:
            async for profile in scraper.scrape_stream(usernames):
                process(profile)
        """
        queue: asyncio.Queue = asyncio.Queue()

        async def worker(username):
            result = await self._scrape_single(username)
            if result:
                await queue.put(result)

        # Start all workers
        tasks = [
            asyncio.create_task(worker(u))
            for u in usernames
        ]

        # Yield results as they arrive
        done_count = 0
        while done_count < len(usernames):
            try:
                profile = await asyncio.wait_for(queue.get(), timeout=1.0)
                yield profile
                done_count += 1
            except asyncio.TimeoutError:
                # Check if all tasks are done
                if all(t.done() for t in tasks):
                    # Drain remaining
                    while not queue.empty():
                        yield await queue.get()
                    break

    async def _worker(self, username: str) -> None:
        """Worker coroutine with semaphore control"""
        async with self._semaphore:
            result = await self._scrape_single(username)
            if result:
                self._results.append(result)

    async def _scrape_single(self, username: str) -> Optional[ProfileData]:
        """Scrape a single profile with full error handling"""
        try:
            async with AsyncProfileScraper(self.config) as scraper:
                profile = await scraper.scrape(username)

                if self.on_result:
                    self.on_result(profile)

                self.logger.info(
                    f"✓ @{username}: {profile.followers} followers"
                )
                return profile

        except ProfileNotFoundError:
            self.logger.warning(f"✗ @{username}: profile not found")
            self._errors[username] = 'not_found'
        except RateLimitError as e:
            self.logger.error(f"✗ @{username}: rate limited - {e}")
            self._errors[username] = 'rate_limited'
        except LoginRequiredError:
            self.logger.error(f"✗ @{username}: session expired")
            self._errors[username] = 'login_required'
        except Exception as e:
            self.logger.error(f"✗ @{username}: {e}")
            self._errors[username] = str(e)

        if self.on_error:
            self.on_error(username, self._errors.get(username, 'unknown'))

        return None

    @property
    def errors(self) -> Dict[str, str]:
        """Get dict of failed usernames and their errors"""
        return dict(self._errors)

    def __repr__(self) -> str:
        return (
            f"AsyncBatchScraper(concurrent={self.max_concurrent}, "
            f"results={len(self._results)}, errors={len(self._errors)})"
        )
