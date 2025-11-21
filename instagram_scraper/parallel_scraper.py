"""
Instagram Scraper - Parallel Post Data Scraper
Scrape multiple posts simultaneously with multiple browser contexts
"""

import time
import random
import json
from typing import List, Optional, Dict, Any
from multiprocessing import Pool, cpu_count
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, Page

from .config import ScraperConfig
from .post_data import PostData
from .logger import setup_logger


def _worker_scrape_batch(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Worker function for multiprocessing - MUST be at module level

    Args:
        args: Dictionary with keys: urls_batch, worker_id, session_data, config_dict

    Returns:
        List of post data dictionaries
    """
    urls_batch = args['urls_batch']
    worker_id = args['worker_id']
    session_data = args['session_data']
    config_dict = args['config_dict']

    # Reconstruct config from dict
    config = ScraperConfig(
        headless=config_dict['headless'],
        viewport_width=config_dict['viewport_width'],
        viewport_height=config_dict['viewport_height'],
        user_agent=config_dict['user_agent'],
        default_timeout=config_dict['default_timeout']
    )

    batch_results = []

    # Each worker gets its own Playwright instance
    with sync_playwright() as p:
        browser = p.chromium.launch(
            channel='chrome',
            headless=config.headless
        )

        context = browser.new_context(
            storage_state=session_data,
            viewport={
                'width': config.viewport_width,
                'height': config.viewport_height
            },
            user_agent=config.user_agent
        )

        page = context.new_page()
        page.set_default_timeout(config.default_timeout)

        for url in urls_batch:
            try:
                # Navigate to post
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                time.sleep(2)

                # Get HTML content
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'lxml')

                # Extract data
                tagged_accounts = _extract_tags_bs4(soup)
                likes = _extract_likes_bs4(soup, page)
                timestamp = _extract_timestamp_bs4(soup)

                batch_results.append({
                    'url': url,
                    'tagged_accounts': tagged_accounts,
                    'likes': likes,
                    'timestamp': timestamp
                })

                # Small delay
                time.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"[Worker {worker_id}] Failed {url}: {e}")
                batch_results.append({
                    'url': url,
                    'tagged_accounts': [],
                    'likes': 'ERROR',
                    'timestamp': 'N/A'
                })

        context.close()
        browser.close()

    return batch_results


def _extract_tags_bs4(soup: BeautifulSoup) -> List[str]:
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


def _extract_likes_bs4(soup: BeautifulSoup, page: Page) -> str:
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


def _extract_timestamp_bs4(soup: BeautifulSoup) -> str:
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


class ParallelPostDataScraper:
    """
    Parallel post data scraper using multiple browser processes

    Features:
    - Multiple independent browser processes (multiprocessing)
    - BeautifulSoup for faster HTML parsing
    - Process-safe operations
    - True parallel execution (not limited by Python GIL)
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
        Parallel scraping with multiple browser processes

        Args:
            post_urls: List of URLs
            session_data: Session data
            num_workers: Number of parallel workers

        Returns:
            List of PostData objects
        """
        # Split URLs into batches
        batches = self._split_into_batches(post_urls, num_workers)

        # Prepare config as dict (must be serializable for multiprocessing)
        config_dict = {
            'headless': self.config.headless,
            'viewport_width': self.config.viewport_width,
            'viewport_height': self.config.viewport_height,
            'user_agent': self.config.user_agent,
            'default_timeout': self.config.default_timeout
        }

        # Prepare arguments for each worker
        worker_args = [
            {
                'urls_batch': batch,
                'worker_id': i,
                'session_data': session_data,
                'config_dict': config_dict
            }
            for i, batch in enumerate(batches, 1)
        ]

        self.logger.info(
            f"Starting {num_workers} parallel processes for {len(post_urls)} posts"
        )

        # Use multiprocessing Pool
        results = []
        with Pool(processes=num_workers) as pool:
            batch_results_list = pool.map(_worker_scrape_batch, worker_args)

            # Flatten results
            for batch_results in batch_results_list:
                for result_dict in batch_results:
                    results.append(PostData(
                        url=result_dict['url'],
                        tagged_accounts=result_dict['tagged_accounts'],
                        likes=result_dict['likes'],
                        timestamp=result_dict['timestamp']
                    ))

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
