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



def _extract_reel_tags(soup: BeautifulSoup, page: Page, url: str, worker_id: int) -> List[str]:
    """
    Extract tagged accounts from REEL via popup button (EXCLUDE comment section!)

    Reels show tags in a popup, not directly in HTML
    Comment class: x5yr21d xw2csxc x1odjw0f x1n2onr6 - MUST BE EXCLUDED!
    """
    tagged = []

    try:
        # METHOD 1: Click tag button to open popup
        tag_button = page.locator('button:has(svg[aria-label="Tags"])').first
        tag_button.click(timeout=3000)
        print(f"[Worker {worker_id}] ✓ Clicked tag button, waiting for popup...")
        time.sleep(1.5)  # Wait for popup animation
        time.sleep(0.5)  # Extra wait for popup content

        # CRITICAL FIX: Extract usernames ONLY from popup container (NOT comment section!)
        # Popup class: x1cy8zhl x9f619 x78zum5 xl56j7k x2lwn1j xeuugli x47corl
        print(f"[Worker {worker_id}] Looking for popup container...")

        # Find popup container
        popup_container = page.locator('div.x1cy8zhl.x9f619.x78zum5.xl56j7k.x2lwn1j.xeuugli.x47corl').first

        if popup_container.count() == 0:
            print(f"[Worker {worker_id}] Popup container not found, trying alternative selectors...")
            # Alternative: role="dialog"
            popup_container = page.locator('div[role="dialog"]').first

        # Extract links ONLY from within popup container
        popup_links = popup_container.locator('a[href^="/"]').all()
        print(f"[Worker {worker_id}] Found {len(popup_links)} links in popup")

        for link in popup_links:
            try:
                href = link.get_attribute('href', timeout=1000)
                if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                    username = href.strip('/').split('/')[-1]

                    # Filter system paths
                    if username in ['explore', 'accounts', 'p', 'reel', 'direct', 'tv', 'stories']:
                        continue

                    if username not in tagged:
                        tagged.append(username)
                        print(f"[Worker {worker_id}] ✓ Added tag: {username}")
            except:
                continue

        # Close popup
        try:
            close_button = page.locator('button:has(svg[aria-label="Close"])').first
            close_button.click(timeout=2000)
            print(f"[Worker {worker_id}] ✓ Closed tag popup")
        except:
            pass

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} reel tags: {tagged}")
            return tagged

    except Exception as e:
        print(f"[Worker {worker_id}] Reel tag extraction failed: {e}")

    # No tags found
    print(f"[Worker {worker_id}] ⚠️ No tags in reel (or no tag button)")
    return []


def _extract_reel_likes(soup: BeautifulSoup, page: Page, worker_id: int) -> str:
    """Extract likes from REEL using reel-specific selector"""
    try:
        # Reel likes selector
        likes_span = page.locator('span.x1ypdohk.x1s688f.x2fvf9.xe9ewy2[role="button"]').first
        likes_text = likes_span.inner_text(timeout=3000).strip()
        likes_clean = likes_text.replace(',', '')
        print(f"[Worker {worker_id}] ✓ Reel likes: {likes_clean}")
        return likes_clean
    except Exception as e:
        print(f"[Worker {worker_id}] Reel likes extraction failed: {e}")
        return 'N/A'


def _extract_reel_timestamp(soup: BeautifulSoup, page: Page, worker_id: int) -> str:
    """Extract timestamp from REEL"""
    try:
        # Method 1: time.x1p4m5qa element
        time_elem = page.locator('time.x1p4m5qa').first

        # Try title attribute first
        title = time_elem.get_attribute('title', timeout=2000)
        if title:
            print(f"[Worker {worker_id}] ✓ Reel timestamp (title): {title}")
            return title

        # Fallback to datetime attribute
        datetime_attr = time_elem.get_attribute('datetime', timeout=2000)
        if datetime_attr:
            print(f"[Worker {worker_id}] ✓ Reel timestamp (datetime): {datetime_attr}")
            return datetime_attr

    except Exception as e:
        print(f"[Worker {worker_id}] Reel timestamp extraction failed: {e}")

    return 'N/A'


def _worker_scrape_batch(args: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Worker function for multiprocessing - MUST be at module level

    Args:
        args: Dictionary with keys: links_batch, worker_id, session_data, config_dict, result_queue

    Returns:
        List of post/reel data dictionaries
    """
    # Register signal handler for this worker process
    signal.signal(signal.SIGINT, _worker_signal_handler)
    signal.signal(signal.SIGTERM, _worker_signal_handler)

    links_batch = args['links_batch']  # Changed: Now receives link dictionaries
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

        try:
            total_in_batch = len(links_batch)
            for idx, link_data in enumerate(links_batch, 1):
                # Extract URL and content type
                url = link_data['url']
                content_type = link_data.get('type', 'Post')  # 'Post' or 'Reel'
                is_reel = (content_type == 'Reel')

                # Check for shutdown request
                global _shutdown_requested
                if _shutdown_requested:
                    print(f"[Worker {worker_id}] Shutdown requested, stopping...")
                    break

                try:
                    # LOG: Starting scrape with type
                    print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] 🔍 Scraping [{content_type}]: {url}")

                    # Navigate to post/reel
                    page.goto(url, wait_until='domcontentloaded', timeout=60000)
                    print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ✓ Page loaded")

                    # CRITICAL: Wait longer for content to load
                    time.sleep(3)  # Increased from 2 to 3 seconds

                    # Get HTML content
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'lxml')

                    # Extract data based on content type
                    if is_reel:
                        # REEL-specific extraction
                        tagged_accounts = _extract_reel_tags(soup, page, url, worker_id)
                        likes = _extract_reel_likes(soup, page, worker_id)
                        timestamp = _extract_reel_timestamp(soup, page, worker_id)
                    else:
                        # POST extraction (original logic)
                        # Try to wait for tag elements specifically
                        try:
                            page.wait_for_selector('div._aa1y', timeout=5000, state='attached')
                            print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ✓ Tag elements detected")
                        except:
                            print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ⚠️ No tag elements (might be normal)")

                        tagged_accounts = _extract_tags_robust(soup, page, url, worker_id)
                        likes = _extract_likes_bs4(soup, page)
                        timestamp = _extract_timestamp_bs4(soup)

                    result = {
                        'url': url,
                        'tagged_accounts': tagged_accounts,
                        'likes': likes,
                        'timestamp': timestamp,
                        'content_type': content_type  # Include content type in result
                    }

                    batch_results.append(result)

                    # LOG: Success
                    print(f"[Worker {worker_id}] [{idx}/{total_in_batch}] ✅ DONE [{content_type}]: {len(tagged_accounts)} tags, {likes} likes")

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
                        'timestamp': 'N/A',
                        'content_type': content_type  # Include content type even in errors
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

        finally:
            # Always cleanup browser resources
            try:
                context.close()
            except:
                pass
            try:
                browser.close()
            except:
                pass

    return batch_results


def _extract_tags_robust(soup: BeautifulSoup, page: Page, url: str, worker_id: int) -> List[str]:
    """
    Extract tags from posts (handles both IMAGE and VIDEO posts)

    Instagram tag structure:
    - IMAGE posts: Tags in <div class="_aa1y"> containers
    - VIDEO posts: Tags in popup (click button, then extract from popup)
    """
    tagged = []

    # STEP 1: Detect if this is a VIDEO post or IMAGE post
    is_video_post = False
    try:
        video_count = page.locator('video').count()
        if video_count > 0:
            is_video_post = True
            print(f"[Worker {worker_id}] Detected VIDEO post")
        else:
            print(f"[Worker {worker_id}] Detected IMAGE post")
    except:
        pass

    # STEP 2: If VIDEO post, use POPUP extraction (like reels)
    if is_video_post:
        print(f"[Worker {worker_id}] Using VIDEO post tag extraction (popup method)...")
        try:
            # Find and click tag button
            tag_button = page.locator('button:has(svg[aria-label="Tags"])').first

            if tag_button.count() > 0:
                # Click the tag button
                tag_button.click(timeout=3000)
                time.sleep(1.5)  # Wait for popup animation
                time.sleep(0.5)  # Extra wait for popup content

                # CRITICAL: Extract from popup container ONLY
                popup_container = page.locator('div.x1cy8zhl.x9f619.x78zum5.xl56j7k.x2lwn1j.xeuugli.x47corl').first

                if popup_container.count() == 0:
                    # Fallback: Try role="dialog"
                    popup_container = page.locator('div[role="dialog"]').first

                if popup_container.count() > 0:
                    # Extract links ONLY from popup
                    popup_links = popup_container.locator('a[href^="/"]').all()

                    for link in popup_links:
                        try:
                            href = link.get_attribute('href', timeout=1000)
                            if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                                username = href.strip('/').split('/')[-1]

                                # Filter out system paths
                                if username in ['explore', 'direct', 'accounts', 'p', 'reel', 'tv', 'stories']:
                                    continue

                                if username and username not in tagged:
                                    tagged.append(username)
                        except:
                            continue

                    # Close popup
                    try:
                        close_button = page.locator('button:has(svg[aria-label="Close"])').first
                        close_button.click(timeout=2000)
                    except:
                        page.keyboard.press('Escape')

                if tagged:
                    print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (VIDEO popup): {tagged}")
                    return tagged

        except Exception as e:
            print(f"[Worker {worker_id}] VIDEO popup extraction failed: {e}")
            # Try closing popup
            try:
                page.keyboard.press('Escape')
            except:
                pass

    # STEP 3: If IMAGE post (or video extraction failed), use div._aa1y extraction
    print(f"[Worker {worker_id}] Using IMAGE post tag extraction (div._aa1y method)...")

    # METHOD 1: BeautifulSoup - div._aa1y > a[href]
    try:
        tag_containers = soup.find_all('div', class_='_aa1y')
        for container in tag_containers:
            link = container.find('a', href=True)
            if link and link.get('href'):
                href = link['href']
                username = href.strip('/').split('/')[-1]

                # Filter out system paths
                if username in ['explore', 'accounts', 'p', 'reel', 'direct', 'tv', 'stories']:
                    continue

                if username and username not in tagged:
                    tagged.append(username)

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (BS4 Method 1): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 1 failed: {e}")

    # METHOD 2: Playwright - div._aa1y locator
    try:
        tag_divs = page.locator('div._aa1y').all()
        for tag_div in tag_divs:
            try:
                link = tag_div.locator('a[href]').first
                href = link.get_attribute('href', timeout=2000)
                if href:
                    username = href.strip('/').split('/')[-1]

                    # Filter out system paths
                    if username in ['explore', 'accounts', 'p', 'reel', 'direct', 'tv', 'stories']:
                        continue

                    if username and username not in tagged:
                        tagged.append(username)
            except:
                continue

        if tagged:
            print(f"[Worker {worker_id}] ✓ Found {len(tagged)} tags (Playwright Method 2): {tagged}")
            return tagged
    except Exception as e:
        print(f"[Worker {worker_id}] Method 2 failed: {e}")

    # ALL METHODS FAILED - Log warning
    print(f"[Worker {worker_id}] ⚠️ WARNING: No tags found in {url}")
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
        post_links: List[Dict[str, str]],  # Changed: Now accepts dictionaries
        parallel: int = 1,
        session_file: str = None,
        excel_exporter = None
    ) -> List[PostData]:
        """
        Scrape multiple posts/reels in parallel with real-time Excel export

        Args:
            post_links: List of dictionaries with 'url' and 'type' keys
            parallel: Number of parallel contexts (default 1 = sequential)
            session_file: Session file path
            excel_exporter: Optional Excel exporter for real-time writing

        Returns:
            List of PostData objects
        """
        session_file = session_file or self.config.session_file

        self.logger.info(
            f"Starting parallel scrape: {len(post_links)} posts/reels, "
            f"{parallel} parallel contexts"
        )

        # Load session
        import json
        with open(session_file, 'r') as f:
            session_data = json.load(f)

        # Sequential (parallel=1)
        if parallel <= 1:
            # Extract URLs for sequential scraping
            urls = [link['url'] for link in post_links]
            return self._scrape_sequential(urls, session_data)

        # Parallel (parallel > 1)
        return self._scrape_parallel(post_links, session_data, parallel, excel_exporter)

    def _scrape_sequential(
        self,
        post_links: List[Dict[str, str]],
        session_data: dict
    ) -> List[PostData]:
        """Sequential scraping (original method)"""
        from .post_data import PostDataScraper

        # Extract URLs from dictionaries
        post_urls = [link['url'] for link in post_links]

        scraper = PostDataScraper(self.config)
        results = scraper.scrape_multiple(
            post_urls,
            delay_between_posts=True
        )

        return results

    def _scrape_parallel(
        self,
        post_links: List[Dict[str, str]],  # Changed: Now accepts dictionaries
        session_data: dict,
        num_workers: int,
        excel_exporter=None
    ) -> List[PostData]:
        """
        Parallel scraping with multiple browser processes + REAL-TIME Excel writing

        Args:
            post_links: List of dictionaries with 'url' and 'type' keys
            session_data: Session data
            num_workers: Number of parallel workers
            excel_exporter: Optional Excel exporter for real-time writing

        Returns:
            List of PostData objects
        """
        # Split link dictionaries into batches
        batches = self._split_into_batches(post_links, num_workers)

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
                'links_batch': batch,  # Changed: Now passing link dictionaries
                'worker_id': i,
                'session_data': session_data,
                'config_dict': config_dict,
                'result_queue': result_queue  # Pass queue to workers
            }
            for i, batch in enumerate(batches, 1)
        ]

        self.logger.info(
            f"Starting {num_workers} parallel processes for {len(post_links)} posts/reels"
        )
        self.logger.info("Real-time monitoring enabled ✓")

        # Use multiprocessing Pool with async
        results = []
        completed_count = 0
        total_posts = len(post_links)

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
                        timestamp=result_dict['timestamp'],
                        content_type=result_dict.get('content_type', 'Post')  # Include content_type
                    ))

        # Sort results by original URL order
        results_dict = {r.url: r for r in results}
        sorted_results = [
            results_dict.get(
                link['url'],
                PostData(
                    url=link['url'],
                    tagged_accounts=[],
                    likes='N/A',
                    timestamp='N/A',
                    content_type=link.get('type', 'Post')
                )
            )
            for link in post_links  # Changed: Now iterating over link dictionaries
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
