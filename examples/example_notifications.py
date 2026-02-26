"""
Example: Instagram Notification Reader
Reads and filters notifications from Instagram's activity feed.

Features:
    - Read all notifications from the activity page
    - Filter by type (follow, comment_like, post_like, comment, mention, etc.)
    - Filter by section (Today, Yesterday, This week, This month, Earlier)
    - Filter by username
    - Get summary statistics
    - Export results to JSON

Requires:
    - instagram_session.json (run save_session.py first)
    - playwright (pip install playwright && playwright install chrome)

Usage:
    python example_notifications.py
"""
import json
import logging
import time
import os
import sys

# Path setup for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from playwright.sync_api import sync_playwright
from instaharvest import ScraperConfig, StealthManager, NotificationReader
from instaharvest.session_utils import find_session_file


def main():
    # Setup logger
    logger = logging.getLogger('notif_example')
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)-7s | %(message)s', datefmt='%H:%M:%S'
    ))
    logger.addHandler(handler)

    # Find session file
    session_file = find_session_file()
    if not session_file:
        logger.error("❌ Session file not found! Run save_session.py first.")
        return

    config = ScraperConfig()
    logger.info(f"🍪 Loading session from: {session_file}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = browser.new_context(
            storage_state=session_file,
            viewport={'width': 1280, 'height': 900},
            user_agent=config.user_agent,
        )
        page = context.new_page()

        # Apply stealth
        stealth = StealthManager(config)
        stealth.apply_page_stealth(page)

        # Navigate and verify login
        logger.info("📍 Navigating to Instagram...")
        page.goto('https://www.instagram.com/', wait_until='domcontentloaded')
        time.sleep(4)

        if 'accounts/login' in (page.url or ''):
            logger.error("❌ Session expired! Please run save_session.py again.")
            context.close()
            browser.close()
            return

        logger.info("✅ Session active")

        # ==================== NOTIFICATION READER ====================

        reader = NotificationReader(page, logger, config)

        # Read up to 50 notifications
        notifications = reader.read_notifications(
            max_count=50,
            scroll=True,       # Scroll to load more
            open_page=True     # Navigate to activity page automatically
        )

        if not notifications:
            logger.warning("⚠️ No notifications found!")
            context.close()
            browser.close()
            return

        # ==================== DISPLAY RESULTS ====================

        print(f"\n{'='*60}")
        print(f" 🔔 Found {len(notifications)} notifications")
        print(f"{'='*60}")

        for i, n in enumerate(notifications, 1):
            users = ', '.join(f"@{u}" for u in n.usernames) if n.usernames else "—"
            section = f"[{n.section}] " if n.section else ""
            print(f"\n  {i:>2}. {section}[{n.type}] {users}")
            print(f"      {n.text}")
            if n.time_text:
                print(f"      ⏰ {n.time_text}")
            if n.action_button:
                print(f"      🔘 {n.action_button}")

        # ==================== FILTERING EXAMPLES ====================

        # Filter by type
        follows = reader.filter_by_type(notifications, 'follow')
        print(f"\n👤 Follow notifications: {len(follows)}")

        likes = reader.filter_by_type(notifications, 'post_like')
        print(f"❤️ Post like notifications: {len(likes)}")

        # Filter by section
        this_week = reader.filter_by_section(notifications, 'This week')
        print(f"📅 This week: {len(this_week)}")

        # ==================== SUMMARY ====================

        stats = reader.summary(notifications)
        print(f"\n📊 Summary:")
        print(f"  Total: {stats['total']}")
        print(f"  By type: {stats['by_type']}")
        print(f"  Unique users: {len(stats['unique_users'])}")

        if stats['has_follow_back']:
            print(f"  ⬅️ Follow Back: {len(stats['has_follow_back'])} users")

        # ==================== EXPORT TO JSON ====================

        output_file = os.path.join(os.path.dirname(__file__), 'notifications_output.json')
        result = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'summary': stats,
            'notifications': reader.to_dicts(notifications),
        }
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 Results saved to: {output_file}")

        # ==================== CONVENIENCE METHODS ====================

        # You can also use shortcut methods:
        # follows = reader.get_follows()           # Only follow notifications
        # likes = reader.get_post_likes()           # Only post likes
        # comment_likes = reader.get_comment_likes() # Only comment likes
        # comments = reader.get_comments()           # Only comments
        # usernames = reader.get_new_followers_usernames()  # Just username strings

        # Cleanup
        time.sleep(2)
        context.storage_state(path=session_file)  # Save updated cookies
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
