"""
Instagram Explore/Discover Scraper
Scrape trending posts from the Instagram explore page.

Usage:
    from instaharvest import ExploreScraper, ScraperConfig

    scraper = ExploreScraper(ScraperConfig())
    result = scraper.scrape(max_posts=50)
    print(f"Found {len(result.posts)} trending posts")
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any

from .base import BaseScraper
from .config import ScraperConfig


@dataclass
class ExploreResult:
    """Result from explore page scraping"""
    posts: List[Dict[str, str]] = field(default_factory=list)
    timestamp: str = ''
    total_collected: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExploreScraper(BaseScraper):
    """
    Scrape trending/suggested posts from Instagram's Explore page.

    Navigates to /explore/ and collects posts from the discovery grid.

    Features:
    - Collects explore page posts (curated/trending)
    - Smart scrolling with staleness detection
    - Configurable post limit
    - Captures post types (Post/Reel)
    - Timestamp tracking
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        super().__init__(config)

    def scrape(
        self,
        target_count: Optional[int] = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> ExploreResult:
        """
        Scrape posts from the explore page.

        Args:
            target_count: Maximum posts to collect (None = all)
            date_from: Filter start date 'YYYY-MM-DD' (inclusive)
            date_to: Filter end date 'YYYY-MM-DD' (inclusive)

        Returns:
            ExploreResult with trending posts
        """
        limit_str = str(target_count) if target_count else "all"
        self.logger.info(f"Scraping explore page (target: {limit_str} posts)")

        result = ExploreResult(
            timestamp=datetime.now().isoformat()
        )

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
            # Navigate to explore
            url = f"{base}/explore/"
            self.goto_url(url)
            time.sleep(self.config.page_stability_delay + 1.0)  # Extra wait for explore grid

            # Collect posts
            posts = self._scroll_and_collect(target_count=target_count)

            # ═══ DATE RANGE FILTER ═══
            if date_from or date_to:
                posts = self._filter_by_date_range(posts, date_from, date_to, url_key='url')

            result.posts = posts
            result.total_collected = len(posts)

            self.logger.info(f"Collected {len(posts)} explore posts")

        except Exception as e:
            self.logger.error(f"Explore scraping failed: {e}")
            raise
        finally:
            if not is_shared_browser:
                self.close()

        return result

    def scrape_topic(
        self,
        topic_id: str,
        target_count: Optional[int] = 50,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None
    ) -> ExploreResult:
        """
        Scrape posts from a specific explore topic/category.

        Args:
            topic_id: Explore topic ID
            target_count: Maximum posts to collect (None = all)
            date_from: Filter start date 'YYYY-MM-DD' (inclusive)
            date_to: Filter end date 'YYYY-MM-DD' (inclusive)

        Returns:
            ExploreResult
        """
        limit_str = str(target_count) if target_count else "all"
        self.logger.info(f"Scraping explore topic: {topic_id} (target: {limit_str} posts)")

        result = ExploreResult(timestamp=datetime.now().isoformat())

        try:
            session_data = self._load_session()
            self.setup_browser(session_data)

            url = f"{self.config.instagram_base_url.rstrip('/')}/explore/search/{topic_id}/"
            self.goto_url(url)
            time.sleep(self.config.page_stability_delay)

            posts = self._scroll_and_collect(target_count=target_count)
            
            # ═══ DATE RANGE FILTER ═══
            if date_from or date_to:
                posts = self._filter_by_date_range(posts, date_from, date_to, url_key='url')
                
            result.posts = posts
            result.total_collected = len(posts)

        except Exception as e:
            self.logger.error(f"Topic scraping failed: {e}")
            raise
        finally:
            self.close()

        return result

    def _scroll_and_collect(self, target_count: Optional[int]) -> List[Dict[str, str]]:
        """Scroll explore grid and collect post links"""
        all_posts = []
        seen_urls = set()
        no_new_count = 0

        while target_count is None or len(all_posts) < target_count:
            if no_new_count >= 5:
                break
                
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

            self.logger.debug(
                f"Explore: {len(all_posts)}/{target_count} "
                f"(+{new_count} new)"
            )

            if target_count is None or len(all_posts) < target_count:
                self.page.evaluate(
                    'window.scrollBy(0, window.innerHeight * 0.8)'
                )
                time.sleep(random.uniform(1.5, 2.5))

        return all_posts

    def _extract_post_links(self) -> List[Dict[str, str]]:
        """Extract post links from explore grid"""
        posts = []
        try:
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"]').all()
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        url = href if href.startswith('http') else f"https://www.instagram.com{href}"
                        post_type = 'Reel' if '/reel/' in url else 'Post'
                        posts.append({
                            'url': url,
                            'type': post_type,
                        })
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
