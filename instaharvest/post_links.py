"""
Instagram Post Links Scraper - USER'S PROVEN 100% ACCURATE METHOD
Collects post and reel links with human-like scrolling
"""

import json
import os
import time
import random
from typing import List, Set, Optional
from pathlib import Path

from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page


class InstagramPostLinksScraper:
    """Instagram postlar linklarini scraping qilish - 100% ACCURATE"""

    def __init__(self, username: str, session_file: str = 'instagram_session.json'):
        """
        Args:
            username: Instagram username (@ belgisisiz)
            session_file: Session fayl nomi (default: instagram_session.json)
        """
        self.username = username.strip().lstrip('@')
        self.profile_url = f'https://www.instagram.com/{self.username}/'
        self.session_file = session_file
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
            headless=False,
            args=['--start-maximized']
        )

        # Session bilan context yaratish
        self.context = self.browser.new_context(
            storage_state=session_data,
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)

        print('✅ Session yuklandi!')

    def goto_profile(self):
        """Profile sahifasiga o'tish"""
        print(f'🔍 Profile ochilmoqda: {self.username}')

        self.page.goto(self.profile_url, wait_until='domcontentloaded', timeout=60000)

        print('⏳ Sahifa yuklanishi kutilmoqda...')
        time.sleep(3)

        # Profile mavjudligini tekshirish
        if 'Page Not Found' in self.page.content() or 'Sorry, this page' in self.page.content():
            raise ValueError(f'❌ Profile topilmadi: {self.username}')

        print('✅ Profile ochildi!')

    def get_posts_count(self):
        """Posts sonini olish"""
        try:
            self.page.wait_for_selector('span:has-text("posts")', timeout=10000)
            posts_element = self.page.locator('span:has-text("posts")').first
            if posts_element:
                posts_text = posts_element.locator('span.html-span').first.inner_text()
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
            links = self.page.locator('a[href*="/p/"], a[href*="/reel/"]').all()

            # Href larni olish
            hrefs = set()
            for link in links:
                href = link.get_attribute('href')
                if href:
                    # To'liq URL yaratish
                    if href.startswith('/'):
                        href = f'https://www.instagram.com{href}'
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
        max_no_new_attempts = 3  # 3 marta yangi link yuklanmasa to'xtatish

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
            self.page.evaluate('window.scrollBy(0, window.innerHeight * 0.8)')

            # 1.5-2.5 sekund kutish (random) - ANTI-DETECTION
            wait_time = random.uniform(1.5, 2.5)
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
