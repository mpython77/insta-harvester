import sys
import os
sys.path.insert(0, os.path.abspath("."))
from instaharvest import ScraperConfig
from instaharvest.comment_scraper import CommentScraper

def main():
    config = ScraperConfig(headless=False, session_file=r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json')
    scraper = CommentScraper(config)
    
    # We override inner method temporarily to just save HTML
    original_smart_scroll = scraper._smart_scroll
    
    def mock_scroll():
        html = scraper.page.content()
        with open("comments_dom.html", "w", encoding="utf-8") as f:
             f.write(html)
        print("DOM saved. Exiting.")
        scraper.close()
        exit(0)
        
    scraper._smart_scroll = mock_scroll
    
    try:
        scraper.scrape("https://www.instagram.com/p/DVqxdFnACFs/", target_count=5)
    except Exception as e:
        print(e)
        
if __name__ == "__main__":
    main()
