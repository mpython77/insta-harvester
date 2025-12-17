"""
Instagram Post Links Scraper - USER'S PROVEN 100% ACCURATE METHOD
Collects post and reel links with human-like scrolling
"""

import json
import os
import time
import random
from typing import List, Set, Optional, Dict
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page

# Import library components for PostLinksScraper
try:
    from .base import BaseScraper
    from .config import ScraperConfig
    from .exceptions import ProfileNotFoundError
    LIBRARY_AVAILABLE = True
except ImportError:
    LIBRARY_AVAILABLE = False


class InstagramPostLinksScraper:
    """Instagram postlar linklarini scraping qilish - 100% ACCURATE"""

    def __init__(self, username: str, session_file: str = None):
        """
        Args:
            username: Instagram username (@ belgisisiz)
            session_file: Session fayl nomi (default: instagram_session.json)
        """
        # Import here to avoid circular dependency
        from .config import ScraperConfig
        self.config = ScraperConfig()

        self.username = username.strip().lstrip('@')
        self.profile_url = self.config.profile_url_pattern.format(username=self.username)
        self.session_file = session_file or self.config.session_file
        self.page: Optional[Page] = None
        self.context: Optional[BrowserContext] = None
        self.browser: Optional[Browser] = None

    def check_session(self):
        """Session faylni tekshirish"""
        if not os.path.exists(self.session_file):
            raise FileNotFoundError(
                f'❌ {self.session_file} topilmadi!\n'
                f'Avval "python save_session.py" ni ishga tushiring.'
            )

    def load_session(self, p):
        """Session bilan browser ochish"""
        print('📂 Session yuklanmoqda...')

        with open(self.session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Browser ochish
        self.browser = p.chromium.launch(
            headless=self.config.headless,
            args=self.config.browser_args
        )

        # Session bilan context yaratish
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={'width': self.config.viewport_width, 'height': self.config.viewport_height},
            user_agent=self.config.user_agent
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(self.config.link_scraper_timeout)

        print('✅ Session yuklandi!')

    def goto_profile(self):
        """Profile sahifasiga o'tish"""
        print(f'🔍 Profile ochilmoqda: {self.username}')

        self.page.goto(self.profile_url, wait_until=self.config.page_load_wait_until, timeout=self.config.link_scraper_timeout)

        print('⏳ Sahifa yuklanishi kutilmoqda...')
        time.sleep(self.config.page_load_delay)

        # Profile mavjudligini tekshirish
        page_content = self.page.content()
        if any(text in page_content for text in self.config.profile_not_found_strings):
            raise ValueError(f'❌ Profile topilmadi: {self.username}')

        print('✅ Profile ochildi!')

    def get_posts_count(self):
        """Posts sonini olish"""
        try:
            self.page.wait_for_selector(self.config.selector_posts_count, timeout=self.config.posts_count_timeout)
            posts_element = self.page.locator(self.config.selector_posts_count).first
            if posts_element:
                posts_text = posts_element.locator(self.config.selector_html_span).first.inner_text()
                # Virgullarni olib tashlash va int ga o'girish
                posts_count = int(posts_text.strip().replace(',', ''))
                return posts_count
        except Exception as e:
            print(f'⚠️  Posts sonini olishda xatolik: {e}')
            return 0

    def extract_post_links(self):
        """Barcha post va reel linklarini topish (scroll qilmasdan)"""
        try:
            # Post va reel linklarini topish
            # /p/ yoki /reel/ pattern
            links = self.page.locator(self.config.selector_post_reel_links).all()

            # Href larni olish
            hrefs = set()
            for link in links:
                href = link.get_attribute('href')
                if href:
                    # To'liq URL yaratish
                    if href.startswith('/'):
                        href = self.config.instagram_base_url.rstrip('/') + href
                    hrefs.add(href)

            return hrefs
        except Exception as e:
            print(f'⚠️  Linklar olishda xatolik: {e}')
            return set()

    def scroll_and_collect_links(self, target_posts_count):
        """Scroll qilib barcha post linklarini yig'ish - USER'S PROVEN METHOD"""
        print(f'\n📜 Scroll qilib {target_posts_count} ta post linkini yig\'ish boshlandi...\n')

        all_links = set()
        scroll_attempts = 0
        no_new_links_count = 0
        max_no_new_attempts = self.config.scroll_max_no_new_attempts

        while True:
            # Hozirgi linklarni olish
            current_links = self.extract_post_links()
            previous_count = len(all_links)
            all_links.update(current_links)
            new_count = len(all_links)

            # Progress ko'rsatish
            print(f'📊 To\'plangan linklar: {new_count}/{target_posts_count}', end='\r')

            # Yangi link topilmasa counter oshirish
            if new_count == previous_count:
                no_new_links_count += 1
            else:
                no_new_links_count = 0  # Yangi link topilsa reset qilish

            # To'xtatish shartlari
            if new_count >= target_posts_count:
                print(f'\n✅ Barcha postlar to\'plandi: {new_count} ta link')
                break

            if no_new_links_count >= max_no_new_attempts:
                print(f'\n⚠️  Yangi linklar yuklanmayapti. To\'plangan: {new_count} ta')
                break

            # Scroll qilish (odamga o'xshab) - USER'S PROVEN METHOD
            self.page.evaluate(f'window.scrollBy(0, window.innerHeight * {self.config.scroll_viewport_percentage})')

            # 1.5-2.5 sekund kutish (random) - ANTI-DETECTION
            wait_time = random.uniform(self.config.scroll_wait_range[0], self.config.scroll_wait_range[1])
            time.sleep(wait_time)

            scroll_attempts += 1

            # Juda ko'p scroll qilinsa to'xtatish (xavfsizlik uchun)
            if scroll_attempts > 1000:
                print(f'\n⚠️  Maksimal scroll limitiga yetildi. To\'plangan: {new_count} ta')
                break

        return list(all_links)

    def save_links_to_file(self, links, filename='post_links.txt'):
        """Linklarni faylga saqlash"""
        with open(filename, 'w', encoding='utf-8') as f:
            for link in sorted(links):
                f.write(link + '\n')
        print(f'\n💾 Linklar saqlandi: {filename}')

    def close(self):
        """Browser yopish"""
        if self.browser:
            self.browser.close()

    def scrape(self):
        """Asosiy scraping funksiyasi"""
        self.check_session()

        with sync_playwright() as p:
            try:
                self.load_session(p)
                self.goto_profile()

                # Posts sonini olish
                posts_count = self.get_posts_count()
                print(f'📸 Jami postlar: {posts_count}\n')

                if posts_count == 0:
                    print('❌ Posts topilmadi yoki olishda xatolik!')
                    return []

                # Scroll qilib linklar yig'ish
                links = self.scroll_and_collect_links(posts_count)

                # Faylga saqlash
                if links:
                    self.save_links_to_file(links)

                return links

            finally:
                time.sleep(2)  # Ko'rish uchun
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
            save_to_file: bool = True
        ) -> List[Dict[str, str]]:
            """
            Scrape all POST and REEL links from profile using USER'S PROVEN METHOD

            Args:
                username: Instagram username
                target_count: Target number of links (None = scrape all)
                save_to_file: Save links to file

            Returns:
                List of dictionaries with 'url' and 'type' keys
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

                # Scroll and collect links using USER'S PROVEN METHOD
                links = self._scroll_and_collect_proven(target_count)

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

        def _extract_current_links_proven(self) -> Set[str]:
            """
            Extract links using USER'S PROVEN DIRECT SELECTOR METHOD

            Returns:
                Set of URLs
            """
            try:
                # USER'S PROVEN METHOD: Direct selector for posts and reels
                links = self.page.locator(self.config.selector_post_reel_links).all()

                hrefs = set()
                for link in links:
                    href = link.get_attribute('href')
                    if href:
                        # Make full URL
                        if href.startswith('/'):
                            href = self.config.instagram_base_url.rstrip('/') + href
                        hrefs.add(href)

                return hrefs

            except Exception as e:
                self.logger.error(f"Error extracting links: {e}")
                return set()

        def _scroll_and_collect_proven(self, target_count: int) -> List[Dict[str, str]]:
            """
            Scroll and collect links using USER'S PROVEN 100% ACCURATE METHOD

            Args:
                target_count: Target number of links

            Returns:
                List of dictionaries with 'url' and 'type' keys
            """
            self.logger.info(f"Starting scroll collection (target: {target_count})...")

            all_links = set()
            scroll_attempts = 0
            no_new_links_count = 0
            MAX_NO_NEW = self.config.scroll_max_no_new_attempts

            while True:
                # Extract current links using proven method
                current_links = self._extract_current_links_proven()
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

            # Convert to list of dicts with type detection
            result = []
            for url in sorted(all_links):
                if '/p/' in url:
                    content_type = 'Post'
                elif '/reel/' in url:
                    content_type = 'Reel'
                else:
                    content_type = 'Unknown'
                result.append({'url': url, 'type': content_type})

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


def main():
    """Main funksiya - CLI uchun"""
    print('🚀 Instagram Post Links Scraper\n')

    # Username ni so'rash
    username = input('Instagram username kiriting (@ belgisisiz): ').strip().lstrip('@')

    if not username:
        print('❌ Username kiritilmadi!')
        return

    # Scraping boshlash
    scraper = InstagramPostLinksScraper(username)

    try:
        links = scraper.scrape()

        print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'✅ Scraping tugadi!')
        print(f'📊 To\'plangan linklar: {len(links)} ta')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        # Birinchi 5 ta linkni ko'rsatish
        if links:
            print('\n🔗 Misol linklar (birinchi 5 ta):')
            for i, link in enumerate(sorted(links)[:5], 1):
                print(f'  {i}. {link}')

    except Exception as e:
        print(f'\n❌ Xatolik: {e}')
        raise


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n⚠️  Dastur to\'xtatildi!')
    except Exception:
        pass
