"""Debug CommentScraper — isolated test"""
import sys, os, traceback
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from instaharvest import ScraperConfig, ProfileScraper, CommentScraper

config = ScraperConfig(headless=True, session_file=r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json')

ps = ProfileScraper(config=config)
session_data = ps.load_session()
ps.setup_browser(session_data)

print("=== CommentScraper (scrape_stream) ===")
try:
    s = CommentScraper(config=config)
    s.page = ps.page; s.browser = ps.browser; s.context = ps.context
    comments = []
    for comment in s.scrape_stream('https://www.instagram.com/p/DFqW7OdNjyF/', target_count=5):
        comments.append(comment)
        print(f"  COMMENT: @{comment.author.username}: {comment.text[:60]}...")
    print(f"  TOTAL: {len(comments)} comments")
    print(f"  RESULT: {'PASS' if len(comments) > 0 else 'FAIL'}")
except Exception as e:
    print(f"  FAIL: {type(e).__name__}: {e}")
    traceback.print_exc()

ps.cleanup()
print("DONE")
