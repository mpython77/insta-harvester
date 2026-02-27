"""
Instagram Post Links Scraper - USER'S PROVEN 100% ACCURATE METHOD
Collects post and reel links with human-like scrolling
"""

import json
import os
import time
import random
import signal  # [NEW]
from typing import List, Set, Optional, Dict
from pathlib import Path


from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Import library components for PostLinksScraper
try:
    from .base import BaseScraper
    from .config import ScraperConfig
    from .exceptions import ProfileNotFoundError
    from .session_utils import find_session_file
    LIBRARY_AVAILABLE = True
except ImportError:
    LIBRARY_AVAILABLE = False


class InstagramPostLinksScraper:
    """Instagram post links scraper - 100% ACCURATE"""

    def __init__(self, username: str, session_file: str = None):
        """
        Args:
            username: Instagram username (without @)
            session_file: Session file name (default: instagram_session.json)
        """
        # Import here to avoid circular dependency
        from .config import ScraperConfig
        self.config = ScraperConfig()

        self.username = username.strip().lstrip('@')
        self.profile_url = self.config.profile_url_pattern.format(username=self.username)
        
        # Use intelligent session discovery if session_file not provided
        if session_file:
             self.session_file = session_file
        else:
             from .session_utils import find_session_file, get_default_session_path
             self.session_file = find_session_file() or get_default_session_path()

        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.browser: Optional[Browser] = None

    def check_session(self):
        """Check session file"""
        if not os.path.exists(self.session_file):
            raise FileNotFoundError(
                f'❌ {self.session_file} not found!\n'
                f'Please run "python save_session.py" first.'
            )

    def load_session(self, p):
        """Open browser with session"""
        print('📂 Loading session...')

        with open(self.session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Open browser
        self.browser = p.chromium.launch(
            headless=self.config.headless,
            args=self.config.browser_args
        )

        # Create context with session
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
            user_agent=self.config.user_agent
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config.link_scraper_timeout)

        print('✅ Session loaded!')

    def goto_profile(self):
        """Go to profile page"""
        print(f'🔍 Opening profile: {self.username}')

        self.page.goto(self.profile_url, wait_until=self.config.page_load_wait_until, timeout=self.config.link_scraper_timeout)

        print('⏳ Waiting for page load...')
        time.sleep(self.config.page_load_delay)

        # Check profile existence
        page_content = self.page.content()
        if any(text in page_content for text in self.config.profile_not_found_strings):
            raise ValueError(f'❌ Profile not found: {self.username}')

        print('✅ Profile opened!')

    def get_posts_count(self):
        """Get posts count"""
        try:
            self.page.wait_for_selector(self.config.selector_posts_count, timeout=self.config.posts_count_timeout)
            posts_element = self.page.locator(self.config.selector_posts_count).first
            if posts_element:
                posts_text = posts_element.locator(self.config.selector_html_span).first.inner_text()
                # Remove commas and convert to int
                posts_count = int(posts_text.strip().replace(',', ''))
                return posts_count
        except Exception as e:
            print(f'⚠️  Error getting posts count: {e}')
            return 0

    def extract_post_links(self):
        """Find all post and reel links (without scrolling)"""
        try:
            # Find post and reel links
            # /p/ or /reel/ pattern
            links = self.page.locator(self.config.selector_post_reel_links).all()

            # Get Hrefs
            hrefs = set()
            for link in links:
                href = link.get_attribute('href')
                if href:
                    # Create full URL
                    if href.startswith('/'):
                        href = self.config.instagram_base_url.rstrip('/') + href
                    hrefs.add(href)

            return hrefs
        except Exception as e:
            print(f'⚠️  Error getting links: {e}')
            return set()

    def scroll_and_collect_links(self, target_posts_count):
        """Scroll and collect all post links - USER'S PROVEN METHOD"""
        print(f'\n📜 Started collecting {target_posts_count} post links via scrolling...\n')

        all_links = set()
        scroll_attempts = 0
        no_new_links_count = 0
        max_no_new_attempts = self.config.scroll_max_no_new_attempts

        max_no_new_attempts = self.config.scroll_max_no_new_attempts
        
        try:  # [NEW] Graceful Exit Wrapper
            while True:
                # Get current links
                current_links = self.extract_post_links()
                previous_count = len(all_links)
                all_links.update(current_links)
                new_count = len(all_links)

                # Show progress
                print(f'📊 Collected links: {new_count}/{target_posts_count}', end='\r')

                # Increment counter if no new links found
                if new_count == previous_count:
                    no_new_links_count += 1
                else:
                    no_new_links_count = 0  # Reset if new links found

                # Stopping conditions
                if new_count >= target_posts_count:
                    print(f'\n✅ All posts collected: {new_count} links')
                    break

                if no_new_links_count >= max_no_new_attempts:
                    print(f'\n⚠️  No new links loading. Collected: {new_count}')
                    break

                # Scroll (human-like) - USER'S PROVEN METHOD
                self.page.evaluate(f'window.scrollBy(0, window.innerHeight * {self.config.scroll_viewport_percentage})')

                # Wait 1.5-2.5 seconds (random) - ANTI-DETECTION
                wait_time = random.uniform(self.config.scroll_wait_range[0], self.config.scroll_wait_range[1])
                time.sleep(wait_time)

                scroll_attempts += 1

                # Stop if too many scrolls (for safety)
                if scroll_attempts > 1000:
                    print(f'\n⚠️  Max scroll limit reached. Collected: {new_count}')
                    break
        except KeyboardInterrupt:  # [NEW]
             print('\n⚠️  Scraping interrupted (Ctrl+C). Saving partial results based on logic...')
             # For standalone script, we might NOT want to raise if we want to save file right after?
             # The caller 'scrape' has logic to save to file.
             pass


        return list(all_links)

    def save_links_to_file(self, links, filename='post_links.txt'):
        """Save links to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            for link in sorted(links):
                f.write(link + '\n')
        print(f'\n💾 Links saved: {filename}')

    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()

    def scrape(self):
        """Main scraping function"""
        self.check_session()

        with sync_playwright() as p:
            try:
                self.load_session(p)
                self.goto_profile()

                # Get posts count
                posts_count = self.get_posts_count()
                print(f'📸 Total posts: {posts_count}\n')

                if posts_count == 0:
                    print('❌ Posts not found or error getting them!')
                    return []

                # Scroll and collect links
                links = self.scroll_and_collect_links(posts_count)

                # Save to file
                if links:
                    self.save_links_to_file(links)

                return links

            finally:
                time.sleep(2)  # For viewing
                self.close()


# Library-compatible wrapper (only if library components available)
if LIBRARY_AVAILABLE:
    class PostLinksScraper(BaseScraper):
        """
        Library-compatible POST links scraper - USES USER'S PROVEN 100% ACCURATE METHOD

        This wrapper integrates the proven standalone method into the library.
        Features:
        - Collects ONLY posts (a[href*="/p/"]) and reels (a[href*="/reel/"])
        - Uses user's proven human-like scrolling method
        - Real-time progress tracking
        - Smart stopping (3 attempts with no new links)
        - Library-compatible interface
        """

        def __init__(self, config: Optional['ScraperConfig'] = None):
            """Initialize post links scraper"""
            super().__init__(config)
            self.logger.info("PostLinksScraper ready (using user's proven 100% accurate method)")

        def scrape(
            self,
            username: str,
            target_count: Optional[int] = None,
            save_to_file: bool = True,
            output_file: Optional[str] = None
        ) -> List[Dict[str, str]]:
            """
            Scrape all POST and REEL links from profile using USER'S PROVEN METHOD

            Args:
                username: Instagram username
                target_count: Target number of links (None = scrape all)
                target_count: Target number of links (None = scrape all)
                save_to_file: Save links to file
                output_file: Optional path to save file (overrides default)

            Returns:
                List of dictionaries with 'url' and 'type' keys
            """
            username = username.strip().lstrip('@')
            self.logger.info(f"Starting post links scrape for: @{username}")

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

                # Scroll and collect links using USER'S PROVEN METHOD
                links = self._scroll_and_collect_proven(target_count)

                # Save to file
                if save_to_file:
                    self._save_links(links, output_file)

                self.logger.info(f"Collected {len(links)} post links")
                return links

            finally:
                # Only close browser if not in SharedBrowser mode
                if not is_shared_browser:
                    self.close()
                else:
                    self.logger.debug("Keeping browser open (SharedBrowser mode)")

        def _profile_exists(self) -> bool:
            """Check if profile exists"""
            try:
                content = self.page.content()
                return not any(text in content for text in self.config.profile_not_found_strings)
            except Exception:
                return False

        def _get_posts_count(self) -> int:
            """Get total posts count from profile"""
            try:
                self.page.wait_for_selector(self.config.selector_posts_count, timeout=self.config.posts_count_timeout)
                posts_element = self.page.locator(self.config.selector_posts_count).first
                posts_text = posts_element.locator(self.config.selector_html_span).first.inner_text()
                count = int(posts_text.strip().replace(',', ''))
                return count
            except Exception as e:
                self.logger.warning(f"Could not get posts count: {e}")
                return 9999  # Large number as fallback

        def _extract_current_links_proven(self) -> List[Dict[str, str]]:
            """
            Extract links AND metadata using USER'S PROVEN DIRECT SELECTOR METHOD

            Returns:
                List of dicts with 'url', 'thumbnail', 'stats'
            """
            try:
                # USER'S PROVEN METHOD: Direct selector for posts and reels
                elements = self.page.locator(self.config.selector_post_reel_links).all()
                
                results = []
                for element in elements:
                    try:
                        href = element.get_attribute('href')
                        if not href:
                            continue
                            
                        # Make full URL
                        if href.startswith('/'):
                            full_url = self.config.instagram_base_url.rstrip('/') + href
                        else:
                            full_url = href
                            
                        # Extract Metadata
                        thumbnail = ""
                        stats = ""
                        
                        # Try Image (PostPage)
                        img = element.locator(self.config.selector_grid_thumbnail_img).first
                        if img.count() > 0:
                            thumbnail = img.get_attribute('src') or ""
                            
                        # Try Background Image (ReelsPage)
                        if not thumbnail:
                            bg_div = element.locator(self.config.selector_grid_thumbnail_bg).first
                            if bg_div.count() > 0:
                                style = bg_div.get_attribute('style') or ""
                                # Extract url('...')
                                if 'url("' in style:
                                    thumbnail = style.split('url("')[1].split('")')[0]
                                elif "url('" in style:
                                    thumbnail = style.split("url('")[1].split("')")[0]

                        # Check if it's a pinned post using robust HTML matching
                        is_pinned = False
                        try:
                            html_content = element.inner_html()
                            if 'Pinned post icon' in html_content or 'm22.707 7.583' in html_content or 'aria-label="Pinned post icon"' in html_content:
                                is_pinned = True
                        except Exception as e:
                            self.logger.debug(f"Error checking pinned status for {full_url}: {e}")
                        
                        # If skip_pinned_posts is True, ignore it
                        if self.config.skip_pinned_posts and is_pinned:
                            self.logger.debug(f"Skipping pinned post: {full_url}")
                            continue

                        # Try Stats (Views/Likes)
                        stat_span = element.locator(self.config.selector_grid_time).first
                        if stat_span.count() > 0:
                            stats = stat_span.inner_text()
                            
                        results.append({
                            'url': full_url,
                            'thumbnail': thumbnail,
                            'stats': stats,
                            'is_pinned': is_pinned
                        })
                    except Exception:
                        continue

                return results

            except Exception as e:
                self.logger.error(f"Error extracting links: {e}")
                return []

        def _scroll_and_collect_proven(self, target_count: int) -> List[Dict[str, str]]:
            """
            Scroll and collect links using USER'S PROVEN 100% ACCURATE METHOD

            Args:
                target_count: Target number of links

            Returns:
                List of dictionaries with 'url', 'type', 'thumbnail', 'stats' keys
            """
            self.logger.info(f"Starting scroll collection (target: {target_count})...")

            all_links = {}  # Dict[url, dict]
            scroll_attempts = 0
            no_new_links_count = 0
            MAX_NO_NEW = self.config.scroll_max_no_new_attempts

            MAX_NO_NEW = self.config.scroll_max_no_new_attempts

            try:  # [NEW] Graceful Exit Wrapper
                while True:
                    # Extract current links using proven method
                    current_items = self._extract_current_links_proven()
                    previous_count = len(all_links)
                    
                    for item in current_items:
                        url = item['url']
                        if url not in all_links:
                            all_links[url] = item
                    
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

                    if scroll_attempts >= self.config.max_scroll_attempts:
                        self.logger.warning(f"Max scroll attempts ({self.config.max_scroll_attempts}) reached")
                        break

                    # USER'S PROVEN METHOD: Human-like scroll
                    self._human_like_scroll_proven()
                    scroll_attempts += 1
            except KeyboardInterrupt:
                 self.logger.warning("\n✋ Scraping interrupted by user! Saving collected data...")
                 self.interrupted = True


            # Convert to list of dicts with type detection
            result = []
            for url, data in all_links.items():
                if '/p/' in url:
                    content_type = 'Post'
                elif '/reel/' in url:
                    content_type = 'Reel'
                else:
                    content_type = 'Unknown'
                
                result.append({
                    'url': url, 
                    'type': content_type,
                    'thumbnail': data.get('thumbnail', ''),
                    'stats': data.get('stats', ''),
                    'is_pinned': data.get('is_pinned', False)
                })

            return result

        def _human_like_scroll_proven(self) -> None:
            """
            USER'S PROVEN 100% ACCURATE SCROLLING METHOD

            Scrolls 80% of viewport height and waits random 1.5-2.5 seconds
            """
            try:
                # USER'S PROVEN: Scroll 80% of viewport (human-like)
                self.page.evaluate(f'window.scrollBy(0, window.innerHeight * {self.config.scroll_viewport_percentage})')

                # USER'S PROVEN: Random wait 1.5-2.5 seconds (anti-detection)
                wait_time = random.uniform(self.config.scroll_wait_range[0], self.config.scroll_wait_range[1])
                time.sleep(wait_time)

                self.logger.debug(f"Scrolled (waited {wait_time:.2f}s)")

            except Exception as e:
                self.logger.debug(f"Scroll error: {e}")
                # Fallback: scroll to bottom
                self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                time.sleep(self.config.scroll_post_delay)

        def _save_links(self, links: List[Dict[str, str]], output_file: Optional[str] = None) -> None:
            """
            Save links to file

            Args:
                links: List of link dictionaries with 'url' and 'type' keys
                output_file: Optional custom path
            """
            if output_file:
                path = Path(output_file)
            else:
                path = Path(self.config.base_output_dir) / self.config.links_file
            
            # Ensure directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            try:
                with open(path, 'w', encoding='utf-8') as f:
                    for link_data in links:
                        url = link_data['url']
                        content_type = link_data['type']
                        f.write(f"{url}\t{content_type}\n")

                self.logger.info(f"Links saved to: {path}")

            except Exception as e:
                self.logger.error(f"Failed to save links: {e}")
                raise


def main():
    """Main function - for CLI"""
    print('🚀 Instagram Post Links Scraper\n')

    # Ask for username
    username = input('Enter Instagram username (without @): ').strip().lstrip('@')

    if not username:
        print('❌ Username not provided!')
        return

    # Start scraping
    scraper = InstagramPostLinksScraper(username)

    try:
        links = scraper.scrape()

        print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'✅ Scraping finished!')
        print(f'📊 Collected links: {len(links)}')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        # Show first 5 links
        if links:
            print('\n🔗 Example links (first 5):')
            for i, link in enumerate(sorted(links)[:5], 1):
                print(f'  {i}. {link}')

    except Exception as e:
        print(f'\n❌ Error: {e}')
        raise


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n⚠️  Program stopped!')
    except Exception:
        pass
