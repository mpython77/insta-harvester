"""
Instagram Scraper - FULL AUTOMATIC SCRAPING
Professional version with complete automation

Just enter username - everything else is automatic!
Features:
- Collects ALL post links from main profile (Phase 1)
- Collects ALL reel links from /reels/ page (SEPARATE - Phase 1.5)
- Extracts data from each post/reel (Phase 2)
- Advanced diagnostics
- Error recovery
- Performance monitoring
- Real-time Excel export with Type column
- Parallel processing (posts only, reels sequential)
"""

import multiprocessing
from instagram_scraper import InstagramOrchestrator, ScraperConfig


def main():
    """
    FULL AUTOMATIC SCRAPING

    Simply enter Instagram username and the scraper will:
    1. Collect ALL post links from main profile
    2. Collect ALL reel links from /reels/ page (SEPARATE!)
    3. Extract tags, likes, dates from each post/reel
    4. Save to Excel with Type column (Post/Reel)
    5. Generate detailed statistics
    6. Monitor performance & errors
    """
    # Required for Windows multiprocessing support
    multiprocessing.freeze_support()

    print("=" * 70)
    print("🚀 INSTAGRAM SCRAPER - PROFESSIONAL FULL AUTO MODE")
    print("=" * 70)
    print()
    print("✨ Features:")
    print("  ✅ Automatic post link collection (from main profile)")
    print("  ✅ Automatic reel link collection (from /reels/ page - SEPARATE!)")
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
        # Phase 1: Collect post links from main profile
        # Phase 1.5: Collect reel links from /reels/ page (SEPARATE!)
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
        total_links = len(results.get('post_links', [])) + len(results.get('reel_links', []))
        print(f"   Total: {total_links} items")
        print(f"   - Posts: {len(results.get('post_links', []))}")
        print(f"   - Reels: {len(results.get('reel_links', []))}")

        print()
        print(f"📝 Data Extracted:")
        total_scraped = len(results.get('posts_data', [])) + len(results.get('reels_data', []))
        print(f"   Total Scraped: {total_scraped} items")

        # Count successful extractions for posts
        posts_success = 0
        if results.get('posts_data'):
            posts_success = sum(1 for item in results['posts_data'] if item.get('likes') != 'ERROR')
            print(f"   Posts Successful: {posts_success}/{len(results['posts_data'])} ({posts_success/len(results['posts_data'])*100:.1f}%)")

        # Count successful extractions for reels
        reels_success = 0
        if results.get('reels_data'):
            reels_success = sum(1 for item in results['reels_data'] if item.get('likes') != 'ERROR')
            print(f"   Reels Successful: {reels_success}/{len(results['reels_data'])} ({reels_success/len(results['reels_data'])*100:.1f}%)")

        # Overall success rate
        if total_scraped > 0:
            overall_success = posts_success + reels_success
            print(f"   Overall: {overall_success}/{total_scraped} ({overall_success/total_scraped*100:.1f}%)")

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
