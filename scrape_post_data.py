"""
Instagram Post Data Scraper
Reads links from post_links.txt and extracts from each:
- Tagged accounts
- Likes count
- Post timestamp
"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SESSION_FILE = 'instagram_session.json'
LINKS_FILE = 'post_links.txt'


class InstagramPostDataScraper:
    """Instagram post data scraping"""

    def __init__(self):
        self.page = None
        self.context = None
        self.browser = None

    def check_session(self):
        """Check if session file exists"""
        if not os.path.exists(SESSION_FILE):
            raise FileNotFoundError(
                f'❌ {SESSION_FILE} not found!\n'
                f'Run "python save_session.py" first.'
            )

    def check_links_file(self):
        """Check if links file exists"""
        if not os.path.exists(LINKS_FILE):
            raise FileNotFoundError(
                f'❌ {LINKS_FILE} not found!\n'
                f'Run "python scrape_post_links.py" first.'
            )

    def load_links(self):
        """Load links from file"""
        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        return links

    def load_session(self, p):
        """Open browser with session"""
        print('📂 Loading session...')

        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Launch browser
        self.browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )

        # Create context with session
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)

        print('✅ Session loaded!')

    def goto_post(self, url):
        """Navigate to post page"""
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(3)  # Wait for page to load

            # Wait for likes element
            try:
                self.page.wait_for_selector('span:has-text("likes")', timeout=5000)
            except Exception:
                pass  # Continue if no likes

            return True
        except Exception as e:
            print(f'⚠️  Error opening post: {e}')
            return False

    def _get_tagged_accounts(self):
        """Get tagged accounts"""
        try:
            # All a[href] links inside ._aa1y class
            tag_containers = self.page.locator('._aa1y').all()

            tagged = []
            for container in tag_containers:
                try:
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href')
                    if href:
                        # Extract username (remove slashes)
                        username = href.strip('/').split('/')[-1]
                        tagged.append(username)
                except Exception:
                    continue

            return tagged if tagged else ['No tags']
        except Exception as e:
            return ['No tags']

    def _get_likes_count(self):
        """Get likes count"""
        # Method 1: span[role="button"] inside section (new Instagram structure)
        try:
            # Find span after like SVG icon inside section
            section = self.page.locator('section').first
            # Find SVG with aria-label="Like"
            like_svg = section.locator('svg[aria-label="Like"]').first
            # Find span[role="button"] after SVG
            # First one among these spans - likes count
            spans = section.locator('span[role="button"]').all()

            for span in spans[:2]:  # First 2 spans (likes and comments)
                try:
                    text = span.inner_text(timeout=2000).strip()
                    # Check if it's a number
                    if text and text.replace(',', '').replace('.', '').replace('K', '').replace('M', '').isdigit():
                        return text.replace(',', '')
                    # If with K or M (44K, 2.5M)
                    if text and ('K' in text or 'M' in text):
                        return text
                except Exception:
                    continue
        except Exception:
            pass

        # Method 2: Direct span selector
        try:
            # Span next to like icon
            section = self.page.locator('section').first
            # x1ypdohk x1s688f class combination
            likes_span = section.locator('span.x1ypdohk.x1s688f').first
            likes_text = likes_span.inner_text(timeout=2000).strip()
            if likes_text and likes_text.replace(',', '').isdigit():
                return likes_text.replace(',', '')
        except Exception:
            pass

        # Method 3: Via link (old structure)
        try:
            likes_link = self.page.locator('a[href*="/liked_by/"]').first
            likes_text = likes_link.locator('span.html-span').first.inner_text(timeout=2000)
            if likes_text.replace(',', '').isdigit():
                return likes_text.strip().replace(',', '')
        except Exception:
            pass

        # Method 4: With "likes" text (fallback)
        try:
            likes_count = self.page.locator('span:has-text("likes")').count()
            for i in range(likes_count):
                try:
                    span = self.page.locator('span:has-text("likes")').nth(i)
                    number = span.locator('span.html-span').first
                    text = number.inner_text(timeout=2000)
                    if text.replace(',', '').isdigit():
                        return text.strip().replace(',', '')
                except Exception:
                    continue
        except Exception:
            pass

        return 'N/A'

    def _get_post_time(self):
        """Get post timestamp"""
        try:
            # time element
            time_element = self.page.locator('time').first
            if time_element:
                # datetime attribute
                datetime_str = time_element.get_attribute('datetime')
                # title attribute (human-readable format)
                title_str = time_element.get_attribute('title')

                if title_str:
                    return title_str
                elif datetime_str:
                    return datetime_str
        except Exception:
            pass

        return 'N/A'

    def scrape_post(self, url):
        """Scrape a single post"""
        # Navigate to post
        if not self.goto_post(url):
            return None

        # Extract data
        tagged = self._get_tagged_accounts()
        likes = self._get_likes_count()
        post_time = self._get_post_time()

        return {
            'url': url,
            'tagged_accounts': tagged,
            'likes': likes,
            'post_time': post_time
        }

    def print_post_data(self, data):
        """Print post data in formatted style"""
        if not data:
            return

        print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'🔗 URL: {data["url"]}')
        print(f'👥 Tagged: {", ".join(data["tagged_accounts"])}')
        print(f'❤️  Likes: {data["likes"]}')
        print(f'🕐 Time: {data["post_time"]}')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

    def close(self):
        """Close browser"""
        if self.browser:
            self.browser.close()

    def scrape_all(self):
        """Scrape all posts"""
        self.check_session()
        self.check_links_file()

        # Load links
        links = self.load_links()
        print(f'📊 Total links: {len(links)}\n')

        if not links:
            print('❌ No links found!')
            return

        with sync_playwright() as p:
            try:
                self.load_session(p)

                print('🚀 Scraping started...\n')

                # Scrape each link
                for i, link in enumerate(links, 1):
                    print(f'[{i}/{len(links)}] 🔍 Scraping: {link}')

                    data = self.scrape_post(link)
                    if data:
                        self.print_post_data(data)

                    # Wait before next post (Instagram rate limiting)
                    if i < len(links):
                        import random
                        wait_time = random.uniform(2, 4)
                        print(f'⏳ Waiting {wait_time:.1f}s...')
                        time.sleep(wait_time)

                print('\n✅ All posts scraped successfully!')

            finally:
                time.sleep(2)
                self.close()


def main():
    """Main function"""
    print('🚀 Instagram Post Data Scraper\n')

    scraper = InstagramPostDataScraper()

    try:
        scraper.scrape_all()
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
