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
- 🔗 **Post & Reel Links** - Intelligent scrolling and link collection
- 🏷️ **Tagged Accounts** - Extract tags from posts and reels
- 👥 **Followers/Following** - Collect lists with real-time output
- 💬 **Direct Messaging** - Send DMs with smart rate limiting
- 🤝 **Follow/Unfollow** - Manage following with rate limiting
- ⚡ **Parallel Processing** - Scrape multiple posts simultaneously
- 📑 **Excel Export** - Real-time data export to Excel
- 🌐 **Shared Browser** - Single browser for all operations
- 🔍 **HTML Detection** - Automatic structure change detection
- 📝 **Professional Logging** - Comprehensive logging system

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
# Just make sure you're in the project directory
cd /path/to/insta-harvester

# Then run examples
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

# Create config for better reliability
config = ScraperConfig()

# One browser for everything!
with SharedBrowser(config=config) as browser:
    # Follow users
    browser.follow("user1")
    browser.follow("user2")

    # Send messages
    browser.send_message("user1", "Thanks for the follow!")

    # Collect followers
    followers = browser.get_followers("my_account", limit=50)
    print(f"Followers: {len(followers)}")
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

**Use one browser for all operations** - Much faster!

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # All operations use the same browser instance
    browser.follow('user1')
    browser.send_message('user1', 'Hello!')
    followers = browser.get_followers('user2', limit=100)
    profile = browser.scrape_profile('user3')

    # No browser reopening! Fast and efficient!
```

### 6. Advanced: Parallel Processing

```python
from instaharvest import InstagramOrchestrator, ScraperConfig

config = ScraperConfig(headless=True)
orchestrator = InstagramOrchestrator(config)

# Scrape with 3 parallel workers + Excel export
results = orchestrator.scrape_complete_profile_advanced(
    'username',
    parallel=3,        # 3 parallel browser tabs
    save_excel=True,   # Real-time Excel export
    max_posts=100
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

</details>

---

## 🎯 Complete Workflow Example

<details>
<summary><b>🔄 Full Automation Workflow</b> - Click to expand</summary>

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

# Create config
config = ScraperConfig()

with SharedBrowser(config=config) as browser:
    # 1. Collect followers from target user
    followers = browser.get_followers('target_user', limit=50)
    print(f"Collected {len(followers)} followers")

    # 2. Follow them
    for follower in followers[:10]:  # Follow first 10
        result = browser.follow(follower)
        if result['success']:  # Check success key
            print(f"✓ Followed {follower}")

    # 3. Send welcome message
    for follower in followers[:5]:
        browser.send_message(follower, "Thanks for following!")
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
│   ├── post_data.py       # Post data extraction
│   ├── shared_browser.py  # Shared browser manager
│   └── ...                # More modules
├── examples/              # Example scripts
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

1. **Use SharedBrowser** - Reuses browser instance, much faster
2. **Rate Limiting** - Built-in delays to avoid Instagram bans
3. **Session Management** - Auto-refreshes session to prevent expiration
4. **Error Handling** - Comprehensive exception handling
5. **Logging** - Professional logging for debugging

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
   - GitHub Issues: https://github.com/mpython77/insta-harvester/issues
   - See `CONTRIBUTING.md` for bug report guidelines

4. **Email support:**
   - kelajak054@gmail.com

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
- Email: kelajak054@gmail.com

---

## 🎉 Acknowledgments

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [Pandas](https://pandas.pydata.org/) - Data processing
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing

---

**Made with ❤️ by Doston**

*Happy Harvesting! 🌾*
