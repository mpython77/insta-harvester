"""
Instagram Scraper - FULL AUTOMATIC SCRAPING
Professional version with complete automation

Just enter username - everything else is automatic!
Features:
- Collects ALL post & reel links (Phase 1)
- Extracts data from each post/reel (Phase 2)
- Advanced diagnostics
- Error recovery
- Performance monitoring
- Real-time Excel export
- Parallel processing
"""

import multiprocessing
from instagram_scraper import InstagramOrchestrator, ScraperConfig


def main():
    """
    FULL AUTOMATIC SCRAPING

    Simply enter Instagram username and the scraper will:
    1. Collect ALL post & reel links from profile
    2. Extract tags, likes, dates from each post/reel
    3. Save to Excel with Type column (Post/Reel)
    4. Generate detailed statistics
    5. Monitor performance & errors
    """
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()

    print("=" * 70)
    print("🚀 INSTAGRAM SCRAPER - PROFESSIONAL FULL AUTO MODE")
    print("=" * 70)
    print()
    print("✨ Features:")
    print("  ✅ Automatic post & reel link collection")
    print("  ✅ Smart data extraction (posts + reels)")
    print("  ✅ Real-time Excel export with Type column")
    print("  ✅ HTML diagnostics & error recovery")
    print("  ✅ Performance monitoring")
    print("  ✅ Parallel processing (3 tabs)")
    print()
    print("=" * 70)
    print()

    # Get username - ONLY input needed!
    username = input("📝 Enter Instagram username (without @): ").strip().lstrip('@')

    if not username:
        print("❌ No username provided!")
        return

    print(f"\n🎯 Target: @{username}")
    print()
    print("⚙️  Configuration (OPTIMIZED):")
    print("   - Parallel: 3 tabs (fast & stable)")
    print("   - Excel: Real-time export")
    print("   - Diagnostics: Enabled")
    print("   - Error Recovery: Enabled")
    print("   - Performance Monitoring: Enabled")
    print()
    print("=" * 70)
    print()

    confirm = input("🚀 Press ENTER to start FULL AUTO SCRAPING (or 'q' to quit): ").strip()
    if confirm.lower() == 'q':
        print("❌ Cancelled.")
        return

    print()
    print("=" * 70)
    print("🚀 STARTING FULL AUTOMATIC SCRAPING...")
    print("=" * 70)
    print()

    # Optimized configuration for production
    config = ScraperConfig(
        headless=False,  # Visual mode for monitoring
        log_level='INFO',
        log_to_console=True,
        log_file=f'instagram_scraper_{username}.log'
    )

    try:
        # Create orchestrator with professional features
        orchestrator = InstagramOrchestrator(config)

        # FULL AUTOMATIC SCRAPING
        # Phase 1: Collect links (posts + reels)
        # Phase 2: Extract data with diagnostics & error recovery
        # Phase 3: Save to Excel + JSON
        results = orchestrator.scrape_complete_profile_advanced(
            username,
            parallel=3,          # 3 parallel tabs (optimal)
            save_excel=True,     # Real-time Excel export
            export_json=True     # JSON backup
        )

        # Display final summary
        print()
        print("=" * 70)
        print("✅ FULL AUTOMATIC SCRAPING COMPLETE!")
        print("=" * 70)
        print()
        print("📊 RESULTS:")
        print("-" * 70)
        print(f"👤 Username: @{results['username']}")
        print()
        print(f"📈 Profile Stats:")
        print(f"   Total Posts: {results['profile']['posts']}")
        print(f"   Followers: {results['profile']['followers']}")
        print(f"   Following: {results['profile']['following']}")
        print()
        print(f"🔗 Links Collected:")
        print(f"   Total: {len(results['post_links'])} items")

        # Count posts vs reels
        if results['post_links']:
            posts_count = sum(1 for link in results['post_links'] if link.get('type') == 'Post')
            reels_count = sum(1 for link in results['post_links'] if link.get('type') == 'Reel')
            print(f"   - Posts: {posts_count}")
            print(f"   - Reels: {reels_count}")

        print()
        print(f"📝 Data Extracted:")
        print(f"   Total Scraped: {len(results['posts_data'])} items")

        # Count successful extractions
        if results['posts_data']:
            success = sum(1 for item in results['posts_data'] if item.get('likes') != 'ERROR')
            print(f"   Successful: {success}/{len(results['posts_data'])} ({success/len(results['posts_data'])*100:.1f}%)")

        print()
        print("💾 Output Files:")
        print(f"   📊 Excel: instagram_data_{username}.xlsx")
        print(f"   📄 JSON: instagram_data_{username}.json")
        print(f"   📋 Log: instagram_scraper_{username}.log")
        print()
        print("=" * 70)
        print()
        print("🎉 All done! Check the Excel file for complete data.")
        print()

    except KeyboardInterrupt:
        print()
        print()
        print("=" * 70)
        print("⚠️  SCRAPING INTERRUPTED (Ctrl+C)")
        print("=" * 70)
        print()
        print("✅ Partial data has been saved.")
        print(f"💾 Check: instagram_data_{username}.xlsx and .json")
        print()

    except Exception as e:
        print()
        print("=" * 70)
        print("❌ ERROR OCCURRED")
        print("=" * 70)
        print()
        print(f"Error: {e}")
        print()
        print("💡 Tips:")
        print("  - Make sure you have a valid Instagram session")
        print("  - Check if the username exists")
        print("  - Check the log file for details")
        print()

        import traceback
        print("📋 Full Error Details:")
        print("-" * 70)
        traceback.print_exc()
        print("-" * 70)


if __name__ == '__main__':
    main()
