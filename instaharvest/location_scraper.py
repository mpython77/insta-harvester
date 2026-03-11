"""
Instagram Location Scraper
Scrape posts from location explore pages.

Usage:
    from instaharvest import LocationScraper, ScraperConfig

    scraper = LocationScraper(ScraperConfig())
    result = scraper.scrape("213385402", max_posts=30)
    print(f"Location: {result.location_name}, {len(result.posts)} posts")
"""

import json
import time
import random
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from .base import BaseScraper
from .config import ScraperConfig


@dataclass
class LocationResult:
    """Result from location scraping"""
    location_id: str = ''
    location_name: str = ''
    address: str = ''
    post_count: int = 0
    posts: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocationScraper(BaseScraper):
    """
    Scrape posts from Instagram location pages.

    Navigate to /explore/locations/{location_id}/ and collect
    top and recent posts.

    Features:
    - Scrape by location ID
    - Smart scrolling with duplicate detection
    - Extract location metadata (name, address)
    - Configurable post limit
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)

    def scrape(
        self,
        location_id: str,
        target_count: Optional[int] = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> LocationResult:
        """
        Scrape posts from a location page.

        Args:
            location_id: Instagram location ID
            target_count: Maximum number of posts to collect (None = all)
            date_from: Filter start date 'YYYY-MM-DD' (inclusive)
            date_to: Filter end date 'YYYY-MM-DD' (inclusive)

        Returns:
            LocationResult with location data and posts
        """
        limit_str = str(target_count) if target_count else "all"
        self.logger.info(f"Scraping location: {location_id} (target: {limit_str} posts)")
        result = LocationResult(location_id=str(location_id))

        try:
            # ═══════ AUTO BROWSER SETUP ═══════
            is_shared_browser = self.page is not None and self.browser is not None
            if not is_shared_browser:
                session_data = self._load_session()
                self.setup_browser(session_data)

                # Warm-up: visit home first to activate session (only standalone)
                base = self.config.instagram_base_url.rstrip('/')
                self.goto_url(base)
                time.sleep(2.0)

            base = self.config.instagram_base_url.rstrip('/')
            # Now navigate to location page
            url = f"{base}/explore/locations/{location_id}/"
            self.goto_url(url)
            time.sleep(self.config.page_stability_delay)

            # Extract location metadata
            result.location_name = self._get_location_name()
            result.address = self._get_location_address()
            result.post_count = self._get_post_count()

            self.logger.info(
                f"Location: {result.location_name} "
                f"({result.post_count} posts)"
            )

            # Collect posts
            posts = self._scroll_and_collect(target_count=target_count)
            
            # ═══ DATE RANGE FILTER ═══
            if date_from or date_to:
                posts = self._filter_by_date_range(posts, date_from, date_to, url_key='url')
                
            result.posts = posts

            self.logger.info(f"Collected {len(posts)} posts from location")

        except Exception as e:
            self.logger.error(f"Location scraping failed: {e}")
            raise
        finally:
            if not is_shared_browser:
                self.close()

        return result

    def _get_location_name(self) -> str:
        """Extract location name from page"""
        try:
            selectors = [
                'h1',
                'header h1',
                'main h1',
            ]
            for selector in selectors:
                try:
                    el = self.page.locator(selector).first
                    if el.count() > 0:
                        text = el.inner_text().strip()
                        if text:
                            return text
                except Exception:
                    continue
        except Exception:
            pass
        return ''

    def _get_location_address(self) -> str:
        """Extract address from location page"""
        try:
            # Address is usually in a span below the heading
            selectors = [
                'header span',
                'main section span',
            ]
            for selector in selectors:
                try:
                    elements = self.page.locator(selector).all()
                    for el in elements:
                        text = el.inner_text().strip()
                        # Address typically has commas or numbers
                        if text and (',' in text or any(c.isdigit() for c in text)):
                            return text
                except Exception:
                    continue
        except Exception:
            pass
        return ''

    def _get_post_count(self) -> int:
        """Extract total post count"""
        try:
            selectors = ['header span', 'main span']
            for selector in selectors:
                try:
                    elements = self.page.locator(selector).all()
                    for el in elements:
                        text = el.inner_text().strip()
                        if text and 'post' in text.lower():
                            num_text = text.split()[0]
                            return self.parse_number(num_text)
                except Exception:
                    continue
        except Exception:
            pass
        return 0

    def _scroll_and_collect(self, max_posts: int) -> List[Dict[str, str]]:
        """Scroll and collect post links"""
        all_posts = []
        seen_urls = set()
        no_new_count = 0

        while len(all_posts) < max_posts and no_new_count < 5:
            current = self._extract_post_links()
            new_count = 0

            for post in current:
                if post['url'] not in seen_urls and len(all_posts) < max_posts:
                    seen_urls.add(post['url'])
                    all_posts.append(post)
                    new_count += 1

            if new_count == 0:
                no_new_count += 1
            else:
                no_new_count = 0

            if len(all_posts) < max_posts:
                self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')
                time.sleep(random.uniform(1.5, 2.5))

        return all_posts

    def _extract_post_links(self) -> List[Dict[str, str]]:
        """Extract post links from current page"""
        posts = []
        try:
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"]').all()
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        url = href if href.startswith('http') else f"https://www.instagram.com{href}"
                        post_type = 'Reel' if '/reel/' in url else 'Post'
                        posts.append({'url': url, 'type': post_type})
                except Exception:
                    continue
        except Exception:
            pass
        return posts

    def _load_session(self) -> Dict:
        session_file = Path(self.config.session_file)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}
