# InstaHarvest 🌾

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/instaharvest)](https://pypi.org/project/instaharvest/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Downloads](https://img.shields.io/pypi/dm/instaharvest)](https://pypi.org/project/instaharvest/)
[![GitHub issues](https://img.shields.io/github/issues/mpython77/insta-harvester)](https://github.com/mpython77/insta-harvester/issues)
[![GitHub stars](https://img.shields.io/github/stars/mpython77/insta-harvester)](https://github.com/mpython77/insta-harvester/stargazers)

**Professional Instagram Data Collection Toolkit** - A powerful and efficient library for Instagram automation, data collection, and analytics.

> 📖 [Documentation](https://github.com/mpython77/insta-harvester#readme) |
> 🐛 [Report Bug](https://github.com/mpython77/insta-harvester/issues) |
> 💡 [Request Feature](https://github.com/mpython77/insta-harvester/issues) |
> 🤝 [Contributing](https://github.com/mpython77/insta-harvester/blob/main/CONTRIBUTING.md) |
> 📋 [Changelog](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md)

---

## ✨ Features

- 📊 **Profile Statistics** - Collect followers, following, posts count
- ✓ **Verified Badge Check** - Detect if account has verified badge
- 🎭 **Profile Category** - Extract profile category (Actor, Model, Photographer, etc.)
- 📝 **Complete Bio** - Extract full bio with links, emails, mentions, and contact info
- 🔗 **Post & Reel Links** - Intelligent scrolling and link collection (Post vs Reel detection)
- 📥 **Media Download** - Download Images & Videos (High Quality + yt-dlp support)
- 🎬 **Reel Data** - Specialized scraping for Reels (views, plays, distinct metrics)
- 🏷️ **Tagged Accounts** - Extract tags from posts and reels (popup & container support)
- 💬 **Comment Scraping** - Full comment extraction with likes, replies, author info
- 👥 **Followers/Following** - Collect lists with real-time output
- 💬 **Direct Messaging** - Send DMs with smart rate limiting
- 🤝 **Follow/Unfollow** - Manage following with rate limiting
- ⚡ **Parallel Processing** - Scrape multiple posts simultaneously
- 🛡️ **Graceful Shutdown** - Safe interruption (Ctrl+C) with auto-save
- 📑 **Excel Export** - Real-time data export to Excel
- 🌐 **Shared Browser** - Single browser for all operations
- 🔍 **HTML Detection** - Automatic structure change detection
- 📝 **Professional Logging** - Comprehensive logging system
- 🔔 **Notification Reader** - Read, filter, and analyze activity feed notifications
- 📸 **Story Scraper** - Extract tagged accounts from stories with per-slide mapping & timestamps
- 🏷️ **Tagged Posts Scraper** - Discover who tags an account: owner, thumbnail, type per post
- 🌟 **Highlights Scraper** - Full highlight slide extraction with mentions, links, music, locations
- 🧬 **JSON-First Architecture** - Instant data extraction from pre-loaded JSON (30+ fields: location, caption, owner, carousel slides, engagement)

---

## 🚀 Installation

<details>
<summary><b>📦 Method 1: Install from PyPI (Recommended)</b> - Click to expand</summary>

```bash
# Install the package
pip install instaharvest

# Install Playwright browser
playwright install chrome
```

</details>

<details>
<summary><b>🔧 Method 2: Install from GitHub (Latest Development Version)</b> - Click to expand</summary>

#### Step 1: Clone the Repository

```bash
git clone https://github.com/mpython77/insta-harvester.git
cd insta-harvester
```

#### Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Playwright browser
playwright install chrome
```

#### Step 3: Install Package in Development Mode (Optional)

```bash
# Install as editable package
pip install -e .
```

**OR** simply use it without installation:

```bash
# ⚡ Run directly from source (Intelligent Session Discovery included)
python examples/save_session.py
```

</details>

---

## 🔧 Complete Setup Guide

<details>
<summary><b>📋 Step-by-Step Setup Instructions</b> - Click to expand</summary>

### Step 1: Verify Python Installation

```bash
# Check Python version (requires 3.8+)
python --version

# Should show: Python 3.8.0 or higher
```

### Step 2: Install InstaHarvest

**From GitHub:**

```bash
git clone https://github.com/mpython77/insta-harvester.git
cd insta-harvester
pip install -r requirements.txt
playwright install chrome
```

**From PyPI:**

```bash
pip install instaharvest
playwright install chrome
```

### Step 3: Create Instagram Session (REQUIRED!)

**Option A: Using Python (Recommended)** ⭐

```python
from instaharvest import save_session
save_session()
```

**Option B: Using Example Script**

```bash
# Navigate to examples directory
cd examples

# Run session setup script
python save_session.py
```

This will:

1. Open Chrome browser
2. Navigate to Instagram
3. Let you log in manually
4. Save your session to `instagram_session.json`
5. All future scripts will use this session (no re-login needed!)

**Important:** Without this session file, the library won't work!

### Step 4: Test Your Setup

```bash
# First, create your Instagram session (required!)
python examples/save_session.py

# Try the all-in-one interactive demo (recommended for learning)
python examples/all_in_one.py

# Or try production scraping
python examples/main_advanced.py
```

</details>

---

> **⚠️ IMPORTANT: Always Use ScraperConfig!**
> All examples below use `ScraperConfig()` for proper timing and reliability.
> Even when using default settings, explicitly creating config is **best practice**.
> This prevents timing issues with popups, buttons, and rate limits.
> See [Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md) for customization options.

## 🚀 First-Time Setup

Before using any features, create an Instagram session (one-time setup):

```python
from instaharvest import save_session

# Create session - this will open a browser
save_session()

# Follow the prompts:
# 1. Browser will open automatically
# 2. Login to Instagram manually
# 3. Press ENTER in terminal when done
# 4. Session saved to instagram_session.json ✅
```

That's it! Now you can use all library features. The session will be reused automatically.

---

## 📖 Quick Start Examples

<details>
<summary><b>Example 1: Follow a User</b> - Click to expand</summary>

```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

# Create config (customize if needed)
config = ScraperConfig()

# Create manager with config
manager = FollowManager(config=config)

# Load session
session_data = manager.load_session()
manager.setup_browser(session_data)

# Follow someone
result = manager.follow("instagram")
print(result)  # {'success': True, 'status': 'followed', ...}

# Clean up
manager.close()
```

</details>

<details>
<summary><b>Example 2: Send Direct Message</b> - Click to expand</summary>

```python
from instaharvest import MessageManager
from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()
manager = MessageManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

# Send message
result = manager.send_message("username", "Hello from Python!")
print(result)

manager.close()
```

</details>

<details>
<summary><b>Example 3: Collect Followers</b> - Click to expand</summary>

```python
from instaharvest import FollowersCollector
from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()
collector = FollowersCollector(config=config)
session_data = collector.load_session()
collector.setup_browser(session_data)

# Collect first 100 followers
followers = collector.get_followers("username", limit=100, print_realtime=True)
print(f"Collected {len(followers)} followers")

collector.close()
```

</details>

<details>
<summary><b>Example 4: All Operations in One Browser (SharedBrowser)</b> - Click to expand</summary>

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

config = ScraperConfig()

# One browser for everything!
with SharedBrowser(config=config) as browser:
    # ── Social Actions ──
    browser.follow("user1")
    browser.send_message("user1", "Thanks for the follow!")
    followers = browser.get_followers("my_account", limit=50)

    # ── Profile ──
    profile = browser.scrape_profile("username")
    print(f"{profile.full_name}: {profile.followers} followers")

    # ── Post Data (NEW) ──
    post = browser.scrape_post("https://www.instagram.com/p/DVld0u9iN3K/")
    print(f"Likes: {post.like_count}, Tags: {post.tagged_accounts}")

    # ── Multiple Posts (NEW) ──
    posts = browser.scrape_posts([
        "https://www.instagram.com/p/ABC/",
        "https://www.instagram.com/p/XYZ/",
    ])

    # ── Reel Data (NEW) ──
    reel = browser.scrape_reel("https://www.instagram.com/reel/DVxyz/")
    print(f"Views: {reel.view_count}, Plays: {reel.play_count}")

    # ── Stories (NEW) ──
    stories = browser.scrape_stories("username")
    print(f"Stories: {stories.story_count}, Tags: {stories.all_tagged_accounts}")

    # ── Comments (NEW) ──
    comments = browser.scrape_comments("https://www.instagram.com/p/ABC/")
    print(f"Comments: {len(comments.comments)}")

    # ── Search (NEW) ──
    results = browser.search("fashion")
    print(f"Found {results.total_count} results")

    # ── Hashtag (NEW) ──
    hashtag = browser.scrape_hashtag("travel")
    print(f"#travel: {hashtag.post_count} posts")

    # ── Notifications (NEW) ──
    notifs = browser.read_notifications()
    print(f"Notifications: {len(notifs)}")

    # ── Download Media ──
    files = browser.download_post("https://www.instagram.com/p/ABC/")
    print(f"Downloaded {len(files)} files")
```

</details>

<details>
<summary><b>Example 5: Scrape Comments from Posts</b> - Click to expand</summary>

```python
from instaharvest import CommentScraper
from instaharvest.exporters import export_comments_to_json, export_comments_to_excel
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = CommentScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Scrape comments from a single post
post_url = 'https://www.instagram.com/p/DTLHDJpDAbO/'
comments = scraper.scrape(
    post_url,
    max_comments=100,
    include_replies=True
)

# Access comment data
print(f"Found {len(comments.comments)} top-level comments.")
print("---")

for comment in comments.comments:
    print(f"ID: {comment.id}")
    print(f"User: {comment.author.username}")
    print(f"Text: '{comment.text}'")
    print(f"Time: {comment.timestamp_iso}")
    print(f"Likes: {comment.likes_count}")
    print(f"Reply Count (Extracted): {comment.reply_count}")
    print(f"Nested Replies: {len(comment.replies)}")
    
    if comment.replies:
        for reply in comment.replies:
             print(f"    > Reply ID: {reply.id} | User: {reply.author.username} | Text: '{reply.text}'")
    print("-" * 20)

# Export Options
save_json = True

print("\n--- Exporting Data ---")
if save_json:
    json_filename = f"comments_{comments.post_id}.json"
    if export_comments_to_json(comments, json_filename):
        print(f"[+] Saved JSON to {json_filename}")
    else:
        print(f"[-] Failed to save JSON")


scraper.close()
```

</details>

<details>
<summary><b>Example 6: Download Media (Images/Videos)</b> - Click to expand</summary>

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # Download from ANY Post or Reel URL
    url = "https://www.instagram.com/reel/C-example..."
    
    # Automatically handles:
    # - Images (High Res)
    # - Videos/Reels (via yt-dlp)
    # - Carousels (multiple files)
    files = browser.download_post(url)
    
    if files:
        print(f"✅ Downloaded {len(files)} files:")
        for f in files:
            print(f"   📂 {f}")
```

</details>

---

## 📁 Example Scripts

<details>
<summary><b>📂 Ready-to-Use Scripts</b> - Click to expand</summary>

The `examples/` directory contains ready-to-use scripts:

### 🔑 Session Setup (Required First)

```bash
python examples/save_session.py
```

Creates Instagram session (one-time setup, then reused automatically).

### 🎮 Interactive Demo

```bash
python examples/all_in_one.py
```

Interactive menu with ALL features:

- Follow/Unfollow users
- Send messages
- Collect followers/following
- Batch operations
- Profile scraping

### 🚀 Production Scraping

```bash
python examples/main_advanced.py
```

Full automatic profile scraping:

- Collects all post/reel links
- Extracts data with parallel processing
- Exports to Excel + JSON
- Advanced diagnostics & error recovery

### 🔧 Video & Reel Support (IMPORTANT)

To download or view Videos/Reels correctly, the scraper defaults to using Google Chrome (`channel='chrome'`) instead of the bundled Chromium, as Chromium often lacks necessary video codecs.

**Requirements:**

- **Google Chrome** must be installed on your system.
- If you see a "Library Error" regarding Chrome, please install it or switch to `channel='chromium'` in your config (note: videos might not play/download).

```python
config = ScraperConfig(
    browser_channel='chrome',  # Default: Uses system Chrome for video support
    # browser_channel='chromium' # Use this if you don't need videos
)
```

### ⚙️ Configuration Examples

```bash
python examples/example_custom_config.py
```

Shows how to customize configuration (delays, viewport, etc.).

</details>

## 📖 Documentation

<details>
<summary><b>📚 Full API Documentation</b> - Click to expand</summary>

### 1. Profile Scraping

```python
from instaharvest import ProfileScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = ProfileScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

profile = scraper.scrape('username')
print(f"Posts: {profile.posts}")
print(f"Followers: {profile.followers}")
print(f"Following: {profile.following}")
print(f"Verified: {'✓ Yes' if profile.is_verified else '✗ No'}")
print(f"Category: {profile.category or 'Not set'}")
print(f"Bio: {profile.bio or 'No bio'}")
print(f"External Links: {profile.external_links}")
print(f"Threads: {profile.threads_profile}")

scraper.close()
```

### 2. Collect Followers/Following

```python
from instaharvest import FollowersCollector
from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()
collector = FollowersCollector(config=config)
session_data = collector.load_session()
collector.setup_browser(session_data)

# Collect first 100 followers
followers = collector.get_followers('username', limit=100, print_realtime=True)
print(f"Collected {len(followers)} followers")

# Collect following
following = collector.get_following('username', limit=50)

collector.close()
```

### 3. Follow/Unfollow Management

```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

config = ScraperConfig()
manager = FollowManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

# Follow a user
result = manager.follow('username')
print(result)  # {'status': 'success', 'action': 'followed', ...}

# Unfollow
result = manager.unfollow('username')

# Batch follow
usernames = ['user1', 'user2', 'user3']
results = manager.batch_follow(usernames)

manager.close()
```

### 4. Direct Messaging

```python
from instaharvest import MessageManager
from instaharvest.config import ScraperConfig

config = ScraperConfig()
messenger = MessageManager(config=config)
session_data = messenger.load_session()
messenger.setup_browser(session_data)

# Send single message
result = messenger.send_message('username', 'Hello!')

# Batch send
usernames = ['user1', 'user2']
results = messenger.batch_send(usernames, 'Hi there!')

messenger.close()
```

### 5. Shared Browser (Recommended!)

**Use one browser for all operations** — Much faster! Supports **15 lazy properties** and **20+ convenience methods**.

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # ── Social Actions ──
    browser.follow('user1')
    browser.send_message('user1', 'Hello!')
    followers = browser.get_followers('user2', limit=100)
    profile = browser.scrape_profile('user3')

    # ── Data Scraping (NEW) ──
    post = browser.scrape_post('https://www.instagram.com/p/ABC/')
    reel = browser.scrape_reel('https://www.instagram.com/reel/XYZ/')
    stories = browser.scrape_stories('username')
    comments = browser.scrape_comments('https://www.instagram.com/p/ABC/')

    # ── Discovery (NEW) ──
    results = browser.search('fashion brands')
    hashtag = browser.scrape_hashtag('streetwear')
    notifs = browser.read_notifications()

    # ── Batch Operations (NEW) ──
    posts = browser.scrape_posts(['url1', 'url2', 'url3'])
    reels = browser.scrape_reels(['reel1', 'reel2'])

    # ── Download ──
    files = browser.download_post('https://www.instagram.com/p/ABC/')

    # No browser reopening! Fast and efficient!
```

**SharedBrowser + Orchestrator (NEW!):**

```python
from instaharvest import SharedBrowser, InstagramOrchestrator, ScraperConfig

config = ScraperConfig(headless=True)

with SharedBrowser(config=config) as browser:
    # Orchestrator reuses the same browser!
    orch = InstagramOrchestrator(config, shared_browser=browser)

    # Full profile scrape with parallel processing — 1 browser!
    results = orch.scrape_complete_profile_advanced(
        'username',
        parallel=3,
        save_excel=True,
        scrape_comments=True,
        scrape_stories=True
    )
```

### 6. Advanced: Parallel Processing

```python
from instaharvest import InstagramOrchestrator, SharedBrowser, ScraperConfig

config = ScraperConfig(headless=True)

# Option A: Standalone (opens new browser)
orchestrator = InstagramOrchestrator(config)
results = orchestrator.scrape_complete_profile_advanced(
    'username',
    parallel=3,
    save_excel=True
)

# Option B: With SharedBrowser (reuses existing browser — faster!)
with SharedBrowser(config=config) as browser:
    orch = InstagramOrchestrator(config, shared_browser=browser)
    results = orch.scrape_complete_profile_advanced(
        'username',
        parallel=3,
        save_excel=True,
        scrape_stories=True
    )

print(f"Scraped {len(results['posts_data'])} posts")
```

### 7. Post Data Extraction

```python
from instaharvest import PostDataScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = PostDataScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Scrape single post
post = scraper.scrape('https://www.instagram.com/p/POST_ID/')
print(f"Tagged: {post.tagged_accounts}")
print(f"Likes: {post.likes}")
print(f"Date: {post.timestamp}")

scraper.close()
```

### 8. Comment Scraping

```python
from instaharvest import CommentScraper
from instaharvest.config import ScraperConfig

# 1. Setup Config & Scraper
config = ScraperConfig(headless=False)  # Set to True for background execution
scraper = CommentScraper(config=config)

# 2. Load Session (Required)
# Ensure you have run 'python examples/save_session.py' first
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# 3. Scrape Comments
result = scraper.scrape(
    'https://www.instagram.com/p/POST_ID/',
    max_comments=100,       # Limit (None = all)
    include_replies=True    # Important: Enable nested reply scraping
)

# 4. Access Data
print(f"Total Comments: {result.total_comments_scraped}")
print(f"Total Replies: {result.total_replies_scraped}")

for comment in result.comments:
    print(f"@{comment.author.username}: {comment.text}")
    print(f"  Likes: {comment.likes_count}")

    # Access Nested Replies
    for reply in comment.replies:
        print(f"    ↳ @{reply.author.username}: {reply.text}")

scraper.close()
```

**Export comments to files:**

```python
from instaharvest import export_comments_to_json, export_comments_to_excel

# Export to JSON
export_comments_to_json(comments, 'comments.json')

# Export to Excel
export_comments_to_excel(comments, 'comments.xlsx')
```

### 9. Notification Reader

```python
from playwright.sync_api import sync_playwright
from instaharvest import ScraperConfig, StealthManager, NotificationReader
import logging, time

config = ScraperConfig()
logger = logging.getLogger('notif')

with sync_playwright() as pw:
    browser = pw.chromium.launch(headless=False)
    context = browser.new_context(
        storage_state='instagram_session.json',
        viewport={'width': 1280, 'height': 900},
        user_agent=config.user_agent,
    )
    page = context.new_page()

    # Apply stealth
    stealth = StealthManager(config)
    stealth.apply_page_stealth(page)
    page.goto('https://www.instagram.com/', wait_until='domcontentloaded')
    time.sleep(4)

    # Read notifications
    reader = NotificationReader(page, logger, config)
    notifications = reader.read_notifications(max_count=50, scroll=True)

    # Filter by type
    follows = reader.filter_by_type(notifications, 'follow')
    likes = reader.filter_by_type(notifications, 'post_like')

    # Filter by section
    this_week = reader.filter_by_section(notifications, 'This week')

    # Summary statistics
    stats = reader.summary(notifications)
    print(f"Total: {stats['total']}, By type: {stats['by_type']}")

    # Convenience methods
    new_followers = reader.get_new_followers_usernames()

    # Export to JSON-serializable dicts
    data = reader.to_dicts(notifications)

    context.close()
    browser.close()
```

**Supported notification types:**

| Type | Example |
|------|---------|
| `follow` | "started following you" |
| `post_like` | "liked your post/reel/photo/video" |
| `comment_like` | "liked your comment: ..." |
| `comment` | "commented: ..." |
| `mention` | "mentioned you" / "tagged you" |
| `follow_request` | "requested to follow you" |
| `follow_accepted` | "accepted your follow request" |
| `thread` | "posted a thread you might be interested in" |
| `story` | "posted a story" |
| `system` | Meta/Instagram system notifications |

</details>

### 10. Story Scraper 📸

Extract tagged accounts from Instagram stories using **JSON-first architecture** — all tags from all slides in a single page load, no slide navigation needed.

```python
from instaharvest import StoryScraper, StorySlideInfo
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file

# 1. Setup
config = ScraperConfig(headless=False)
config.session_file = find_session_file()
scraper = StoryScraper(config=config)

# 2. Scrape stories
result = scraper.scrape(
    'username',
    extract_tags=True,       # Extract tagged accounts
    challenge_delay=10       # Seconds to wait for challenge
)

# 3. Access data
print(f"Has stories: {result.has_stories}")
print(f"All tags: {result.all_tagged_accounts}")

# 4. Per-slide mapping (which tag on which story + timestamp)
for slide in result.slides:
    print(f"Slide {slide.slide_index + 1}: "
          f"[{slide.media_type}] {slide.timestamp} → "
          f"{slide.tagged_accounts}")

# Output:
# Slide 1: [image] 2026-03-10 23:58:45 UTC → []
# Slide 2: [video] 2026-03-10 00:24:42 UTC → []
# Slide 3: [video] 2026-03-10 10:41:20 UTC → ['d_24_erkinovna']
# Slide 4: [video] 2026-03-10 12:44:56 UTC → []
# Slide 5: [video] 2026-03-10 15:44:28 UTC → ['___noooza', 'isfira_saphir']
```

**Using Orchestrator (standalone):**

```python
from instaharvest import InstagramOrchestrator
from instaharvest.config import ScraperConfig

orchestrator = InstagramOrchestrator(ScraperConfig())
result = orchestrator.scrape_stories_only('username')
# Auto-exports to story_tags_username.json
```

**Using Orchestrator (integrated with full profile scrape):**

```python
results = orchestrator.scrape_complete_profile_advanced(
    'username',
    parallel=3,
    scrape_stories=True,          # Enable story scraping
    story_challenge_delay=10,     # Challenge wait time
    save_excel=True
)
# results['story_data'] contains full story data with per-slide mapping
```

**StoryResult data structure:**

| Field | Type | Description |
|-------|------|-------------|
| `has_stories` | `bool` | Whether user has active stories |
| `story_count` | `int` | Number of story items |
| `items` | `List[StoryItem]` | Story media items |
| `slides` | `List[StorySlideInfo]` | Per-slide tag mapping |
| `all_tagged_accounts` | `List[str]` | All unique tagged usernames |

**StorySlideInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `slide_index` | `int` | Slide position (0-based) |
| `timestamp` | `str` | When story was posted (UTC) |
| `media_type` | `str` | `image` or `video` |
| `tagged_accounts` | `List[str]` | Tags on this specific slide |
| `has_tags` | `bool` | Quick check if slide has tags |

---

### 11. JSON-First Post Data 🧬

Instagram embeds full post data in `<script type="application/json">` tags. Our library now extracts **30+ fields** from this JSON automatically — no DOM clicks needed.

```python
from instaharvest import PostDataScraper
from instaharvest.config import ScraperConfig
from instaharvest.session_utils import find_session_file

config = ScraperConfig(headless=True)
config.session_file = find_session_file()

scraper = PostDataScraper(config=config)
session = scraper.load_session()
scraper.setup_browser(session)

result = scraper.scrape("https://www.instagram.com/p/DVs7LK-iO0C/")

# ── Basic ──
print(result.shortcode)           # "DVs7LK-iO0C"
print(result.json_extracted)      # True (came from JSON)
print(result.content_type)        # "Post" / "Reel"

# ── Engagement ──
print(result.like_count)          # 1234 (exact integer)
print(result.comment_count)       # 56
print(result.top_likers)          # ['famous_user1', 'brand_x']

# ── Caption ──
print(result.caption)             # Full caption text with hashtags

# ── Location (GPS) ──
if result.location:
    print(result.location.name)      # "Tashkent, Uzbekistan"
    print(result.location.latitude)  # 41.2995
    print(result.location.longitude) # 69.2401

# ── Owner ──
if result.owner:
    print(result.owner.username)     # "raykhana_nasillayeva"
    print(result.owner.full_name)    # "Raykhana"
    print(result.owner.is_verified)  # False

# ── Tags with Positions ──
print(result.tagged_accounts)     # ['brand_a', 'brand_b']
print(result.tag_positions)       # [{'username': 'brand_a', 'x': 0.5, 'y': 0.7}]

# ── Carousel Slides ──
for slide in result.carousel_slides:
    print(f"Slide {slide.slide_index}: {slide.media_type} "
          f"({slide.width}x{slide.height}) "
          f"tags={slide.tagged_accounts}")

# ── Timestamp ──
print(result.taken_at_human)      # "2025-03-10 15:30:00 UTC"
print(result.taken_at)            # 1741617000 (Unix)

scraper.close()
```

**All Enriched Fields:**

| Field | Type | Description |
| --- | --- | --- |
| `json_extracted` | `bool` | Whether data came from JSON |
| `shortcode` | `str` | Post shortcode (URL segment) |
| `pk` | `str` | Post unique numeric ID |
| `media_type` | `int` | 1=image, 2=video, 8=carousel |
| `product_type` | `str` | `feed`, `clips`, `carousel_container` |
| `like_count` | `int` | Exact integer like count |
| `comment_count` | `int` | Total comments |
| `top_likers` | `List[str]` | Notable users who liked |
| `has_liked` | `bool` | Current user has liked |
| `caption` | `str` | Full caption text |
| `location` | `PostLocation` | `.name`, `.latitude`, `.longitude`, `.city` |
| `owner` | `PostOwner` | `.username`, `.full_name`, `.is_verified` |
| `taken_at` | `int` | Unix timestamp |
| `taken_at_human` | `str` | Human-readable UTC timestamp |
| `width` / `height` | `int` | Original media dimensions |
| `accessibility_caption` | `str` | AI-generated image description |
| `video_duration` | `float` | Video length in seconds |
| `has_audio` | `bool` | Has audio track |
| `carousel_media_count` | `int` | Number of carousel slides |
| `carousel_slides` | `List[CarouselSlide]` | Per-slide details |
| `tag_positions` | `List[Dict]` | Tag coordinates on image |

> **Architecture**: JSON extraction is the primary method. DOM-based extraction is only used as fallback when JSON is unavailable. This works in both `PostDataScraper` and `ParallelPostDataScraper`.

---

### 🏷️ Tagged Posts Scraper

Discover which accounts tag a specific user. Scrapes `/{username}/tagged/` with infinite scroll.

```python
from instaharvest import TaggedPostsScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = TaggedPostsScraper(config=config)
session = scraper.load_session()
scraper.setup_browser(session)

result = scraper.scrape('mondayswimwear', max_posts=100)

print(f"Total: {result.total_found} tagged posts")
print(f"Unique taggers: {result.unique_taggers}")

for post in result.tagged_posts:
    print(f"  @{post.owner} → {post.url} ({post.media_type})")

scraper.close()
```

**Available via:**
```python
# Orchestrator
orch = InstagramOrchestrator(config)
result = orch.scrape_tagged_posts('username')

# Shared Browser
with SharedBrowser(config=config) as browser:
    result = browser.scrape_tagged_posts('username', max_posts=50)
```

---

### 🌟 Highlights Scraper

Extract ALL slides from Instagram highlights with rich metadata — mentions, links, music, locations, hashtags.

```python
from instaharvest import HighlightsScraper
from instaharvest.config import ScraperConfig

config = ScraperConfig()
scraper = HighlightsScraper(config=config)
session = scraper.load_session()
scraper.setup_browser(session)

# ── Single highlight ──
result = scraper.scrape('18092082532805201', max_slides=200)
print(f"{result.highlight_title}: {result.slide_count} slides")
print(f"Mentions: {result.all_mentions}")
print(f"Links: {result.all_links}")
for slide in result.slides:
    print(f"Slide {slide.slide_index}: {slide.media_type}, {slide.mentions}")

# ── List ALL highlights for a user ──
highlights = scraper.list_highlights('mondayswimwear')
for h in highlights:
    print(f"🌟 {h.highlight_id} — {h.title}")

# ── Scrape ALL highlights sequentially ──
full = scraper.scrape_all('mondayswimwear', max_slides_per=100)
print(f"{full.total_highlights} highlights, {full.total_slides} total slides")
for r in full.full_results:
    print(f"  {r.highlight_title}: {r.slide_count} slides")

scraper.close()
```

**Per-slide data:**

| Field | Type | Description |
| --- | --- | --- |
| `media_type` | `str` | `image` or `video` |
| `image_url` | `str` | HD image URL |
| `video_url` | `str` | Video URL (if video) |
| `taken_at_human` | `str` | `2026-01-20 02:37:13 UTC` |
| `mentions` | `List[str]` | @usernames from stickers |
| `link_stickers` | `List[str]` | URLs from link stickers |
| `location_stickers` | `List[Dict]` | Location name, pk, address |
| `music` | `HighlightMusic` | title, artist, album |
| `hashtag_stickers` | `List[str]` | #hashtags |

**Available via:**
```python
# Orchestrator
orch.scrape_highlight('18092082532805201')
orch.scrape_all_highlights('mondayswimwear')

# Shared Browser
browser.scrape_highlight('18092082532805201')
browser.list_highlights('mondayswimwear')
browser.scrape_all_highlights('mondayswimwear')
```

---

## 🎯 Complete Workflow Example

<details>
<summary><b>🔄 Full Automation Workflow</b> - Click to expand</summary>

```python
from instaharvest import SharedBrowser, InstagramOrchestrator
from instaharvest.config import ScraperConfig

config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # 1. Profile analysis
    profile = browser.scrape_profile('target_user')
    print(f"📊 {profile.full_name}: {profile.followers} followers")

    # 2. Collect followers
    followers = browser.get_followers('target_user', limit=50)
    print(f"👥 Collected {len(followers)} followers")

    # 3. Follow them
    for follower in followers[:10]:
        result = browser.follow(follower)
        if result['success']:
            print(f"✓ Followed {follower}")

    # 4. Send welcome message
    for follower in followers[:5]:
        browser.send_message(follower, "Thanks for following!")

    # 5. Scrape user's latest posts
    post_links = browser.get_post_links('target_user')
    posts = browser.scrape_posts([l['url'] for l in post_links[:5]])
    for post in posts:
        print(f"📸 {post.shortcode}: {post.like_count} likes")

    # 6. Check stories
    stories = browser.scrape_stories('target_user')
    if stories.has_stories:
        print(f"📖 {stories.story_count} stories, tags: {stories.all_tagged_accounts}")

    # 7. Read notifications
    notifs = browser.read_notifications()
    print(f"🔔 {len(notifs)} notifications")

    # 8. Full orchestrated scrape (same browser!)
    orch = InstagramOrchestrator(config, shared_browser=browser)
    results = orch.scrape_complete_profile_advanced(
        'target_user',
        parallel=3,
        save_excel=True,
        scrape_stories=True
    )
    print(f"✅ Total: {len(results['posts_data'])} posts scraped")
```

</details>

---

## 📋 Requirements

- Python 3.8+
- Playwright (with Chrome browser)
- pandas
- openpyxl
- beautifulsoup4
- lxml

---

## 🔧 Session Setup

**First-time setup** - Save your Instagram session:

### Method 1: Using Library Function (Recommended) ⭐

```python
from instaharvest import save_session

# Create session - opens browser for manual login
save_session()
```

### Method 2: Using Example Script

```bash
python examples/save_session.py
```

Both methods will:

1. Open Chrome browser
2. Let you log in to Instagram manually
3. Save session to `instagram_session.json`
4. All future scripts will use this session (no re-login needed!)

---

## 📁 Project Structure

<details>
<summary><b>🗂️ Package Structure</b> - Click to expand</summary>

```
instaharvest/
├── instaharvest/          # Main package
│   ├── __init__.py        # Package entry point
│   ├── base.py            # Base scraper class
│   ├── config.py          # Configuration
│   ├── profile.py         # Profile scraping
│   ├── followers.py       # Followers collection
│   ├── follow.py          # Follow/unfollow
│   ├── message.py         # Direct messaging
│   ├── post_data.py       # Post data extraction (JSON-first)
│   ├── reel_data.py       # Reel data extraction
│   ├── post_links.py      # Post link collection
│   ├── reel_links.py      # Reel link collection
│   ├── story_scraper.py   # Story scraping with tag mapping
│   ├── comment_scraper.py # Comment extraction with replies
│   ├── search_api.py      # Instagram search
│   ├── hashtag_scraper.py # Hashtag post collection
│   ├── location_scraper.py # Location-based scraping
│   ├── explore_scraper.py # Explore page scraping
│   ├── notifications.py   # Notification reader
│   ├── highlight_scraper.py # Highlight slides extraction
│   ├── tagged_posts.py    # Tagged posts scraping
│   ├── shared_browser.py  # SharedBrowser (15 lazy properties)
│   ├── orchestrator.py    # Full workflow orchestrator
│   ├── parallel_scraper.py # Parallel processing
│   ├── interactions.py    # Like/comment interactions
│   ├── downloader.py      # Media download (images/videos)
│   └── ...                # More modules
├── examples/              # Example scripts
│   ├── save_session.py    # Session setup
│   ├── all_in_one.py      # Interactive demo
│   ├── main_advanced.py   # Production scraping
│   └── example_custom_config.py
├── tests/                 # Unit tests (87 tests)
├── README.md              # This file
├── setup.py               # Package setup
└── LICENSE                # MIT License
```

</details>

---

## ⚙️ Configuration

<details>
<summary><b>🛠️ Configuration Options</b> - Click to expand</summary>

```python
from instaharvest import ScraperConfig

config = ScraperConfig(
    headless=True,              # Run in headless mode
    viewport_width=1920,
    viewport_height=1080,
    default_timeout=30000,      # 30 seconds
    max_scroll_attempts=50,
    log_level='INFO'
)
```

</details>

---

## 🛡️ Best Practices

<details>
<summary><b>✅ Recommended Practices</b> - Click to expand</summary>

1. **Use SharedBrowser** - Reuses browser instance, much faster (15 modules, 1 browser)
2. **Use SharedBrowser + Orchestrator** - Pass `shared_browser` to `InstagramOrchestrator` for maximum efficiency
3. **Rate Limiting** - Built-in delays to avoid Instagram bans
4. **Session Management** - Auto-refreshes session to prevent expiration
5. **Error Handling** - Comprehensive exception handling
6. **JSON-First Architecture** - 30+ fields extracted from pre-loaded JSON
7. **Logging** - Professional logging for debugging

</details>

---

## 🔧 Troubleshooting

<details>
<summary><b>🔍 Common Issues & Solutions</b> - Click to expand</summary>

### Installation Issues

#### Error: "playwright command not found"

```bash
# Solution: Install Playwright first
pip install playwright
playwright install chrome
```

#### Error: "No module named 'instaharvest'"

```bash
# Solution 1: If installed from PyPI
pip install instaharvest

# Solution 2: If using GitHub clone
cd /path/to/insta-harvester
pip install -e .

# Solution 3: Run from project directory
cd /path/to/insta-harvester
python examples/save_session.py  # Works without installation
```

#### Error: "Could not find Chrome browser"

```bash
# Solution: Install Playwright browsers
playwright install chrome
```

---

### Session Issues

#### Error: "Session file not found"

```bash
# Solution: Create session first (REQUIRED!)
cd examples
python save_session.py

# Then run your script
python all_in_one.py  # or any other script
```

### Data Issues

#### "Posts: 0" or "Reels: 0" but content exists

If you see 0 posts despite successful scrolling:

1. Ensure you are using the latest version (v2.7.1+)
2. **Case Sensitivity**: Newest version handles 'Post' vs 'post' automatically.
3. Check `save_excel=True` output - data might be saved even if console count is confusing.

#### Error: "Login required" or "Session expired"

```bash
# Solution: Re-create session
cd examples
python save_session.py

# Log in again when browser opens
```

---

### Operation Errors

#### Error: "Could not unfollow @username"

**Cause:** Unfollow popup appears too slowly for the program

**Solution:** Increase popup delays in configuration

```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

config = ScraperConfig(
    popup_open_delay=4.0,       # Wait longer for popup
    action_delay_min=3.0,
    action_delay_max=4.5,
)

manager = FollowManager(config=config)
```

See **[Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md)** for detailed configuration options.

#### Error: "Could not follow @username"

**Solution:**

```python
config = ScraperConfig(
    button_click_delay=3.0,
    action_delay_min=2.5,
    action_delay_max=4.0,
)
```

#### Error: "Instagram says 'Try again later'"

**Cause:** Instagram rate limiting - you're doing too much too quickly

**Solution:** Increase rate limiting delays

```python
config = ScraperConfig(
    follow_delay_min=10.0,      # Wait 10-15 seconds between follows
    follow_delay_max=15.0,
    message_delay_min=15.0,     # Wait 15-20 seconds between messages
    message_delay_max=20.0,
)
```

---

### Slow Internet Issues

**Problem:** You have slow internet, pages load slowly, getting errors

**Solution:**

```python
from instaharvest.config import ScraperConfig

config = ScraperConfig(
    page_load_delay=5.0,        # Wait longer for pages
    popup_open_delay=4.0,       # Wait longer for popups
    scroll_delay_min=3.0,       # Slower scrolling
    scroll_delay_max=5.0,
)

# Use with any manager
from instaharvest import FollowManager
manager = FollowManager(config=config)
```

---

### Getting Help

1. **Check documentation:**
   - [README.md](https://github.com/mpython77/insta-harvester#readme) - Main guide
   - [Configuration Guide](https://github.com/mpython77/insta-harvester/blob/main/CONFIGURATION_GUIDE.md) - Complete configuration reference
   - [Examples Guide](https://github.com/mpython77/insta-harvester/blob/main/examples/README.md) - Example scripts guide
   - [Changelog](https://github.com/mpython77/insta-harvester/blob/main/CHANGELOG.md) - Version history and changes
   - [Contributing](https://github.com/mpython77/insta-harvester/blob/main/CONTRIBUTING.md) - How to contribute

2. **Common issues:**
   - Unfollow errors → Increase `popup_open_delay`
   - Slow internet → Increase all delays
   - Rate limiting → Increase `follow_delay_*` and `message_delay_*`

3. **Report bugs:**
   - GitHub Issues: <https://github.com/mpython77/insta-harvester/issues>
   - See `CONTRIBUTING.md` for bug report guidelines

4. **Email support:**
   - <kelajak054@gmail.com>

</details>

---

## ⚠️ Disclaimer

This tool is for educational purposes only. Make sure to:

- Follow Instagram's Terms of Service
- Respect rate limits
- Don't spam or harass users
- Use responsibly

**The authors are not responsible for any misuse of this library.**

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📞 Support

- GitHub Issues: [Report a bug](https://github.com/mpython77/insta-harvester/issues)
- Documentation: [Read the docs](https://github.com/mpython77/insta-harvester#readme)
- Email: <kelajak054@gmail.com>

---

## 🎉 Acknowledgments

Built with:

- [Playwright](https://playwright.dev/) - Browser automation
- [Pandas](https://pandas.pydata.org/) - Data processing
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing

---

**Made with ❤️ by Muydinov Doston**

*Happy Harvesting! 🌾*
