# Instagram Scraper - Professional Library

Enterprise-grade Instagram scraping library with modular architecture, comprehensive logging, and intelligent error handling.

## 🌟 Features

### ✅ **All Requirements Met:**

1. **Class-based architecture** - Everything in well-structured classes
2. **Strong code architecture** - Modular, extensible, maintainable
3. **Professional logging** - Timestamps, log levels, file + console output
4. **Comprehensive error handling** - Retries, fallbacks, graceful degradation
5. **HTML structure change detection** - Automatic detection with detailed error messages
6. **Library-ready** - Import and use any component independently
7. **Parallel execution support** - Architecture ready for concurrent operations
8. **Modular extraction** - Get only what you need (posts only, likes only, etc.)
9. **Smart delays** - 1-2 second delays between operations
10. **Complete orchestrator** - Main class that coordinates everything

### 📦 **Package Structure:**

```
instagram_scraper/
├── __init__.py              # Package exports
├── config.py                # Configuration management
├── exceptions.py            # Custom exceptions
├── logger.py                # Professional logging
├── base.py                  # Base scraper class
├── profile.py               # Profile scraper
├── post_links.py            # Post links collector
├── post_data.py             # Post data extractor
└── orchestrator.py          # Main orchestrator
```

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
playwright install chromium
```

### 1. Save Session (First Time Only)

```bash
python save_session.py
```

### 2. Run Complete Scrape

```bash
python main.py
```

## 📖 Usage Examples

### Complete Workflow (Recommended)

```python
from instagram_scraper import InstagramOrchestrator, ScraperConfig

# Configure
config = ScraperConfig(
    headless=False,
    log_level='INFO',
    log_file='scraper.log'
)

# Run complete scrape
orchestrator = InstagramOrchestrator(config)
results = orchestrator.scrape_complete_profile(
    'cristiano',
    scrape_posts=True,
    export_results=True
)

# Access results
print(results['profile'])  # Profile stats
print(results['post_links'])  # All post URLs
print(results['posts_data'])  # Data from each post
```

### Quick Scrape (One-Liner)

```python
from instagram_scraper import quick_scrape

results = quick_scrape('cristiano')
```

### Modular Usage - Profile Only

```python
from instagram_scraper import ProfileScraper

scraper = ProfileScraper()
profile = scraper.scrape('cristiano')

print(f"Posts: {profile.posts}")
print(f"Followers: {profile.followers}")
print(f"Following: {profile.following}")
```

### Modular Usage - Specific Data Only

```python
from instagram_scraper import ProfileScraper

scraper = ProfileScraper()

# Only get followers (skip posts and following)
profile = scraper.scrape(
    'cristiano',
    get_posts=False,
    get_followers=True,
    get_following=False
)

print(f"Followers: {profile.followers}")
```

### Extract Post Data

```python
from instagram_scraper import PostDataScraper

scraper = PostDataScraper()
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Single post
data = scraper.scrape('https://www.instagram.com/p/ABC123/')
print(f"Tags: {data.tagged_accounts}")
print(f"Likes: {data.likes}")
print(f"Time: {data.timestamp}")

# Multiple posts
data_list = scraper.scrape_multiple([
    'https://www.instagram.com/p/ABC123/',
    'https://www.instagram.com/p/DEF456/',
])

scraper.close()
```

### Extract Only What You Need

```python
from instagram_scraper import PostDataScraper

scraper = PostDataScraper()
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Only get likes (skip tags and timestamp)
data = scraper.scrape(
    'https://www.instagram.com/p/ABC123/',
    get_tags=False,
    get_likes=True,
    get_timestamp=False
)

print(f"Likes: {data.likes}")
scraper.close()
```

## 🔧 Configuration

```python
from instagram_scraper import ScraperConfig

config = ScraperConfig(
    # Session
    session_file='instagram_session.json',

    # Browser
    headless=False,
    viewport_width=1920,
    viewport_height=1080,

    # Timeouts (milliseconds)
    default_timeout=60000,
    navigation_timeout=60000,
    element_timeout=10000,

    # Delays (seconds)
    page_load_delay=2.0,
    scroll_delay_min=1.5,
    scroll_delay_max=2.5,
    post_scrape_delay_min=2.0,
    post_scrape_delay_max=4.0,

    # Retry
    max_retries=3,
    retry_delay=2.0,

    # Logging
    log_file='instagram_scraper.log',
    log_level='INFO',
    log_to_console=True,

    # Output
    links_file='post_links.txt'
)
```

## 🎯 Architecture Highlights

### 1. **Inheritance Hierarchy**

```
BaseScraper (abstract)
├── ProfileScraper
├── PostLinksScraper
└── PostDataScraper
```

### 2. **Error Handling**

```python
try:
    scraper.scrape('username')
except ProfileNotFoundError:
    print("Profile doesn't exist")
except HTMLStructureChangedError as e:
    print(f"Instagram changed: {e.element_name}")
    print(f"Failed selector: {e.selector}")
except SessionNotFoundError:
    print("Run save_session.py first")
```

### 3. **Professional Logging**

```
2025-01-21 10:30:45 [INFO] ProfileScraper: Starting scrape for @cristiano
2025-01-21 10:30:46 [DEBUG] ProfileScraper: ✓ Extracted posts_count: 3970
2025-01-21 10:30:47 [WARNING] ProfileScraper: ✗ Failed to extract likes: selector timeout
2025-01-21 10:30:48 [ERROR] ProfileScraper: HTML structure may have changed for 'likes_count'
```

### 4. **HTML Structure Change Detection**

When Instagram changes their HTML:

```python
try:
    profile.get_followers_count()
except HTMLStructureChangedError as e:
    print(f"Element: {e.element_name}")  # "followers_count"
    print(f"Selector: {e.selector}")     # "a[href*='/followers/']"
    print(f"Message: {e.message}")       # "Cannot find followers count..."
```

## 🔄 Parallel Execution (Example)

```python
from concurrent.futures import ThreadPoolExecutor
from instagram_scraper import ProfileScraper, ScraperConfig

config = ScraperConfig(headless=True)
usernames = ['user1', 'user2', 'user3']

def scrape_profile(username):
    scraper = ProfileScraper(config)
    return scraper.scrape(username)

# Parallel execution
with ThreadPoolExecutor(max_workers=3) as executor:
    results = list(executor.map(scrape_profile, usernames))

for result in results:
    print(f"@{result.username}: {result.followers} followers")
```

## 📊 Data Structures

### ProfileData

```python
@dataclass
class ProfileData:
    username: str
    posts: str
    followers: str
    following: str
```

### PostData

```python
@dataclass
class PostData:
    url: str
    tagged_accounts: List[str]
    likes: str
    timestamp: str
```

## 🛡️ Error Handling Features

1. **Automatic retries** - Failed requests retry up to 3 times
2. **Multiple fallback methods** - If one selector fails, try alternatives
3. **Graceful degradation** - Returns 'N/A' instead of crashing
4. **Session validation** - Detects expired sessions
5. **HTML change detection** - Alerts when Instagram updates their structure

## 📁 Output Files

- `instagram_scraper.log` - Detailed logs with timestamps
- `post_links.txt` - Collected post URLs
- `instagram_data_<username>.json` - Complete scraping results

## 🎓 Advanced Examples

See `main.py` for complete examples including:
- Complete workflow
- Modular usage
- Parallel execution patterns
- Custom configuration

## ⚠️ Best Practices

1. **Rate Limiting:** Built-in 2-4 second delays between posts
2. **Session Management:** Reuse sessions, don't login repeatedly
3. **Error Handling:** Always use try-except blocks
4. **Logging:** Monitor logs for HTML structure changes
5. **Headless Mode:** Use `headless=True` in production

## 🔒 Security

- Never commit `instagram_session.json`
- Don't share session files
- Use environment variables for sensitive data
- Respect Instagram's Terms of Service

## 📝 License

MIT License - Use freely with attribution

## 👨‍💻 Author

AI Assistant - Professional Instagram Scraping Library

---

**Note:** This is a professional library designed for legitimate use cases like data analysis, research, and automation. Always respect Instagram's Terms of Service and rate limits.
