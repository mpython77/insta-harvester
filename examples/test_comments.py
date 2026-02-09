#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Comment Scraping Test Script
Run this to test the comment scraping functionality

Usage:
    python examples/test_comments.py

Requirements:
    - Instagram session must be saved first (run save_session.py)
    - playwright must be installed (pip install playwright && playwright install chrome)
"""

import sys
import os

# ALWAYS prioritize local development version if available
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if os.path.exists(os.path.join(parent_dir, 'instaharvest')):
    sys.path.insert(0, parent_dir)

from instaharvest import InstagramOrchestrator, CommentScraper
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file


def test_comment_scraping_basic():
    """
    Test 1: Basic comment scraping from a single post
    """
    print("\n" + "="*60)
    print("TEST 1: Basic Comment Scraping")
    print("="*60)

    session_file = find_session_file()
    if session_file:
         print(f"✅ Found session: {session_file}")
         config = ScraperConfig(headless=False, session_file=session_file)
    else:
         print("⚠️  No session file found, using default...")
         config = ScraperConfig(headless=False)
    scraper = CommentScraper(config=config)

    try:
        # Load session
        session_data = scraper.load_session()
        scraper.setup_browser(session_data)

        # Test with a public post (replace with actual post URL)
        test_url = input("Enter a post URL to test (e.g., https://www.instagram.com/p/ABC123/): ").strip()

        if not test_url:
            print("No URL provided, skipping test")
            return False

        print(f"\nScraping comments from: {test_url}")
        print("Max comments: 10 (for quick test)")

        # Scrape with limit
        result = scraper.scrape(
            test_url,
            max_comments=10,
            include_replies=True
        )

        # Print results
        print(f"\n{'='*40}")
        print("RESULTS:")
        print(f"{'='*40}")
        print(f"Total comments scraped: {result.total_comments_scraped}")
        print(f"Total replies scraped: {result.total_replies_scraped}")
        print(f"Scraping duration: {result.scraping_duration_seconds}s")

        print(f"\n{'='*40}")
        print("COMMENTS:")
        print(f"{'='*40}")

        for i, comment in enumerate(result.comments, 1):
            print(f"\n[{i}] @{comment.author.username}")
            print(f"    Text: {comment.text[:100]}{'...' if len(comment.text) > 100 else ''}")
            print(f"    Likes: {comment.likes_count}")
            print(f"    Time: {comment.timestamp}")
            print(f"    Replies: {len(comment.replies)}")

            # Show replies
            for j, reply in enumerate(comment.replies[:3], 1):  # Show max 3 replies
                print(f"      ↳ [{j}] @{reply.author.username}: {reply.text[:50]}...")

        print(f"\n✅ TEST 1 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        return False
    finally:
        scraper.close()


def test_orchestrator_comments():
    """
    Test 2: Comment scraping via Orchestrator
    """
    print("\n" + "="*60)
    print("TEST 2: Orchestrator Comment Scraping")
    print("="*60)

    session_file = find_session_file()
    if session_file:
         print(f"✅ Found session: {session_file}")
         config = ScraperConfig(headless=False, session_file=session_file)
    else:
         print("⚠️  No session file found, using default...")
         config = ScraperConfig(headless=False)
    orchestrator = InstagramOrchestrator(config)

    try:
        username = input("Enter username to test (e.g., instagram): ").strip()

        if not username:
            print("No username provided, skipping test")
            return False

        print(f"\nScraping comments from @{username}'s posts")
        print("This will scrape posts first, then comments")

        # Use scrape_comments_only for faster test
        results = orchestrator.scrape_comments_only(
            username,
            max_comments_per_post=5,  # Limit for quick test
            include_replies=True,
            save_excel=True,
            export_json=True
        )

        print(f"\n{'='*40}")
        print("RESULTS:")
        print(f"{'='*40}")
        print(f"Total posts processed: {results['total_posts']}")
        print(f"Total comments: {results['total_comments']}")
        print(f"Total replies: {results['total_replies']}")

        print(f"\n✅ TEST 2 PASSED!")
        return True

    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        return False


def test_export_functions():
    """
    Test 3: Export functions (no browser needed)
    """
    print("\n" + "="*60)
    print("TEST 3: Export Functions (No Browser)")
    print("="*60)

    try:
        from instaharvest.models import CommentData, CommentAuthor
        from instaharvest.comment_scraper import PostCommentsData
        from instaharvest.exporters import export_comments_to_json, export_comments_to_excel

        # Create test data
        author = CommentAuthor(
            username="test_user",
            profile_url="https://instagram.com/test_user/",
            profile_picture_url="",
            is_verified=False
        )

        comment = CommentData(
            id="123456",
            author=author,
            text="This is a test comment!",
            timestamp="January 14, 2026",
            timestamp_iso="2026-01-14T12:00:00Z",
            likes_count=42,
            reply_count=2,
            permalink="https://instagram.com/p/ABC123/c/123456/",
            is_reply=False,
            replies=[]
        )

        post_comments = PostCommentsData(
            post_url="https://instagram.com/p/ABC123/",
            post_id="ABC123",
            total_comments_scraped=1,
            total_replies_scraped=0,
            comments=[comment]
        )

        # Test JSON export
        print("\nTesting JSON export...")
        export_comments_to_json(post_comments, "test_comments.json")
        print("✅ JSON export successful: test_comments.json")

        # Test Excel export
        print("\nTesting Excel export...")
        export_comments_to_excel(post_comments, "test_comments.xlsx")
        print("✅ Excel export successful: test_comments.xlsx")

        # Verify files exist
        import os
        if os.path.exists("test_comments.json") and os.path.exists("test_comments.xlsx"):
            print(f"\n✅ TEST 3 PASSED!")

            # Cleanup
            os.remove("test_comments.json")
            os.remove("test_comments.xlsx")
            print("(Test files cleaned up)")
            return True
        else:
            print(f"\n❌ TEST 3 FAILED: Files not created")
            return False

    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Run all tests
    """
    print("\n" + "="*60)
    print("COMMENT SCRAPING TEST SUITE")
    print("="*60)
    print("\nThis script tests the comment scraping functionality.")
    print("Make sure you have:")
    print("  1. Saved Instagram session (run save_session.py first)")
    print("  2. Installed playwright (pip install playwright)")
    print("  3. Installed Chrome browser (playwright install chrome)")

    print("\n" + "-"*60)
    print("Available tests:")
    print("  1. Basic comment scraping (single post)")
    print("  2. Orchestrator comment scraping (profile)")
    print("  3. Export functions (no browser)")
    print("  4. Run all tests")
    print("-"*60)

    choice = input("\nSelect test (1-4): ").strip()

    results = {}

    if choice == "1":
        results["Basic"] = test_comment_scraping_basic()
    elif choice == "2":
        results["Orchestrator"] = test_orchestrator_comments()
    elif choice == "3":
        results["Export"] = test_export_functions()
    elif choice == "4":
        results["Export"] = test_export_functions()
        results["Basic"] = test_comment_scraping_basic()
        results["Orchestrator"] = test_orchestrator_comments()
    else:
        print("Invalid choice")
        return

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"  {name}: {status}")

    all_passed = all(results.values())
    print(f"\n{'✅ ALL TESTS PASSED!' if all_passed else '❌ SOME TESTS FAILED'}")


if __name__ == "__main__":
    main()
