"""
Instagram Scraper - Post data extractor
Extract tags, likes, and timestamps from individual posts
"""

import time
import random
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import HTMLStructureChangedError


@dataclass
class PostData:
    """Post data structure"""
    url: str
    tagged_accounts: List[str]
    likes: str
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


class PostDataScraper(BaseScraper):
    """
    Instagram post data scraper

    Features:
    - Extract tagged accounts
    - Extract likes count
    - Extract post timestamp
    - Multiple fallback methods
    - HTML structure change detection
    - Modular extraction (get only what you need)
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize post data scraper"""
        super().__init__(config)
        self.logger.info("PostDataScraper ready")

    def scrape(
        self,
        post_url: str,
        *,
        get_tags: bool = True,
        get_likes: bool = True,
        get_timestamp: bool = True
    ) -> PostData:
        """
        Scrape data from a single post

        Args:
            post_url: URL of the post
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract post timestamp

        Returns:
            PostData object
        """
        self.logger.info(f"Scraping post: {post_url}")

        # Navigate to post
        self.goto_url(post_url)

        # Wait for post to load
        time.sleep(2)

        # Extract data
        data = PostData(
            url=post_url,
            tagged_accounts=self.get_tagged_accounts() if get_tags else [],
            likes=self.get_likes_count() if get_likes else 'N/A',
            timestamp=self.get_timestamp() if get_timestamp else 'N/A'
        )

        self.logger.debug(
            f"Extracted: {len(data.tagged_accounts)} tags, "
            f"{data.likes} likes, time={data.timestamp}"
        )

        return data

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
        Scrape multiple posts sequentially

        Args:
            post_urls: List of post URLs
            get_tags: Extract tagged accounts
            get_likes: Extract likes count
            get_timestamp: Extract post timestamp
            delay_between_posts: Add delay between posts (rate limiting)

        Returns:
            List of PostData objects
        """
        self.logger.info(f"Scraping {len(post_urls)} posts...")

        # Load session and setup browser
        session_data = self.load_session()
        self.setup_browser(session_data)

        results = []

        try:
            for i, url in enumerate(post_urls, 1):
                self.logger.info(f"[{i}/{len(post_urls)}] Processing: {url}")

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
                        timestamp='N/A'
                    ))

                # Delay between posts (rate limiting)
                if delay_between_posts and i < len(post_urls):
                    delay = random.uniform(
                        self.config.post_scrape_delay_min,
                        self.config.post_scrape_delay_max
                    )
                    self.logger.debug(f"Waiting {delay:.1f}s...")
                    time.sleep(delay)

            return results

        finally:
            self.close()

    def get_tagged_accounts(self) -> List[str]:
        """
        Extract tagged accounts from post

        Returns:
            List of usernames (without @)
        """
        selector = '._aa1y'

        def extract():
            tag_containers = self.page.locator(selector).all()
            tagged = []

            for container in tag_containers:
                try:
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href')
                    if href:
                        username = href.strip('/').split('/')[-1]
                        tagged.append(username)
                except Exception:
                    continue

            return tagged if tagged else ['No tags']

        result = self.safe_extract(
            extract,
            element_name='tagged_accounts',
            selector=selector,
            default=['No tags']
        )

        return result

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
