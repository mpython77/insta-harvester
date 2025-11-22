"""
Instagram Scraper - Post data extractor
Extract tags, likes, and timestamps from individual posts

PROFESSIONAL VERSION with:
- Advanced diagnostics
- Intelligent error recovery
- Performance monitoring
"""

import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import HTMLStructureChangedError
from .diagnostics import HTMLDiagnostics, run_diagnostic_mode
from .error_handler import ErrorHandler
from .performance import PerformanceMonitor


@dataclass
class PostData:
    """Post/Reel data structure"""
    url: str
    tagged_accounts: List[str]
    likes: str
    timestamp: str
    content_type: str = 'Post'  # 'Post' or 'Reel'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PostDataScraper(BaseScraper):
    """
    Instagram post data scraper - PROFESSIONAL VERSION

    Features:
    - Extract tagged accounts
    - Extract likes count
    - Extract post timestamp
    - Multiple fallback methods
    - HTML structure change detection
    - Modular extraction (get only what you need)
    - Advanced diagnostics
    - Intelligent error recovery
    - Performance monitoring
    """

    def __init__(self, config: Optional[ScraperConfig] = None, enable_diagnostics: bool = True):
        """
        Initialize post data scraper

        Args:
            config: Scraper configuration
            enable_diagnostics: Enable diagnostic mode (default: True)
        """
        super().__init__(config)

        # Initialize advanced systems
        self.error_handler = ErrorHandler(self.logger)
        self.performance_monitor = PerformanceMonitor(self.logger)
        self.diagnostics = None  # Will be initialized when page is ready
        self.enable_diagnostics = enable_diagnostics

        self.logger.info("✨ PostDataScraper ready (Professional Mode)")

    def _is_reel(self, url: str) -> bool:
        """Check if URL is a reel"""
        return '/reel/' in url

    def scrape(
        self,
        post_url: str,
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True
    ) -> PostData:
        """
        Scrape data from a single post or reel - PROFESSIONAL VERSION

        Args:
            post_url: URL of the post/reel
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract post timestamp

        Returns:
            PostData object
        """
        # Start performance monitoring
        with self.performance_monitor.measure(f"scrape_{self._get_content_type(post_url)}"):
            # Detect content type
            is_reel = self._is_reel(post_url)
            content_type = 'Reel' if is_reel else 'Post'

            self.logger.info(f"🎯 Scraping {content_type}: {post_url}")

            # Navigate to post/reel
            self.goto_url(post_url)

            # CRITICAL: Wait for content to load
            time.sleep(self.config.post_open_delay)

            # Initialize diagnostics if page is ready
            if self.enable_diagnostics and self.diagnostics is None:
                self.diagnostics = HTMLDiagnostics(self.page, self.logger)

            # Run diagnostics to detect HTML structure changes
            if self.enable_diagnostics and self.diagnostics:
                try:
                    if is_reel:
                        report = self.diagnostics.diagnose_reel(post_url)
                    else:
                        report = self.diagnostics.diagnose_post(post_url)

                    if report.overall_status == 'FAILED':
                        self.logger.critical(
                            f"❌ CRITICAL HTML STRUCTURE CHANGE DETECTED!\n"
                            f"   {', '.join(report.recommendations)}"
                        )
                    elif report.overall_status == 'PARTIAL':
                        self.logger.warning(
                            f"⚠️ Some HTML selectors may have changed: "
                            f"{report.get_success_rate():.1f}% success rate"
                        )
                except Exception as e:
                    self.logger.debug(f"Diagnostics failed: {e}")

            # Extract data based on type with error recovery
            if is_reel:
                tagged_accounts = self._extract_with_recovery(
                    self.get_reel_tagged_accounts, 'reel_tags'
                ) if get_tags else []

                likes = self._extract_with_recovery(
                    self.get_reel_likes_count, 'reel_likes', default='N/A'
                ) if get_likes else 'N/A'

                timestamp = self._extract_with_recovery(
                    self.get_reel_timestamp, 'reel_timestamp', default='N/A'
                ) if get_timestamp else 'N/A'
            else:
                tagged_accounts = self._extract_with_recovery(
                    self.get_tagged_accounts, 'post_tags'
                ) if get_tags else []

                likes = self._extract_with_recovery(
                    self.get_likes_count, 'post_likes', default='N/A'
                ) if get_likes else 'N/A'

                timestamp = self._extract_with_recovery(
                    self.get_timestamp, 'post_timestamp', default='N/A'
                ) if get_timestamp else 'N/A'

            data = PostData(
                url=post_url,
                tagged_accounts=tagged_accounts,
                likes=likes,
                timestamp=timestamp,
                content_type=content_type
            )

            self.logger.info(
                f"✅ Extracted [{content_type}]: {len(data.tagged_accounts)} tags, "
                f"{data.likes} likes, {data.timestamp}"
            )

            return data

    def _get_content_type(self, url: str) -> str:
        """Helper to get content type from URL"""
        return 'reel' if self._is_reel(url) else 'post'

    def _extract_with_recovery(self, extractor_func, element_name: str, default: Any = None):
        """
        Extract with intelligent error recovery

        Args:
            extractor_func: Extraction function
            element_name: Name for logging
            default: Default value if extraction fails

        Returns:
            Extracted value or default
        """
        return self.error_handler.safe_extract(
            extractor=extractor_func,
            element_name=element_name,
            default=default if default is not None else []
        )

    def scrape_multiple(
        self,
        post_urls: List[str],
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True,
        delay_between_posts: bool = True
    ) -> List[PostData]:
        """
        Scrape multiple posts sequentially - PROFESSIONAL VERSION

        Args:
            post_urls: List of post URLs
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract post timestamp
            delay_between_posts: Add delay between posts (rate limiting)

        Returns:
            List of PostData objects
        """
        self.logger.info(f"📦 Scraping {len(post_urls)} posts/reels...")
        self.performance_monitor.log_system_info()

        # Load session and setup browser
        session_data = self.load_session()
        self.setup_browser(session_data)

        results = []
        start_time = time.time()

        try:
            for i, url in enumerate(post_urls, 1):
                content_type = 'Reel' if self._is_reel(url) else 'Post'
                self.logger.info(f"[{i}/{len(post_urls)}] Processing [{content_type}]: {url}")

                try:
                    data = self.scrape(
                        url,
                        get_tags=get_tags,
                        get_likes=get_likes,
                        get_timestamp=get_timestamp
                    )
                    results.append(data)

                except Exception as e:
                    self.logger.error(f"Failed to scrape {url}: {e}")
                    # Add placeholder data
                    results.append(PostData(
                        url=url,
                        tagged_accounts=[],
                        likes='ERROR',
                        timestamp='N/A',
                        content_type=content_type
                    ))

                # Check memory usage and optimize if needed
                if i % 10 == 0:  # Check every 10 posts
                    if not self.performance_monitor.check_memory_threshold(500):
                        self.performance_monitor.optimize_memory()

                # Delay between posts (rate limiting)
                if delay_between_posts and i < len(post_urls):
                    delay = random.uniform(
                        self.config.post_scrape_delay_min,
                        self.config.post_scrape_delay_max
                    )
                    self.logger.debug(f"⏱️ Waiting {delay:.1f}s...")
                    time.sleep(delay)

            # Print final statistics
            total_time = time.time() - start_time
            success_count = sum(1 for r in results if r.likes != 'ERROR')
            posts_count = sum(1 for r in results if r.content_type == 'Post' and r.likes != 'ERROR')
            reels_count = sum(1 for r in results if r.content_type == 'Reel' and r.likes != 'ERROR')

            self.logger.info(
                f"\n{'='*70}\n"
                f"📊 SCRAPING COMPLETE - STATISTICS\n"
                f"{'='*70}\n"
                f"Total URLs: {len(post_urls)}\n"
                f"Successfully scraped: {success_count}/{len(post_urls)} "
                f"({(success_count/len(post_urls)*100):.1f}%)\n"
                f"  - Posts: {posts_count}\n"
                f"  - Reels: {reels_count}\n"
                f"Failed: {len(post_urls) - success_count}\n"
                f"Total time: {total_time:.2f}s\n"
                f"Average time per item: {total_time/len(post_urls):.2f}s\n"
                f"{'='*70}"
            )

            # Print performance report
            self.performance_monitor.print_report()

            # Print error statistics
            self.error_handler.print_stats()

            return results

        finally:
            self.close()

    def get_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from posts (handles both IMAGE and VIDEO posts)

        Instagram tag structure:
        - IMAGE posts: Tags in <div class="_aa1y"> containers
        - VIDEO posts: Tags in popup (click button, then extract from popup)

        Returns:
            List of usernames (without @)
        """
        tagged = []

        # Check if this post has tags (look for Tags SVG)
        try:
            has_tags = self.page.locator('svg[aria-label="Tags"]').count() > 0
            if not has_tags:
                self.logger.debug("No tag icon found - post has no tags")
                return ['No tags']
        except:
            pass

        # STEP 1: Detect if this is a VIDEO post or IMAGE post
        is_video_post = False
        try:
            # Check for video element
            video_count = self.page.locator('video').count()
            if video_count > 0:
                is_video_post = True
                self.logger.debug("Detected VIDEO post")
            else:
                self.logger.debug("Detected IMAGE post")
        except:
            pass

        # STEP 2: If VIDEO post, use POPUP extraction (like reels)
        if is_video_post:
            self.logger.debug("Using VIDEO post tag extraction (popup method)...")
            try:
                # Find and click tag button
                tag_button = self.page.locator('button:has(svg[aria-label="Tags"])').first

                if tag_button.count() == 0:
                    self.logger.debug("No tag button found")
                    return ['No tags']

                # Click the tag button
                self.logger.debug("Clicking tag button...")
                tag_button.click(timeout=3000)
                time.sleep(self.config.popup_animation_delay)
                time.sleep(self.config.popup_content_load_delay)

                # CRITICAL: Extract from popup container ONLY
                self.logger.debug("Extracting tags from popup...")
                popup_container = self.page.locator('div.x1cy8zhl.x9f619.x78zum5.xl56j7k.x2lwn1j.xeuugli.x47corl').first

                if popup_container.count() == 0:
                    # Fallback: Try role="dialog"
                    popup_container = self.page.locator('div[role="dialog"]').first

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
                                    self.logger.debug(f"✓ Found tag: {username}")
                        except:
                            continue

                    # Close popup
                    try:
                        close_button = self.page.locator('button:has(svg[aria-label="Close"])').first
                        close_button.click(timeout=2000)
                    except:
                        self.page.keyboard.press('Escape')

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags (VIDEO popup): {tagged}")
                    return tagged

            except Exception as e:
                self.logger.warning(f"VIDEO post popup extraction failed: {e}")
                # Try closing popup
                try:
                    self.page.keyboard.press('Escape')
                except:
                    pass

        # STEP 3: If IMAGE post (or video extraction failed), use div._aa1y extraction
        self.logger.debug("Using IMAGE post tag extraction (div._aa1y method)...")
        try:
            # Find all tag containers
            tag_containers = self.page.locator('div._aa1y').all()
            self.logger.debug(f"Found {len(tag_containers)} div._aa1y tag containers")

            for container in tag_containers:
                try:
                    # Get the link inside this container
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href', timeout=2000)

                    if href:
                        # Extract username from href="/username/"
                        username = href.strip('/').split('/')[-1]

                        # Filter out system paths
                        if username in ['explore', 'accounts', 'p', 'reel', 'direct', 'tv', 'stories']:
                            continue

                        if username and username not in tagged:
                            tagged.append(username)
                            self.logger.debug(f"✓ Found tag: {username}")
                except:
                    continue

            if tagged:
                self.logger.info(f"✓ Found {len(tagged)} tags (IMAGE): {tagged}")
                return tagged

        except Exception as e:
            self.logger.warning(f"Tag extraction from div._aa1y failed: {e}")

        # FALLBACK: BeautifulSoup method
        try:
            from bs4 import BeautifulSoup
            html = self.page.content()
            soup = BeautifulSoup(html, 'lxml')

            tag_containers = soup.find_all('div', class_='_aa1y')
            self.logger.debug(f"BS4: Found {len(tag_containers)} div._aa1y containers")

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
                self.logger.info(f"✓ Found {len(tagged)} tags (BS4 method): {tagged}")
                return tagged

        except Exception as e:
            self.logger.warning(f"BS4 tag extraction failed: {e}")

        # No tags found
        self.logger.warning("⚠️ No tags found in this post")
        return ['No tags']

    def get_likes_count(self) -> str:
        """
        Extract likes count with multiple fallback methods

        Returns:
            Likes count as string
        """
        # Method 1: span[role="button"] after Like SVG (new structure)
        try:
            section = self.page.locator('section').first
            spans = section.locator('span[role="button"]').all()

            for span in spans[:2]:  # First 2 spans (likes and comments)
                try:
                    text = span.inner_text(timeout=2000).strip()
                    # Check if it's a number
                    if text and text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit():
                        self.logger.debug(f"✓ Found likes (method 1): {text}")
                        return text.replace(',', '')
                    # Handle K/M notation
                    if text and ('K' in text or 'M' in text):
                        self.logger.debug(f"✓ Found likes (method 1): {text}")
                        return text
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Method 1 failed: {e}")

        # Method 2: Direct class selector
        try:
            section = self.page.locator('section').first
            likes_span = section.locator('span.x1ypdohk.x1s688f').first
            likes_text = likes_span.inner_text(timeout=2000).strip()
            if likes_text and likes_text.replace(',', '').isdigit():
                self.logger.debug(f"✓ Found likes (method 2): {likes_text}")
                return likes_text.replace(',', '')
        except Exception as e:
            self.logger.debug(f"Method 2 failed: {e}")

        # Method 3: Link-based (old structure)
        try:
            likes_link = self.page.locator('a[href*="/liked_by/"]').first
            likes_text = likes_link.locator('span.html-span').first.inner_text(timeout=2000)
            if likes_text.replace(',', '').isdigit():
                self.logger.debug(f"✓ Found likes (method 3): {likes_text}")
                return likes_text.strip().replace(',', '')
        except Exception as e:
            self.logger.debug(f"Method 3 failed: {e}")

        # Method 4: Text-based search
        try:
            likes_count = self.page.locator('span:has-text("likes")').count()
            for i in range(likes_count):
                try:
                    span = self.page.locator('span:has-text("likes")').nth(i)
                    number = span.locator('span.html-span').first
                    text = number.inner_text(timeout=2000)
                    if text.replace(',', '').isdigit():
                        self.logger.debug(f"✓ Found likes (method 4): {text}")
                        return text.strip().replace(',', '')
                except Exception:
                    continue
        except Exception as e:
            self.logger.debug(f"Method 4 failed: {e}")

        self.logger.warning("All methods failed to extract likes count")
        return 'N/A'

    def get_timestamp(self) -> str:
        """
        Extract post timestamp

        Returns:
            Timestamp string (e.g., "Nov 17, 2025")
        """
        selector = 'time'

        def extract():
            time_element = self.page.locator(selector).first

            # Try title attribute first (human-readable)
            title = time_element.get_attribute('title')
            if title:
                return title

            # Try datetime attribute
            datetime_str = time_element.get_attribute('datetime')
            if datetime_str:
                return datetime_str

            # Fallback to inner text
            return time_element.inner_text()

        result = self.safe_extract(
            extract,
            element_name='timestamp',
            selector=selector,
            default='N/A'
        )

        return result

    # ==================== REEL-SPECIFIC EXTRACTION METHODS ====================

    def get_reel_likes_count(self) -> str:
        """
        Extract likes count from REEL (different HTML structure than posts)

        Reel likes location:
        <span class="x1ypdohk x1s688f x2fvf9 xe9ewy2" role="button" tabindex="0">3</span>

        Returns:
            Likes count as string
        """
        # Method 1: Reel-specific selector (user provided)
        try:
            likes_span = self.page.locator('span.x1ypdohk.x1s688f.x2fvf9.xe9ewy2[role="button"]').first
            likes_text = likes_span.inner_text(timeout=3000).strip()
            if likes_text:
                self.logger.debug(f"✓ Found reel likes: {likes_text}")
                return likes_text.replace(',', '')
        except Exception as e:
            self.logger.debug(f"Reel likes method 1 failed: {e}")

        # Method 2: General span with role=button (first one is usually likes)
        try:
            spans = self.page.locator('span[role="button"]').all()
            for span in spans[:3]:  # Check first 3
                try:
                    text = span.inner_text(timeout=2000).strip()
                    # Check if it looks like a number
                    if text and (text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit() or 'K' in text or 'M' in text):
                        self.logger.debug(f"✓ Found reel likes (method 2): {text}")
                        return text.replace(',', '')
                except:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 2 failed: {e}")

        self.logger.warning("Failed to extract reel likes count")
        return 'N/A'

    def get_reel_timestamp(self) -> str:
        """
        Extract timestamp from REEL

        Reel timestamp location:
        <time class="x1p4m5qa" datetime="2025-07-23T12:34:14.000Z" title="Jul 23, 2025">July 23</time>

        Returns:
            Timestamp string
        """
        # Method 1: time.x1p4m5qa selector
        try:
            time_element = self.page.locator('time.x1p4m5qa').first

            # Try title attribute first
            title = time_element.get_attribute('title', timeout=3000)
            if title:
                self.logger.debug(f"✓ Found reel timestamp (title): {title}")
                return title

            # Try datetime attribute
            datetime_str = time_element.get_attribute('datetime', timeout=3000)
            if datetime_str:
                self.logger.debug(f"✓ Found reel timestamp (datetime): {datetime_str}")
                return datetime_str

            # Fallback to text
            text = time_element.inner_text(timeout=3000)
            if text:
                self.logger.debug(f"✓ Found reel timestamp (text): {text}")
                return text
        except Exception as e:
            self.logger.debug(f"Reel timestamp method 1 failed: {e}")

        # Method 2: Any time element (fallback)
        try:
            time_element = self.page.locator('time').first
            title = time_element.get_attribute('title')
            if title:
                self.logger.debug(f"✓ Found reel timestamp (fallback): {title}")
                return title
        except Exception as e:
            self.logger.debug(f"Reel timestamp method 2 failed: {e}")

        self.logger.warning("Failed to extract reel timestamp")
        return 'N/A'

    def get_reel_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from REEL (different logic than posts)

        Reel tag extraction:
        1. Find tag button: <button> with <svg aria-label="Tags">
        2. Click the button to open popup
        3. Extract href attributes from popup: href="/username/"

        Returns:
            List of usernames (without @)
        """
        tagged = []

        try:
            # Step 1: Find and click tag button
            self.logger.debug("Looking for reel tag button...")

            # Look for button with Tags SVG
            tag_button = self.page.locator('button:has(svg[aria-label="Tags"])').first

            # Check if button exists
            if tag_button.count() == 0:
                self.logger.debug("No tag button found - reel has no tags")
                return ['No tags']

            # Click the tag button
            self.logger.debug("Clicking tag button...")
            tag_button.click(timeout=3000)

            # Step 2: Wait for popup to appear
            time.sleep(self.config.ui_animation_delay)

            # Step 3: Extract tagged accounts from popup
            self.logger.debug("Extracting tagged accounts from popup...")

            # Method 1: All links in the popup
            try:
                # Look for links with username pattern
                links = self.page.locator('a[href^="/"]').all()
                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=1000)
                        if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                            username = href.strip('/').split('/')[-1]
                            # Filter out Instagram system paths
                            if username and username not in ['explore', 'direct', 'accounts', 'p', 'reel'] and username not in tagged:
                                tagged.append(username)
                    except:
                        continue

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags in reel: {tagged}")

                    # Close popup by clicking outside or close button
                    try:
                        close_button = self.page.locator('button:has(svg[aria-label="Close"])').first
                        close_button.click(timeout=2000)
                    except:
                        # Try pressing Escape
                        self.page.keyboard.press('Escape')

                    return tagged
            except Exception as e:
                self.logger.debug(f"Reel tag extraction from popup failed: {e}")

            # If popup method failed, try closing and return
            try:
                self.page.keyboard.press('Escape')
            except:
                pass

        except Exception as e:
            self.logger.debug(f"Reel tag button click failed: {e}")

        # Fallback: Try post tag extraction method
        self.logger.debug("Fallback to post tag extraction for reel...")
        try:
            tagged = self.get_tagged_accounts()
            if tagged and tagged != ['No tags']:
                return tagged
        except Exception as e:
            self.logger.debug(f"Fallback tag extraction failed: {e}")

        self.logger.warning("No tags found in reel")
        return ['No tags']
