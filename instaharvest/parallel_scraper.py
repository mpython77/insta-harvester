"""
Instagram Scraper - Parallel Post Data Scraper
Scrape multiple posts simultaneously with multiple browser contexts
"""

import time
import random
import json
import signal
import logging
from typing import List, Optional, Dict, Any
from multiprocessing import Pool, cpu_count, Manager, Queue
from bs4 import BeautifulSoup
from datetime import datetime

from playwright.sync_api import sync_playwright, Page

from .config import ScraperConfig
from .post_data import PostData
from .logging_config import get_logger

# Global flag for graceful shutdown in worker processes
_shutdown_requested = False


def _worker_signal_handler(signum, frame):
    """Signal handler for worker processes"""
    global _shutdown_requested
    _shutdown_requested = True
    # We use print here as logging might not be fully configured/safe in signal handler depending on platform
    # But usually safe enough to just set the flag
    pass 

def _get_worker_logger(worker_id: int):
    """Get logger for worker process"""
    logger = logging.getLogger(f"Worker-{worker_id}")
    if not logger.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            force=True # Ensure we override any previous basicConfig
        )
    return logger

def _extract_reel_tags(soup: BeautifulSoup, page: Page, url: str, worker_id: int, config: ScraperConfig) -> List[str]:
    """
    Extract tagged accounts from REEL via popup button (EXCLUDE comment section!)

    Reels show tags in a popup, not directly in HTML
    Comment class: x5yr21d xw2csxc x1odjw0f x1n2onr6 - MUST BE EXCLUDED!
    """
    tagged = []
    logger = _get_worker_logger(worker_id)

    try:
        # METHOD 1: Click tag button to open popup
        tag_button = page.locator(config.selector_tag_button).first
        tag_button.click(timeout=config.tag_button_click_timeout)
        logger.debug(f"✓ Clicked tag button, waiting for popup...")
        time.sleep(config.popup_animation_delay)
        time.sleep(config.popup_content_load_delay)

        # CRITICAL FIX: Extract usernames ONLY from popup container (NOT comment section!)
        # Popup class: x1cy8zhl x9f619 x78zum5 xl56j7k x2lwn1j xeuugli x47corl
        logger.debug(f"Looking for popup container...")

        # Find popup container
        popup_container = page.locator(config.selector_popup_containers[0]).first

        if popup_container.count() == 0:
            logger.debug(f"Popup container not found, trying alternative selectors...")
            # Alternative: role="dialog"
            popup_container = page.locator(config.selector_popup_dialog).first

        # Extract links ONLY from within popup container
        popup_links = popup_container.locator('a[href^="/"]').all()
        logger.debug(f"Found {len(popup_links)} links in popup")

        for link in popup_links:
            try:
                href = link.get_attribute('href', timeout=config.attribute_timeout)
                if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                    username = href.strip('/').split('/')[-1]

                    # Filter system paths
                    if username in config.instagram_system_paths:
                        continue

                    if username not in tagged:
                        tagged.append(username)
                        logger.debug(f"✓ Added tag: {username}")
            except Exception:
                continue

        # Close popup
        try:
            close_button = page.locator(config.selector_close_button).first
            close_button.click(timeout=config.popup_close_timeout)
            logger.debug(f"✓ Closed tag popup")
        except Exception:
            pass

        if tagged:
            logger.info(f"✓ Found {len(tagged)} reel tags: {tagged}")
            return tagged

    except Exception as e:
        logger.debug(f"Reel tag extraction failed: {e}")

    # No tags found
    logger.debug(f"⚠️ No tags in reel (or no tag button)")
    if config.return_empty_list_for_no_tags:
        return []
    return ['No tags']


def _parse_number(text: str, config: ScraperConfig) -> Optional[int]:
    """Parse number with config settings"""
    if not text:
        return None
    
    clean_text = text.strip().upper()
    multiplier = 1
    
    # Check suffixes
    for suffix, mult in config.number_suffixes.items():
        if clean_text.endswith(suffix.upper()):
            multiplier = mult
            clean_text = clean_text[:-len(suffix)].strip()
            break
            
    try:
        clean_text = clean_text.replace(' ', '')
        if ',' in clean_text and '.' in clean_text:
            clean_text = clean_text.replace(',', '')
        elif ',' in clean_text:
            if multiplier > 1:
                clean_text = clean_text.replace(',', '.')
            else:
                clean_text = clean_text.replace(',', '')
                
        value = float(clean_text)
        return int(value * multiplier)
    except Exception:
        return None

def _extract_reel_likes(soup: BeautifulSoup, page: Page, worker_id: int, config: ScraperConfig) -> int:
    """Extract likes from REEL using reel-specific selector"""
    logger = _get_worker_logger(worker_id)
    try:
        # Reel likes selector
        likes_span = page.locator(config.selector_reel_likes + '[role="button"]').first
        likes_text = likes_span.inner_text(timeout=config.reel_likes_timeout).strip()
        val = _parse_number(likes_text, config)
        if val is not None:
             logger.debug(f"✓ Reel likes: {val}")
             return val
    except Exception as e:
        logger.debug(f"Reel likes extraction failed: {e}")
    return 0



def _extract_likes_bs4(soup: BeautifulSoup, page: Page, worker_id: int, config: ScraperConfig) -> int:
    """Extract likes using BeautifulSoup + fallback to Playwright"""
    logger = _get_worker_logger(worker_id)
    
    # Method 1: BS4 - span[role="button"]
    try:
        section = soup.find('section')
        if section:
            spans = section.find_all('span', role='button')
            for span in spans[:2]:
                text = span.get_text(strip=True)
                val = _parse_number(text, config)
                if val is not None:
                    return val
    except Exception:
        pass

    # Method 2: Playwright fallback
    try:
        section = page.locator('section').first
        spans = section.locator('span[role="button"]').all()
        for span in spans[:2]:
            text = span.inner_text(timeout=config.visibility_timeout).strip()
            val = _parse_number(text, config)
            if val is not None:
                return val
    except Exception:
        pass

    return 0



def _extract_reel_timestamp(soup: BeautifulSoup, page: Page, worker_id: int, config: ScraperConfig) -> str:
    """Extract timestamp from REEL"""
    logger = _get_worker_logger(worker_id)
    try:
        # Method 1: time.x1p4m5qa element
        time_elem = page.locator(config.selector_reel_timestamp).first

        # Try title attribute first
        title = time_elem.get_attribute('title', timeout=config.visibility_timeout)
        if title:
            logger.debug(f"✓ Reel timestamp (title): {title}")
            return title

        # Fallback to datetime attribute
        datetime_attr = time_elem.get_attribute('datetime', timeout=config.visibility_timeout)
        if datetime_attr:
            logger.debug(f"✓ Reel timestamp (datetime): {datetime_attr}")
            return datetime_attr

    except Exception as e:
        logger.debug(f"Reel timestamp extraction failed: {e}")

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

    # Helper for logging
    logger = _get_worker_logger(worker_id)
    
    # Reconstruct config from dict
    config = ScraperConfig(
        headless=config_dict.get('headless', True),
        viewport_width=config_dict.get('viewport_width', 1280),
        viewport_height=config_dict.get('viewport_height', 720),
        user_agent=config_dict.get('user_agent', ''),
        default_timeout=config_dict.get('default_timeout', 60000),
        popup_animation_delay=config_dict.get('popup_animation_delay', 1.5),
        popup_content_load_delay=config_dict.get('popup_content_load_delay', 0.5),
        error_recovery_delay_min=config_dict.get('error_recovery_delay_min', 1.0),
        error_recovery_delay_max=config_dict.get('error_recovery_delay_max', 2.0),
        post_open_delay=config_dict.get('post_open_delay', 3.0),
        ui_element_load_delay=config_dict.get('ui_element_load_delay', 0.1),
        browser_channel=config_dict.get('browser_channel', 'chrome'),
        browser_args=config_dict.get('browser_args', ['--start-maximized'])
    )
    
    # Manually inject new fields if they exist in dict but config.__init__ doesn't capture them (it uses kwargs? No, explicit fields)
    if 'selector_post_tag_container' in config_dict:
        config.selector_post_tag_container = config_dict['selector_post_tag_container']
    if 'return_empty_list_for_no_tags' in config_dict:
        config.return_empty_list_for_no_tags = config_dict['return_empty_list_for_no_tags']

    batch_results = []

    # Each worker gets its own Playwright instance
    with sync_playwright() as p:
        try:
            # Prepare launch options
            launch_options = {
                'headless': config.headless,
                'args': config.browser_args
            }
            if config.browser_channel and config.browser_channel != 'chromium':
                launch_options['channel'] = config.browser_channel

            browser = p.chromium.launch(**launch_options)
        except Exception as launch_error:
            # Handle Chrome launch failure
            if config.browser_channel == 'chrome':
                error_msg = (
                    f"LIBRARY ERROR: System Google Chrome not found!\n"
                    f"Chrome is required to correctly load Videos and Reels.\n"
                    f"Solution: Install Chrome or set browser_channel='chromium' in config.py."
                )
                logger.error(error_msg)
            raise launch_error

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

                global _shutdown_requested
                if _shutdown_requested:
                    logger.info("Shutdown requested, stopping...")
                    break

                try:
                    # LOG: Starting scrape with type
                    logger.info(f"[{idx}/{total_in_batch}] 🔍 Scraping [{content_type}]: {url}")

                    # Navigate to post/reel
                    page.goto(url, wait_until=config.page_load_wait_until, timeout=config.navigation_timeout)
                    logger.debug(f"[{idx}/{total_in_batch}] ✓ Page loaded")

                    # CRITICAL: Wait longer for content to load
                    time.sleep(config.post_open_delay)

                    # Get HTML content
                    html_content = page.content()
                    soup = BeautifulSoup(html_content, 'lxml')

                    # ═══════ JSON-FIRST FULL EXTRACTION ═══════
                    json_result = None
                    try:
                        import json as json_lib
                        from datetime import datetime as dt_class, timezone as tz_class
                        scripts = page.locator('script[type="application/json"]').all()
                        for script_el in scripts:
                            try:
                                script_content = script_el.inner_text(timeout=1000)
                                if len(script_content) < 500:
                                    continue
                                parsed_json = json_lib.loads(script_content)
                                
                                # Find items[0] recursively
                                def find_item(o, d=0):
                                    if d > 15 or not o: return None
                                    if isinstance(o, dict):
                                        if 'items' in o and isinstance(o['items'], list):
                                            for it in o['items']:
                                                if isinstance(it, dict) and ('pk' in it or 'media_type' in it):
                                                    return it
                                        for v in o.values():
                                            if isinstance(v, (dict, list)):
                                                r = find_item(v, d+1)
                                                if r: return r
                                    elif isinstance(o, list):
                                        for it in o:
                                            if isinstance(it, (dict, list)):
                                                r = find_item(it, d+1)
                                                if r: return r
                                    return None
                                
                                item = find_item(parsed_json)
                                if item:
                                    # Extract all fields from JSON
                                    j_tags = []
                                    j_usertags = item.get('usertags')
                                    if isinstance(j_usertags, dict) and 'in' in j_usertags:
                                        for entry in j_usertags['in']:
                                            if isinstance(entry, dict) and 'user' in entry:
                                                u = entry['user']
                                                if isinstance(u, dict) and 'username' in u:
                                                    uname = u['username']
                                                    if uname not in j_tags:
                                                        j_tags.append(uname)
                                    
                                    # Carousel tags
                                    carousel = item.get('carousel_media', [])
                                    if isinstance(carousel, list):
                                        for slide in carousel:
                                            if isinstance(slide, dict):
                                                s_ut = slide.get('usertags')
                                                if isinstance(s_ut, dict) and 'in' in s_ut:
                                                    for entry in s_ut['in']:
                                                        if isinstance(entry, dict) and 'user' in entry:
                                                            u = entry['user']
                                                            if isinstance(u, dict) and 'username' in u:
                                                                uname = u['username']
                                                                if uname not in j_tags:
                                                                    j_tags.append(uname)
                                    
                                    j_likes = item.get('like_count', 0)
                                    j_ts = ''
                                    taken_at = item.get('taken_at', 0)
                                    if taken_at:
                                        try:
                                            j_ts = dt_class.fromtimestamp(taken_at, tz=tz_class.utc).strftime('%b %d, %Y')
                                        except Exception:
                                            j_ts = 'N/A'
                                    
                                    j_caption = ''
                                    cap = item.get('caption')
                                    if isinstance(cap, dict):
                                        j_caption = cap.get('text', '')
                                    
                                    j_comment_count = item.get('comment_count', 0)
                                    
                                    # Location
                                    j_location = ''
                                    loc = item.get('location')
                                    if isinstance(loc, dict):
                                        j_location = loc.get('name', '')
                                    
                                    json_result = {
                                        'url': url,
                                        'tagged_accounts': j_tags,
                                        'likes': j_likes,
                                        'timestamp': j_ts,
                                        'content_type': content_type,
                                        'caption': j_caption,
                                        'comment_count': j_comment_count,
                                        'location': j_location,
                                        'json_extracted': True
                                    }
                                    
                                    logger.info(
                                        f"[{idx}/{total_in_batch}] ✅ JSON-FIRST: "
                                        f"{len(j_tags)} tags, {j_likes} likes"
                                    )
                                    break
                            except Exception:
                                continue
                    except Exception as je:
                        logger.debug(f"JSON extraction failed: {je}")
                    
                    if json_result:
                        result = json_result
                    else:
                        # ═══════ DOM FALLBACK ═══════
                        logger.debug(f"[{idx}/{total_in_batch}] JSON failed, using DOM...")
                        
                        # Extract data based on content type
                        if is_reel:
                            # REEL-specific extraction
                            tagged_accounts = _extract_reel_tags(soup, page, url, worker_id, config)
                            likes = _extract_reel_likes(soup, page, worker_id, config)
                            timestamp = _extract_reel_timestamp(soup, page, worker_id, config)
                        else:
                            # POST extraction (original logic)
                            try:
                                page.wait_for_selector(config.selector_post_tag_container, timeout=config.post_tag_wait_timeout, state='attached')
                                logger.debug(f"[{idx}/{total_in_batch}] ✓ Tag elements detected")
                            except Exception:
                                logger.debug(f"[{idx}/{total_in_batch}] ⚠️ No tag elements (might be normal)")

                            tagged_accounts = _extract_tags_robust(soup, page, url, worker_id, config)
                            likes = _extract_likes_bs4(soup, page, worker_id, config)
                            timestamp = _extract_timestamp_bs4(soup)

                        result = {
                            'url': url,
                            'tagged_accounts': tagged_accounts,
                            'likes': likes,
                            'timestamp': timestamp,
                            'content_type': content_type
                        }

                    batch_results.append(result)

                    # LOG: Success
                    logger.info(f"[{idx}/{total_in_batch}] ✅ DONE [{content_type}]: {len(tagged_accounts)} tags, {likes} likes")

                    # REAL-TIME: Send to queue immediately for Excel writing
                    if result_queue is not None:
                        result_queue.put({
                            'type': 'post_result',
                            'worker_id': worker_id,
                            'data': result,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        })

                    # Small delay
                    time.sleep(random.uniform(config.error_recovery_delay_min, config.error_recovery_delay_max))

                except Exception as e:
                    logger.error(f"[{idx}/{total_in_batch}] ❌ ERROR: {e}")
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
            except Exception:
                pass
            try:
                browser.close()
            except Exception:
                pass

    return batch_results


def _extract_tags_robust(soup: BeautifulSoup, page: Page, url: str, worker_id: int, config: ScraperConfig) -> List[str]:
    """
    Extract tags from posts (handles both IMAGE and VIDEO posts)

    Instagram tag structure:
    - IMAGE posts: Tags in <div class="_aa1y"> containers
    - VIDEO posts: Tags in popup (click button, then extract from popup)
    """
    tagged = []
    logger = _get_worker_logger(worker_id)

    # STEP 1: Detect if this is a VIDEO post or IMAGE post
    is_video_post = False
    try:
        video_count = page.locator('video').count()
        if video_count > 0:
            is_video_post = True
            logger.debug("Detected VIDEO post")
        else:
            logger.debug("Detected IMAGE post")
    except Exception:
        pass

    # STEP 2: If VIDEO post, use POPUP extraction (like reels)
    if is_video_post:
        logger.debug("Using VIDEO post tag extraction (popup method)...")
        try:
            # Find and click tag button
            tag_button = page.locator(config.selector_tag_button).first

            if tag_button.count() > 0:
                # Click the tag button
                tag_button.click(timeout=config.tag_button_click_timeout)
                time.sleep(config.popup_animation_delay)
                time.sleep(config.popup_content_load_delay)

                # CRITICAL: Extract from popup container ONLY
                popup_container = page.locator(config.selector_popup_containers[0]).first

                if popup_container.count() == 0:
                    # Fallback: Try role="dialog"
                    popup_container = page.locator(config.selector_popup_dialog).first

                if popup_container.count() > 0:
                    # Extract links ONLY from popup
                    popup_links = popup_container.locator('a[href^="/"]').all()

                    for link in popup_links:
                        try:
                            href = link.get_attribute('href', timeout=config.attribute_timeout)
                            if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                                username = href.strip('/').split('/')[-1]

                                # Filter out system paths
                                if username in config.instagram_system_paths:
                                    continue

                                if username and username not in tagged:
                                    tagged.append(username)
                        except Exception:
                            continue

                    # Close popup
                    try:
                        close_button = page.locator(config.selector_close_button).first
                        close_button.click(timeout=config.popup_close_timeout)
                    except Exception:
                        page.keyboard.press('Escape')

        except Exception as e:
            logger.debug(f"VIDEO popup extraction failed: {e}")

    # STEP 3: If IMAGE post (or video extraction failed), Use BS4 with Config Selector
    try:
        # Determine class from config selector (e.g. 'div._aa1y' -> '_aa1y')
        tag_selector = config.selector_post_tag_container
        tag_class = tag_selector.replace('div.', '').replace('.', '')
        
        tag_containers = soup.find_all('div', class_=tag_class)
        for container in tag_containers:
            link = container.find('a', href=True)
            if link and link.get('href'):
                href = link['href']
                username = href.strip('/').split('/')[-1]

                # Filter out system paths
                if username in config.instagram_system_paths:
                    continue

                if username and username not in tagged:
                    tagged.append(username)

        if tagged:
            logger.debug(f"✓ Found {len(tagged)} tags (BS4 Method 1): {tagged}")
            return tagged
    except Exception as e:
        logger.debug(f"Method 1 failed: {e}")

    # METHOD 2: Playwright - Config Locator
    try:
        tag_divs = page.locator(config.selector_post_tag_container).all()
        for tag_div in tag_divs:
            try:
                link = tag_div.locator('a[href]').first
                href = link.get_attribute('href', timeout=config.visibility_timeout)
                if href:
                    username = href.strip('/').split('/')[-1]

                    # Filter out system paths
                    if username in config.instagram_system_paths:
                        continue

                    if username and username not in tagged:
                        tagged.append(username)
            except Exception:
                continue

        if tagged:
            logger.debug(f"✓ Found {len(tagged)} tags (Playwright Method 2): {tagged}")
            return tagged
    except Exception as e:
        logger.debug(f"Method 2 failed: {e}")

    # ALL METHODS FAILED - Log warning
    logger.debug(f"⚠️ WARNING: No tags found in {url}")
    if config.return_empty_list_for_no_tags:
        return []
    return ['No tags']





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
        self.logger = get_logger('ParallelPostDataScraper')
        # SharedBrowser support
        self.page = None
        self.browser = None
        self.context = None

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
        post_links: List[str], # Original expects urls
        session_data: dict
    ) -> List[PostData]:
        """Sequential scraping (original method)"""
        from .post_data import PostDataScraper

        # Note: If called from scrape_multiple, post_links is actually list of urls
        
        scraper = PostDataScraper(self.config)

        # SharedBrowser injection — reuse existing browser if available
        if self.page is not None and self.browser is not None:
            scraper.page = self.page
            scraper.browser = self.browser
            scraper.context = self.context
            self.logger.debug("SharedBrowser injected into PostDataScraper")

        results = scraper.scrape_multiple(
            post_links,
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
            'default_timeout': self.config.default_timeout,
            'popup_animation_delay': self.config.popup_animation_delay,
            'popup_content_load_delay': self.config.popup_content_load_delay,
            'error_recovery_delay_min': self.config.error_recovery_delay_min,
            'error_recovery_delay_max': self.config.error_recovery_delay_max,
            'post_open_delay': self.config.post_open_delay,
            'ui_element_load_delay': self.config.ui_element_load_delay,
            'browser_channel': self.config.browser_channel,
            'browser_args': self.config.browser_args,
            # Add dynamic fields
            'selector_post_tag_container': self.config.selector_post_tag_container,
            'return_empty_list_for_no_tags': self.config.return_empty_list_for_no_tags
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

            # Collected data for partial return
            collected_data_map = {}

            # REAL-TIME: Monitor queue while workers are running
            try:
                while not async_result.ready() or not result_queue.empty():
                    try:
                        # Non-blocking queue check
                        message = result_queue.get(timeout=0.5)

                        if message['type'] == 'post_result':
                            # SUCCESS: Post scraped
                            data = message['data']
                            worker_id = message['worker_id']
                            completed_count += 1
                            
                            # Store for partial return
                            collected_data_map[data['url']] = data

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

                    except KeyboardInterrupt:
                        raise # Re-raise to outer block
                    except Exception:
                        # Queue empty or timeout - continue
                        time.sleep(self.config.ui_element_load_delay)

                # Get final results from workers (normal completion)
                batch_results_list = async_result.get()

                # Flatten results
                for batch_results in batch_results_list:
                    for result_dict in batch_results:
                        results.append(PostData(
                            url=result_dict['url'],
                            tagged_accounts=result_dict['tagged_accounts'],
                            likes=result_dict['likes'],
                            timestamp=result_dict['timestamp'],
                            content_type=result_dict.get('content_type', 'Post')
                        ))
            
            except KeyboardInterrupt:
                self.logger.warning("\n⚠️ Parallel scraping interrupted! Terminating workers...")
                pool.terminate()
                pool.join()
                
                # Construct partial results from what we collected from queue
                for url, data in collected_data_map.items():
                    results.append(PostData(
                        url=data['url'],
                        tagged_accounts=data['tagged_accounts'],
                        likes=data['likes'],
                        timestamp=data['timestamp'],
                        content_type=data.get('content_type', 'Post')
                    ))
                
                self.logger.warning(f"Returning {len(results)} partial results...")
                return results

        # Sort results by original URL order
        # Filter out any dicts that may have slipped through (only keep PostData objects)
        valid_results = [r for r in results if hasattr(r, 'url') and not isinstance(r, dict)]
        results_dict = {r.url: r for r in valid_results}
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
            for link in post_links
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
