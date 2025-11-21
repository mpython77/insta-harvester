"""
Instagram Scraper - Post links collector
Scroll through profile and collect all post/reel links
"""

import time
import random
from typing import List, Set, Optional
from pathlib import Path

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import ProfileNotFoundError


class PostLinksScraper(BaseScraper):
    """
    Instagram post links scraper with intelligent scrolling

    Features:
    - Automatic scrolling with human-like behavior
    - Real-time progress tracking
    - Duplicate detection
    - Smart stopping (target reached or no new content)
    - Export to file
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
    ) -> List[str]:
        """
        Scrape all post links from profile

        Args:
            username: Instagram username
            target_count: Target number of links (None = scrape all)
            save_to_file: Save links to file

        Returns:
            List of post URLs
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

    def _extract_current_links(self) -> Set[str]:
        """Extract all visible post/reel links from current viewport"""
        try:
            # Find all post and reel links
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"]').all()

            hrefs = set()
            for link in links:
                try:
                    href = link.get_attribute('href')
                    if href:
                        # Make full URL
                        if href.startswith('/'):
                            href = f'https://www.instagram.com{href}'
                        hrefs.add(href)
                except Exception:
                    continue

            return hrefs
        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
            return set()

    def _scroll_and_collect(self, target_count: int) -> List[str]:
        """
        Scroll through profile and collect all links

        Args:
            target_count: Target number of links

        Returns:
            List of unique post URLs
        """
        self.logger.info(f"Starting scroll collection (target: {target_count})...")

        all_links: Set[str] = set()
        scroll_attempts = 0
        no_new_links_count = 0

        while True:
            # Extract current links
            current_links = self._extract_current_links()
            previous_count = len(all_links)
            all_links.update(current_links)
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

            if no_new_links_count >= self.config.no_new_content_threshold:
                self.logger.warning(
                    f"No new links after {self.config.no_new_content_threshold} attempts. "
                    f"Collected: {new_count}/{target_count}"
                )
                break

            if scroll_attempts >= self.config.max_scroll_attempts:
                self.logger.warning(
                    f"Max scroll attempts ({self.config.max_scroll_attempts}) reached"
                )
                break

            # Scroll down (human-like)
            self._human_like_scroll()

            scroll_attempts += 1

        return sorted(list(all_links))

    def _human_like_scroll(self) -> None:
        """Scroll down with human-like behavior"""
        # Scroll 80% of viewport height
        self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')

        # Random delay
        delay = random.uniform(
            self.config.scroll_delay_min,
            self.config.scroll_delay_max
        )
        time.sleep(delay)

    def _save_links(self, links: List[str]) -> None:
        """
        Save links to file

        Args:
            links: List of URLs to save
        """
        output_file = Path(self.config.links_file)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                for link in links:
                    f.write(link + '\n')

            self.logger.info(f"Links saved to: {output_file}")

        except Exception as e:
            self.logger.error(f"Failed to save links: {e}")
            raise
