"""
Instagram Followers Collector - Simple Script
Collect followers list from any profile with real-time output
"""

from instagram_scraper import FollowersCollector


def main():
    """Collect followers from a profile"""
    print("=" * 70)
    print("Instagram Followers Collector")
    print("=" * 70)
    print()

    # Get username
    username = input("Enter username (without @): ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return

    # Get limit
    limit_input = input("Enter limit (or press Enter for all): ").strip()
    limit = int(limit_input) if limit_input else None

    # Initialize collector
    collector = FollowersCollector()

    try:
        # Load session and setup browser
        print("\n🔄 Loading session...")
        session_data = collector.load_session()

        print("🌐 Starting browser...")
        collector.setup_browser(session_data)

        # Collect followers
        print(f"\n📊 Collecting followers from @{username}...")
        if limit:
            print(f"   (Limit: {limit} followers)")
        else:
            print("   (No limit - collecting all)")

        followers = collector.get_followers(
            username,
            limit=limit,
            print_realtime=True
        )

        # Summary
        print(f"\n✅ Successfully collected {len(followers)} followers!")

        # Save to file
        save = input("\nSave to file? (y/n): ").strip().lower()
        if save == 'y':
            filename = f"{username}_followers.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                for follower in followers:
                    f.write(f"{follower}\n")
            print(f"✅ Saved to: {filename}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise

    finally:
        collector.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Program stopped!")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
