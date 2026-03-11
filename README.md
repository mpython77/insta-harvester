# InstaHarvest 🌾

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/instaharvest)](https://pypi.org/project/instaharvest/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/instaharvest)](https://pypi.org/project/instaharvest/)
[![GitHub stars](https://img.shields.io/github/stars/mpython77/insta-harvester)](https://github.com/mpython77/insta-harvester/stargazers)

**Professional Instagram Data Collection Toolkit** — Powerful library for Instagram automation, data collection, and analytics built on Playwright.

> 📖 [Documentation](#-api-reference) |
> 🐛 [Report Bug](https://github.com/mpython77/insta-harvester/issues) |
> 💡 [Request Feature](https://github.com/mpython77/insta-harvester/issues) |
> 📋 [Changelog](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md)

---

## ✨ Features

| Category | Capabilities |
|----------|-------------|
| 📊 **Profile** | Stats, verified badge, category, full bio, external links, Threads |
| 🔌 **Web API** | 16+ JSON endpoints — profiles, followers, feed, comments, reels, stories, hashtags |
| 📸 **Content** | Posts, Reels, Stories, Highlights, Tagged Posts — with JSON-first architecture |
| 💬 **Engagement** | Comments (with replies), likes, media download (images/videos via yt-dlp) |
| 👥 **Social** | Followers/Following lists, Follow/Unfollow, Direct Messaging |
| 🔍 **Discovery** | Search, Hashtag feeds, Location feeds, Explore, Notifications |
| ⚡ **Performance** | Parallel processing, SharedBrowser (1 browser for all), Excel export |
| 🛡️ **Reliability** | Rate limiting, graceful shutdown (Ctrl+C), auto-save, retry logic |

---

## 🚀 Installation & Setup

```bash
# Install from PyPI
pip install instaharvest
playwright install chrome

# OR install from GitHub (latest dev version)
git clone https://github.com/mpython77/insta-harvester.git
cd insta-harvester
pip install -r requirements.txt
playwright install chrome
```

**Create Instagram session (required, one-time):**

```python
from instaharvest import save_session
save_session()
# Browser opens → Login manually → Press ENTER → Session saved ✅
```

> ⚠️ Without `instagram_session.json`, the library won't work.

---

## 📖 Quick Start — SharedBrowser (Recommended)

**One browser for ALL operations** — fastest and most efficient way to use InstaHarvest.

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # ── Profile ──
    profile = browser.scrape_profile("username")
    print(f"{profile.full_name}: {profile.followers} followers")

    # ── Social Actions ──
    browser.follow("user1")
    browser.send_message("user1", "Hello!")
    followers = browser.get_followers("user2", limit=100)

    # ── Content Scraping ──
    post = browser.scrape_post("https://www.instagram.com/p/ABC/")
    reel = browser.scrape_reel("https://www.instagram.com/reel/XYZ/")
    stories = browser.scrape_stories("username")
    comments = browser.scrape_comments("https://www.instagram.com/p/ABC/")

    # ── Discovery ──
    results = browser.search("fashion brands")
    hashtag = browser.scrape_hashtag("streetwear")
    notifs = browser.read_notifications()

    # ── Batch Operations ──
    posts = browser.scrape_posts(["url1", "url2", "url3"])
    files = browser.download_post("https://www.instagram.com/p/ABC/")

    # ── Web API (Direct JSON — exact data) ──
    profile_json = browser.get_profile_json("username")
    print(f"Exact followers: {profile_json.follower_count:,}")

    feed = browser.get_user_feed_api(profile_json.user_id, count=5)
    reels = browser.get_reels_api(profile_json.user_id)
    highlights = browser.get_highlights_api(profile_json.user_id)
```

---

## 📚 API Reference

### 1. Profile Scraping

```python
from instaharvest import ProfileScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = ProfileScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

profile = scraper.scrape('username')
print(f"Posts: {profile.posts}, Followers: {profile.followers}")
print(f"Verified: {profile.is_verified}, Category: {profile.category}")
print(f"Bio: {profile.bio}, Links: {profile.external_links}")

scraper.close()
```

### 2. Followers / Following

```python
from instaharvest import FollowersCollector
from instaharvest.config import ScraperConfig

config = ScraperConfig()
collector = FollowersCollector(config=config)
session_data = collector.load_session()
collector.setup_browser(session_data)

followers = collector.get_followers('username', limit=100, print_realtime=True)
following = collector.get_following('username', limit=50)

collector.close()
```

### 3. Follow / Unfollow & Direct Messaging

```python
from instaharvest import FollowManager, MessageManager
from instaharvest.config import ScraperConfig

config = ScraperConfig()

# Follow
manager = FollowManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)
manager.follow('username')
manager.batch_follow(['user1', 'user2', 'user3'])
manager.close()

# DM
messenger = MessageManager(config=config)
session_data = messenger.load_session()
messenger.setup_browser(session_data)
messenger.send_message('username', 'Hello!')
messenger.batch_send(['user1', 'user2'], 'Hi there!')
messenger.close()
```

### 4. Post & Reel Data (JSON-First)

```python
from instaharvest import PostDataScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = PostDataScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

post = scraper.scrape('https://www.instagram.com/p/DVs7LK-iO0C/')

# 30+ fields extracted automatically from JSON
print(post.like_count, post.comment_count)     # Engagement
print(post.caption, post.tagged_accounts)       # Content
print(post.location.name if post.location else 'N/A')  # Location
print(post.owner.username if post.owner else 'N/A')     # Owner

for slide in post.carousel_slides:              # Carousel
    print(f"  Slide {slide.slide_index}: {slide.media_type}")

scraper.close()
```

### 5. Comment Scraping

```python
from instaharvest import CommentScraper
from instaharvest.exporters import export_comments_to_json, export_comments_to_excel
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = CommentScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

result = scraper.scrape(
    'https://www.instagram.com/p/POST_ID/',
    max_comments=100,
    include_replies=True
)

for comment in result.comments:
    print(f"@{comment.author.username}: {comment.text}")
    for reply in comment.replies:
        print(f"  ↳ @{reply.author.username}: {reply.text}")

# Export
export_comments_to_json(result, 'comments.json')
export_comments_to_excel(result, 'comments.xlsx')

scraper.close()
```

### 6. Stories & Highlights

```python
from instaharvest import StoryScraper, HighlightsScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()

# Stories — JSON-first, per-slide tag mapping
scraper = StoryScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

result = scraper.scrape('username', extract_tags=True)
print(f"Stories: {result.story_count}, Tags: {result.all_tagged_accounts}")
for slide in result.slides:
    print(f"  Slide {slide.slide_index}: [{slide.media_type}] {slide.timestamp} → {slide.tagged_accounts}")

scraper.close()

# Highlights — mentions, links, music, locations
hl_scraper = HighlightsScraper(config=config)
session = hl_scraper.load_session()
hl_scraper.setup_browser(session)

full = hl_scraper.scrape_all('mondayswimwear', max_slides_per=100)
print(f"{full.total_highlights} highlights, {full.total_slides} total slides")

hl_scraper.close()
```

### 7. Parallel Processing & Orchestrator

```python
from instaharvest import SharedBrowser, InstagramOrchestrator
from instaharvest.config import ScraperConfig

config = ScraperConfig(headless=True)

with SharedBrowser(config=config) as browser:
    orch = InstagramOrchestrator(config, shared_browser=browser)

    results = orch.scrape_complete_profile_advanced(
        'username',
        parallel=3,
        save_excel=True,
        scrape_comments=True,
        scrape_stories=True
    )
    print(f"Scraped {len(results['posts_data'])} posts")
```

### 8. Tagged Posts

```python
from instaharvest import TaggedPostsScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = TaggedPostsScraper(config=config)
session = scraper.load_session()
scraper.setup_browser(session)

result = scraper.scrape('mondayswimwear', max_posts=100)
print(f"Total: {result.total_found} tagged posts, Unique taggers: {result.unique_taggers}")
for post in result.tagged_posts:
    print(f"  @{post.owner} → {post.url} ({post.media_type})")

scraper.close()
```

### 9. Notifications

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

config = ScraperConfig()
with SharedBrowser(config=config) as browser:
    notifs = browser.read_notifications()
    print(f"Total: {len(notifs)} notifications")
```

**Notification types:** `follow`, `post_like`, `comment_like`, `comment`, `mention`, `follow_request`, `follow_accepted`, `thread`, `story`, `system`

### 10. Media Download

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

config = ScraperConfig()
with SharedBrowser(config=config) as browser:
    # Handles images, videos, reels, carousels automatically
    files = browser.download_post("https://www.instagram.com/reel/C-example...")
    print(f"Downloaded {len(files)} files")
```

> 🔧 **Video support** requires Google Chrome (`browser_channel='chrome'`, the default). Chromium lacks video codecs.

---

## 🔌 Web API — Direct JSON Data Extraction

Access Instagram's internal API endpoints directly through Playwright. Returns **exact, structured data** — no DOM scraping.

> **16+ endpoints** | **15 data models** | **Auto-pagination** | **Rate limiting** | **POST + GET support**

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

config = ScraperConfig(headless=True)

with SharedBrowser(config=config) as browser:
    # ── Profile (exact stats) ──
    profile = browser.get_profile_json('mondayswimwear')
    print(f"{profile.full_name}: {profile.follower_count:,} followers")
    user_id = profile.user_id

    # ── Followers / Following ──
    followers = browser.get_followers_api(user_id, count=50)
    following = browser.get_following_api(user_id, count=50)

    # ── Feed, Comments, Likers ──
    feed = browser.get_user_feed_api(user_id, count=12)
    comments = browser.get_media_comments_api(feed.posts[0].media_id)
    likers = browser.get_media_likers_api(feed.posts[0].media_id)

    # ── Stories, Highlights, Reels ──
    stories = browser.get_stories_api(user_id)
    highlights = browser.get_highlights_api(user_id)
    reels = browser.get_reels_api(user_id)

    # ── Hashtag & Location ──
    hashtag = browser.get_hashtag_feed_api('swimwear')
    location = browser.get_location_feed_api('213385402')

    # ── Raw API (any endpoint, GET or POST) ──
    raw = browser.fetch_raw_api('/api/v1/users/1059031072/info/')
```

**Available Endpoints:**

| Method | Description | Returns |
|--------|-------------|--------|
| `get_profile_json(username)` | Profile with exact stats | `WebProfileData` |
| `get_user_info(user_id)` | Profile by ID | `WebProfileData` |
| `get_followers_api(id, count)` | Followers list (paginated) | `FollowListResult` |
| `get_following_api(id, count)` | Following list (paginated) | `FollowListResult` |
| `get_friendship_status(id)` | Follow relationship | `FriendshipStatus` |
| `get_user_feed_api(id, count)` | User's posts | `UserFeedResult` |
| `get_media_info_api(media_id)` | Detailed post info | `MediaInfo` |
| `get_media_comments_api(id)` | Post comments | `CommentsResult` |
| `get_media_likers_api(id)` | Post likers | `LikersResult` |
| `get_stories_api(id)` | Active stories | `List[StoryMediaItem]` |
| `get_highlights_api(id)` | Highlights list | `HighlightsResult` |
| `get_reels_api(id)` | Reels with plays | `ReelsResult` |
| `get_hashtag_feed_api(tag)` | Hashtag posts | `HashtagSection` |
| `get_location_feed_api(id)` | Location posts | `LocationSection` |
| `get_tagged_posts_api(id)` | Tagged posts | `UserFeedResult` |
| `fetch_raw_api(endpoint)` | Any endpoint (GET/POST) | `Dict` |

**Direct API access (without SharedBrowser):**

```python
from instaharvest import InstagramWebAPI
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(storage_state='instagram_session.json')
    page = context.new_page()
    page.goto('https://www.instagram.com/')

    api = InstagramWebAPI(page=page)
    profile = api.get_profile('mondayswimwear')
    print(f"{profile.follower_count:,} followers")

    browser.close()
```

---

## 🎯 Complete Workflow Example

```python
from instaharvest import SharedBrowser, InstagramOrchestrator
from instaharvest.config import ScraperConfig

config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # 1. Profile analysis
    profile = browser.scrape_profile('target_user')
    print(f"📊 {profile.full_name}: {profile.followers} followers")

    # 2. Collect & follow
    followers = browser.get_followers('target_user', limit=50)
    for f in followers[:10]:
        browser.follow(f)

    # 3. Scrape posts
    post_links = browser.scrape_post_links('target_user')
    posts = browser.scrape_posts([l['url'] for l in post_links[:5]])

    # 4. Stories + Web API
    stories = browser.scrape_stories('target_user')
    profile_json = browser.get_profile_json('target_user')
    reels = browser.get_reels_api(profile_json.user_id)

    # 5. Full orchestrated scrape
    orch = InstagramOrchestrator(config, shared_browser=browser)
    results = orch.scrape_complete_profile_advanced(
        'target_user', parallel=3,
        save_excel=True, scrape_stories=True
    )
    print(f"✅ {len(results['posts_data'])} posts scraped")
```

---

## 📁 Project Structure

<details>
<summary><b>🗂️ Package Structure</b></summary>

```
insta-harvester/
├── instaharvest/              # Main package
│   ├── __init__.py            # Package entry point
│   ├── base.py                # Base scraper class
│   ├── config.py              # Configuration
│   ├── profile.py             # Profile scraping
│   ├── followers.py           # Followers collection
│   ├── follow.py              # Follow/unfollow
│   ├── message.py             # Direct messaging
│   ├── post_data.py           # Post data (JSON-first)
│   ├── reel_data.py           # Reel data extraction
│   ├── comment_scraper.py     # Comments with replies
│   ├── story_scraper.py       # Story scraping
│   ├── highlight_scraper.py   # Highlights extraction
│   ├── tagged_posts.py        # Tagged posts
│   ├── notifications.py       # Notification reader
│   ├── web_api.py             # 🔌 Web API (16+ endpoints)
│   ├── shared_browser.py      # SharedBrowser
│   ├── orchestrator.py        # Workflow orchestrator
│   ├── parallel_scraper.py    # Parallel processing
│   ├── downloader.py          # Media download
│   └── ...                    # More modules
├── examples/
│   ├── save_session.py        # Session setup
│   ├── all_in_one.py          # Interactive demo
│   ├── main_advanced.py       # Production scraping
│   ├── example_web_api.py     # 🔌 Web API demo
│   └── example_custom_config.py
├── tests/                     # 130+ unit tests
└── LICENSE                    # MIT License
```

</details>

---

## ⚙️ Configuration

```python
from instaharvest import ScraperConfig

config = ScraperConfig(
    headless=True,              # Run without browser UI
    viewport_width=1920,
    viewport_height=1080,
    default_timeout=30000,      # 30 seconds
    max_scroll_attempts=50,
    log_level='INFO',
    # Rate limiting
    follow_delay_min=10.0,
    follow_delay_max=15.0,
    message_delay_min=15.0,
    message_delay_max=20.0,
)
```

See [Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md) for all options.

---

## 🔧 Troubleshooting

<details>
<summary><b>🔍 Common Issues & Solutions</b></summary>

| Problem | Solution |
|---------|----------|
| `playwright command not found` | `pip install playwright && playwright install chrome` |
| `No module named 'instaharvest'` | `pip install instaharvest` or `pip install -e .` |
| `Session file not found` | Run `save_session()` first |
| `Login required / Session expired` | Re-run `save_session()` |
| `Instagram says 'Try again later'` | Increase rate limiting delays in config |
| `Could not follow/unfollow` | Increase `popup_open_delay` and `action_delay_*` |
| `Slow internet errors` | Increase `page_load_delay` and `scroll_delay_*` |
| `Posts: 0 but content exists` | Update to latest version (v2.7.1+) |

**Getting Help:**
- [GitHub Issues](https://github.com/mpython77/insta-harvester/issues)
- [Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md)
- Email: <kelajak054@gmail.com>

</details>

---

## ⚠️ Disclaimer

This tool is for educational purposes only. Follow Instagram's Terms of Service, respect rate limits, and use responsibly.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions welcome! Submit a [Pull Request](https://github.com/mpython77/insta-harvester/pulls).

---

**Made with ❤️ by Muydinov Doston**

*Happy Harvesting! 🌾*
