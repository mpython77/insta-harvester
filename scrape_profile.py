"""
Instagram Profile Scraper
Session orqali Instagram ga kirib, profile ma'lumotlarini oladi:
- Posts soni
- Followers soni
- Following soni
"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SESSION_FILE = 'instagram_session.json'


class InstagramScraper:
    """Instagram profil ma'lumotlarini scraping qilish"""

    def __init__(self, username: str):
        """
        Args:
            username: Instagram username (@ belgisisiz)
        """
        self.username = username
        self.profile_url = f'https://www.instagram.com/{username}/'
        self.page = None
        self.context = None
        self.browser = None

    def check_session(self):
        """Session faylni tekshirish"""
        if not os.path.exists(SESSION_FILE):
            raise FileNotFoundError(
                f'❌ {SESSION_FILE} topilmadi!\n'
                f'Avval "python save_session.py" ni ishga tushiring.'
            )

    def load_session(self, p):
        """Session bilan browser ochish"""
        print('📂 Session yuklanmoqda...')

        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Browser ochish
        self.browser = p.chromium.launch(
            headless=False,  # Ko'rish uchun False, tezkor ish uchun True qiling
            args=['--start-maximized']
        )

        # Session bilan context yaratish
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = self.context.new_page()

        # Timeout ni oshirish
        self.page.set_default_timeout(60000)  # 60 sekund

        print('✅ Session yuklandi!')

    def goto_profile(self):
        """Profile sahifasiga o'tish"""
        print(f'🔍 Profile ochilmoqda: {self.username}')

        # networkidle o'rniga domcontentloaded ishlatamiz (tezroq)
        self.page.goto(self.profile_url, wait_until='domcontentloaded', timeout=60000)

        print('⏳ Sahifa yuklanishi kutilmoqda...')
        # Sahifa elementlari yuklanishi uchun biroz kutish
        time.sleep(3)

        # Profile mavjudligini tekshirish
        if 'Page Not Found' in self.page.content() or 'Sorry, this page' in self.page.content():
            raise ValueError(f'❌ Profile topilmadi: {self.username}')

        print('✅ Profile ochildi!')

    def extract_profile_data(self):
        """Profile ma'lumotlarini olish"""
        print('📊 Ma\'lumotlar olinmoqda...\n')

        # Profile statslarini kutish
        try:
            self.page.wait_for_selector('span:has-text("posts")', timeout=10000)
        except Exception:
            print('⚠️  Profile ma\'lumotlari yuklanmadi, qayta urinilmoqda...')
            time.sleep(2)

        # Posts sonini olish
        posts = self._get_posts_count()

        # Followers sonini olish
        followers = self._get_followers_count()

        # Following sonini olish
        following = self._get_following_count()

        return {
            'username': self.username,
            'posts': posts,
            'followers': followers,
            'following': following
        }

    def _get_posts_count(self):
        """Posts sonini olish"""
        try:
            # "posts" so'zini topish va ichidagi raqamni olish
            posts_element = self.page.locator('span:has-text("posts")').first
            if posts_element:
                # Element ichidan span.html-span ni topish
                posts_text = posts_element.locator('span.html-span').first.inner_text()
                return posts_text.strip().replace(',', '')
        except Exception as e:
            print(f'⚠️  Posts olishda xatolik: {e}')
            return 'N/A'

    def _get_followers_count(self):
        """Followers sonini olish"""
        try:
            # followers link ni topish
            followers_link = self.page.locator('a[href*="/followers/"]').first
            if followers_link:
                # title attributidan aniq sonni olish
                title = followers_link.locator('span[title]').first
                if title:
                    return title.get_attribute('title').replace(',', '')
                else:
                    # yoki ko'rinadigan textni olish
                    return followers_link.locator('span.html-span').first.inner_text()
        except Exception as e:
            print(f'⚠️  Followers olishda xatolik: {e}')
            return 'N/A'

    def _get_following_count(self):
        """Following sonini olish"""
        try:
            # following link ni topish
            following_link = self.page.locator('a[href*="/following/"]').first
            if following_link:
                # span.html-span ichidan text olish
                return following_link.locator('span.html-span').first.inner_text().replace(',', '')
        except Exception as e:
            print(f'⚠️  Following olishda xatolik: {e}')
            return 'N/A'

    def print_profile_data(self, data):
        """Ma'lumotlarni chiroyli formatda chiqarish"""
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'👤 Username:  @{data["username"]}')
        print(f'📸 Posts:     {data["posts"]}')
        print(f'👥 Followers: {data["followers"]}')
        print(f'➕ Following: {data["following"]}')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

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
                data = self.extract_profile_data()
                self.print_profile_data(data)
                return data
            finally:
                self.close()


def main():
    """Main funksiya"""
    print('🚀 Instagram Profile Scraper\n')

    # Username ni so'rash
    username = input('Instagram username kiriting (@ belgisisiz): ').strip().lstrip('@')

    if not username:
        print('❌ Username kiritilmadi!')
        return

    # Scraping boshlash
    scraper = InstagramScraper(username)

    try:
        scraper.scrape()
        print('\n✅ Scraping tugadi!')
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
