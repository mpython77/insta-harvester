# 📖 InstaHarvest Configuration - Complete Beginner's Guide

## 📌 Table of Contents
1. [What is Configuration?](#what-is-configuration)
2. [Why Do We Need Configuration?](#why-do-we-need-configuration)
3. [When to Use Configuration?](#when-to-use-configuration)
4. [How to Use Configuration?](#how-to-use-configuration)
5. [Real-World Examples](#real-world-examples)
6. [Troubleshooting Guide](#troubleshooting-guide)

---

## 🤔 What is Configuration?

**Configuration** is a system that allows you to control **all timing and behavior** of InstaHarvest without changing the library code.

Think of it like this:
- **Without config**: The library uses fixed delays (2 seconds, 3 seconds, etc.)
- **With config**: You decide the delays based on YOUR internet speed and needs

### The Configuration Class

```python
from instaharvest.config import ScraperConfig

# This is the configuration object that controls EVERYTHING
config = ScraperConfig(
    headless=True,              # Run Chrome in background?
    page_load_delay=2.0,        # How long to wait after loading pages?
    button_click_delay=2.5,     # How long to wait after clicking buttons?
    popup_open_delay=2.5,       # How long to wait for popups to open?
    # ... 40+ more parameters
)
```

---

## ❓ Why Do We Need Configuration?

### Problem 1: Different Internet Speeds

**Your situation**: You have slow internet
- Instagram pages load slowly
- Buttons don't respond immediately
- The program runs too fast → errors like "Could not unfollow @username"

**Solution**: Increase delays in configuration
```python
config = ScraperConfig(
    page_load_delay=5.0,        # Wait 5 seconds instead of 2
    popup_open_delay=4.0,       # Wait 4 seconds for popups
)
```

### Problem 2: Instagram Rate Limiting

**Your situation**: Instagram is blocking you
- Too many follows/unfollows
- Too many messages sent quickly
- Instagram shows "Try again later"

**Solution**: Increase rate limiting delays
```python
config = ScraperConfig(
    follow_delay_min=10.0,      # Wait 10-15 seconds between follows
    follow_delay_max=15.0,
    message_delay_min=15.0,     # Wait 15-20 seconds between messages
    message_delay_max=20.0,
)
```

### Problem 3: Unfollow Popup Issues

**Your situation**: The unfollow button requires 2 clicks (confirmation popup), but program is too fast
- Click "Following" button → popup appears
- Program doesn't wait → tries to click before popup loads
- Result: "Could not unfollow" error

**Solution**: Increase popup delays
```python
config = ScraperConfig(
    popup_open_delay=3.5,       # Give popup time to open
    action_delay_min=2.5,       # Wait before clicking buttons
    action_delay_max=4.0,
)
```

---

## ⏰ When to Use Configuration?

### ✅ You SHOULD use configuration when:

1. **Getting errors** - "Could not follow", "Could not send message", etc.
2. **Slow internet** - Pages load slowly, content takes time to appear
3. **Instagram blocking** - Rate limiting, temporary blocks
4. **Different language** - Instagram interface loads slower in some languages
5. **First time using** - Test with slower delays first, then optimize

### ❌ You DON'T need configuration when:

1. **Everything works** - Default settings are fine
2. **Fast internet** - Content loads instantly
3. **No errors** - Program runs smoothly

---

## 🚀 How to Use Configuration?

### Method 1: Default Configuration (No Setup Needed)

```python
from instaharvest import FollowManager

# Uses default configuration automatically
manager = FollowManager()
session_data = manager.load_session()
manager.setup_browser(session_data)

# Follow someone
result = manager.follow("instagram")
print(result)

manager.close()
```

**When to use**: When default settings work fine for you.

---

### Method 2: Custom Configuration (Recommended)

```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

# Step 1: Create your custom configuration
config = ScraperConfig(
    headless=True,              # Run in background
    page_load_delay=3.0,        # Wait 3 seconds after page loads
    popup_open_delay=3.5,       # Wait 3.5 seconds for popups
)

# Step 2: Pass config to manager
manager = FollowManager(config=config)

# Step 3: Use normally
session_data = manager.load_session()
manager.setup_browser(session_data)

result = manager.unfollow("username")
manager.close()
```

**When to use**: When you need custom delays for your situation.

---

### Method 3: All Managers with Same Config

```python
from instaharvest import FollowManager, MessageManager, FollowersCollector
from instaharvest.config import ScraperConfig

# Create ONE config for all operations
config = ScraperConfig(
    headless=True,
    page_load_delay=4.0,
    popup_open_delay=3.0,
)

# Use same config for different managers
follow_manager = FollowManager(config=config)
message_manager = MessageManager(config=config)
collector = FollowersCollector(config=config)

# Now all managers use the same timing settings
```

**When to use**: When you want consistent behavior across all operations.

---

### Method 4: SharedBrowser with Config

```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

# Custom config
config = ScraperConfig(
    headless=False,             # Show browser (for testing)
    page_load_delay=3.0,
    popup_open_delay=4.0,
)

# Use with SharedBrowser
with SharedBrowser(config=config) as browser:
    # All operations use your custom config
    browser.follow("user1")
    browser.send_message("user2", "Hello!")
    followers = browser.get_followers("user3")
```

**When to use**: When doing multiple operations in one session.

---

## 🌟 Real-World Examples

### Example 1: Fix "Could Not Unfollow" Error

**Problem**: Getting "Could not unfollow @username" errors

**Reason**: Unfollow popup appears too slowly, program clicks before it's ready

**Solution**:
```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

# Increase popup and action delays
config = ScraperConfig(
    popup_open_delay=4.0,       # Wait 4 seconds for popup
    popup_animation_delay=2.5,  # Wait for animation
    action_delay_min=3.0,       # Wait 3-4 seconds before clicking
    action_delay_max=4.0,
    button_click_delay=3.0,     # Wait 3 seconds after clicking
)

manager = FollowManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

# Now unfollow should work
result = manager.unfollow("username")
print(result)  # Should show success

manager.close()
```

---

### Example 2: Slow Internet Connection

**Problem**: You have slow internet, content loads slowly

**Solution**:
```python
from instaharvest import ProfileScraper
from instaharvest.config import ScraperConfig

# Increase ALL delays for slow internet
config = ScraperConfig(
    # Pages load slowly
    page_load_delay=6.0,
    page_stability_delay=5.0,
    profile_load_delay=5.0,

    # Buttons respond slowly
    button_click_delay=4.0,
    action_delay_min=3.0,
    action_delay_max=5.0,

    # Popups open slowly
    popup_open_delay=5.0,
    popup_animation_delay=3.0,

    # Scrolling loads content slowly
    scroll_delay_min=3.0,
    scroll_delay_max=5.0,
    scroll_content_load_delay=2.0,
    scroll_lazy_load_delay=3.0,
)

scraper = ProfileScraper(config=config)
session_data = scraper.load_session()
scraper.setup_browser(session_data)

# Now scraping works with slow internet
profile = scraper.scrape("username")
print(f"Posts: {profile.posts}")
print(f"Followers: {profile.followers}")

scraper.close()
```

---

### Example 3: Avoid Instagram Rate Limiting

**Problem**: Instagram is blocking you - "Try again later" message

**Reason**: Too many operations too quickly (looks like a bot)

**Solution**:
```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

# Increase rate limiting delays significantly
config = ScraperConfig(
    # Wait longer between follows
    follow_delay_min=10.0,      # Minimum 10 seconds
    follow_delay_max=15.0,      # Maximum 15 seconds

    # Wait longer between messages
    message_delay_min=15.0,     # Minimum 15 seconds
    message_delay_max=20.0,     # Maximum 20 seconds

    # Wait longer in batch operations
    batch_operation_delay_min=8.0,
    batch_operation_delay_max=12.0,

    # Slower button clicks (more human-like)
    action_delay_min=3.0,
    action_delay_max=5.0,
)

manager = FollowManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

# Follow multiple users safely (with long delays)
users = ["user1", "user2", "user3"]
for user in users:
    result = manager.follow(user)
    print(result)
    # Automatic 10-15 second delay happens here

manager.close()
```

---

### Example 4: Fast Internet + Testing Mode

**Problem**: You have fast internet and want to see what's happening

**Solution**:
```python
from instaharvest import MessageManager
from instaharvest.config import ScraperConfig

# Decrease delays + show browser
config = ScraperConfig(
    headless=False,             # SHOW browser (see what's happening)

    # Faster delays (fast internet)
    page_load_delay=1.0,
    popup_open_delay=1.5,
    button_click_delay=1.5,
    action_delay_min=1.0,
    action_delay_max=2.0,
)

manager = MessageManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

# You'll see the browser and operations happen faster
result = manager.send_message("friend", "Test message")
print(result)

manager.close()
```

---

### Example 5: Collect Many Followers (Slow and Safe)

**Problem**: Need to collect 1000+ followers without getting blocked

**Solution**:
```python
from instaharvest import FollowersCollector
from instaharvest.config import ScraperConfig

# Safe scrolling delays
config = ScraperConfig(
    # Popup handling
    popup_open_delay=3.0,

    # Scroll slowly (don't trigger Instagram detection)
    scroll_delay_min=2.5,       # Wait 2.5-4 seconds between scrolls
    scroll_delay_max=4.0,
    scroll_content_load_delay=1.5,
    scroll_lazy_load_delay=2.0,
)

collector = FollowersCollector(config=config)
session_data = collector.load_session()
collector.setup_browser(session_data)

# Collect followers slowly and safely
followers = collector.get_followers(
    "celebrity_account",
    limit=1000,
    print_realtime=True
)

print(f"\n✅ Collected {len(followers)} followers")

# Save to file
with open("followers.txt", "w") as f:
    for follower in followers:
        f.write(f"{follower}\n")

collector.close()
```

---

### Example 6: Batch Send Messages (Maximum Safety)

**Problem**: Need to send messages to 50 people without being flagged

**Solution**:
```python
from instaharvest import MessageManager
from instaharvest.config import ScraperConfig

# Very slow and safe for bulk messaging
config = ScraperConfig(
    # Slow page navigation
    page_load_delay=3.0,

    # Slow popup handling
    popup_open_delay=3.5,

    # Slow typing (more human-like)
    input_before_type_delay_min=2.0,
    input_before_type_delay_max=3.0,
    input_after_type_delay_min=1.5,
    input_after_type_delay_max=2.5,

    # LONG delays between messages
    message_delay_min=20.0,     # 20-30 seconds between each message
    message_delay_max=30.0,

    # LONG delays in batch operations
    batch_operation_delay_min=15.0,
    batch_operation_delay_max=25.0,
)

manager = MessageManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

# Send messages to many people
users = ["user1", "user2", "user3", "user4", "user5"]
message = "Hey! Just wanted to say hi 👋"

for user in users:
    result = manager.send_message(user, message)
    print(f"✅ Sent to @{user}")
    # Automatic 20-30 second delay happens here

manager.close()
```

---

### Example 7: All-in-One Operations (Production Ready)

**Problem**: Need to do everything (follow, message, collect) in one session

**Solution**:
```python
from instaharvest import SharedBrowser
from instaharvest.config import ScraperConfig

# Balanced config for all operations
config = ScraperConfig(
    headless=True,

    # Moderate page delays
    page_load_delay=2.5,
    page_stability_delay=2.0,

    # Moderate button delays
    button_click_delay=2.5,
    action_delay_min=2.0,
    action_delay_max=3.5,

    # Moderate popup delays
    popup_open_delay=3.0,
    popup_animation_delay=2.0,

    # Safe rate limiting
    follow_delay_min=5.0,
    follow_delay_max=8.0,
    message_delay_min=8.0,
    message_delay_max=12.0,
)

# One browser for everything
with SharedBrowser(config=config) as browser:
    print("=== Step 1: Follow users ===")
    browser.follow("user1")
    browser.follow("user2")

    print("\n=== Step 2: Send messages ===")
    browser.send_message("user1", "Thanks for the follow!")
    browser.send_message("user2", "Hey, how are you?")

    print("\n=== Step 3: Collect followers ===")
    followers = browser.get_followers("my_account", limit=50)
    print(f"My followers: {len(followers)}")

    print("\n=== Step 4: Check following status ===")
    result = browser.is_following("instagram")
    print(f"Following Instagram: {result['following']}")

print("\n✅ All operations completed!")
```

---

## 🔧 Troubleshooting Guide

### Error: "Could not follow @username"

**Fix**:
```python
config = ScraperConfig(
    page_load_delay=4.0,        # Increase
    button_click_delay=3.0,     # Increase
    action_delay_min=2.5,       # Increase
    action_delay_max=4.0,       # Increase
)
```

---

### Error: "Could not unfollow @username"

**Fix**:
```python
config = ScraperConfig(
    popup_open_delay=4.0,       # Increase (MOST IMPORTANT)
    popup_animation_delay=2.5,  # Increase
    action_delay_min=3.0,       # Increase
    action_delay_max=4.5,       # Increase
    button_click_delay=3.0,     # Increase
)
```

---

### Error: "Could not send message to @username"

**Fix**:
```python
config = ScraperConfig(
    popup_open_delay=3.5,       # Message box is a popup
    input_before_type_delay_min=2.0,
    input_before_type_delay_max=3.0,
    input_after_type_delay_min=1.5,
    input_after_type_delay_max=2.0,
)
```

---

### Error: "Followers list incomplete" or "Missing followers"

**Fix**:
```python
config = ScraperConfig(
    popup_open_delay=3.0,       # Followers popup
    scroll_delay_min=2.5,       # Slow down scrolling
    scroll_delay_max=4.0,
    scroll_content_load_delay=2.0,  # Wait for content
    scroll_lazy_load_delay=3.0,     # Wait for lazy loading
)
```

---

### Error: "Instagram says 'Try again later'"

**Fix**:
```python
config = ScraperConfig(
    # INCREASE ALL RATE LIMITING DELAYS
    follow_delay_min=15.0,
    follow_delay_max=20.0,
    message_delay_min=20.0,
    message_delay_max=30.0,
    batch_operation_delay_min=10.0,
    batch_operation_delay_max=15.0,
)
```

---

### Pages Load Slowly (Blank Screen)

**Fix**:
```python
config = ScraperConfig(
    page_load_delay=5.0,        # Increase significantly
    page_stability_delay=4.0,
    profile_load_delay=5.0,
)
```

---

## 📊 Quick Reference: What Delay to Change?

| Problem | Increase This Delay |
|---------|-------------------|
| "Could not follow" | `button_click_delay`, `action_delay_min/max` |
| "Could not unfollow" | `popup_open_delay` ⭐ MOST IMPORTANT |
| "Could not send message" | `popup_open_delay`, `input_*_delay` |
| Missing followers/following | `scroll_delay_min/max`, `scroll_content_load_delay` |
| Instagram rate limiting | `follow_delay_*`, `message_delay_*` |
| Pages load slowly | `page_load_delay`, `page_stability_delay` |
| Popups don't open | `popup_open_delay`, `popup_animation_delay` |
| Content not loading | `scroll_lazy_load_delay`, `scroll_content_load_delay` |

---

## 💡 Best Practices

### 1. Start Slow, Then Optimize
```python
# First time: Use SLOW delays
config = ScraperConfig(
    page_load_delay=5.0,
    popup_open_delay=4.0,
    # ... other slow delays
)

# After testing: If it works, you can decrease delays
config = ScraperConfig(
    page_load_delay=2.0,  # Faster now
    popup_open_delay=2.5,
)
```

### 2. Test with `headless=False` First
```python
# WHILE TESTING: See the browser
config = ScraperConfig(headless=False)

# PRODUCTION: Hide the browser
config = ScraperConfig(headless=True)
```

### 3. One Config for All Operations
```python
# DON'T create new config for each operation
# DO create ONE config and reuse it

config = ScraperConfig(...)  # Create once

manager1 = FollowManager(config=config)  # Reuse
manager2 = MessageManager(config=config)  # Reuse
```

### 4. Save Your Working Config
```python
# When you find delays that work well, save them!

# my_config.py
from instaharvest.config import ScraperConfig

MY_WORKING_CONFIG = ScraperConfig(
    headless=True,
    page_load_delay=3.0,
    popup_open_delay=3.5,
    # ... delays that work for you
)

# Then import in your scripts
from my_config import MY_WORKING_CONFIG
from instaharvest import FollowManager

manager = FollowManager(config=MY_WORKING_CONFIG)
```

---

## 📚 Related Documentation

- **CONFIGURATION_GUIDE.md** - Complete technical reference (all 41+ parameters)
- **examples/example_custom_config.py** - Working code examples
- **README.md** - Main documentation

---

## ✅ Summary

### What is Configuration?
A system to control all timing and behavior of InstaHarvest

### Why Do We Need It?
- Different internet speeds
- Instagram rate limiting
- Popup timing issues
- Content loading delays

### When to Use It?
- When getting errors
- When you have slow internet
- When Instagram is blocking you
- When default settings don't work

### How to Use It?
```python
from instaharvest.config import ScraperConfig

config = ScraperConfig(
    # Change any parameter you need
    popup_open_delay=4.0,
    page_load_delay=3.0,
)

# Pass to any manager
manager = FollowManager(config=config)
```

---

**Remember**: Start with SLOW delays, test, then optimize! 🚀

For complete list of all 41+ parameters, see `CONFIGURATION_GUIDE.md`
