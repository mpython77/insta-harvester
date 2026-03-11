"""
Example: Instagram Web API — Direct JSON Data Extraction
=========================================================
Uses Playwright's authenticated browser context to access Instagram's
internal API endpoints. Returns accurate, structured data — no DOM scraping.

Endpoints covered:
  - Profile (exact followers/following/posts count)
  - Followers / Following lists (paginated)
  - User Feed (posts with engagement data)
  - Media Info (detailed post info)
  - Comments & Likers
  - Stories, Highlights, Reels
  - Hashtag & Location feeds
  - Friendship status

Requirements:
  pip install instaharvest
  playwright install chrome
  python examples/save_session.py  (one-time login)
"""
import json
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

# ── Setup ──────────────────────────────────────────────
config = ScraperConfig(headless=True)
TARGET = 'mondayswimwear'

with SharedBrowser(config=config) as browser:

    # ══════════════════════════════════════════════════════
    # 1. PROFILE — Exact stats via JSON API
    # ══════════════════════════════════════════════════════
    print("=" * 60)
    print("1️⃣  Profile Data (JSON API)")
    print("=" * 60)

    profile = browser.get_profile_json(TARGET)
    if profile:
        print(f"   Username:    @{profile.username}")
        print(f"   Full Name:   {profile.full_name}")
        print(f"   User ID:     {profile.user_id}")
        print(f"   Followers:   {profile.follower_count:,}")
        print(f"   Following:   {profile.following_count:,}")
        print(f"   Posts:        {profile.media_count:,}")
        print(f"   Verified:    {'✓' if profile.is_verified else '✗'}")
        print(f"   Business:    {'✓' if profile.is_business else '✗'}")
        print(f"   Category:    {profile.category_name}")
        print(f"   Bio:         {profile.biography[:80]}...")
        print(f"   Website:     {profile.external_url}")
        print(f"   Highlights:  {profile.highlight_reel_count}")
        user_id = profile.user_id
    else:
        print("   ❌ Failed to get profile")
        exit(1)

    # ══════════════════════════════════════════════════════
    # 2. FOLLOWERS — Paginated list
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("2️⃣  Followers (first 10)")
    print("=" * 60)

    followers = browser.get_followers_api(user_id, count=10)
    for f in followers.users[:10]:
        print(f"   👤 @{f.username} {'✓' if f.is_verified else ''}")
    print(f"   Has more: {followers.has_more}")

    # ══════════════════════════════════════════════════════
    # 3. FOLLOWING — Who they follow
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("3️⃣  Following (first 10)")
    print("=" * 60)

    following = browser.get_following_api(user_id, count=10)
    for f in following.users[:10]:
        print(f"   👤 @{f.username} {'✓' if f.is_verified else ''}")

    # ══════════════════════════════════════════════════════
    # 4. USER FEED — Posts with engagement
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("4️⃣  User Feed (latest 5 posts)")
    print("=" * 60)

    feed = browser.get_user_feed_api(user_id, count=5)
    for post in feed.posts:
        emoji = "🎬" if post.is_video else "📸"
        print(f"   {emoji} {post.shortcode}: {post.like_count:,} likes, {post.comment_count:,} comments")
        if post.caption:
            print(f"      Caption: {post.caption[:60]}...")

    # ══════════════════════════════════════════════════════
    # 5. MEDIA INFO — Detailed post data
    # ══════════════════════════════════════════════════════
    if feed.posts:
        first_post = feed.posts[0]
        print(f"\n{'='*60}")
        print(f"5️⃣  Media Info ({first_post.shortcode})")
        print("=" * 60)

        media = browser.get_media_info_api(first_post.media_id)
        if media:
            print(f"   Shortcode:  {media.shortcode}")
            print(f"   Likes:      {media.like_count:,}")
            print(f"   Comments:   {media.comment_count:,}")
            print(f"   Type:       {media.media_type}")

        # ──────────────────────────────────────────────────
        # 6. COMMENTS
        # ──────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"6️⃣  Comments ({first_post.shortcode})")
        print("=" * 60)

        comments = browser.get_media_comments_api(first_post.media_id)
        for c in comments.comments[:5]:
            print(f"   💬 @{c.username}: {c.text[:50]}...")

        # ──────────────────────────────────────────────────
        # 7. LIKERS
        # ──────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"7️⃣  Likers ({first_post.shortcode})")
        print("=" * 60)

        likers = browser.get_media_likers_api(first_post.media_id)
        for l in likers.likers[:5]:
            print(f"   ❤️ @{l.username}")
        print(f"   Total: {likers.total_count:,}")

    # ══════════════════════════════════════════════════════
    # 8. FRIENDSHIP STATUS
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("8️⃣  Friendship Status")
    print("=" * 60)

    status = browser.get_friendship_status(user_id)
    print(f"   Following:   {status.following}")
    print(f"   Followed by: {status.followed_by}")
    print(f"   Blocking:    {status.blocking}")

    # ══════════════════════════════════════════════════════
    # 9. STORIES
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("9️⃣  Stories")
    print("=" * 60)

    stories = browser.get_stories_api(user_id)
    if stories:
        for s in stories[:5]:
            print(f"   📖 Story {s.story_id}: type={'video' if s.media_type == 2 else 'image'}")
    else:
        print("   No active stories")

    # ══════════════════════════════════════════════════════
    # 10. HIGHLIGHTS
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("🔟  Highlights")
    print("=" * 60)

    highlights = browser.get_highlights_api(user_id)
    for h in highlights.highlights[:5]:
        print(f"   ✨ {h.title} ({h.media_count} items)")
    print(f"   Total: {highlights.total_count}")

    # ══════════════════════════════════════════════════════
    # 11. REELS
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("1️⃣1️⃣  Reels")
    print("=" * 60)

    reels = browser.get_reels_api(user_id)
    for r in reels.reels[:5]:
        print(f"   🎬 {r.shortcode}: {r.play_count:,} plays, {r.like_count:,} likes")

    # ══════════════════════════════════════════════════════
    # 12. HASHTAG FEED
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("1️⃣2️⃣  Hashtag Feed (#swimwear)")
    print("=" * 60)

    hashtag = browser.get_hashtag_feed_api('swimwear')
    print(f"   Posts found: {len(hashtag.posts)}")
    for p in hashtag.posts[:3]:
        print(f"   #️⃣ {p.get('shortcode', 'N/A')}: {p.get('like_count', 0):,} likes")

    # ══════════════════════════════════════════════════════
    # 13. RAW API — Any endpoint
    # ══════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("1️⃣3️⃣  Raw API Access")
    print("=" * 60)

    raw = browser.fetch_raw_api(f'/api/v1/users/{user_id}/info/')
    if raw:
        user = raw.get('user', {})
        print(f"   Raw username: {user.get('username')}")
        print(f"   Raw full_name: {user.get('full_name')}")

    # ══════════════════════════════════════════════════════
    # SUMMARY
    # ══════════════════════════════════════════════════════
    api = browser.web_api
    print(f"\n{'='*60}")
    print(f"📊 Done! Total API requests: {api.request_count}")
    print("=" * 60)
