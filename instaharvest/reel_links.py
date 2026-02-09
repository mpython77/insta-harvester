"""
Instagram Scraper - Reel links collector
Scroll through reels page and collect all reel links

SEPARATE FILE - FOR REELS ONLY!
"""

import time
import random
from typing import List, Set, Optional, Dict
from pathlib import Path

from .base import BaseScraper
from .config import ScraperConfig
from .exceptions import ProfileNotFoundError


class ReelLinksScraper(BaseScraper):
    """
    Instagram REEL links scraper - REELS ONLY!

    Features:
    - Scrapes from {username}/reels/ page
    - Automatic scrolling with human-like behavior
    - Real-time progress tracking
    - Duplicate detection
    - Smart stopping (2-3 scroll attempts with no new reels = DONE)
    - Export to file
    """

    def __init__(self, config: Optional[ScraperConfig] = None):
        """Initialize reel links scraper"""
        super().__init__(config)
        self.logger.info("ReelLinksScraper ready (REELS ONLY)")

    def scrape(
        self,
        username: str,
        save_to_file: bool = True,
        output_file: Optional[str] = None
    ) -> List[str]:
        """
        Scrape all REEL links from {username}/reels/ page

        Args:
            username: Instagram username
            save_to_file: Save links to file
            output_file: Optional path to save file (overrides default)

        Returns:
            List of reel URLs (e.g., ['https://instagram.com/user/reel/ABC/', ...])
        """
        username = username.strip().lstrip('@')
        self.logger.info(f"🎬 Starting REEL links scrape for: @{username}")

        # Check if browser is already setup (SharedBrowser mode)
        is_shared_browser = self.page is not None and self.browser is not None

        if is_shared_browser:
            self.logger.debug("Using existing browser session (SharedBrowser mode)")
        else:
            # Load session and setup browser (standalone mode)
            self.logger.debug("Setting up new browser session (standalone mode)")
            session_data = self.load_session()
            self.setup_browser(session_data)

        try:
            # Navigate to REELS page (not profile!)
            reels_url = f'https://www.instagram.com/{username}/reels/'
            self.logger.info(f"📍 Navigating to: {reels_url}")
            self.goto_url(reels_url)

            # Check profile exists
            if not self._profile_exists():
                raise ProfileNotFoundError(f"Profile @{username} not found or has no reels")

            # Wait for reels to load
            time.sleep(self.config.reel_open_delay)

            # Scroll and collect reel links
            reel_links = self._scroll_and_collect()

            # Save to file (uses full dict with metadata)
            if save_to_file:
                self._save_links(reel_links, username, output_file)

            # Return only URL strings (as declared in return type)
            urls = [item['url'] for item in reel_links]
            self.logger.info(f"✅ Collected {len(urls)} REEL links")
            return urls

        finally:
            # Only close browser if not in SharedBrowser mode
            if not is_shared_browser:
                self.close()
            else:
                self.logger.debug("Keeping browser open (SharedBrowser mode)")

    def _profile_exists(self) -> bool:
        """Check if profile/reels page exists"""
        try:
            content = self.page.content()
            return 'Page Not Found' not in content and 'Sorry, this page' not in content
        except Exception:
            return False

    def _extract_current_reel_links(self) -> List[Dict[str, str]]:
        """
        Extract REEL links and metadata from div._ac7v containers (NEW INSTAGRAM STRUCTURE)

        Instagram structure on /reels/ page:
        - div._ac7v.x1ty9z65.xzboxd6 contains 3 reels
        - Each container has 3x <a href="/username/reel/XYZ/">
        - Thumbnail in style="background-image..."
        - Views count in span.html-span

        Returns:
            List of dicts with 'url', 'thumbnail', 'stats'
        """
        try:
            results = []
            seen_urls = set()

            # Find all post/reel grid containers
            containers = self.page.locator(self.config.selector_reel_container).all()

            for container in containers:
                try:
                    # Get all links within this container
                    links = container.locator('a[href]').all()

                    for link in links:
                        try:
                            href = link.get_attribute('href')
                            if not href:
                                continue

                            # ONLY collect /reel/ links
                            if '/reel/' not in href:
                                continue

                            # Make full URL
                            if href.startswith('/'):
                                href = f'https://www.instagram.com{href}'

                            # Skip duplicates within this batch
                            if href in seen_urls:
                                continue
                            seen_urls.add(href)

                            # Extract metadata
                            thumbnail = ""
                            stats = ""

                            # Try background image (standard for reels grid)
                            bg_div = link.locator(self.config.selector_grid_thumbnail_bg).first
                            if bg_div.count() > 0:
                                style = bg_div.get_attribute('style') or ""
                                if 'url("' in style:
                                    thumbnail = style.split('url("')[1].split('")')[0]
                                elif "url('" in style:
                                    thumbnail = style.split("url('")[1].split("')")[0]
                            
                            # Fallback to img tag
                            if not thumbnail:
                                img = link.locator('img').first
                                if img.count() > 0:
                                    thumbnail = img.get_attribute('src') or ""

                            # Try stats
                            stat_span = link.locator(self.config.selector_grid_time).first
                            if stat_span.count() > 0:
                                stats = stat_span.inner_text()

                            # Add reel data
                            results.append({
                                'url': href,
                                'thumbnail': thumbnail,
                                'stats': stats
                            })
                        except Exception:
                            continue
                except Exception:
                    continue

            return results

        except Exception as e:
            self.logger.error(f"Error extracting reel links: {e}")
            return []

    def _scroll_and_collect(self) -> List[Dict[str, str]]:
        """
        Scroll through reels page and collect all reel links (IMPROVED for Instagram lazy loading)

        Smart stopping: If 5 scrolls with NO new reels → DONE

        Returns:
            List of dicts with 'url', 'thumbnail', 'stats'
        """
        self.logger.info(f"🎬 Starting reel link collection...")

        all_reel_links = {}  # Dict[url, dict]
        scroll_attempts = 0
        no_new_reels_count = 0
        MAX_NO_NEW_REELS = self.config.scroll_max_no_new_attempts

        try:
            while True:
                # Extract current reel links
                current_items = self._extract_current_reel_links()
                previous_count = len(all_reel_links)

                # Add new reel links
                for item in current_items:
                    url = item['url']
                    if url not in all_reel_links:
                        all_reel_links[url] = item

                new_count = len(all_reel_links)

                # Log progress
                self.logger.info(
                    f"Progress: {new_count} reel links "
                    f"(+{new_count - previous_count} new)"
                )

                # Check if no new reels found
                if new_count == previous_count:
                    no_new_reels_count += 1
                    self.logger.info(f"⚠️ No new reels found ({no_new_reels_count}/{MAX_NO_NEW_REELS})")
                else:
                    # Reset counter if new reels found
                    no_new_reels_count = 0

                # Stopping condition: 5 scrolls with no new reels
                if no_new_reels_count >= MAX_NO_NEW_REELS:
                    self.logger.info(
                        f"✓ Finished! No new reels after {MAX_NO_NEW_REELS} scroll attempts. "
                        f"Total collected: {new_count}"
                    )
                    break

                # Safety: Max scroll attempts
                if scroll_attempts >= self.config.scroll_max_attempts_override:
                    self.logger.warning(
                        f"Max scroll attempts ({self.config.scroll_max_attempts_override}) reached"
                    )
                    break

                # IMPROVED: Scroll to bottom and wait for lazy loading
                self._aggressive_scroll()

                scroll_attempts += 1
        except KeyboardInterrupt:
             self.logger.warning("\n✋ Scraping interrupted by user! Saving collected data...")
             self.interrupted = True

        # Convert to list
        result = [
            all_reel_links[url] for url in sorted(all_reel_links.keys())
        ]
        return result

    def _aggressive_scroll(self) -> None:
        """
        Fast scroll optimized for Instagram's div._ac7v container loading

        As we scroll, Instagram loads new div._ac7v containers (each with 3 reels)
        """
        try:
            # Scroll to last container to trigger loading of next batch
            containers = self.page.locator(self.config.selector_reel_container).all()

            if len(containers) > 0:
                # Scroll last container into view to trigger lazy loading
                last_container = containers[-1]
                last_container.scroll_into_view_if_needed()
                time.sleep(self.config.scroll_content_load_delay)
            else:
                # Fallback: scroll to bottom
                self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(self.config.ui_stability_delay)
        except Exception:
            # Fallback: scroll to bottom
            self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(self.config.ui_stability_delay)

    def _save_links(self, reel_links: List[Dict[str, str]], username: str, output_file: Optional[str] = None) -> None:
        """
        Save reel links to file (URL + Stats + Thumbnail)

        Args:
            reel_links: List of reel dicts
            username: Username for filename
            output_file: Optional custom path
        """
        # Use a separate file for reels
        if output_file:
            path = Path(output_file)
        else:
            path = Path(self.config.base_output_dir) / self.config.reel_links_filename_pattern.format(username=username)
        
        # Ensure directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                for item in reel_links:
                    url = item.get('url', '')
                    stats = item.get('stats', '').replace('\n', ' ')
                    thumb = item.get('thumbnail', '')
                    f.write(f"{url}\t{stats}\t{thumb}\n")

            self.logger.info(f"💾 Reel links saved to: {path}")

        except Exception as e:
            self.logger.error(f"Failed to save reel links: {e}")
            raise
