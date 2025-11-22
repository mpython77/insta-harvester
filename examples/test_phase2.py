"""
Test Phase 2: Reel Data Extraction
Tests the extraction of tags, likes, and dates from reels
"""

from instaharvest import PostDataScraper, ScraperConfig

def test_reel_extraction():
    """Test reel data extraction"""
    print("=" * 70)
    print("PHASE 2 TEST: Reel Data Extraction")
    print("=" * 70)
    print()

    # Get reel URL
    reel_url = input("Enter Instagram reel URL to test: ").strip()

    if not reel_url or '/reel/' not in reel_url:
        print("❌ Invalid reel URL!")
        return

    print(f"\n🎯 Testing with reel: {reel_url}\n")

    # Configuration
    config = ScraperConfig(
        headless=False,
        log_level='INFO',
        log_to_console=True
    )

    try:
        # Test PostDataScraper with reel
        scraper = PostDataScraper(config)
        scraper.load_session()
        scraper.setup_browser(scraper.load_session())

        try:
            data = scraper.scrape(reel_url)

            print("\n" + "=" * 70)
            print("✅ REEL EXTRACTION TEST COMPLETE!")
            print("=" * 70)
            print(f"Content Type: {data.content_type}")
            print(f"Likes: {data.likes}")
            print(f"Date: {data.timestamp}")
            print(f"Tagged Accounts: {data.tagged_accounts}")
            print(f"Tags Count: {len(data.tagged_accounts)}")
            print("=" * 70)

            # Test against expected
            print("\n🔍 Verification:")
            print(f"  ✓ Content type is 'Reel': {data.content_type == 'Reel'}")
            print(f"  ✓ Likes extracted: {data.likes != 'N/A'}")
            print(f"  ✓ Date extracted: {data.timestamp != 'N/A'}")
            print(f"  ✓ Tags extraction attempted: {data.tagged_accounts is not None}")

            print("\n📋 Full Data:")
            print(data.to_dict())

        finally:
            scraper.close()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

def test_mixed_content():
    """Test with both posts and reels"""
    print("=" * 70)
    print("PHASE 2 TEST: Mixed Content (Posts + Reels)")
    print("=" * 70)
    print()

    # Get URLs
    print("Enter URLs (one per line, empty line to finish):")
    urls = []
    while True:
        url = input(f"  URL {len(urls) + 1}: ").strip()
        if not url:
            break
        urls.append(url)

    if not urls:
        print("❌ No URLs provided!")
        return

    print(f"\n🎯 Testing with {len(urls)} URLs\n")

    # Configuration
    config = ScraperConfig(
        headless=False,
        log_level='INFO',
        log_to_console=True
    )

    try:
        # Test PostDataScraper with multiple URLs
        scraper = PostDataScraper(config)
        results = scraper.scrape_multiple(urls, delay_between_posts=True)

        print("\n" + "=" * 70)
        print("✅ MIXED CONTENT TEST COMPLETE!")
        print("=" * 70)
        print(f"Total URLs: {len(urls)}")
        print(f"Successfully scraped: {len(results)}")

        # Count by type
        posts = sum(1 for r in results if r.content_type == 'Post')
        reels = sum(1 for r in results if r.content_type == 'Reel')
        print(f"  📸 Posts: {posts}")
        print(f"  🎬 Reels: {reels}")

        print("\n📋 Results:")
        for i, data in enumerate(results, 1):
            print(f"\n  {i}. [{data.content_type}] {data.url}")
            print(f"     Likes: {data.likes}")
            print(f"     Date: {data.timestamp}")
            print(f"     Tags: {len(data.tagged_accounts)} - {data.tagged_accounts[:3]}...")

        print("\n" + "=" * 70)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("Select test mode:")
    print("  1. Test single reel")
    print("  2. Test mixed content (posts + reels)")
    choice = input("\nChoice (1-2): ").strip()

    if choice == '1':
        test_reel_extraction()
    elif choice == '2':
        test_mixed_content()
    else:
        print("❌ Invalid choice!")
