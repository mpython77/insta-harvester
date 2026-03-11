"""Quick test: ReelLinksScraper with target_count=20"""
import sys, os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from instaharvest import ScraperConfig, ProfileScraper, ReelLinksScraper, PostLinksScraper

config = ScraperConfig(headless=True, session_file=r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json')

ps = ProfileScraper(config=config)
session = ps.load_session()
ps.setup_browser(session)

# Test 1: ReelLinksScraper with target_count=20
print("=== ReelLinksScraper target_count=20 ===")
s = ReelLinksScraper(config=config)
s.page = ps.page; s.browser = ps.browser; s.context = ps.context
result = s.scrape('mondayswimwear', target_count=20, save_to_file=False)
print(f"  Collected: {len(result)} reels")
print(f"  PASS: {len(result) <= 20}")
for i, url in enumerate(result[:5]):
    print(f"  [{i+1}] {url[:60]}...")

import time; time.sleep(2)

# Test 2: PostLinksScraper with target_count=10
print("\n=== PostLinksScraper target_count=10 ===")
s2 = PostLinksScraper(config=config)
s2.page = ps.page; s2.browser = ps.browser; s2.context = ps.context
result2 = s2.scrape('mondayswimwear', target_count=10, save_to_file=False)
print(f"  Collected: {len(result2)} posts")
print(f"  PASS: {len(result2) <= 10}")
for i, link in enumerate(result2[:5]):
    if isinstance(link, dict):
        print(f"  [{i+1}] {link.get('url','')[:50]} type={link.get('type','')}")
    else:
        print(f"  [{i+1}] {str(link)[:60]}")

try:
    ps.close()
except:
    pass
print("\nDONE")
