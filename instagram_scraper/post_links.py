"""
Instagram Scraper - Post links collector
Scroll through profile and collect ONLY POST links (NO REELS)

NOTE: Reels are collected separately by ReelLinksScraper from /reels/ page
"""

import time
import random
from typing import List, Set, Optional, Dict
from pathlib import Path

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import ProfileNotFoundError


class PostLinksScraper(BaseScraper):
    """
    Instagram POST links scraper with intelligent scrolling (POSTS ONLY - NO REELS!)

    Features:
    - Collects ONLY posts (a[href*="/p/"]) - reels are handled separately
    - Automatic scrolling with human-like behavior
    - Real-time progress tracking
    - Duplicate detection
    - Smart stopping (target reached or no new content)
    - Export to file

    NOTE: For reels, use ReelLinksScraper which scrapes from /reels/ page
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize post links scraper"""
        super().__init__(config)
        self.logger.info("PostLinksScraper ready")

    def scrape(
        self,
        username: str,
        target_count: Optional[int] = None,
        save_to_file: bool = True
    ) -> List[Dict[str, str]]:
        """
        Scrape all POST links from profile (POSTS ONLY - NO REELS!)

        Args:
            username: Instagram username
            target_count: Target number of links (None = scrape all)
            save_to_file: Save links to file

        Returns:
            List of dictionaries with 'url' and 'type' keys (all type='Post')
            Example: [{'url': 'https://.../p/ABC/', 'type': 'Post'}]

        NOTE: For reels, use ReelLinksScraper which scrapes from /reels/ page
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"Starting post links scrape for: @{username}")

        # Load session and setup browser
        session_data = self.load_session()
        self.setup_browser(session_data)

        try:
            # Navigate to profile
            profile_url = f'https://www.instagram.com/{username}/'
            self.goto_url(profile_url)

            # Check profile exists
            if not self._profile_exists():
                raise ProfileNotFoundError(f"Profile @{username} not found")

            # Get target count if not provided
            if target_count is None:
                target_count = self._get_posts_count()
                self.logger.info(f"Target: {target_count} posts")

            # Scroll and collect links
            links = self._scroll_and_collect(target_count)

            # Save to file
            if save_to_file:
                self._save_links(links)

            self.logger.info(f"Collected {len(links)} post links")
            return links

        finally:
            self.close()

    def _profile_exists(self) -> bool:
        """Check if profile exists"""
        try:
            content = self.page.content()
            return 'Page Not Found' not in content and 'Sorry, this page' not in content
        except Exception:
            return False

    def _get_posts_count(self) -> int:
        """Get total posts count from profile"""
        try:
            self.page.wait_for_selector('span:has-text("posts")', timeout=10000)
            posts_element = self.page.locator('span:has-text("posts")').first
            posts_text = posts_element.locator('span.html-span').first.inner_text()
            count = int(posts_text.strip().replace(',', ''))
            return count
        except Exception as e:
            self.logger.warning(f"Could not get posts count: {e}")
            return 9999  # Large number as fallback

    def _extract_current_links(self) -> List[Dict[str, str]]:
        """
        Extract all visible POST links from current viewport (POSTS ONLY - NO REELS!)

        Returns:
            List of dictionaries with 'url' and 'type' keys
            Example: [{'url': 'https://...', 'type': 'Post'}]
        """
        try:
            # IMPORTANT: Find ONLY post links (a[href*="/p/"]) - NO REELS!
            # Reels are collected separately by ReelLinksScraper from /reels/ page
            links = self.page.locator('a[href*="/p/"]').all()

            results = []
            seen_urls = set()

            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        # Skip if it's actually a reel (safety check)
                        if '/reel/' in href:
                            continue

                        # Make full URL
                        if href.startswith('/'):
                            href = f'https://www.instagram.com{href}'

                        # Skip duplicates
                        if href in seen_urls:
                            continue
                        seen_urls.add(href)

                        # Only posts (no reels)
                        results.append({
                            'url': href,
                            'type': 'Post'
                        })
                except Exception:
                    continue

            return results
        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
            return []

    def _scroll_and_collect(self, target_count: int) -> List[Dict[str, str]]:
        """
        Scroll through profile and collect all links (IMPROVED for Instagram lazy loading)

        Args:
            target_count: Target number of links

        Returns:
            List of dictionaries with 'url' and 'type' keys
        """
        self.logger.info(f"Starting scroll collection (target: {target_count})...")

        all_links: Dict[str, str] = {}  # url -> type mapping
        scroll_attempts = 0
        no_new_links_count = 0
        MAX_NO_NEW = 5  # Increased from 3 to 5 for better coverage

        while True:
            # Extract current links
            current_links = self._extract_current_links()
            previous_count = len(all_links)

            # Add new links (url as key, type as value)
            for link_data in current_links:
                url = link_data['url']
                content_type = link_data['type']
                if url not in all_links:
                    all_links[url] = content_type

            new_count = len(all_links)

            # Log progress
            self.logger.info(
                f"Progress: {new_count}/{target_count} links "
                f"(+{new_count - previous_count} new)"
            )

            # Check if no new links found
            if new_count == previous_count:
                no_new_links_count += 1
            else:
                no_new_links_count = 0

            # Stopping conditions
            if new_count >= target_count:
                self.logger.info("✓ Target reached!")
                break

            if no_new_links_count >= MAX_NO_NEW:
                self.logger.warning(
                    f"No new links after {MAX_NO_NEW} attempts. "
                    f"Collected: {new_count}/{target_count}"
                )
                break

            if scroll_attempts >= self.config.max_scroll_attempts:
                self.logger.warning(
                    f"Max scroll attempts ({self.config.max_scroll_attempts}) reached"
                )
                break

            # IMPROVED: Scroll to bottom and wait for lazy loading
            self._aggressive_scroll()

            scroll_attempts += 1

        # Convert dict back to list of dicts, sorted by URL
        result = [{'url': url, 'type': content_type} for url, content_type in sorted(all_links.items())]
        return result

    def _aggressive_scroll(self) -> None:
        """Aggressive scrolling to ensure all content loads (Instagram lazy loading fix)"""
        # Scroll to bottom of page
        self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')

        # Wait for lazy loading (Instagram needs more time)
        time.sleep(1.5)

        # Small scroll up and down to trigger loading
        self.page.evaluate('window.scrollBy(0, -200)')
        time.sleep(0.3)
        self.page.evaluate('window.scrollBy(0, 200)')

        # Additional wait with random delay
        delay = random.uniform(
            self.config.scroll_delay_min,
            self.config.scroll_delay_max
        )
        time.sleep(delay)

    def _save_links(self, links: List[Dict[str, str]]) -> None:
        """
        Save links to file

        Args:
            links: List of link dictionaries with 'url' and 'type' keys
        """
        output_file = Path(self.config.links_file)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for link_data in links:
                    url = link_data['url']
                    content_type = link_data['type']
                    f.write(f"{url}\t{content_type}\n")

            self.logger.info(f"Links saved to: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to save links: {e}")
            raise
