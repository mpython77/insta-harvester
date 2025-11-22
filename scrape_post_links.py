"""
Instagram Post Links Scraper
Collects all post links from a profile (with scrolling)
"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SESSION_FILE = 'instagram_session.json'


class InstagramPostLinksScraper:
    """Scrape Instagram post links"""

    def __init__(self, username: str):
        """
        Args:
            username: Instagram username (without @ symbol)
        """
        self.username = username
        self.profile_url = f'https://www.instagram.com/{username}/'
        self.page = None
        self.context = None
        self.browser = None

    def check_session(self):
        """Check session file"""
        if not os.path.exists(SESSION_FILE):
            raise FileNotFoundError(
                f'❌ {SESSION_FILE} not found!\n'
                f'Please run "python save_session.py" first.'
            )

    def load_session(self, p):
        """Launch browser with session"""
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

    def goto_profile(self):
        """Navigate to profile page"""
        print(f'🔍 Opening profile: {self.username}')

        self.page.goto(self.profile_url, wait_until='domcontentloaded', timeout=60000)

        print('⏳ Waiting for page to load...')
        time.sleep(3)

        # Check if profile exists
        if 'Page Not Found' in self.page.content() or 'Sorry, this page' in self.page.content():
            raise ValueError(f'❌ Profile not found: {self.username}')

        print('✅ Profile opened!')

    def get_posts_count(self):
        """Get number of posts"""
        try:
            self.page.wait_for_selector('span:has-text("posts")', timeout=10000)
            posts_element = self.page.locator('span:has-text("posts")').first
            if posts_element:
                posts_text = posts_element.locator('span.html-span').first.inner_text()
                # Remove commas and convert to int
                posts_count = int(posts_text.strip().replace(',', ''))
                return posts_count
        except Exception as e:
            print(f'⚠️  Error getting posts count: {e}')
            return 0

    def extract_post_links(self):
        """Find all post links (without scrolling)"""
        try:
            # Find post and reel links
            # /username/p/ or /username/reel/ pattern
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"]').all()

            # Get hrefs
            hrefs = set()
            for link in links:
                href = link.get_attribute('href')
                if href:
                    # Create full URL
                    if href.startswith('/'):
                        href = f'https://www.instagram.com{href}'
                    hrefs.add(href)

            return hrefs
        except Exception as e:
            print(f'⚠️  Error getting links: {e}')
            return set()

    def scroll_and_collect_links(self, target_posts_count):
        """Scroll and collect all post links"""
        print(f'\n📜 Starting to scroll and collect {target_posts_count} post links...\n')

        all_links = set()
        scroll_attempts = 0
        no_new_links_count = 0
        max_no_new_attempts = 3  # Stop if no new links after 3 attempts

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

            # Stop conditions
            if new_count >= target_posts_count:
                print(f'\n✅ All posts collected: {new_count} links')
                break

            if no_new_links_count >= max_no_new_attempts:
                print(f'\n⚠️  No new links loading. Collected: {new_count} links')
                break

            # Scroll (human-like)
            self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')

            # Wait 1.5-2.5 seconds (random)
            import random
            wait_time = random.uniform(1.5, 2.5)
            time.sleep(wait_time)

            scroll_attempts += 1

            # Stop if too many scrolls (safety limit)
            if scroll_attempts > 1000:
                print(f'\n⚠️  Maximum scroll limit reached. Collected: {new_count} links')
                break

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
                    print('❌ No posts found or error getting count!')
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


def main():
    """Main function"""
    print('🚀 Instagram Post Links Scraper\n')

    # Ask for username
    username = input('Enter Instagram username (without @ symbol): ').strip().lstrip('@')

    if not username:
        print('❌ Username not provided!')
        return

    # Start scraping
    scraper = InstagramPostLinksScraper(username)

    try:
        links = scraper.scrape()

        print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'✅ Scraping complete!')
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
        print('\n\n⚠️  Program interrupted!')
    except Exception:
        pass
