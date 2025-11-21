"""
Instagram Scraper - Advanced Main Example
Complete workflow with parallel processing and Excel export
"""

import multiprocessing
from instagram_scraper import InstagramOrchestrator, ScraperConfig


def main():
    """Main function - advanced scraping with all features"""
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()

    print("=" * 70)
    print("Instagram Scraper - ADVANCED (Parallel + Excel)")
    print("=" * 70)
    print()

    # Get username
    username = input("Enter Instagram username (without @): ").strip().lstrip('@')

    if not username:
        print("❌ No username provided!")
        return

    print(f"\n🎯 Target: @{username}\n")

    # Get parallel option
    print("Parallel processing (faster scraping):")
    print("  1 = Sequential (one by one)")
    print("  2 = 2 parallel tabs")
    print("  3 = 3 parallel tabs (recommended)")
    print("  5 = 5 parallel tabs (fastest)")
    parallel_input = input("\nEnter number of parallel tabs (default=1): ").strip()

    try:
        parallel = int(parallel_input) if parallel_input else None
    except ValueError:
        parallel = None

    # Get Excel option
    excel_input = input("\nSave to Excel in real-time? (y/n, default=n): ").strip().lower()
    save_excel = excel_input == 'y'

    print("\n" + "=" * 70)
    print(f"Configuration:")
    print(f"  Username: @{username}")
    print(f"  Parallel: {parallel if parallel else 'Sequential (1)'}")
    print(f"  Excel Export: {'Yes' if save_excel else 'No'}")
    print("=" * 70)
    print()

    input("Press ENTER to start scraping...")
    print()

    # Configuration
    config = ScraperConfig(
        headless=False,  # Set True for production
        log_level='INFO',
        log_to_console=True,
        log_file='instagram_scraper.log'
    )

    try:
        # Create orchestrator
        orchestrator = InstagramOrchestrator(config)

        # Run advanced scraping
        results = orchestrator.scrape_complete_profile_advanced(
            username,
            parallel=parallel,
            save_excel=save_excel,
            export_json=True
        )

        # Summary
        print("\n" + "=" * 70)
        print("✅ SCRAPING COMPLETE!")
        print("=" * 70)
        print(f"👤 Username: @{results['username']}")
        print(f"📊 Profile:")
        print(f"   Posts: {results['profile']['posts']}")
        print(f"   Followers: {results['profile']['followers']}")
        print(f"   Following: {results['profile']['following']}")
        print(f"📁 Post Links: {len(results['post_links'])}")
        print(f"📝 Posts Scraped: {len(results['posts_data'])}")
        print()

        if save_excel:
            print(f"💾 Excel: instagram_data_{username}.xlsx")

        print(f"💾 JSON: instagram_data_{username}.json")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


def example_quick_usage():
    """Quick usage example"""
    from instagram_scraper import InstagramOrchestrator, ScraperConfig

    config = ScraperConfig(headless=True)
    orchestrator = InstagramOrchestrator(config)

    # Simple call with all features
    results = orchestrator.scrape_complete_profile_advanced(
        'dindinku__',
        parallel=3,        # 3 parallel tabs
        save_excel=True,   # Real-time Excel export
        export_json=True   # JSON export
    )

    print(f"Scraped {len(results['posts_data'])} posts")
    print(f"Excel saved: instagram_data_dindinku__.xlsx")


def example_parallel_only():
    """Example: Only parallel processing, no Excel"""
    from instagram_scraper import InstagramOrchestrator

    orchestrator = InstagramOrchestrator()

    results = orchestrator.scrape_complete_profile_advanced(
        'cristiano',
        parallel=5,         # Fast! 5 parallel tabs
        save_excel=False,   # No Excel
        export_json=True
    )

    return results


def example_excel_only():
    """Example: Only Excel export, no parallel"""
    from instagram_scraper import InstagramOrchestrator

    orchestrator = InstagramOrchestrator()

    results = orchestrator.scrape_complete_profile_advanced(
        'cristiano',
        parallel=None,      # Sequential
        save_excel=True,    # Real-time Excel
        export_json=False
    )

    return results


def example_library_usage():
    """Example: Use as library - parallel scraper only"""
    from instagram_scraper import ParallelPostDataScraper, ScraperConfig

    config = ScraperConfig(headless=True)
    scraper = ParallelPostDataScraper(config)

    post_urls = [
        'https://www.instagram.com/p/ABC123/',
        'https://www.instagram.com/p/DEF456/',
        'https://www.instagram.com/p/GHI789/',
    ]

    # Parallel scrape
    results = scraper.scrape_multiple(
        post_urls,
        parallel=3  # 3 tabs
    )

    for data in results:
        print(f"{data.url}: {data.likes} likes, {len(data.tagged_accounts)} tags")


if __name__ == '__main__':
    main()
