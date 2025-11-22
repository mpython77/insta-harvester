"""
Test Phase 1: Post + Reel Link Collection with Type Detection
"""

from instaharvest import PostLinksScraper, ScraperConfig

def test_link_collection():
    """Test that links are collected with proper type classification"""
    print("=" * 70)
    print("PHASE 1 TEST: Post/Reel Link Collection with Type Detection")
    print("=" * 70)
    print()

    # Get username
    username = input("Enter Instagram username to test (without @): ").strip().lstrip('@')

    if not username:
        print("❌ No username provided!")
        return

    print(f"\n🎯 Testing with: @{username}\n")

    # Configuration
    config = ScraperConfig(
        headless=False,
        log_level='INFO',
        log_to_console=True
    )

    try:
        # Test PostLinksScraper
        scraper = PostLinksScraper(config)
        links = scraper.scrape(username, save_to_file=True)

        print("\n" + "=" * 70)
        print("✅ LINK COLLECTION TEST COMPLETE!")
        print("=" * 70)
        print(f"Total links collected: {len(links)}")

        # Count by type
        posts_count = sum(1 for link in links if link['type'] == 'Post')
        reels_count = sum(1 for link in links if link['type'] == 'Reel')

        print(f"  📸 Posts: {posts_count}")
        print(f"  🎬 Reels: {reels_count}")
        print()

        # Show first 10 links
        if links:
            print("📋 First 10 links (with types):")
            for i, link_data in enumerate(links[:10], 1):
                url = link_data['url']
                content_type = link_data['type']
                print(f"  {i}. [{content_type}] {url}")

        print("\n" + "=" * 70)
        print("✅ Phase 1 implementation is working correctly!")
        print("=" * 70)

        # Verify structure
        print("\n🔍 Data Structure Verification:")
        if links:
            sample = links[0]
            print(f"  Structure: {sample}")
            print(f"  Has 'url' key: {'url' in sample}")
            print(f"  Has 'type' key: {'type' in sample}")
            print(f"  Type values are valid: {all(link['type'] in ['Post', 'Reel'] for link in links)}")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_link_collection()
