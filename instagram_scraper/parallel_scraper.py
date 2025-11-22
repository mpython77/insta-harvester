"""
Instagram Scraper - Parallel Post Data Scraper
Scrape multiple posts simultaneously with multiple browser contexts
"""

import time
import random
import json
import signal
from typing import List, Optional, Dict, Any
from multiprocessing import Pool, cpu_count, Manager, Queue
from bs4 import BeautifulSoup
from datetime import datetime

from playwright.sync_api import sync_playwright, Page

from .config import ScraperConfig
from .post_data import PostData
from .logger import setup_logger

# Global flag for graceful shutdown in worker processes
_shutdown_requested = False


def _worker_signal_handler(signum, frame):
    """Signal handler for worker processes"""
    global _shutdown_requested
    _shutdown_requested = True
    print(f"\n[Worker] Shutdown signal received, finishing current post...")



def _worker_scrape_batch(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Worker function for multiprocessing - MUST be at module level

    Args:
        args: Dictionary with keys: urls_batch, worker_id, session_data, config_dict, result_queue

    Returns:
        List of post data dictionaries
    """
    # Register signal handler for this worker process
    signal.signal(signal.SIGINT, _worker_signal_handler)
    signal.signal(signal.SIGTERM, _worker_signal_handler)

    urls_batch = args['urls_batch']
    worker_id = args['worker_id']
    session_data = args['session_data']
    config_dict = args['config_dict']
    result_queue = args.get('result_queue')  # Optional queue for real-time results

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

        total_in_batch = len(urls_batch)
        for idx, url in enumerate(urls_batch, 1):
            # Check for shutdown request
            global _shutdown_requested
            if _shutdown_requested:
                print(f"[Worker {worker_id}] Shutdown requested, stopping...")
                break

            try:
                # LOG: Starting scrape
                print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] 🔍 Scraping: {url}")

                # Navigate to post
                page.goto(url, wait_until='domcontentloaded', timeout=60000)
                print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ✓ Page loaded")

                # CRITICAL: Wait longer for tags to load
                time.sleep(3)  # Increased from 2 to 3 seconds

                # Try to wait for tag elements specifically
                try:
                    page.wait_for_selector('div._aa1y', timeout=5000, state='attached')
                    print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ✓ Tag elements detected")
                except:
                    print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ⚠️ No tag elements (might be normal)")

                # Get HTML content
                html_content = page.content()
                soup = BeautifulSoup(html_content, 'lxml')

                # Extract data with robust multi-method approach
                tagged_accounts = _extract_tags_robust(soup, page, url, worker_id)
                likes = _extract_likes_bs4(soup, page)
                timestamp = _extract_timestamp_bs4(soup)

                result = {
                    'url': url,
                    'tagged_accounts': tagged_accounts,
                    'likes': likes,
                    'timestamp': timestamp
                }

                batch_results.append(result)

                # LOG: Success
                print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ✅ DONE: {len(tagged_accounts)} tags, {likes} likes")

                # REAL-TIME: Send to queue immediately for Excel writing
                if result_queue is not None:
                    result_queue.put({
                        'type': 'post_result',
                        'worker_id': worker_id,
                        'data': result,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                # Small delay
                time.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ❌ ERROR: {e}")
                error_result = {
                    'url': url,
                    'tagged_accounts': [],
                    'likes': 'ERROR',
                    'timestamp': 'N/A'
                }
                batch_results.append(error_result)

                # Send error to queue too
                if result_queue is not None:
                    result_queue.put({
                        'type': 'post_error',
                        'worker_id': worker_id,
                        'url': url,
                        'error': str(e)
                    })

        context.close()
        browser.close()

    return batch_results


def _extract_tags_robust(soup: BeautifulSoup, page: Page, url: str, worker_id: int) -> List[str]:
    """
    ROBUST tag extraction with 5 fallback methods

    CRITICAL: Tags are very important - we cannot miss them!
    Always in: <div class="_aa1y"><a href="/username/"></a></div>
    """
    tagged = []

    # METHOD 1: BeautifulSoup - div._aa1y > a[href]
    try:
        tag_containers = soup.find_all('div', class_='_aa1y')
        for container in tag_containers:
            link = container.find('a', href=True)
            if link and link.get('href'):
                href = link['href']
                username = href.strip('/').split('/')[-1]
                if username and username not in tagged:
                    tagged.append(username)

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (BS4 Method 1): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 1 failed: {e}")

    # METHOD 2: BeautifulSoup - all <a> tags with href containing single /username/
    try:
        all_links = soup.find_all('a', href=True)
        for link in all_links:
            href = link.get('href', '')
            # Pattern: /username/ (not /p/ or /reel/)
            if href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                username = href.strip('/').split('/')[-1]
                if username and username not in ['p', 'reel', 'explore', 'accounts'] and username not in tagged:
                    # Check if parent has _aa1y class
                    parent = link.find_parent('div', class_='_aa1y')
                    if parent:
                        tagged.append(username)

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (BS4 Method 2): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 2 failed: {e}")

    # METHOD 3: Playwright - div._aa1y locator
    try:
        tag_divs = page.locator('div._aa1y').all()
        for tag_div in tag_divs:
            try:
                link = tag_div.locator('a[href]').first
                href = link.get_attribute('href', timeout=2000)
                if href:
                    username = href.strip('/').split('/')[-1]
                    if username and username not in tagged:
                        tagged.append(username)
            except:
                continue

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (Playwright Method 3): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 3 failed: {e}")

    # METHOD 4: Playwright - XPath for div with class _aa1y
    try:
        xpath = '//div[@class="_aa1y"]//a[@href]'
        tag_links = page.locator(f'xpath={xpath}').all()
        for link in tag_links:
            try:
                href = link.get_attribute('href', timeout=2000)
                if href:
                    username = href.strip('/').split('/')[-1]
                    if username and username not in tagged:
                        tagged.append(username)
            except:
                continue

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (Playwright XPath Method 4): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 4 failed: {e}")

    # METHOD 5: BeautifulSoup - Search in alt text and aria-label
    try:
        # Sometimes tagged usernames appear in alt text or aria-labels
        imgs = soup.find_all('img', alt=True)
        for img in imgs:
            alt_text = img.get('alt', '')
            if 'tagging' in alt_text.lower():
                # Extract @username patterns
                import re
                usernames_in_alt = re.findall(r'@(\w+\.?\w*)', alt_text)
                for username in usernames_in_alt:
                    if username and username not in tagged:
                        tagged.append(username)

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (Alt text Method 5): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 5 failed: {e}")

    # ALL METHODS FAILED - Log warning
    print(f"[Worker {worker_id}] ⚠️ WARNING: No tags found in {url} after 5 methods!")
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
        session_file: str = None,
        excel_exporter = None
    ) -> List[PostData]:
        """
        Scrape multiple posts in parallel with real-time Excel export

        Args:
            post_urls: List of post URLs
            parallel: Number of parallel contexts (default 1 = sequential)
            session_file: Session file path
            excel_exporter: Optional Excel exporter for real-time writing

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
        return self._scrape_parallel(post_urls, session_data, parallel, excel_exporter)

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
        num_workers: int,
        excel_exporter=None
    ) -> List[PostData]:
        """
        Parallel scraping with multiple browser processes + REAL-TIME Excel writing

        Args:
            post_urls: List of URLs
            session_data: Session data
            num_workers: Number of parallel workers
            excel_exporter: Optional Excel exporter for real-time writing

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

        # Create Manager Queue for real-time communication
        manager = Manager()
        result_queue = manager.Queue()

        # Prepare arguments for each worker
        worker_args = [
            {
                'urls_batch': batch,
                'worker_id': i,
                'session_data': session_data,
                'config_dict': config_dict,
                'result_queue': result_queue  # Pass queue to workers
            }
            for i, batch in enumerate(batches, 1)
        ]

        self.logger.info(
            f"Starting {num_workers} parallel processes for {len(post_urls)} posts"
        )
        self.logger.info("Real-time monitoring enabled ✓")

        # Use multiprocessing Pool with async
        results = []
        completed_count = 0
        total_posts = len(post_urls)

        with Pool(processes=num_workers) as pool:
            # Start workers asynchronously
            async_result = pool.map_async(_worker_scrape_batch, worker_args)

            # REAL-TIME: Monitor queue while workers are running
            while not async_result.ready() or not result_queue.empty():
                try:
                    # Non-blocking queue check
                    message = result_queue.get(timeout=0.5)

                    if message['type'] == 'post_result':
                        # SUCCESS: Post scraped
                        data = message['data']
                        worker_id = message['worker_id']
                        completed_count += 1

                        self.logger.info(
                            f"📦 [{completed_count}/{total_posts}] Worker {worker_id} completed: "
                            f"{len(data['tagged_accounts'])} tags, {data['likes']} likes"
                        )

                        # REAL-TIME Excel write
                        if excel_exporter:
                            try:
                                excel_exporter.add_row(
                                    post_url=data['url'],
                                    tagged_accounts=data['tagged_accounts'],
                                    likes=data['likes'],
                                    post_date=data['timestamp'],
                                    content_type=data.get('content_type', 'Post')
                                )
                                self.logger.info(f"  ✓ Saved to Excel: {data['url']}")
                            except Exception as e:
                                self.logger.error(f"  ✗ Excel write failed: {e}")

                    elif message['type'] == 'post_error':
                        # ERROR: Post failed
                        worker_id = message['worker_id']
                        url = message['url']
                        error = message['error']
                        completed_count += 1

                        self.logger.error(
                            f"❌ [{completed_count}/{total_posts}] Worker {worker_id} failed: {url} - {error}"
                        )

                except:
                    # Queue empty or timeout - continue
                    time.sleep(0.1)

            # Get final results from workers
            batch_results_list = async_result.get()

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
            f"✅ Parallel scraping complete: {len(sorted_results)} posts"
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
