#!/usr/bin/env python3
"""
Simple Unfollow Script - Direct approach using proven selectors
Works with Instagram's div[role='button'] structure
"""

import time
import random
from playwright.sync_api import sync_playwright


def unfollow_user(username: str, session_file: str = "instagram_session.json"):
    """
    Unfollow an Instagram user using proven selectors

    Args:
        username: Instagram username to unfollow
        session_file: Path to session JSON file

    Returns:
        bool: True if successful, False otherwise
    """
    print(f"🔄 Starting unfollow process for @{username}")

    with sync_playwright() as p:
        # Launch browser
        print("🌐 Launching browser...")
        browser = p.chromium.launch(
            headless=False,  # Show browser for debugging
            args=['--start-maximized']
        )

        # Create context with session
        print("📂 Loading session...")
        try:
            import json
            with open(session_file, 'r') as f:
                session_data = json.load(f)

            context = browser.new_context(
                viewport={'width': 1280, 'height': 720},
                storage_state=session_data
            )
        except FileNotFoundError:
            print(f"❌ Session file not found: {session_file}")
            print("Run examples/save_session.py first!")
            browser.close()
            return False

        page = context.new_page()

        try:
            # Navigate to user profile
            url = f"https://www.instagram.com/{username}/"
            print(f"📍 Navigating to {url}")
            page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)  # Wait for page to load

            print("✓ Page loaded")

            # Step 1: Find and click "Following" button
            print("\n👆 Step 1: Looking for 'Following' button...")
            following_button = None

            # Try multiple selectors for Following button
            selectors = [
                "div[role='button']:has-text('Following')",
                "[role='button']:has-text('Following')",
                "text='Following'",
            ]

            for selector in selectors:
                try:
                    btn = page.locator(selector).first
                    if btn.count() > 0 and btn.is_visible():
                        following_button = btn
                        print(f"  ✓ Found Following button using: {selector}")
                        break
                except:
                    continue

            if not following_button:
                print("❌ Following button not found - user might not be followed")
                context.close()
                browser.close()
                return False

            # Click Following button
            print("  👆 Clicking Following button...")
            following_button.click()

            # Wait for popup to appear
            print("  ⏳ Waiting for popup to appear...")
            time.sleep(4)  # Important: wait for popup animation
            print("  ✓ Popup should be open now")

            # Step 2: Find and click "Unfollow" confirmation button
            print("\n👆 Step 2: Looking for 'Unfollow' confirmation button...")
            unfollow_button = None

            # Use PROVEN selectors from user
            # Try each method until one works

            # Method 1: Span inside div button
            try:
                print("  Trying Method 1: div[role='button'] span:has-text('Unfollow')")
                btn = page.locator("div[role='button'] span:has-text('Unfollow')").first
                if btn.count() > 0:
                    unfollow_button = btn
                    print("  ✓ Found with Method 1!")
            except Exception as e:
                print(f"  ✗ Method 1 failed: {e}")

            # Method 2: More specific with tabindex
            if not unfollow_button:
                try:
                    print("  Trying Method 2: div[role='button'][tabindex='0'] span:has-text('Unfollow')")
                    btn = page.locator("div[role='button'][tabindex='0'] span:has-text('Unfollow')").first
                    if btn.count() > 0:
                        unfollow_button = btn
                        print("  ✓ Found with Method 2!")
                except Exception as e:
                    print(f"  ✗ Method 2 failed: {e}")

            # Method 3: Playwright's get_by_role
            if not unfollow_button:
                try:
                    print("  Trying Method 3: get_by_role('button', name='Unfollow')")
                    btn = page.get_by_role("button", name="Unfollow")
                    if btn.count() > 0:
                        unfollow_button = btn
                        print("  ✓ Found with Method 3!")
                except Exception as e:
                    print(f"  ✗ Method 3 failed: {e}")

            # Method 4: XPath
            if not unfollow_button:
                try:
                    print("  Trying Method 4: XPath")
                    btn = page.locator("//span[text()='Unfollow']/ancestor::div[@role='button'][1]").first
                    if btn.count() > 0:
                        unfollow_button = btn
                        print("  ✓ Found with Method 4 (XPath)!")
                except Exception as e:
                    print(f"  ✗ Method 4 failed: {e}")

            # Last resort: Search all buttons
            if not unfollow_button:
                print("  ⚠️  Trying last resort: searching all visible buttons...")
                all_buttons = page.locator("div[role='button']")
                count = all_buttons.count()
                print(f"  Found {count} buttons on page")

                for i in range(min(count, 20)):
                    try:
                        btn = all_buttons.nth(i)
                        if btn.is_visible():
                            text = btn.inner_text()
                            print(f"    Button {i}: '{text.strip()}'")
                            if 'unfollow' in text.lower():
                                unfollow_button = btn
                                print(f"  ✓ Found Unfollow button at index {i}!")
                                break
                    except:
                        continue

            if not unfollow_button:
                print("❌ Unfollow confirmation button not found")
                print("   The popup might not have opened, or Instagram's HTML changed")
                context.close()
                browser.close()
                return False

            # Click Unfollow button
            print("  👆 Clicking Unfollow button...")
            time.sleep(random.uniform(1, 2))  # Human-like delay
            unfollow_button.click()

            # Wait for action to complete
            print("  ⏳ Waiting for unfollow to complete...")
            time.sleep(3)

            print(f"\n✅ Successfully unfollowed @{username}!")

            # Keep browser open for a moment
            print("\n⏸️  Keeping browser open for 5 seconds...")
            time.sleep(5)

            context.close()
            browser.close()
            return True

        except Exception as e:
            print(f"\n❌ Error during unfollow: {e}")
            import traceback
            traceback.print_exc()
            context.close()
            browser.close()
            return False


def main():
    """Main function"""
    print("=" * 60)
    print("Instagram Unfollow Tool (Fixed Version)")
    print("=" * 60)

    username = input("\nEnter username to unfollow: ").strip()

    if not username:
        print("❌ Username cannot be empty")
        return

    # Remove @ if user included it
    username = username.lstrip('@')

    print(f"\n🎯 Target: @{username}")
    confirm = input("Proceed? (y/n): ").strip().lower()

    if confirm != 'y':
        print("❌ Cancelled")
        return

    success = unfollow_user(username)

    if success:
        print("\n" + "=" * 60)
        print("✅ UNFOLLOW COMPLETED SUCCESSFULLY!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ UNFOLLOW FAILED - Check the errors above")
        print("=" * 60)


if __name__ == "__main__":
    main()
