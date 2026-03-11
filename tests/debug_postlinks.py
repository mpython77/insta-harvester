"""Debug PostLinksScraper — isolated test"""
import sys, os, traceback
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from instaharvest import ScraperConfig, ProfileScraper, PostLinksScraper, ReelLinksScraper

config = ScraperConfig(headless=True, session_file=r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json')

ps = ProfileScraper(config=config)
session_data = ps.load_session()
ps.setup_browser(session_data)

# === PostLinksScraper ===
print("=== PostLinksScraper ===")
try:
    s = PostLinksScraper(config=config)
    s.page = ps.page; s.browser = ps.browser; s.context = ps.context
    result = s.scrape('mondayswimwear', target_count=3, save_to_file=False)
    print(f"TYPE: {type(result)}")
    print(f"LEN: {len(result)}")
    for i, link in enumerate(result[:3]):
        t = type(link).__name__
        print(f"  [{i}] type={t} value={link}")
        if isinstance(link, dict):
            url = link.get('url', 'N/A')
            tp = link.get('type', 'N/A')
            print(f"       url={url[:60]} type={tp}")
        elif isinstance(link, str):
            print(f"       str={link[:60]}")
    print("PostLinksScraper: PASS")
except Exception as e:
    print(f"PostLinksScraper: FAIL - {type(e).__name__}: {e}")
    traceback.print_exc()

import time; time.sleep(2)

# === ReelLinksScraper ===
print("\n=== ReelLinksScraper ===")
try:
    s2 = ReelLinksScraper(config=config)
    s2.page = ps.page; s2.browser = ps.browser; s2.context = ps.context
    result2 = s2.scrape('mondayswimwear', save_to_file=False)
    print(f"TYPE: {type(result2)}")
    print(f"LEN: {len(result2)}")
    for i, link in enumerate(result2[:3]):
        t = type(link).__name__
        print(f"  [{i}] type={t} value={str(link)[:80]}")
    print("ReelLinksScraper: PASS")
except Exception as e:
    print(f"ReelLinksScraper: FAIL - {type(e).__name__}: {e}")
    traceback.print_exc()

ps.cleanup()
print("\nDONE")
