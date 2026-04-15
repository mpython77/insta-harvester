"""
Instagram Hashtag Scraper
Scrape posts from hashtag explore pages.

Usage:
    from instaharvest import HashtagScraper, ScraperConfig

    scraper = HashtagScraper(ScraperConfig())
    result = scraper.scrape("fashion", max_posts=50)
    print(f"Found {result.post_count} posts for #{result.hashtag}")
"""

import time
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from .base import BaseScraper
from .config import ScraperConfig


@dataclass
class HashtagResult:
    """Result data from hashtag scraping"""
    hashtag: str = ''
    post_count: int = 0
    posts: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HashtagScraper(BaseScraper):
    """
    Scrape posts from Instagram hashtag pages.

    Navigates to /explore/tags/{hashtag}/, scrolls to collect
    post links, and returns structured results.

    Features:
    - Collects top and recent posts
    - Smart scrolling with duplicate detection
    - Configurable post limit
    - Human-like interaction delays
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)

    def scrape(
        self,
        hashtag: str,
        target_count: Optional[int] = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> HashtagResult:
        """
        Scrape posts from a hashtag page.

        Args:
            hashtag: Hashtag name (without #)
            target_count: Maximum number of posts to collect (None = all)
            date_from: Filter start date 'YYYY-MM-DD' (inclusive)
            date_to: Filter end date 'YYYY-MM-DD' (inclusive)

        Returns:
            HashtagResult with post data
        """
        hashtag = hashtag.strip().lstrip('#').lower()
        limit_str = str(target_count) if target_count else "all"
        self.logger.info(f"Scraping hashtag: #{hashtag} (target: {limit_str} posts)")

        result = HashtagResult(hashtag=hashtag)

        try:
            # ═══════ AUTO BROWSER SETUP ═══════
            is_shared_browser = self.page is not None and self.browser is not None
            if not is_shared_browser:
                session_data = self._load_session()
                self.setup_browser(session_data)

            # Navigate to hashtag page
            url = f"{self.config.instagram_base_url.rstrip('/')}/explore/tags/{hashtag}/"
            self.goto_url(url)
            time.sleep(self.config.page_stability_delay)

            # Get post count from page header
            result.post_count = self._get_post_count()
            self.logger.info(f"#{hashtag}: {result.post_count} total posts")

            # Collect post links
            posts = self._scroll_and_collect(target_count=target_count)
            
            # ═══ DATE RANGE FILTER ═══
            if date_from or date_to:
                posts = self._filter_by_date_range(posts, date_from, date_to, url_key='url')
                
            result.posts = posts

            self.logger.info(f"Collected {len(posts)} posts for #{hashtag}")

        except Exception as e:
            self.logger.error(f"Hashtag scraping failed: {e}")
            raise
        finally:
            if not is_shared_browser:
                self.close()

        return result

    def _get_post_count(self) -> int:
        """Extract total post count from hashtag page header"""
        try:
            selectors = [
                'header span',
                'span.x1lliihq',
                'meta[name="description"]',
            ]
            for selector in selectors:
                try:
                    elements = self.page.locator(selector).all()
                    for el in elements:
                        text = el.inner_text() if selector != 'meta[name="description"]' else (el.get_attribute('content') or '')
                        if text and any(c.isdigit() for c in text):
                            result = self.parse_number(text.split()[0])
                            if result is not None and isinstance(result, (int, float)):
                                return int(result)
                except Exception:
                    continue
        except Exception:
            pass
        return 0

    def _scroll_and_collect(self, target_count: Optional[int]) -> List[Dict[str, str]]:
        """Scroll and collect post links from hashtag grid"""
        all_posts = []
        seen_urls = set()
        no_new_count = 0

        while target_count is None or len(all_posts) < target_count:
            if no_new_count >= 5:
                break
                
            # Extract current links
            current = self._extract_post_links()
            new_count = 0

            for post in current:
                if target_count is not None and len(all_posts) >= target_count:
                    break
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    all_posts.append(post)
                    new_count += 1

            if new_count == 0:
                no_new_count += 1
            else:
                no_new_count = 0

            if target_count is not None and len(all_posts) >= target_count:
                break

            self.logger.debug(
                f"Collected: {len(all_posts)}/{target_count} "
                f"(+{new_count} new, stale={no_new_count})"
            )

            # Scroll down
            if target_count is None or len(all_posts) < target_count:
                self.page.evaluate(
                    'window.scrollBy(0, window.innerHeight * 0.8)'
                )
                time.sleep(random.uniform(1.5, 2.5))

        return all_posts

    def _extract_post_links(self) -> List[Dict[str, str]]:
        """Extract post links from current visible grid"""
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
        """Load session from file"""
        import json
        from pathlib import Path
        session_file = Path(self.config.session_file)
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
        return {}
