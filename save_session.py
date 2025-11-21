"""
Instagram Session Saqlash Dasturi
Playwright yordamida Instagram ga manual login qilib, sessionni saqlaydi.
"""

import json
from playwright.sync_api import sync_playwright

SESSION_FILE = 'instagram_session.json'


def save_session():
    """Instagram sessiyasini saqlash"""
    print('🚀 Instagram session saqlash dasturi ishga tushdi...')

    with sync_playwright() as p:
        # Browser ochish (headless=False - ko'rinishi uchun)
        browser = p.chromium.launch(
            headless=False,
            args=['--start-maximized']
        )

        # Context yaratish
        context = browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        page = context.new_page()

        print('📱 Instagram ochilmoqda...')
        page.goto('https://www.instagram.com/', wait_until='networkidle')

        print('\n✋ KUTISH REJIMI:')
        print('1️⃣  Instagram ga manual login qiling')
        print('2️⃣  Login tugagandan keyin "Eslab qolish" ni tanlang')
        print('3️⃣  Bosh sahifaga o\'tganingizda bu terminalga qaytib ENTER bosing')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        # Enter tugmasini kutish
        input('\n⌨️  Tayyor bo\'lsangiz ENTER bosing: ')

        print('\n💾 Session saqlanmoqda...')

        # Session ma'lumotlarini saqlash
        session_data = context.storage_state()

        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        print(f'✅ Session muvaffaqiyatli saqlandi: {SESSION_FILE}')
        print(f'📊 Cookies soni: {len(session_data["cookies"])}')

        browser.close()
        print('👋 Browser yopildi. Dastur tugadi!')


if __name__ == '__main__':
    try:
        save_session()
    except KeyboardInterrupt:
        print('\n\n⚠️  Dastur to\'xtatildi!')
    except Exception as e:
        print(f'❌ Xatolik yuz berdi: {e}')
        raise
