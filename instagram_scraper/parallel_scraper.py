"""
Instagram Scraper - Parallel Post Data Scraper
Scrape multiple posts simultaneously with multiple browser contexts
"""

import time
import random
from typing import List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, BrowserContext, Page

from .config import ScraperConfig
from .post_data import PostData
from .logger import setup_logger


class ParallelPostDataScraper:
    """
    Parallel post data scraper using multiple browser contexts

    Features:
    - Multiple browser tabs/contexts in parallel
    - BeautifulSoup for faster HTML parsing
    - Thread-safe operations
    - Progress tracking
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize parallel scraper"""
        self.config = config or ScraperConfig()
        self.logger = setup_logger(
            name='ParallelPostDataScraper',
            log_file=self.config.log_file,
            level=self.config.log_level,
            log_to_console=self.config.log_to_console
        )

    def scrape_multiple(
        self,
        post_urls: List[str],
        parallel: int = 1,
        session_file: str = None
    ) -> List[PostData]:
        """
        Scrape multiple posts in parallel

        Args:
            post_urls: List of post URLs
            parallel: Number of parallel contexts (default 1 = sequential)
            session_file: Session file path

        Returns:
            List of PostData objects
        """
        session_file = session_file or self.config.session_file

        self.logger.info(
            f"Starting parallel scrape: {len(post_urls)} posts, "
            f"{parallel} parallel contexts"
        )

        # Load session
        import json
        with open(session_file, 'r') as f:
            session_data = json.load(f)

        # Sequential (parallel=1)
        if parallel <= 1:
            return self._scrape_sequential(post_urls, session_data)

        # Parallel (parallel > 1)
        return self._scrape_parallel(post_urls, session_data, parallel)

    def _scrape_sequential(
        self,
        post_urls: List[str],
        session_data: dict
    ) -> List[PostData]:
        """Sequential scraping (original method)"""
        from .post_data import PostDataScraper

        scraper = PostDataScraper(self.config)
        results = scraper.scrape_multiple(
            post_urls,
            delay_between_posts=True
        )

        return results

    def _scrape_parallel(
        self,
        post_urls: List[str],
        session_data: dict,
        num_workers: int
    ) -> List[PostData]:
        """
        Parallel scraping with multiple browser contexts

        Args:
            post_urls: List of URLs
            session_data: Session data
            num_workers: Number of parallel workers

        Returns:
            List of PostData objects
        """
        results = []

        with sync_playwright() as p:
            # Launch single browser
            browser = p.chromium.launch(
                channel='chrome',
                headless=self.config.headless
            )

            try:
                # Create worker function
                def scrape_batch(urls_batch: List[str], worker_id: int) -> List[PostData]:
                    """Worker function for each parallel context"""
                    # Create separate context for this worker
                    context = browser.new_context(
                        storage_state=session_data,
                        viewport={
                            'width': self.config.viewport_width,
                            'height': self.config.viewport_height
                        },
                        user_agent=self.config.user_agent
                    )

                    page = context.new_page()
                    page.set_default_timeout(self.config.default_timeout)

                    batch_results = []

                    for url in urls_batch:
                        try:
                            self.logger.info(
                                f"[Worker {worker_id}] Scraping: {url}"
                            )
                            data = self._scrape_single_post(page, url)
                            batch_results.append(data)

                            # Small delay
                            time.sleep(random.uniform(1, 2))

                        except Exception as e:
                            self.logger.error(
                                f"[Worker {worker_id}] Failed {url}: {e}"
                            )
                            batch_results.append(PostData(
                                url=url,
                                tagged_accounts=[],
                                likes='ERROR',
                                timestamp='N/A'
                            ))

                    context.close()
                    return batch_results

                # Split URLs into batches
                batches = self._split_into_batches(post_urls, num_workers)

                # Execute in parallel using ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    futures = {
                        executor.submit(scrape_batch, batch, i): i
                        for i, batch in enumerate(batches, 1)
                    }

                    # Collect results as they complete
                    for future in as_completed(futures):
                        worker_id = futures[future]
                        try:
                            batch_results = future.result()
                            results.extend(batch_results)
                            self.logger.info(
                                f"[Worker {worker_id}] Completed "
                                f"{len(batch_results)} posts"
                            )
                        except Exception as e:
                            self.logger.error(
                                f"[Worker {worker_id}] Failed: {e}"
                            )

            finally:
                browser.close()

        # Sort results by original URL order
        results_dict = {r.url: r for r in results}
        sorted_results = [
            results_dict.get(url, PostData(url=url, tagged_accounts=[], likes='N/A', timestamp='N/A'))
            for url in post_urls
        ]

        self.logger.info(
            f"Parallel scraping complete: {len(sorted_results)} posts"
        )

        return sorted_results

    def _scrape_single_post(self, page: Page, url: str) -> PostData:
        """
        Scrape single post using BeautifulSoup for speed

        Args:
            page: Playwright page
            url: Post URL

        Returns:
            PostData object
        """
        # Navigate to post
        page.goto(url, wait_until='domcontentloaded', timeout=60000)
        time.sleep(2)

        # Get HTML content
        html_content = page.content()

        # Parse with BeautifulSoup (faster than Playwright selectors)
        soup = BeautifulSoup(html_content, 'lxml')

        # Extract data
        tagged_accounts = self._extract_tags_bs4(soup)
        likes = self._extract_likes_bs4(soup, page)
        timestamp = self._extract_timestamp_bs4(soup)

        return PostData(
            url=url,
            tagged_accounts=tagged_accounts,
            likes=likes,
            timestamp=timestamp
        )

    def _extract_tags_bs4(self, soup: BeautifulSoup) -> List[str]:
        """Extract tagged accounts using BeautifulSoup"""
        try:
            tag_containers = soup.find_all('div', class_='_aa1y')
            tagged = []

            for container in tag_containers:
                link = container.find('a', href=True)
                if link:
                    href = link['href']
                    username = href.strip('/').split('/')[-1]
                    tagged.append(username)

            return tagged if tagged else ['No tags']

        except Exception:
            return ['No tags']

    def _extract_likes_bs4(self, soup: BeautifulSoup, page: Page) -> str:
        """Extract likes using BeautifulSoup + fallback to Playwright"""
        # Method 1: BS4 - span[role="button"]
        try:
            section = soup.find('section')
            if section:
                spans = section.find_all('span', role='button')
                for span in spans[:2]:
                    text = span.get_text(strip=True)
                    if text and text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit():
                        return text.replace(',', '')
                    if text and ('K' in text or 'M' in text):
                        return text
        except Exception:
            pass

        # Method 2: Playwright fallback
        try:
            section = page.locator('section').first
            spans = section.locator('span[role="button"]').all()
            for span in spans[:2]:
                text = span.inner_text(timeout=2000).strip()
                if text and text.replace(',', '').isdigit():
                    return text.replace(',', '')
        except Exception:
            pass

        return 'N/A'

    def _extract_timestamp_bs4(self, soup: BeautifulSoup) -> str:
        """Extract timestamp using BeautifulSoup"""
        try:
            time_element = soup.find('time')
            if time_element:
                # Try title attribute
                title = time_element.get('title')
                if title:
                    return title

                # Try datetime attribute
                datetime_str = time_element.get('datetime')
                if datetime_str:
                    return datetime_str

                # Fallback to text
                return time_element.get_text(strip=True)

        except Exception:
            pass

        return 'N/A'

    def _split_into_batches(
        self,
        items: List[str],
        num_batches: int
    ) -> List[List[str]]:
        """Split list into roughly equal batches"""
        batch_size = len(items) // num_batches
        remainder = len(items) % num_batches

        batches = []
        start = 0

        for i in range(num_batches):
            # Add extra item to first 'remainder' batches
            size = batch_size + (1 if i < remainder else 0)
            end = start + size
            batches.append(items[start:end])
            start = end

        return batches
