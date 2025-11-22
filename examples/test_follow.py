"""
Instagram Follow Manager - Example Usage
Demonstrates how to use the FollowManager class
"""

from instaharvest import FollowManager, ScraperConfig


def example_single_follow():
    """Example 1: Follow a single user"""
    print("=" * 70)
    print("Example 1: Follow Single User")
    print("=" * 70)

    # Initialize FollowManager
    manager = FollowManager()

    try:
        # Load session and setup browser
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        # Follow a user
        username = input("Enter username to follow (without @): ").strip()

        print(f"\n🔄 Following @{username}...")
        result = manager.follow(username)

        # Print result
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")

        print(f"\nStatus: {result['status']}")

    finally:
        manager.close()


def example_check_status():
    """Example 2: Check if following a user"""
    print("=" * 70)
    print("Example 2: Check Following Status")
    print("=" * 70)

    manager = FollowManager()

    try:
        # Load session and setup browser
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        # Check status
        username = input("Enter username to check (without @): ").strip()

        print(f"\n🔍 Checking status for @{username}...")
        result = manager.is_following(username)

        # Print result
        if result['success']:
            if result['following']:
                print(f"✅ You are following @{username}")
            else:
                print(f"ℹ️ You are not following @{username}")
        else:
            print(f"❌ {result['message']}")

    finally:
        manager.close()


def example_unfollow():
    """Example 3: Unfollow a user"""
    print("=" * 70)
    print("Example 3: Unfollow User")
    print("=" * 70)

    manager = FollowManager()

    try:
        # Load session and setup browser
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        # Unfollow a user
        username = input("Enter username to unfollow (without @): ").strip()

        print(f"\n🔄 Unfollowing @{username}...")
        result = manager.unfollow(username)

        # Print result
        if result['success']:
            print(f"✅ {result['message']}")
        else:
            print(f"❌ {result['message']}")

        print(f"\nStatus: {result['status']}")

    finally:
        manager.close()


def example_batch_follow():
    """Example 4: Follow multiple users"""
    print("=" * 70)
    print("Example 4: Batch Follow Multiple Users")
    print("=" * 70)

    manager = FollowManager()

    try:
        # Load session and setup browser
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        # Get list of users to follow
        print("\nEnter usernames to follow (one per line, empty line to finish):")
        usernames = []
        while True:
            username = input(f"  Username {len(usernames) + 1}: ").strip()
            if not username:
                break
            usernames.append(username)

        if not usernames:
            print("❌ No usernames provided!")
            return

        print(f"\n🔄 Following {len(usernames)} users...")
        result = manager.batch_follow(
            usernames,
            delay_between=(3, 5),  # 3-5 seconds between follows
            stop_on_error=False    # Continue even if some fail
        )

        # Print summary
        print("\n" + "=" * 70)
        print("📊 BATCH FOLLOW SUMMARY")
        print("=" * 70)
        print(f"Total users: {result['total']}")
        print(f"Successfully followed: {result['succeeded']}")
        print(f"Already following: {result['already_following']}")
        print(f"Failed: {result['failed']}")
        print()

        # Print individual results
        print("Individual results:")
        for r in result['results']:
            status_icon = "✅" if r['success'] else "❌"
            print(f"  {status_icon} @{r['username']}: {r['status']}")

    finally:
        manager.close()


def example_smart_follow():
    """Example 5: Smart follow with status check"""
    print("=" * 70)
    print("Example 5: Smart Follow (Check Before Follow)")
    print("=" * 70)

    manager = FollowManager()

    try:
        # Load session and setup browser
        session_data = manager.load_session()
        manager.setup_browser(session_data)

        # Get username
        username = input("Enter username (without @): ").strip()

        # Step 1: Check current status
        print(f"\n🔍 Checking current status for @{username}...")
        status_result = manager.is_following(username)

        if not status_result['success']:
            print(f"❌ Error checking status: {status_result['message']}")
            return

        # Step 2: Follow if not already following
        if status_result['following']:
            print(f"✅ You are already following @{username}")

            # Ask if user wants to unfollow
            unfollow = input("\nDo you want to unfollow? (yes/no): ").strip().lower()
            if unfollow == 'yes':
                print(f"\n🔄 Unfollowing @{username}...")
                unfollow_result = manager.unfollow(username)
                print(f"✅ {unfollow_result['message']}")
        else:
            print(f"ℹ️ You are not following @{username}")

            # Ask if user wants to follow
            follow = input("\nDo you want to follow? (yes/no): ").strip().lower()
            if follow == 'yes':
                print(f"\n🔄 Following @{username}...")
                follow_result = manager.follow(username)
                print(f"✅ {follow_result['message']}")

    finally:
        manager.close()


def main():
    """Main function - choose example to run"""
    print("\n" + "=" * 70)
    print("🚀 Instagram Follow Manager - Examples")
    print("=" * 70)
    print()
    print("Choose an example:")
    print("  1. Follow a single user")
    print("  2. Check if following a user")
    print("  3. Unfollow a user")
    print("  4. Batch follow multiple users")
    print("  5. Smart follow (check status first)")
    print()

    choice = input("Enter choice (1-5): ").strip()

    if choice == '1':
        example_single_follow()
    elif choice == '2':
        example_check_status()
    elif choice == '3':
        example_unfollow()
    elif choice == '4':
        example_batch_follow()
    elif choice == '5':
        example_smart_follow()
    else:
        print("❌ Invalid choice!")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
