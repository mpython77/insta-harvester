"""
Test Professional Instagram Scraper
Tests all advanced features: diagnostics, error handling, performance monitoring
"""

from instaharvest import PostDataScraper, ScraperConfig

def test_professional_scraper():
    """Test professional scraper with all features"""
    print("=" * 70)
    print("PROFESSIONAL INSTAGRAM SCRAPER TEST")
    print("=" * 70)
    print()
    print("Features:")
    print("  ✅ Advanced HTML diagnostics")
    print("  ✅ Intelligent error recovery")
    print("  ✅ Performance monitoring")
    print("  ✅ Memory optimization")
    print("  ✅ Detailed statistics")
    print("=" * 70)
    print()

    # Get test URLs
    print("Enter test URLs (mix of posts and reels):")
    print("(Enter empty line when done)")
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
        # Create professional scraper with diagnostics enabled
        scraper = PostDataScraper(config, enable_diagnostics=True)

        # Scrape all URLs with full monitoring
        results = scraper.scrape_multiple(
            urls,
            get_tags=True,
            get_likes=True,
            get_timestamp=True,
            delay_between_posts=True
        )

        print("\n" + "=" * 70)
        print("✅ TEST COMPLETE!")
        print("=" * 70)
        print(f"\nResults Summary:")
        print(f"  Total: {len(results)}")
        print(f"  Success: {sum(1 for r in results if r.likes != 'ERROR')}")
        print(f"  Failed: {sum(1 for r in results if r.likes == 'ERROR')}")

        # Show sample results
        print("\n📋 Sample Results (first 3):")
        for i, data in enumerate(results[:3], 1):
            print(f"\n  {i}. [{data.content_type}] {data.url}")
            print(f"     Likes: {data.likes}")
            print(f"     Date: {data.timestamp}")
            print(f"     Tags: {len(data.tagged_accounts)} - {data.tagged_accounts[:3]}")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def test_single_with_diagnostics():
    """Test single URL with full diagnostics"""
    print("=" * 70)
    print("SINGLE URL DIAGNOSTIC TEST")
    print("=" * 70)
    print()

    url = input("Enter Instagram URL (post or reel): ").strip()
    if not url:
        print("❌ No URL provided!")
        return

    print(f"\n🔍 Running full diagnostics on: {url}\n")

    config = ScraperConfig(
        headless=False,
        log_level='DEBUG',  # More detailed logs
        log_to_console=True
    )

    try:
        scraper = PostDataScraper(config, enable_diagnostics=True)
        scraper.load_session()
        scraper.setup_browser(scraper.load_session())

        try:
            # Scrape with full diagnostics
            data = scraper.scrape(url)

            print("\n" + "=" * 70)
            print("✅ DIAGNOSTIC TEST COMPLETE!")
            print("=" * 70)
            print(f"\nExtracted Data:")
            print(f"  Type: {data.content_type}")
            print(f"  Likes: {data.likes}")
            print(f"  Date: {data.timestamp}")
            print(f"  Tags: {data.tagged_accounts}")
            print("=" * 70)

        finally:
            scraper.close()

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main test menu"""
    print("\n🚀 Professional Instagram Scraper - Test Suite\n")
    print("Select test mode:")
    print("  1. Test multiple URLs (full statistics)")
    print("  2. Test single URL (detailed diagnostics)")
    print()

    choice = input("Choice (1-2): ").strip()

    if choice == '1':
        test_professional_scraper()
    elif choice == '2':
        test_single_with_diagnostics()
    else:
        print("❌ Invalid choice!")


if __name__ == '__main__':
    main()
