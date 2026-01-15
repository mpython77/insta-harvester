"""
Instagram Session Save Utility
Uses Playwright to manually login to Instagram and save the session.
"""

import json
from playwright.sync_api import sync_playwright
from instaharvest.config import ScraperConfig

SESSION_FILE = 'instagram_session.json'


def save_session():
    """Save Instagram session"""
    print('🚀 Instagram session save utility started...')

    # Use config for consistent settings
    config = ScraperConfig(headless=False)

    with sync_playwright() as p:
        # Prepare launch options
        launch_options = {'headless': config.headless}
        if config.browser_channel and config.browser_channel != 'chromium':
            launch_options['channel'] = config.browser_channel

        # Launch browser using config settings
        browser = p.chromium.launch(**launch_options)

        # Create context using config settings
        context = browser.new_context(
            viewport={'width': config.viewport_width, 'height': config.viewport_height},
            user_agent=config.user_agent
        )

        page = context.new_page()

        print('📱 Opening Instagram...')
        page.goto('https://www.instagram.com/', wait_until='networkidle')

        print('\n✋ WAITING MODE:')
        print('1️⃣  Manually login to Instagram')
        print('2️⃣  Select "Remember me" after login')
        print('3️⃣  Once you reach the home page, return to this terminal and press ENTER')
        print('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

        # Wait for Enter key
        input('\n⌨️  Press ENTER when ready: ')

        print('\n💾 Saving session...')

        # Save session data
        session_data = context.storage_state()

        with open(SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)

        print(f'✅ Session successfully saved: {SESSION_FILE}')
        print(f'📊 Number of cookies: {len(session_data["cookies"])}')

        browser.close()
        print('👋 Browser closed. Program finished!')


if __name__ == '__main__':
    try:
        save_session()
    except KeyboardInterrupt:
        print('\n\n⚠️  Program interrupted!')
    except Exception as e:
        print(f'❌ Error occurred: {e}')
        raise
