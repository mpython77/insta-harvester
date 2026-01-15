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
    likes: Optional[int] # Changed to Optional[int]
    timestamp: str
    content_type: str = 'Post'  # 'Post' or 'Reel'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PostDataScraper(BaseScraper):
    # ... (header docstring same) ...

    # ... (init methods same) ...
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
                    self.get_reel_likes_count, 'reel_likes', default=0
                ) if get_likes else 0

                timestamp = self._extract_with_recovery(
                    self.get_reel_timestamp, 'reel_timestamp', default='N/A'
                ) if get_timestamp else 'N/A'
            else:
                tagged_accounts = self._extract_with_recovery(
                    self.get_tagged_accounts, 'post_tags'
                ) if get_tags else []

                likes = self._extract_with_recovery(
                    self.get_likes_count, 'post_likes', default=0
                ) if get_likes else 0

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
         return self.error_handler.safe_extract(
            extractor=extractor_func,
            element_name=element_name,
            default=default if default is not None else []
        )
    
    # ... scrape_multiple can stay same mostly ...

    def get_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from posts (handles both IMAGE and VIDEO posts)
        Returns:
            List of usernames (without @)
        """
        tagged = []

        # Check if this post has tags (look for Tags SVG)
        # Using improved regex-like replacement for selector cleanup if needed, or just trust config
        # Simply trusting config selector execution or checking button existence
        
        # STEP 1: Detect if this is a VIDEO post
        is_video_post = False
        try:
            video_count = self.page.locator('video').count()
            if video_count > 0:
                is_video_post = True
                self.logger.debug("Detected VIDEO post")
            else:
                self.logger.debug("Detected IMAGE post")
        except:
            pass

        # STEP 2: If VIDEO post, use POPUP extraction
        if is_video_post:
            self.logger.debug("Using VIDEO post tag extraction (popup method)...")
            try:
                tag_button = self.page.locator(self.config.selector_tag_button).first
                if tag_button.count() > 0:
                     tag_button.click(timeout=self.config.tag_button_click_timeout)
                     time.sleep(self.config.popup_animation_delay)
                     time.sleep(self.config.popup_content_load_delay)
                     
                     popup_container = self.page.locator(self.config.selector_popup_containers[0]).first
                     if popup_container.count() == 0:
                         popup_container = self.page.locator(self.config.selector_popup_dialog).first
                     
                     if popup_container.count() > 0:
                         popup_links = popup_container.locator('a[href^="/"]').all()
                         for link in popup_links:
                             try:
                                 href = link.get_attribute('href', timeout=1000)
                                 if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                                     username = href.strip('/').split('/')[-1]
                                     if username not in self.config.instagram_system_paths and username not in tagged:
                                         tagged.append(username)
                             except:
                                 continue
                         
                         # Close popup
                         try:
                             self.page.locator(self.config.selector_close_button).first.click(timeout=self.config.popup_close_timeout)
                         except:
                             self.page.keyboard.press('Escape')
            except Exception as e:
                self.logger.debug(f"VIDEO popup extraction failed: {e}")

        # STEP 3: IMAGE post (or fallback)
        # Use config-driven selector for tag container
        self.logger.debug(f"Using IMAGE post tag extraction ({self.config.selector_post_tag_container})...")
        try:
             tag_containers = self.page.locator(self.config.selector_post_tag_container).all()
             for container in tag_containers:
                 try:
                     href = container.locator('a[href]').first.get_attribute('href', timeout=self.config.attribute_timeout)
                     if href:
                         username = href.strip('/').split('/')[-1]
                         if username not in self.config.instagram_system_paths and username not in tagged:
                             tagged.append(username)
                 except:
                     continue
        except Exception as e:
             self.logger.warning(f"Tag extraction failed: {e}")

        if tagged:
            self.logger.info(f"✓ Found {len(tagged)} tags: {tagged}")
            return tagged

        # No tags found
        self.logger.debug("No tags found")
        if self.config.return_empty_list_for_no_tags:
            return []
        return [self.config.default_no_tags_text]


    def get_likes_count(self) -> int:
        """
        Extract likes count with multiple fallback methods

        Returns:
            Likes count as int
        """
        # Method 1: span[role="button"] after Like SVG (new structure)
        try:
            section = self.page.locator('section').first
            spans = section.locator('span[role="button"]').all()

            for span in spans[:2]:  # First 2 spans (likes and comments)
                try:
                    text = span.inner_text(timeout=self.config.visibility_timeout).strip()
                    val = self.parse_number(text)
                    if val is not None:
                        self.logger.debug(f"✓ Found likes (method 1): {val}")
                        return val
                except Exception:
                    continue
        except Exception:
            pass

        # Method 2: Direct class selector
        try:
            section = self.page.locator('section').first
            likes_span = section.locator(self.config.selector_likes_options[0]).first
            likes_text = likes_span.inner_text(timeout=self.config.visibility_timeout).strip()
            val = self.parse_number(likes_text)
            if val is not None:
                 self.logger.debug(f"✓ Found likes (method 2): {val}")
                 return val
        except Exception:
            pass

        # Method 3: Link-based (old structure)
        try:
            likes_link = self.page.locator('a[href*="/liked_by/"]').first
            likes_text = likes_link.locator(self.config.selector_html_span).first.inner_text(timeout=self.config.visibility_timeout)
            val = self.parse_number(likes_text)
            if val is not None:
                self.logger.debug(f"✓ Found likes (method 3): {val}")
                return val
        except Exception:
            pass

        # Method 4: Text-based search
        try:
            likes_count = self.page.locator('span:has-text("likes")').count()
            for i in range(likes_count):
                try:
                    span = self.page.locator('span:has-text("likes")').nth(i)
                    number = span.locator(self.config.selector_html_span).first
                    text = number.inner_text(timeout=self.config.visibility_timeout)
                    val = self.parse_number(text)
                    if val is not None:
                        self.logger.debug(f"✓ Found likes (method 4): {val}")
                        return val
                except Exception:
                    continue
        except Exception:
            pass

        self.logger.warning("All methods failed to extract likes count")
        return 0

    def get_reel_likes_count(self) -> int:
        """
        Extract likes count from REEL (different HTML structure than posts)

        Returns:
            Likes count as int
        """
        # Method 1: Reel-specific selector (user provided)
        try:
            likes_span = self.page.locator(self.config.selector_reel_likes + '[role="button"]').first
            likes_text = likes_span.inner_text(timeout=self.config.reel_likes_timeout).strip()
            val = self.parse_number(likes_text)
            if val is not None:
                self.logger.debug(f"✓ Found reel likes: {val}")
                return val
        except Exception as e:
            self.logger.debug(f"Reel likes method 1 failed: {e}")

        # Method 2: General span with role=button (first one is usually likes)
        try:
            spans = self.page.locator('span[role="button"]').all()
            for span in spans[:3]:  # Check first 3
                try:
                    text = span.inner_text(timeout=self.config.visibility_timeout).strip()
                    val = self.parse_number(text)
                    if val is not None:
                        self.logger.debug(f"✓ Found reel likes (method 2): {val}")
                        return val
                except:
                    continue
        except Exception as e:
            self.logger.debug(f"Reel likes method 2 failed: {e}")

        self.logger.warning("Failed to extract reel likes count")
        return 0

    def get_reel_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from REEL (different logic than posts)
        Returns:
            List of usernames (without @)
        """
        tagged = []

        try:
            # Step 1: Find and click tag button
            self.logger.debug("Looking for reel tag button...")
            tag_button = self.page.locator(self.config.selector_tag_button).first

            # Check if button exists
            if tag_button.count() == 0:
                self.logger.debug("No tag button found - reel has no tags")
                if self.config.return_empty_list_for_no_tags:
                    return []
                return [self.config.default_no_tags_text]

            # Click
            tag_button.click(timeout=self.config.tag_button_click_timeout)
            time.sleep(self.config.ui_animation_delay)

            # Step 3: Extract tagged accounts from popup
            self.logger.debug("Extracting tagged accounts from popup...")

            try:
                # Look for links with username pattern
                links = self.page.locator('a[href^="/"]').all()
                for link in links:
                    try:
                        href = link.get_attribute('href', timeout=1000)
                        if href and href.startswith('/') and href.endswith('/') and href.count('/') == 2:
                            username = href.strip('/').split('/')[-1]
                            if username and username not in self.config.instagram_system_paths and username not in tagged:
                                tagged.append(username)
                    except:
                        continue

                # Close popup
                try:
                    self.page.locator(self.config.selector_close_button).first.click(timeout=self.config.popup_close_timeout)
                except:
                    self.page.keyboard.press('Escape')

                if tagged:
                    self.logger.info(f"✓ Found {len(tagged)} tags in reel: {tagged}")
                    return tagged
            except Exception as e:
                self.logger.debug(f"Reel tag extraction from popup failed: {e}")
                self.page.keyboard.press('Escape')

        except Exception as e:
            self.logger.debug(f"Reel tag button click failed: {e}")

        # Fallback to post tags? Maybe not for reels, usually different.
        
        self.logger.warning("No tags found in reel")
        if self.config.return_empty_list_for_no_tags:
            return []
        return [self.config.default_no_tags_text]

