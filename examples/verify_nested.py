import sys
import os

# Force loading local package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from instaharvest import CommentScraper
from instaharvest.config import ScraperConfig

def verify():
    config = ScraperConfig(headless=False)
    scraper = CommentScraper(config=config)
    
    try:
        session = scraper.load_session()
        scraper.setup_browser(session)
        
        # URL provided by user
        url = "https://www.instagram.com/p/DTLHDJpDAbO/"
        print(f"Scraping {url}...")
        
        result = scraper.scrape(url, max_comments=30, include_replies=True)
        
        print(f"\nTotal Top-Level Comments: {len(result.comments)}")
        print(f"Total Replies Scraped: {result.total_replies_scraped}")
        
        found_nested = False
        for c in result.comments:
            if c.reply_count > 0 or len(c.replies) > 0:
                print(f"\nParent: {c.author.username} | Extracted Count: {c.reply_count} | Actual List Len: {len(c.replies)}")
                if len(c.replies) > 0:
                    found_nested = True
                    for r in c.replies:
                         print(f"  -> {r.author.username}: {r.text[:30]}...")
        
        if not found_nested:
            print("\n❌ NO nested replies found in the actual list objects!")
        else:
            print("\n✅ Verified: Nested replies are present in the objects.")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        scraper.close()

if __name__ == "__main__":
    verify()
