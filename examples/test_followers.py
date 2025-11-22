"""
Instagram Followers Collector - Example Usage
Demonstrates how to use the FollowersCollector class
"""

from instagram_scraper import FollowersCollector, ScraperConfig


def example_basic_followers():
    """Example 1: Collect followers with limit"""
    print("=" * 70)
    print("Example 1: Collect Followers with Limit")
    print("=" * 70)

    collector = FollowersCollector()

    try:
        # Load session and setup browser
        session_data = collector.load_session()
        collector.setup_browser(session_data)

        # Get username
        username = input("Enter username to collect followers from: ").strip()

        # Collect first 50 followers
        print(f"\n📊 Collecting first 50 followers from @{username}...")
        followers = collector.get_followers(
            username,
            limit=50,
            print_realtime=True
        )

        print(f"\n✅ Collected {len(followers)} followers!")

    finally:
        collector.close()


def example_all_followers():
    """Example 2: Collect all followers (no limit)"""
    print("=" * 70)
    print("Example 2: Collect All Followers")
    print("=" * 70)

    collector = FollowersCollector()

    try:
        # Load session and setup browser
        session_data = collector.load_session()
        collector.setup_browser(session_data)

        # Get username
        username = input("Enter username to collect all followers from: ").strip()

        # Warning
        print("\n⚠️ This will collect ALL followers (may take a long time)")
        confirm = input("Continue? (y/n): ").strip().lower()

        if confirm != 'y':
            print("❌ Cancelled")
            return

        # Collect all followers
        print(f"\n📊 Collecting all followers from @{username}...")
        followers = collector.get_followers(
            username,
            limit=None,  # No limit
            print_realtime=True
        )

        print(f"\n✅ Collected {len(followers)} followers!")

        # Save to file
        filename = f"{username}_all_followers.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            for follower in followers:
                f.write(f"{follower}\n")
        print(f"💾 Saved to: {filename}")

    finally:
        collector.close()


def example_following():
    """Example 3: Collect following list"""
    print("=" * 70)
    print("Example 3: Collect Following List")
    print("=" * 70)

    collector = FollowersCollector()

    try:
        # Load session and setup browser
        session_data = collector.load_session()
        collector.setup_browser(session_data)

        # Get username
        username = input("Enter username to collect following from: ").strip()

        # Get limit
        limit_input = input("Enter limit (or press Enter for all): ").strip()
        limit = int(limit_input) if limit_input else None

        # Collect following
        print(f"\n📊 Collecting following from @{username}...")
        following = collector.get_following(
            username,
            limit=limit,
            print_realtime=True
        )

        print(f"\n✅ Collected {len(following)} following!")

    finally:
        collector.close()


def example_compare_followers_following():
    """Example 4: Compare followers vs following"""
    print("=" * 70)
    print("Example 4: Compare Followers vs Following")
    print("=" * 70)
    print("Find who you follow but doesn't follow you back")
    print()

    collector = FollowersCollector()

    try:
        # Load session and setup browser
        session_data = collector.load_session()
        collector.setup_browser(session_data)

        # Get username
        username = input("Enter username to analyze: ").strip()

        # Collect followers
        print(f"\n📊 Step 1: Collecting followers from @{username}...")
        followers = collector.get_followers(
            username,
            limit=None,
            print_realtime=False  # Silent mode for comparison
        )
        print(f"✅ Collected {len(followers)} followers")

        # Collect following
        print(f"\n📊 Step 2: Collecting following from @{username}...")
        following = collector.get_following(
            username,
            limit=None,
            print_realtime=False  # Silent mode for comparison
        )
        print(f"✅ Collected {len(following)} following")

        # Analysis
        print("\n" + "=" * 70)
        print("📊 ANALYSIS RESULTS")
        print("=" * 70)

        followers_set = set(followers)
        following_set = set(following)

        # Who doesn't follow back
        not_following_back = following_set - followers_set
        print(f"\n🔴 Users you follow but don't follow you back: {len(not_following_back)}")
        if not_following_back and len(not_following_back) <= 20:
            for user in sorted(not_following_back):
                print(f"   - @{user}")
        elif not_following_back:
            print(f"   (Too many to display. Showing first 20)")
            for user in sorted(not_following_back)[:20]:
                print(f"   - @{user}")

        # Who you don't follow back
        not_followed_back = followers_set - following_set
        print(f"\n🟡 Users who follow you but you don't follow back: {len(not_followed_back)}")
        if not_followed_back and len(not_followed_back) <= 20:
            for user in sorted(not_followed_back):
                print(f"   - @{user}")
        elif not_followed_back:
            print(f"   (Too many to display. Showing first 20)")
            for user in sorted(not_followed_back)[:20]:
                print(f"   - @{user}")

        # Mutual followers
        mutual = followers_set & following_set
        print(f"\n🟢 Mutual (following each other): {len(mutual)}")

        # Summary
        print("\n" + "=" * 70)
        print(f"Total followers: {len(followers)}")
        print(f"Total following: {len(following)}")
        print(f"Mutual: {len(mutual)}")
        print(f"Not following back: {len(not_following_back)}")
        print(f"Not followed back: {len(not_followed_back)}")
        print("=" * 70)

        # Save results
        save = input("\nSave results to files? (y/n): ").strip().lower()
        if save == 'y':
            # Save not following back
            with open(f"{username}_not_following_back.txt", 'w', encoding='utf-8') as f:
                for user in sorted(not_following_back):
                    f.write(f"{user}\n")

            # Save not followed back
            with open(f"{username}_not_followed_back.txt", 'w', encoding='utf-8') as f:
                for user in sorted(not_followed_back):
                    f.write(f"{user}\n")

            # Save mutual
            with open(f"{username}_mutual.txt", 'w', encoding='utf-8') as f:
                for user in sorted(mutual):
                    f.write(f"{user}\n")

            print(f"✅ Saved to:")
            print(f"   - {username}_not_following_back.txt")
            print(f"   - {username}_not_followed_back.txt")
            print(f"   - {username}_mutual.txt")

    finally:
        collector.close()


def example_silent_collection():
    """Example 5: Silent collection (no real-time output)"""
    print("=" * 70)
    print("Example 5: Silent Collection")
    print("=" * 70)
    print("Collect without real-time printing for faster performance")
    print()

    collector = FollowersCollector()

    try:
        # Load session and setup browser
        session_data = collector.load_session()
        collector.setup_browser(session_data)

        # Get username
        username = input("Enter username: ").strip()
        limit_input = input("Enter limit (or press Enter for all): ").strip()
        limit = int(limit_input) if limit_input else None

        # Collect silently
        print(f"\n📊 Collecting followers from @{username} (silent mode)...")
        followers = collector.get_followers(
            username,
            limit=limit,
            print_realtime=False  # Silent mode
        )

        # Show results after completion
        print(f"\n✅ Collected {len(followers)} followers!")
        print("\nFirst 10 followers:")
        for i, follower in enumerate(followers[:10], 1):
            print(f"  {i}. @{follower}")

        if len(followers) > 10:
            print(f"  ... and {len(followers) - 10} more")

    finally:
        collector.close()


def main():
    """Main function - choose example to run"""
    print("\n" + "=" * 70)
    print("📊 Instagram Followers Collector - Examples")
    print("=" * 70)
    print()
    print("Choose an example:")
    print("  1. Collect followers with limit (50 users)")
    print("  2. Collect all followers (no limit)")
    print("  3. Collect following list")
    print("  4. Compare followers vs following (find who doesn't follow back)")
    print("  5. Silent collection (no real-time output)")
    print()

    choice = input("Enter choice (1-5): ").strip()

    if choice == '1':
        example_basic_followers()
    elif choice == '2':
        example_all_followers()
    elif choice == '3':
        example_following()
    elif choice == '4':
        example_compare_followers_following()
    elif choice == '5':
        example_silent_collection()
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
