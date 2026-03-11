import sys
import os
sys.path.insert(0, os.path.abspath("."))
from instaharvest import ScraperConfig
from instaharvest.comment_scraper import CommentScraper

def main():
    config = ScraperConfig(headless=False, session_file=r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json')
    scraper = CommentScraper(config)
    try:
        print("Scraping...")
        res = scraper.scrape("https://www.instagram.com/p/DVqxdFnACFs/", target_count=10, include_replies=True)
        print(f"Total Comments Scraped: {res.total_comments_scraped}")
        import json
        with open("comments_out.json", "w", encoding="utf-8") as f:
            f.write(json.dumps(res.to_dict(), ensure_ascii=False, indent=2))
        print("Saved to comments_out.json")
    except Exception as e:
        print("Error:", e)
    finally:
        scraper.close()
        
if __name__ == "__main__":
    main()
