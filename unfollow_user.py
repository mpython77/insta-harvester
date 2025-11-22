"""
Instagram Unfollow Script
Simple script to unfollow Instagram users

Usage:
    python unfollow_user.py

Requirements:
    - Instagram session must be saved first (run save_session.py)
"""

from instagram_scraper import FollowManager


def main():
    """Unfollow an Instagram user"""
    print("=" * 70)
    print("🚀 Instagram Unfollow Script")
    print("=" * 70)
    print()

    # Get username from user
    username = input("Enter Instagram username to unfollow (without @): ").strip().lstrip('@')

    if not username:
        print("❌ No username provided!")
        return

    # Initialize FollowManager
    print("\n📂 Loading session...")
    manager = FollowManager()

    try:
        # Load session and setup browser
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        print(f"✅ Session loaded!\n")

        # Unfollow the user
        print(f"🔄 Unfollowing @{username}...")
        result = manager.unfollow(username)

        # Print result
        print()
        print("=" * 70)
        if result['success']:
            if result['status'] == 'unfollowed':
                print(f"✅ SUCCESS! You have unfollowed @{username}")
            elif result['status'] == 'not_following':
                print(f"ℹ️ INFO: You were not following @{username}")
        else:
            print(f"❌ ERROR: {result['message']}")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
    finally:
        manager.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception:
        pass
