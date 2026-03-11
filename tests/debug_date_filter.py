"""Test date range filter with PostLinksScraper"""
import sys, os
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from instaharvest import ScraperConfig, ProfileScraper, PostLinksScraper

config = ScraperConfig(headless=True, session_file=r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json')

ps = ProfileScraper(config=config)
session = ps.load_session()
ps.setup_browser(session)

# Post links with date range: March 7-11
print("=== PostLinksScraper: date_from='2025-03-07', date_to='2025-03-11' ===")
s = PostLinksScraper(config=config)
s.page = ps.page; s.browser = ps.browser; s.context = ps.context

result = s.scrape(
    'instagram',
    target_count=30,
    date_from='2026-03-07',
    date_to='2026-03-11',
    save_to_file=False
)

print(f"\n=== RESULTS ===")
print(f"Total links in range: {len(result)}")
for i, link in enumerate(result):
    if isinstance(link, dict):
        print(f"  [{i+1}] {link.get('url','')[:60]} type={link.get('type','')}")
    else:
        print(f"  [{i+1}] {str(link)[:60]}")

try:
    ps.close()
except:
    pass
print("\nDONE")
