#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Instagram All-in-One Script
Single browser for all operations

This script demonstrates using SharedBrowser to perform
multiple operations in a single browser session:
- Follow/Unfollow users
- Send messages
- Scrape profiles
- All without reopening browser!

Usage:
    python all_in_one.py
"""

import sys
import os

# ALWAYS prioritize local development version if available
# This ensures we use the latest code in the parent directory
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.exists(os.path.join(parent_dir, 'instaharvest')):
    sys.path.insert(0, parent_dir)

from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file


def main():
    """All-in-one Instagram operations in single browser"""
    print("=" * 70)
    print("🚀 Instagram All-in-One - Single Browser Session")
    print("=" * 70)
    print()
    print("This script uses a SINGLE browser for all operations!")
    print("No need to reopen browser for each action.\n")

    # Intelligent session discovery
    session_file_path = find_session_file()
    if not session_file_path:
        print("❌ Error: Session file not found!")
        print("   Please run 'save_session.py' first.")
        print("   The script will search in:")
        print("   - Current directory")
        print("   - Script directory")
        print("   - ~/.instaharvest/")
        return

    print(f"✅ Found session: {session_file_path}")

    # Create config for better reliability
    config = ScraperConfig(
        headless=False,
        session_file=session_file_path,  # Explicitly pass the found session path
        # base_output_dir="./output_data", # Optional: Save all data to a specific folder
        log_level='INFO',
        log_to_console=True,
        popup_open_delay=3.0,
        button_click_delay=3.0,
    )

    # Use SharedBrowser context manager with config
    # Browser will open once and close automatically at the end
    try:
        with SharedBrowser(config=config) as browser:
            print("✅ Browser opened and session loaded!\n")

            while True:
                print("=" * 70)
                print("Choose an action:")
                print("  1. Follow a user")
                print("  2. Unfollow a user")
                print("  3. Send a message")
                print("  4. Check if following a user")
                print("  5. Scrape profile")
                print("  6. Batch follow multiple users")
                print("  7. Batch send messages")
                print("  8. Get followers list")
                print("  9. Get following list")
                print("  10. Scrape post links")
                print("  11. Scrape reel links")
                print("  0. Exit")
                print("=" * 70)

                choice = input("\nEnter choice (0-11): ").strip()

                if choice == '0':
                    print("\n👋 Goodbye!")
                    break

                elif choice == '1':
                    # Follow a user
                    username = input("Enter username to follow: ").strip()
                    print(f"\n🔄 Following @{username}...")
                    result = browser.follow(username)
                    if result['success']:
                        print(f"✅ {result['message']}")
                    else:
                        print(f"❌ {result['message']}")

                elif choice == '2':
                    # Unfollow a user
                    username = input("Enter username to unfollow: ").strip()
                    print(f"\n🔄 Unfollowing @{username}...")
                    result = browser.unfollow(username)
                    if result['success']:
                        print(f"✅ {result['message']}")
                    else:
                        print(f"❌ {result['message']}")

                elif choice == '3':
                    # Send message
                    username = input("Enter username to message: ").strip()
                    message = input("Enter message: ").strip()
                    print(f"\n📨 Sending message to @{username}...")
                    result = browser.send_message(username, message)
                    if result['success']:
                        print(f"✅ {result['message']}")
                    else:
                        print(f"❌ {result['message']}")

                elif choice == '4':
                    # Check following status
                    username = input("Enter username to check: ").strip()
                    print(f"\n🔍 Checking if following @{username}...")
                    result = browser.is_following(username)
                    if result['success']:
                        if result['following']:
                            print(f"✅ You are following @{username}")
                        else:
                            print(f"ℹ️ You are not following @{username}")
                    else:
                        print(f"❌ {result['message']}")

                elif choice == '5':
                    # Scrape profile
                    username = input("Enter username to scrape: ").strip()
                    print(f"\n🔍 Scraping profile @{username}...")
                    try:
                        data = browser.scrape_profile(username)
                        print(f"\n✅ Profile data:")
                        print(f"  Posts: {data.get('posts', 'N/A')}")
                        print(f"  Followers: {data.get('followers', 'N/A')}")
                        print(f"  Following: {data.get('following', 'N/A')}")
                        print(f"  Verified: {'✓ Yes' if data.get('is_verified', False) else '✗ No'}")
                        print(f"  Category: {data.get('category') or 'Not set'}")
                        print(f"  Bio: {data.get('bio') or 'No bio'}")
                        if data.get('external_links'):
                            print(f"  External Links: {', '.join(data.get('external_links'))}")
                        if data.get('threads_profile'):
                            print(f"  Threads: {data.get('threads_profile')}")
                    except Exception as e:
                        print(f"❌ Error: {e}")

                elif choice == '6':
                    # Batch follow
                    print("\nEnter usernames to follow (one per line, empty to finish):")
                    usernames = []
                    while True:
                        user = input(f"  Username {len(usernames) + 1}: ").strip()
                        if not user:
                            break
                        usernames.append(user)

                    if usernames:
                        print(f"\n🔄 Following {len(usernames)} users...")
                        result = browser.batch_follow(usernames)
                        print(f"\n📊 Results:")
                        print(f"  Total: {result['total']}")
                        print(f"  Succeeded: {result['succeeded']}")
                        print(f"  Already following: {result['already_following']}")
                        print(f"  Failed: {result['failed']}")
                    else:
                        print("❌ No usernames provided")

                elif choice == '7':
                    # Batch send messages
                    message = input("Enter message to send: ").strip()
                    print("\nEnter usernames to message (one per line, empty to finish):")
                    usernames = []
                    while True:
                        user = input(f"  Username {len(usernames) + 1}: ").strip()
                        if not user:
                            break
                        usernames.append(user)

                    if usernames and message:
                        print(f"\n📨 Sending message to {len(usernames)} users...")
                        result = browser.batch_send(usernames, message)
                        print(f"\n📊 Results:")
                        print(f"  Total: {result['total']}")
                        print(f"  Succeeded: {result['succeeded']}")
                        print(f"  Failed: {result['failed']}")
                    else:
                        print("❌ Message or usernames missing")

                elif choice == '8':
                    # Get followers
                    username = input("Enter username to get followers from: ").strip()
                    limit_input = input("Enter limit (or press Enter for all): ").strip()
                    limit = int(limit_input) if limit_input else None

                    print(f"\n📊 Collecting followers from @{username}...")
                    try:
                        followers = browser.get_followers(username, limit=limit, print_realtime=True)
                        print(f"\n✅ Total followers collected: {len(followers)}")

                        # Ask to save
                        save = input("\nSave to file? (y/n): ").strip().lower()
                        if save == 'y':
                            filename = f"{username}_followers.txt"
                            with open(filename, 'w', encoding='utf-8') as f:
                                for follower in followers:
                                    f.write(f"{follower}\n")
                            print(f"✅ Saved to: {filename}")
                    except Exception as e:
                        print(f"❌ Error: {e}")

                elif choice == '9':
                    # Get following
                    username = input("Enter username to get following from: ").strip()
                    limit_input = input("Enter limit (or press Enter for all): ").strip()
                    limit = int(limit_input) if limit_input else None

                    print(f"\n📊 Collecting following from @{username}...")
                    try:
                        following = browser.get_following(username, limit=limit, print_realtime=True)
                        print(f"\n✅ Total following collected: {len(following)}")

                        # Ask to save
                        save = input("\nSave to file? (y/n): ").strip().lower()
                        if save == 'y':
                            filename = f"{username}_following.txt"
                            with open(filename, 'w', encoding='utf-8') as f:
                                for user in following:
                                    f.write(f"{user}\n")
                            print(f"✅ Saved to: {filename}")
                    except Exception as e:
                        print(f"❌ Error: {e}")

                elif choice == '10':
                    # Scrape post links
                    username = input("Enter username to scrape post links: ").strip()
                    target_input = input("Enter target count (or press Enter for all): ").strip()
                    target_count = int(target_input) if target_input else None

                    print(f"\n📸 Scraping post links from @{username}...")
                    try:
                        links = browser.scrape_post_links(username, target_count=target_count, save_to_file=True)
                        print(f"\n✅ Total links collected: {len(links)}")
                        print(f"  Posts: {sum(1 for link in links if link.get('type') == 'Post')}")
                        print(f"  Reels: {sum(1 for link in links if link.get('type') == 'Reel')}")
                    except Exception as e:
                        print(f"❌ Error: {e}")

                elif choice == '11':
                    # Scrape reel links
                    username = input("Enter username to scrape reel links: ").strip()

                    print(f"\n🎬 Scraping reel links from @{username}...")
                    try:
                        links = browser.scrape_reel_links(username, save_to_file=True)
                        print(f"\n✅ Total reel links collected: {len(links)}")
                    except Exception as e:
                        print(f"❌ Error: {e}")

                else:
                    print("❌ Invalid choice!")

                print()

        print("\n✅ Browser closed. Session saved!")

    except Exception as e:
        print(f"\n❌ Error during execution: {e}")
        # Only print traceback in debug mode or if not handled
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
