# InstaHarvest 🌾

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)

**Professional Instagram Data Collection Toolkit** - A powerful and efficient library for Instagram automation, data collection, and analytics.

---

## ✨ Features

- 📊 **Profile Statistics** - Collect followers, following, posts count
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

## 🚀 Quick Start

### Installation

```bash
pip install instaharvest
```

### Install Playwright Browser

```bash
playwright install chrome
```

### Basic Usage

```python
from instaharvest import quick_scrape

# Simple profile scraping
results = quick_scrape('username')
print(f"Followers: {results['profile']['followers']}")
```

---

## 📖 Documentation

### 1. Profile Scraping

```python
from instaharvest import ProfileScraper

scraper = ProfileScraper()
session_data = scraper.load_session()
scraper.setup_browser(session_data)

profile = scraper.scrape('username')
print(f"Posts: {profile.posts}")
print(f"Followers: {profile.followers}")
print(f"Following: {profile.following}")

scraper.close()
```

### 2. Collect Followers/Following

```python
from instaharvest import FollowersCollector

collector = FollowersCollector()
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

manager = FollowManager()
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

messenger = MessageManager()
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

with SharedBrowser() as browser:
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

scraper = PostDataScraper()
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Scrape single post
post = scraper.scrape('https://www.instagram.com/p/POST_ID/')
print(f"Tagged: {post.tagged_accounts}")
print(f"Likes: {post.likes}")
print(f"Date: {post.timestamp}")

scraper.close()
```

---

## 🎯 Complete Workflow Example

```python
from instaharvest import SharedBrowser

with SharedBrowser() as browser:
    # 1. Get profile stats
    profile = browser.scrape_profile('target_user')
    print(f"Target has {profile['followers']} followers")

    # 2. Collect their followers
    followers = browser.get_followers('target_user', limit=50)
    print(f"Collected {len(followers)} followers")

    # 3. Follow them
    for follower in followers[:10]:  # Follow first 10
        result = browser.follow(follower)
        if result['status'] == 'success':
            print(f"✓ Followed {follower}")

    # 4. Send welcome message
    for follower in followers[:5]:
        browser.send_message(follower, "Thanks for following!")
```

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

```bash
python save_session.py
```

This will:
1. Open Chrome browser
2. Let you log in to Instagram manually
3. Save session to `instagram_session.json`
4. All future scripts will use this session (no re-login needed!)

---

## 📁 Project Structure

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

---

## ⚙️ Configuration

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

---

## 🛡️ Best Practices

1. **Use SharedBrowser** - Reuses browser instance, much faster
2. **Rate Limiting** - Built-in delays to avoid Instagram bans
3. **Session Management** - Auto-refreshes session to prevent expiration
4. **Error Handling** - Comprehensive exception handling
5. **Logging** - Professional logging for debugging

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

- GitHub Issues: [Report a bug](https://github.com/yourusername/instaharvest/issues)
- Documentation: [Read the docs](https://github.com/yourusername/instaharvest#readme)

---

## 🎉 Acknowledgments

Built with:
- [Playwright](https://playwright.dev/) - Browser automation
- [Pandas](https://pandas.pydata.org/) - Data processing
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing

---

**Made with ❤️ by Artem**

*Happy Harvesting! 🌾*
