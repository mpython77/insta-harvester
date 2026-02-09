#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Instagram Session Save Utility
Uses Playwright to manually login to Instagram and save the session.

This script opens a browser, lets you login manually, then saves
the session for later use by other scripts.
"""

import json
import os

# Robust import - works whether installed via pip or run from source
import sys

# ALWAYS prioritize local development version if available
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.exists(os.path.join(parent_dir, 'instaharvest')):
    sys.path.insert(0, parent_dir)

from instaharvest.config import ScraperConfig
from instaharvest.session_utils import get_session_save_path, SESSION_FILENAME

from playwright.sync_api import sync_playwright

# Get the save path using new intelligent system
SESSION_FILE = get_session_save_path()


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
