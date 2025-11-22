"""
Instagram Follow Script
Simple script to follow Instagram users

Usage:
    python follow_user.py

Requirements:
    - Instagram session must be saved first (run save_session.py)
"""

from instaharvest import FollowManager


def main():
    """Follow an Instagram user"""
    print("=" * 70)
    print("🚀 Instagram Follow Script")
    print("=" * 70)
    print()

    # Get username from user
    username = input("Enter Instagram username to follow (without @): ").strip().lstrip('@')

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

        # Follow the user
        print(f"🔄 Following @{username}...")
        result = manager.follow(username)

        # Print result
        print()
        print("=" * 70)
        if result['success']:
            if result['status'] == 'followed':
                print(f"✅ SUCCESS! You are now following @{username}")
            elif result['status'] == 'already_following':
                print(f"ℹ️ INFO: You are already following @{username}")
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
