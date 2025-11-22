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

from instagram_scraper import SharedBrowser


def main():
    """All-in-one Instagram operations in single browser"""
    print("=" * 70)
    print("🚀 Instagram All-in-One - Single Browser Session")
    print("=" * 70)
    print()
    print("This script uses a SINGLE browser for all operations!")
    print("No need to reopen browser for each action.\n")

    # Use SharedBrowser context manager
    # Browser will open once and close automatically at the end
    with SharedBrowser() as browser:
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
            print("  0. Exit")
            print("=" * 70)

            choice = input("\nEnter choice (0-7): ").strip()

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

            else:
                print("❌ Invalid choice!")

            print()

    print("\n✅ Browser closed. Session saved!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
