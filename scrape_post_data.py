"""
Instagram Post Data Scraper
post_links.txt dan linklar o'qib, har biridan:
- Tagged akkauntlar
- Likes soni
- Post vaqti
"""

import json
import os
import time
from playwright.sync_api import sync_playwright

SESSION_FILE = 'instagram_session.json'
LINKS_FILE = 'post_links.txt'


class InstagramPostDataScraper:
    """Instagram post ma'lumotlarini scraping qilish"""

    def __init__(self):
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

    def check_links_file(self):
        """Links faylni tekshirish"""
        if not os.path.exists(LINKS_FILE):
            raise FileNotFoundError(
                f'❌ {LINKS_FILE} topilmadi!\n'
                f'Avval "python scrape_post_links.py" ni ishga tushiring.'
            )

    def load_links(self):
        """Linklar faylni o'qish"""
        with open(LINKS_FILE, 'r', encoding='utf-8') as f:
            links = [line.strip() for line in f if line.strip()]
        return links

    def load_session(self, p):
        """Session bilan browser ochish"""
        print('📂 Session yuklanmoqda...')

        with open(SESSION_FILE, 'r', encoding='utf-8') as f:
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

    def goto_post(self, url):
        """Post sahifasiga o'tish"""
        try:
            self.page.goto(url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(2)  # Sahifa yuklanishi uchun
            return True
        except Exception as e:
            print(f'⚠️  Post ochishda xatolik: {e}')
            return False

    def _get_tagged_accounts(self):
        """Tag qilingan akkauntlarni olish"""
        try:
            # ._aa1y class ichidagi barcha a[href] linklar
            tag_containers = self.page.locator('._aa1y').all()

            tagged = []
            for container in tag_containers:
                try:
                    link = container.locator('a[href]').first
                    href = link.get_attribute('href')
                    if href:
                        # Username ni olish (/ larni olib tashlash)
                        username = href.strip('/').split('/')[-1]
                        tagged.append(username)
                except Exception:
                    continue

            return tagged if tagged else ['No tags']
        except Exception as e:
            return ['No tags']

    def _get_likes_count(self):
        """Likes sonini olish"""
        try:
            # a[href*="liked_by"] ni topish
            likes_link = self.page.locator('a[href*="liked_by"]').first
            if likes_link:
                # span.html-span ichidan raqamni olish
                likes_text = likes_link.locator('span.html-span').first.inner_text()
                return likes_text.strip().replace(',', '')
        except Exception:
            pass

        # Agar yuqoridagi ishlamasa, "likes" so'zi bilan topish
        try:
            likes_element = self.page.locator('span:has-text("likes")').first
            if likes_element:
                likes_text = likes_element.locator('span.html-span').first.inner_text()
                return likes_text.strip().replace(',', '')
        except Exception:
            pass

        return 'N/A'

    def _get_post_time(self):
        """Post vaqtini olish"""
        try:
            # time elementi
            time_element = self.page.locator('time').first
            if time_element:
                # datetime attribute
                datetime_str = time_element.get_attribute('datetime')
                # title attribute (odam o'qiy oladigan format)
                title_str = time_element.get_attribute('title')

                if title_str:
                    return title_str
                elif datetime_str:
                    return datetime_str
        except Exception:
            pass

        return 'N/A'

    def scrape_post(self, url):
        """Bitta postni scraping qilish"""
        # Postga kirish
        if not self.goto_post(url):
            return None

        # Ma'lumotlar olish
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
        """Post ma'lumotlarini chiroyli formatda chiqarish"""
        if not data:
            return

        print('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
        print(f'🔗 URL: {data["url"]}')
        print(f'👥 Tagged: {", ".join(data["tagged_accounts"])}')
        print(f'❤️  Likes: {data["likes"]}')
        print(f'🕐 Time: {data["post_time"]}')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

    def close(self):
        """Browser yopish"""
        if self.browser:
            self.browser.close()

    def scrape_all(self):
        """Barcha postlarni scraping qilish"""
        self.check_session()
        self.check_links_file()

        # Linklar yuklanmoqda
        links = self.load_links()
        print(f'📊 Jami linklar: {len(links)}\n')

        if not links:
            print('❌ Linklar topilmadi!')
            return

        with sync_playwright() as p:
            try:
                self.load_session(p)

                print('🚀 Scraping boshlandi...\n')

                # Har bir linkni scraping qilish
                for i, link in enumerate(links, 1):
                    print(f'[{i}/{len(links)}] 🔍 Scraping: {link}')

                    data = self.scrape_post(link)
                    if data:
                        self.print_post_data(data)

                    # Keyingi postga o'tishdan oldin kutish (Instagram limiting)
                    if i < len(links):
                        import random
                        wait_time = random.uniform(2, 4)
                        print(f'⏳ {wait_time:.1f}s kutilmoqda...')
                        time.sleep(wait_time)

                print('\n✅ Barcha postlar scraping qilindi!')

            finally:
                time.sleep(2)
                self.close()


def main():
    """Main funksiya"""
    print('🚀 Instagram Post Data Scraper\n')

    scraper = InstagramPostDataScraper()

    try:
        scraper.scrape_all()
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
