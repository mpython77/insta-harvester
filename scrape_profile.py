"""
Instagram Profile Scraper
Logs into Instagram via session and retrieves profile information:
- Number of posts
- Number of followers
- Number of following
"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SESSION_FILE = 'instagram_session.json'


class InstagramScraper:
    """Scrape Instagram profile information"""

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
            headless=False,  # False for viewing, True for faster operation
            args=['--start-maximized']
        )

        # Create context with session
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = self.context.new_page()

        # Increase timeout
        self.page.set_default_timeout(60000)  # 60 seconds

        print('✅ Session loaded!')

    def goto_profile(self):
        """Navigate to profile page"""
        print(f'🔍 Opening profile: {self.username}')

        # Use domcontentloaded instead of networkidle (faster)
        self.page.goto(self.profile_url, wait_until='domcontentloaded', timeout=60000)

        print('⏳ Waiting for page to load...')
        # Wait a bit for page elements to load
        time.sleep(3)

        # Check if profile exists
        if 'Page Not Found' in self.page.content() or 'Sorry, this page' in self.page.content():
            raise ValueError(f'❌ Profile not found: {self.username}')

        print('✅ Profile opened!')

    def extract_profile_data(self):
        """Extract profile information"""
        print('📊 Retrieving data...\n')

        # Wait for profile stats
        try:
            self.page.wait_for_selector('span:has-text("posts")', timeout=10000)
        except Exception:
            print('⚠️  Profile data not loaded, retrying...')
            time.sleep(2)

        # Get posts count
        posts = self._get_posts_count()

        # Get followers count
        followers = self._get_followers_count()

        # Get following count
        following = self._get_following_count()

        return {
            'username': self.username,
            'posts': posts,
            'followers': followers,
            'following': following
        }

    def _get_posts_count(self):
        """Get posts count"""
        try:
            # Find "posts" text and get the number inside
            posts_element = self.page.locator('span:has-text("posts")').first
            if posts_element:
                # Find span.html-span inside element
                posts_text = posts_element.locator('span.html-span').first.inner_text()
                return posts_text.strip().replace(',', '')
        except Exception as e:
            print(f'⚠️  Error getting posts: {e}')
            return 'N/A'

    def _get_followers_count(self):
        """Get followers count"""
        try:
            # Find followers link
            followers_link = self.page.locator('a[href*="/followers/"]').first
            if followers_link:
                # Get exact count from title attribute
                title = followers_link.locator('span[title]').first
                if title:
                    return title.get_attribute('title').replace(',', '')
                else:
                    # or get visible text
                    return followers_link.locator('span.html-span').first.inner_text()
        except Exception as e:
            print(f'⚠️  Error getting followers: {e}')
            return 'N/A'

    def _get_following_count(self):
        """Get following count"""
        try:
            # Find following link
            following_link = self.page.locator('a[href*="/following/"]').first
            if following_link:
                # Get text from span.html-span
                return following_link.locator('span.html-span').first.inner_text().replace(',', '')
        except Exception as e:
            print(f'⚠️  Error getting following: {e}')
            return 'N/A'

    def print_profile_data(self, data):
        """Print data in a nice format"""
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'👤 Username:  @{data["username"]}')
        print(f'📸 Posts:     {data["posts"]}')
        print(f'👥 Followers: {data["followers"]}')
        print(f'➕ Following: {data["following"]}')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

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
                data = self.extract_profile_data()
                self.print_profile_data(data)
                return data
            finally:
                self.close()


def main():
    """Main function"""
    print('🚀 Instagram Profile Scraper\n')

    # Ask for username
    username = input('Enter Instagram username (without @ symbol): ').strip().lstrip('@')

    if not username:
        print('❌ Username not provided!')
        return

    # Start scraping
    scraper = InstagramScraper(username)

    try:
        scraper.scrape()
        print('\n✅ Scraping complete!')
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
