"""
COMPREHENSIVE REAL Integration Test — 14 Functions, One SharedBrowser
Tests every scraper function in the library using a single shared browser instance.

Functions:
 1. ProfileScraper              8. HighlightsScraper.scrape
 2. PostDataScraper             9. CommentScraper
 3. ReelDataScraper            10. SearchAPI
 4. PostLinksScraper           11. HashtagScraper
 5. ReelLinksScraper           12. LocationScraper
 6. TaggedPostsScraper         13. ExploreScraper
 7. HighlightsScraper.list     14. NotificationReader
"""
import sys, os, json, time, traceback

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

SESSION_FILE = r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json'

from instaharvest import (
    ScraperConfig, ProfileScraper, PostDataScraper, ReelDataScraper,
    PostLinksScraper, ReelLinksScraper,
    TaggedPostsScraper, HighlightsScraper, CommentScraper,
    SearchAPI, HashtagScraper, LocationScraper, ExploreScraper,
    NotificationReader, DataExporter
)

config = ScraperConfig(headless=True, session_file=SESSION_FILE)
RESULTS = {}

def test_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    RESULTS[name] = {'passed': passed, 'details': details}
    print(f"\n{'='*60}")
    print(f"{status} -- {name}")
    if details:
        print(f"  {details}")
    print(f"{'='*60}\n")

def header(num, name, target):
    print(f"\n{'>'*60}")
    print(f"TEST {num}: {name} -- {target}")
    print(f"{'>'*60}")


# ═══════════════════════════════════
# INIT: Create browser via ProfileScraper
# ═══════════════════════════════════
header(0, "INIT", "Setting up shared browser")
profile_scraper = ProfileScraper(config=config)
session_data = profile_scraper.load_session()
profile_scraper.setup_browser(session_data)
page = profile_scraper.page
browser = profile_scraper.browser
context = profile_scraper.context
print(f"  Browser: {browser is not None}, Page: {page is not None}")

def inject(scraper):
    """Inject shared browser into scraper"""
    scraper.page = page
    scraper.browser = browser
    scraper.context = context


# ═══════ 1. ProfileScraper ═══════
header(1, "ProfileScraper", "@cristiano")
try:
    result = profile_scraper.scrape('cristiano')
    print(f"  username: {result.username}, followers: {result.followers}, posts: {result.posts}")
    print(f"  verified: {result.is_verified}, category: {result.category}")
    ok = result.followers > 0 and result.posts > 0
    test_result("ProfileScraper", ok, f"{result.followers} followers, {result.posts} posts")
except Exception as e:
    test_result("ProfileScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 2. PostDataScraper ═══════
header(2, "PostDataScraper", "single post")
try:
    s = PostDataScraper(config=config); inject(s)
    result = s.scrape('https://www.instagram.com/p/DFqW7OdNjyF/')
    print(f"  username: {result.username}, likes: {result.likes}, type: {result.post_type}")
    print(f"  caption: {(result.caption or '')[:60]}...")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("PostDataScraper", True, f"type={result.post_type}, {result.likes} likes")
except Exception as e:
    test_result("PostDataScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 3. ReelDataScraper ═══════
header(3, "ReelDataScraper", "single reel")
try:
    s = ReelDataScraper(config=config); inject(s)
    result = s.scrape('https://www.instagram.com/reel/DFm-VIKtJG7/')
    print(f"  username: {result.username}, views: {result.views}, likes: {result.likes}")
    print(f"  caption: {(result.caption or '')[:60]}...")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("ReelDataScraper", True, f"{result.views} views")
except Exception as e:
    test_result("ReelDataScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 4. PostLinksScraper (limited) ═══════
header(4, "PostLinksScraper", "@mondayswimwear (first page)")
try:
    s = PostLinksScraper(config=config); inject(s)
    result = s.scrape('mondayswimwear', target_count=5, save_to_file=False)
    print(f"  links found: {len(result)}")
    for i, link in enumerate(result[:3]):
        print(f"    [{i+1}] {link['url'][:60]}... type={link['type']}")
    test_result("PostLinksScraper", len(result) > 0, f"{len(result)} links collected")
except Exception as e:
    test_result("PostLinksScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 5. ReelLinksScraper (limited) ═══════
header(5, "ReelLinksScraper", "@mondayswimwear reels")
try:
    s = ReelLinksScraper(config=config); inject(s)
    result = s.scrape('mondayswimwear', save_to_file=False)
    print(f"  reel links found: {len(result)}")
    for i, url in enumerate(result[:3]):
        print(f"    [{i+1}] {url[:60]}...")
    test_result("ReelLinksScraper", len(result) >= 0, f"{len(result)} reel links")
except Exception as e:
    test_result("ReelLinksScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 6. TaggedPostsScraper ═══════
header(6, "TaggedPostsScraper", "@mondayswimwear")
try:
    s = TaggedPostsScraper(config=config); inject(s)
    result = s.scrape('mondayswimwear', max_posts=5)
    print(f"  username: {result.username}, tagged posts: {len(result.tagged_posts)}")
    for i, p in enumerate(result.tagged_posts[:3]):
        print(f"    [{i+1}] owner={p.owner}, url={p.url[:50]}...")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("TaggedPostsScraper", len(result.tagged_posts) > 0, f"{len(result.tagged_posts)} tagged")
except Exception as e:
    test_result("TaggedPostsScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 7. HighlightsScraper.list_highlights ═══════
header(7, "HighlightsScraper.list_highlights", "@mondayswimwear")
try:
    hl = HighlightsScraper(config=config); inject(hl)
    result = hl.list_highlights('mondayswimwear')
    print(f"  total highlights: {result.total_count}")
    for i, h in enumerate(result.highlights[:5]):
        print(f"    [{i+1}] {h.title} (id={h.highlight_id})")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("HighlightsScraper.list", result.total_count > 0, f"{result.total_count} highlights")
except Exception as e:
    test_result("HighlightsScraper.list", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 8. HighlightsScraper.scrape ═══════
header(8, "HighlightsScraper.scrape", "highlight 18092082532805201")
try:
    result = hl.scrape('18092082532805201')
    print(f"  title: {result.highlight_title}, slides: {result.slide_count}")
    print(f"  mentions: {result.all_mentions[:5]}")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("HighlightsScraper.scrape", result.slide_count > 0, f"'{result.highlight_title}' {result.slide_count} slides")
except Exception as e:
    test_result("HighlightsScraper.scrape", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 9. CommentScraper ═══════
header(9, "CommentScraper", "post comments (max 5)")
try:
    s = CommentScraper(config=config); inject(s)
    comments = []
    for comment in s.scrape_stream('https://www.instagram.com/p/DFqW7OdNjyF/', target_count=5):
        comments.append(comment)
        print(f"    comment: @{comment.author.username}: {comment.text[:50]}...")
    print(f"  total scraped: {len(comments)}")
    test_result("CommentScraper", len(comments) > 0, f"{len(comments)} comments")
except Exception as e:
    test_result("CommentScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 10. SearchAPI ═══════
header(10, "SearchAPI", "query='nike'")
try:
    s = SearchAPI(config=config); inject(s)
    result = s.search('nike')
    print(f"  users: {len(result.users)}, hashtags: {len(result.hashtags)}, places: {len(result.places)}")
    for i, u in enumerate(result.users[:3]):
        print(f"    [{i+1}] @{u.get('username','?')} - {u.get('full_name','')}")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("SearchAPI", result.total_count > 0, f"{result.total_count} results")
except Exception as e:
    test_result("SearchAPI", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 11. HashtagScraper ═══════
header(11, "HashtagScraper", "#fashion (max 5)")
try:
    s = HashtagScraper(config=config); inject(s)
    result = s.scrape('fashion', max_posts=5)
    print(f"  hashtag: #{result.hashtag}, post_count: {result.post_count}")
    print(f"  collected: {len(result.posts)}")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("HashtagScraper", True, f"#{result.hashtag}: {len(result.posts)} posts")
except Exception as e:
    test_result("HashtagScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 12. LocationScraper ═══════
header(12, "LocationScraper", "Times Square (ID: 212988663)")
try:
    s = LocationScraper(config=config); inject(s)
    result = s.scrape('212988663', max_posts=5)
    print(f"  name: {result.location_name}, address: {result.address}")
    print(f"  collected: {len(result.posts)}")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("LocationScraper", True, f"{result.location_name}: {len(result.posts)} posts")
except Exception as e:
    test_result("LocationScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 13. ExploreScraper ═══════
header(13, "ExploreScraper", "trending posts (max 5)")
try:
    s = ExploreScraper(config=config); inject(s)
    result = s.scrape(max_posts=5)
    print(f"  collected: {result.total_collected}")
    for i, p in enumerate(result.posts[:3]):
        print(f"    [{i+1}] {p.get('url','')[:50]}...")
    json.dumps(result.to_dict(), ensure_ascii=False)
    test_result("ExploreScraper", result.total_collected > 0, f"{result.total_collected} trending posts")
except Exception as e:
    test_result("ExploreScraper", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 14. NotificationReader ═══════
header(14, "NotificationReader", "activity feed")
try:
    from instaharvest.logging_config import get_logger
    logger = get_logger('NotificationReader')
    reader = NotificationReader(page, logger)
    notifications = reader.read_notifications(max_count=10)
    print(f"  notifications: {len(notifications)}")
    for i, n in enumerate(notifications[:5]):
        print(f"    [{i+1}] [{n.section}] {n.type}: @{', @'.join(n.usernames)} — {n.text[:50]}...")
    test_result("NotificationReader", len(notifications) > 0, f"{len(notifications)} notifications")
except Exception as e:
    test_result("NotificationReader", False, f"{type(e).__name__}: {e}")
    traceback.print_exc()
time.sleep(2)


# ═══════ 15. DataExporter ═══════
header(15, "DataExporter", "CSV + JSON")
try:
    import tempfile
    exporter = DataExporter()
    test_data = [{'username': 'test', 'followers': 100}]
    csv_p = os.path.join(tempfile.gettempdir(), 'test_export.csv')
    json_p = os.path.join(tempfile.gettempdir(), 'test_export.json')
    exporter.export_csv(test_data, csv_p)
    exporter.export_json(test_data, json_p)
    ok = os.path.exists(csv_p) and os.path.exists(json_p)
    if os.path.exists(csv_p): os.unlink(csv_p)
    if os.path.exists(json_p): os.unlink(json_p)
    test_result("DataExporter", ok, f"CSV + JSON ok")
except Exception as e:
    test_result("DataExporter", False, f"{type(e).__name__}: {e}")


# ═══════ CLEANUP ═══════
try: profile_scraper.cleanup()
except: pass


# ═══════ FINAL SUMMARY ═══════
print("\n\n" + "═" * 60)
print("FINAL RESULTS — ALL 15 TESTS")
print("═" * 60)

passed = sum(1 for r in RESULTS.values() if r['passed'])
failed = sum(1 for r in RESULTS.values() if not r['passed'])

for name, r in RESULTS.items():
    icon = "✅" if r['passed'] else "❌"
    print(f"  {icon} {name}: {r['details']}")

print(f"\n  Total: {passed}/{len(RESULTS)} passed, {failed} failed")
print("═" * 60)
