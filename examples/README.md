# 📚 Examples Directory

This folder contains all example scripts and usage demonstrations for InstaHarvest.

---

## 📁 Directory Structure

```
examples/
├── save_session.py             # Create Instagram session (REQUIRED FIRST)
├── all_in_one.py               # Complete demo with ALL features
├── example_custom_config.py    # Configuration customization examples
└── unfollow_fixed.py           # Standalone unfollow script
```

**Note:** All operations (follow, unfollow, messaging, collect followers/following, batch operations, etc.) are demonstrated in `all_in_one.py`. It's a complete interactive menu showing all library features.

## 🚀 Quick Start

### 1. Save Instagram Session (ONE TIME ONLY)
```bash
cd examples
python save_session.py
```
This will:
- Open Chrome browser
- Let you login to Instagram manually
- Save session to `instagram_session.json`
- All future scripts use this session (no re-login!)

### 2. Try the Complete Demo
```bash
python all_in_one.py
```

This interactive menu demonstrates ALL library features:
- Follow/Unfollow users
- Send messages
- Collect followers/following
- Batch operations
- Profile scraping

### 3. Custom Configuration
```bash
python example_custom_config.py  # See configuration examples
```

```

---

## 📖 Library Usage Examples

### Example 1: Follow a User

```python
from instaharvest import FollowManager

manager = FollowManager()
session_data = manager.load_session()
manager.setup_browser(session_data)

result = manager.follow("instagram")
print(result)  # {'success': True, 'status': 'followed', ...}

manager.close()
```

### Example 2: Send Direct Message

```python
from instaharvest import MessageManager

manager = MessageManager()
session_data = manager.load_session()
manager.setup_browser(session_data)

result = manager.send_message("username", "Hello from Python!")
print(result)

manager.close()
```

### Example 3: Collect Followers

```python
from instaharvest import FollowersCollector

collector = FollowersCollector()
session_data = collector.load_session()
collector.setup_browser(session_data)

# Collect first 100 followers
followers = collector.get_followers("username", limit=100, print_realtime=True)
print(f"Collected {len(followers)} followers")

collector.close()
```

### Example 4: Using SharedBrowser (Recommended)

```python
from instaharvest import SharedBrowser

# Opens browser once, reuses for all operations
with SharedBrowser() as browser:
    # Follow
    result = browser.follow("user1")
    
    # Send message
    result = browser.send_message("user2", "Hello!")
    
    # Get followers
    followers = browser.get_followers("user3", limit=50)
    
    # Browser closes automatically

## 🎯 Usage Guide

### For Interactive Demo (Recommended for beginners):
```bash
python examples/all_in_one.py
```
This shows ALL features in an interactive menu - perfect for learning!

### For Custom Configuration:
```bash
python examples/example_custom_config.py  # See all config options
```

### For Production Code:
Use the library directly in your Python scripts (see examples above).

---

## 💡 Tips

1. **Before using:**
   - Create Instagram session ONCE: `python examples/save_session.py`
   - Session is saved and reused automatically

2. **Configuration:**
   - Default settings work for most users
   - Customize via `ScraperConfig` if needed
   - See `CONFIGURATION_GUIDE.md` for all 40+ parameters

3. **All scripts must be run from project root:**
   ```bash
   # From project root directory
   python examples/all_in_one.py
   ```

   ```
---

## 📚 Related Documentation

- `CONFIGURATION_GUIDE.md` - Complete configuration guide with all parameters
- Main project `README.md` - Full library documentation
- Library source: `instaharvest/` directory

---

## 🎯 Next Steps

1. **Create Instagram session** (required once):
   ```bash
   python examples/save_session.py
   ```

2. **Try the interactive demo**:
   ```bash
   python examples/all_in_one.py
   ```

3. **Use in your own code**:
   ```python
   from instaharvest import FollowManager, MessageManager, SharedBrowser
   from instaharvest.config import ScraperConfig
   ```

---

**For questions or issues, check the main README.md or open an issue on GitHub.** 🚀
