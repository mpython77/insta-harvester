# 📚 Examples

Ready-to-use scripts for InstaHarvest. **Run `save_session.py` first!**

---

## 📁 Scripts

| Script | Description |
|--------|-------------|
| `save_session.py` | 🔑 Create Instagram session (required, one-time) |
| `all_in_one.py` | 🎮 Interactive demo — ALL features in one menu |
| `main_advanced.py` | 🚀 Production scraping — parallel processing, Excel export |
| `example_web_api.py` | 🔌 Web API demo — 16+ JSON endpoints (profiles, reels, feed) |
| `example_notifications.py` | 🔔 Read & filter activity notifications |
| `example_post_data.py` | 📸 Post data extraction (JSON-first, 30+ fields) |
| `example_custom_config.py` | ⚙️ Configuration customization examples |
| `example_proxy.py` | 🌐 Proxy configuration & rotation |
| `download_media.py` | 📥 Download images & videos from posts/reels |

---

## 🚀 Quick Start

```bash
# 1. Create session (one-time)
python examples/save_session.py

# 2. Try interactive demo
python examples/all_in_one.py

# 3. Or try Web API
python examples/example_web_api.py
```

---

## 💡 Usage

All scripts should be run from the **project root**:

```bash
python examples/all_in_one.py        # Interactive demo
python examples/main_advanced.py     # Production scraping (3 parallel workers)
python examples/example_web_api.py   # Direct API access (profiles, reels, etc.)
```

**SharedBrowser (recommended for custom scripts):**

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

with SharedBrowser(config=ScraperConfig()) as browser:
    profile = browser.scrape_profile("username")
    browser.follow("user1")
    browser.send_message("user1", "Hello!")

    # Web API
    profile_json = browser.get_profile_json("username")
    reels = browser.get_reels_api(profile_json.user_id)
```

---

For full documentation, see the main [README.md](../README.md) 🚀
