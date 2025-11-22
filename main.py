"""
Instagram Scraper - Main Example
Complete workflow demonstration
"""

from instagram_scraper import (
    InstagramOrchestrator,
    ScraperConfig,
    ProfileScraper,
    PostLinksScraper,
    PostDataScraper,
    quick_scrape
)


def main():
    """Main function - complete scraping workflow"""

    print("=" * 70)
    print("Instagram Scraper - Professional Library")
    print("=" * 70)
    print()

    # Get username from user
    username = input("Enter Instagram username (without @): ").strip().lstrip('@')

    if not username:
        print("❌ No username provided!")
        return

    print(f"\n🎯 Target: @{username}\n")

    # Configuration
    config = ScraperConfig(
        headless=False,  # Set True for production
        log_level='INFO',
        log_to_console=True,
        log_file='instagram_scraper.log'
    )

    print("Choose scraping mode:")
    print("1. Complete scrape (profile + posts data)")
    print("2. Profile stats only")
    print("3. Post links only")
    print("4. Quick scrape (all in one)")
    print()

    choice = input("Enter choice (1-4): ").strip()

    try:
        if choice == '1':
            # Complete scrape with orchestrator
            orchestrator = InstagramOrchestrator(config)
            results = orchestrator.scrape_complete_profile(
                username,
                scrape_posts=True,
                export_results=True
            )

            print("\n✅ Complete scraping finished!")
            print(f"📊 Results exported to: instagram_data_{username}.json")

        elif choice == '2':
            # Profile stats only
            scraper = ProfileScraper(config)
            profile = scraper.scrape(username)

            print("\n" + "=" * 70)
            print(f"👤 Profile: @{profile.username}")
            print(f"📸 Posts: {profile.posts}")
            print(f"👥 Followers: {profile.followers}")
            print(f"➕ Following: {profile.following}")
            print("=" * 70)

        elif choice == '3':
            # Post links only
            scraper = PostLinksScraper(config)
            links = scraper.scrape(username, save_to_file=True)

            print(f"\n✅ Collected {len(links)} post/reel links")
            print(f"📁 Saved to: {config.links_file}")

            # Show first 5
            if links:
                print("\n🔗 First 5 links:")
                for i, link_data in enumerate(links[:5], 1):
                    url = link_data['url']
                    content_type = link_data['type']
                    print(f"  {i}. [{content_type}] {url}")

        elif choice == '4':
            # Quick scrape
            print("\n🚀 Quick scrape mode...\n")
            results = quick_scrape(username, config)

            print("\n✅ Quick scrape complete!")
            print(f"Profile: {results['profile']}")
            print(f"Links collected: {len(results['post_links'])}")
            print(f"Posts scraped: {len(results['posts_data'])}")

        else:
            print("❌ Invalid choice!")
            return

    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise


def example_modular_usage():
    """
    Example: Using scrapers individually for specific needs

    This demonstrates library usage where you only need
    specific data (e.g., only likes, only tags, etc.)
    """

    config = ScraperConfig(headless=True)

    # Example 1: Only get followers count
    scraper = ProfileScraper(config)
    profile = scraper.scrape(
        'username',
        get_posts=False,
        get_followers=True,
        get_following=False
    )
    print(f"Followers: {profile.followers}")

    # Example 2: Only get tags from specific posts
    post_scraper = PostDataScraper(config)
    session_data = post_scraper.load_session()
    post_scraper.setup_browser(session_data)

    post_url = "https://www.instagram.com/p/ABC123/"
    data = post_scraper.scrape(
        post_url,
        get_tags=True,
        get_likes=False,
        get_timestamp=False
    )
    print(f"Tagged: {data.tagged_accounts}")

    post_scraper.close()


def example_parallel_usage():
    """
    Example: Parallel execution (future implementation)

    Note: Current implementation is sequential.
    This shows the API design for parallel execution.
    """
    from concurrent.futures import ThreadPoolExecutor

    config = ScraperConfig(headless=True)
    usernames = ['user1', 'user2', 'user3']

    def scrape_profile(username):
        scraper = ProfileScraper(config)
        return scraper.scrape(username)

    # Parallel execution
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(scrape_profile, usernames))

    for result in results:
        print(f"@{result.username}: {result.followers} followers")


if __name__ == '__main__':
    main()
