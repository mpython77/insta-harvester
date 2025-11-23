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
        Extract POST links from div._ac7v containers (NEW INSTAGRAM STRUCTURE)
        OPTIMIZED: Fast extraction matching ReelLinksScraper approach

        Instagram structure:
        - div._ac7v.x1ty9z65.xzboxd6 contains 3-4 posts/reels per row
        - Each container has 3-4x <a href="/username/p/ABC/" or href="/username/reel/XYZ/">
        - We ONLY collect /p/ links (posts), skip /reel/

        Returns:
            List of dictionaries with 'url' and 'type' keys
        """
        try:
            results = []
            seen_urls = set()

            # Find all post/reel grid containers
            containers = self.page.locator('div._ac7v.x1ty9z65.xzboxd6').all()

            for container in containers:
                try:
                    # Get all links within this container
                    links = container.locator('a[href]').all()

                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            if not href:
                                continue

                            # ONLY collect /p/ links (posts), skip /reel/
                            if '/p/' not in href:
                                continue

                            # Make full URL
                            if href.startswith('/'):
                                href = f'https://www.instagram.com{href}'

                            # Skip duplicates
                            if href in seen_urls:
                                continue
                            seen_urls.add(href)

                            # Add post
                            results.append({
                                'url': href,
                                'type': 'Post'
                            })
                        except:
                            continue
                except:
                    continue

            return results

        except Exception as e:
            self.logger.error(f"Error extracting links: {e}")
            return []

    def _scroll_and_collect(self, target_count: int) -> List[Dict[str, str]]:
        """
        Scroll through profile and collect all links (IMPROVED for Instagram lazy loading)
        OPTIMIZED: Matching ReelLinksScraper's proven approach

        Args:
            target_count: Target number of links

        Returns:
            List of dictionaries with 'url' and 'type' keys
        """
        self.logger.info(f"Starting scroll collection (target: {target_count})...")

        all_links: Dict[str, str] = {}  # url -> type mapping
        scroll_attempts = 0
        no_new_links_count = 0
        MAX_NO_NEW = 7  # Increased to 7 for better coverage (Instagram sometimes slow)

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
                self.logger.info(f"⚠️ No new links found ({no_new_links_count}/{MAX_NO_NEW})")
            else:
                # Reset counter if new links found
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

            if scroll_attempts >= 150:  # Increased limit matching ReelLinksScraper
                self.logger.warning(f"Max scroll attempts (150) reached")
                break

            # IMPROVED: Fast scroll matching ReelLinksScraper
            self._aggressive_scroll()

            scroll_attempts += 1

        # Convert dict back to list of dicts, sorted by URL
        result = [{'url': url, 'type': content_type} for url, content_type in sorted(all_links.items())]
        return result

    def _aggressive_scroll(self) -> None:
        """
        Smart scroll with intelligent waiting for Instagram's lazy loading
        OPTIMIZED: Scrolls gradually (not to the very last container) for better loading

        As we scroll, Instagram loads new div._ac7v containers (each with 3-4 posts)
        We scroll to 2-3 containers before the last one to avoid jumping too far
        """
        try:
            # Get current container count BEFORE scroll
            containers = self.page.locator('div._ac7v.x1ty9z65.xzboxd6').all()
            containers_before = len(containers)

            if len(containers) > 0:
                # GRADUAL SCROLL: Scroll to 3rd container from end (not the very last)
                # This prevents jumping too far and missing intermediate content
                scroll_target_index = max(0, len(containers) - 3)
                target_container = containers[scroll_target_index]

                # Scroll to target container (gradual, not to the very end)
                target_container.scroll_into_view_if_needed()

                self.logger.debug(f"Scrolled to container {scroll_target_index + 1}/{len(containers)} (3 from end)")

                # INTELLIGENT WAIT: Keep checking until new containers load (max 5 seconds)
                wait_time = 0
                max_wait = 5.0  # Maximum 5 seconds to wait for new containers
                check_interval = 0.5  # Check every 0.5 seconds

                while wait_time < max_wait:
                    time.sleep(check_interval)
                    wait_time += check_interval

                    # Check if new containers appeared
                    containers_after = len(self.page.locator('div._ac7v.x1ty9z65.xzboxd6').all())
                    if containers_after > containers_before:
                        # New containers loaded! Wait a bit more for stability
                        time.sleep(0.5)
                        self.logger.debug(f"✓ New containers loaded: {containers_before} → {containers_after}")
                        return

                # If no new containers after max_wait, scroll a bit more
                self.logger.debug(f"No new containers after {max_wait}s, trying small scroll")
                self.page.evaluate('window.scrollBy(0, 300)')  # Small 300px scroll
                time.sleep(1.0)
            else:
                # Fallback: small scroll
                self.page.evaluate('window.scrollBy(0, 300)')
                time.sleep(1.0)
        except:
            # Fallback: small scroll
            self.page.evaluate('window.scrollBy(0, 300)')
            time.sleep(1.0)

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
