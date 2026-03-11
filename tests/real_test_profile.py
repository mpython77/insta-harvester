"""
REAL Integration Test #1 — ProfileScraper
Tests against a real public profile
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from instaharvest import ProfileScraper, ScraperConfig

# Session file path — absolute
SESSION_FILE = r'c:\Users\TROLL\Desktop\All\My_Scripts\MY_Library\instagram_session.json'

config = ScraperConfig(
    headless=True,
    session_file=SESSION_FILE
)
scraper = ProfileScraper(config=config)

try:
    result = scraper.scrape('cristiano')
    
    print("=" * 60)
    print("PROFILE SCRAPER RESULTS")
    print("=" * 60)
    print(f"Username: {result.username}")
    print(f"Full name: {result.full_name}")
    print(f"Followers: {result.followers}")
    print(f"Following: {result.following}")
    print(f"Posts: {result.posts_count}")
    print(f"Is verified: {result.is_verified}")
    print(f"Is private: {result.is_private}")
    print(f"Category: {result.category}")
    print(f"Bio: {result.bio[:100]}..." if result.bio and len(result.bio) > 100 else f"Bio: {result.bio}")
    print(f"External URL: {result.external_url}")
    print(f"Profile pic: {'Yes' if result.profile_pic_url else 'No'}")
    
    # Validation 
    errors = []
    if not result.username:
        errors.append("username is empty!")
    if result.followers == 0:
        errors.append("followers is 0!")
    if result.posts_count == 0:
        errors.append("posts_count is 0!")
    if not result.is_verified:
        errors.append("is_verified should be True for cristiano!")
    if result.is_private:
        errors.append("is_private should be False!")
    if not result.full_name:
        errors.append("full_name is empty!")
    
    if errors:
        print("\n❌ VALIDATION ERRORS:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\n✅ ALL VALIDATIONS PASSED!")
    
    d = result.to_dict()
    json_str = json.dumps(d, ensure_ascii=False, indent=2)
    print(f"\nJSON serializable: ✅ ({len(json_str)} chars)")
    
except Exception as e:
    print(f"\n❌ FATAL ERROR: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
