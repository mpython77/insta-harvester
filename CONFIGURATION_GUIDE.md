# InstaHarvest Configuration Guide

## 📚 Complete Guide to Customizing Delays and Settings

InstaHarvest provides comprehensive configuration options to adapt to different internet speeds, Instagram rate limiting, and system performance. **All delays are now fully configurable** - no hardcoded values!

---

## 🚀 Quick Start

### Default Configuration (Recommended for Most Users)

```python
from instaharvest import FollowManager

# Uses default configuration - optimized for average internet speed
manager = FollowManager()
session_data = manager.load_session()
manager.setup_browser(session_data)

result = manager.unfollow("username")
manager.close()
```

### Custom Configuration

```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

# Create custom config
config = ScraperConfig(
    headless=True,           # Run in background
    page_load_delay=3.0,     # Wait 3s after page loads
    button_click_delay=2.0,  # Wait 2s after button clicks
)

# Use custom config
manager = FollowManager(config=config)
session_data = manager.load_session()
manager.setup_browser(session_data)

result = manager.unfollow("username")
manager.close()
```

---

## ⚙️ Configuration Categories

All timing values are in **seconds** and can be customized based on your needs.

### 1. Browser Settings

```python
config = ScraperConfig(
    headless=True,  # Run Chrome in background (no visible window)
    # headless=False  # Show browser window (useful for debugging)

    viewport_width=1920,
    viewport_height=1080,
    user_agent='Mozilla/5.0 ...'
)
```

**When to change:**
- Set `headless=False` when debugging to see what the browser is doing
- Keep `headless=True` in production for better performance

---

### 2. Page Navigation Delays

Controls waiting times for page loading and navigation.

```python
config = ScraperConfig(
    page_load_delay=2.0,        # Wait after page loads
    page_stability_delay=2.0,   # Wait for page to stabilize
    profile_load_delay=2.0,     # Wait after loading profiles
)
```

**When to change:**
- **Slow internet**: Increase to `4.0-5.0` seconds
- **Fast internet**: Decrease to `1.0-1.5` seconds
- **Unstable connection**: Increase to `5.0+` seconds

**Example for slow internet:**
```python
config = ScraperConfig(
    page_load_delay=5.0,
    page_stability_delay=4.0,
    profile_load_delay=4.0,
)
```

---

### 3. Button & Click Delays

Controls delays around button clicks and interactive elements.

```python
config = ScraperConfig(
    button_click_delay=2.5,    # Wait after clicking any button
    action_delay_min=2.0,      # Min random delay BEFORE clicking
    action_delay_max=3.5,      # Max random delay BEFORE clicking
)
```

**When to change:**
- **Instagram shows errors**: Increase delays
- **Smooth operation**: Can decrease slightly
- **Rate limiting concerns**: Increase significantly

**Example for avoiding rate limits:**
```python
config = ScraperConfig(
    button_click_delay=4.0,
    action_delay_min=3.0,
    action_delay_max=5.0,
)
```

---

### 4. Popup & Dialog Delays

Controls delays for popup dialogs (unfollow confirmation, etc.).

```python
config = ScraperConfig(
    popup_open_delay=2.5,           # Wait for popup to open
    popup_animation_delay=1.5,      # Wait for popup animation
    popup_content_load_delay=0.5,   # Wait for content inside popup
    popup_close_delay=0.5,          # Wait for popup to close
)
```

**When to change:**
- **"Could not unfollow" errors**: Increase `popup_open_delay` to `4.0+`
- **Slow animations**: Increase `popup_animation_delay`
- **Popup content not loading**: Increase `popup_content_load_delay`

**Example for fixing unfollow errors:**
```python
config = ScraperConfig(
    popup_open_delay=4.0,       # Give popup more time to appear
    popup_animation_delay=2.5,  # Wait longer for animation
    popup_content_load_delay=1.0,
)
```

---

### 5. Scroll Delays

Controls delays when scrolling (followers list, posts, etc.).

```python
config = ScraperConfig(
    scroll_delay_min=1.5,          # Min delay between scrolls
    scroll_delay_max=2.5,          # Max delay between scrolls
    scroll_post_delay=0.5,         # Wait after individual scroll
    scroll_content_load_delay=0.8, # Wait for content to load
    scroll_lazy_load_delay=1.5,    # Wait for lazy-loaded content
)
```

**When to change:**
- **Content not loading**: Increase all delays
- **Very slow connection**: Increase to `3.0-5.0` range
- **Fast scrolling needed**: Decrease (but may miss content)

**Example for slow loading:**
```python
config = ScraperConfig(
    scroll_delay_min=3.0,
    scroll_delay_max=5.0,
    scroll_content_load_delay=2.0,
    scroll_lazy_load_delay=3.0,
)
```

---

### 6. Input & Typing Delays

Controls delays when typing messages or interacting with text fields.

```python
config = ScraperConfig(
    input_focus_delay=0.5,              # Wait after clicking input field
    input_before_type_delay_min=1.0,    # Min wait before typing
    input_before_type_delay_max=1.5,    # Max wait before typing
    input_after_type_delay_min=0.5,     # Min wait after typing
    input_after_type_delay_max=1.0,     # Max wait after typing
)
```

**When to change:**
- **Message sending fails**: Increase after-type delays
- **Input field not ready**: Increase before-type delays

---

### 7. Post/Reel Scraping Delays

Controls delays when scraping posts and reels.

```python
config = ScraperConfig(
    post_open_delay=3.0,            # Wait after opening post
    post_scrape_delay_min=2.0,      # Min delay when scraping
    post_scrape_delay_max=4.0,      # Max delay when scraping
    post_navigation_delay=1.5,      # Wait between posts

    reel_open_delay=3.0,            # Wait after opening reel
    reel_scrape_delay_min=2.0,      # Min delay when scraping
    reel_scrape_delay_max=4.0,      # Max delay when scraping
)
```

**When to change:**
- **Content not fully loaded**: Increase open delays
- **Scraping too fast**: Increase scrape delays

---

### 8. Rate Limiting Delays

**IMPORTANT**: These delays help avoid Instagram blocks and rate limiting.

```python
config = ScraperConfig(
    follow_delay_min=2.0,               # Min delay after follow/unfollow
    follow_delay_max=4.0,               # Max delay after follow/unfollow
    message_delay_min=3.0,              # Min delay after sending message
    message_delay_max=5.0,              # Max delay after sending message
    batch_operation_delay_min=2.0,      # Min delay between batch ops
    batch_operation_delay_max=4.0,      # Max delay between batch ops
)
```

**When to change:**
- **Getting rate limited/blocked**: Increase ALL to `5.0-10.0` seconds
- **Normal operation**: Keep defaults
- **Being very careful**: Increase to `10.0-15.0` seconds

**Example for maximum safety:**
```python
config = ScraperConfig(
    follow_delay_min=8.0,
    follow_delay_max=15.0,
    message_delay_min=10.0,
    message_delay_max=20.0,
    batch_operation_delay_min=5.0,
    batch_operation_delay_max=10.0,
)
```

---

### 9. UI Stability Delays

Fine-grained delays for UI elements and animations.

```python
config = ScraperConfig(
    ui_animation_delay=1.5,      # Wait for UI animations
    ui_stability_delay=1.0,      # Wait for UI to stabilize
    ui_micro_delay=0.3,          # Tiny delay for UI updates
    ui_mini_delay=0.5,           # Small delay for quick changes
    ui_element_load_delay=0.1,   # Very small delay for elements
)
```

**When to change:**
- Usually don't need to change these
- Increase if UI seems glitchy or unstable

---

## 🌍 Common Use Cases

### 1. Slow Internet Connection

```python
config = ScraperConfig(
    # Browser
    headless=True,

    # Pages load slowly
    page_load_delay=5.0,
    page_stability_delay=4.0,

    # Buttons take time to respond
    button_click_delay=4.0,
    action_delay_min=3.0,
    action_delay_max=5.0,

    # Popups load slowly
    popup_open_delay=4.0,
    popup_animation_delay=2.5,

    # Scrolling needs time
    scroll_delay_min=3.0,
    scroll_delay_max=5.0,
    scroll_content_load_delay=2.0,

    # Be extra safe with rate limiting
    follow_delay_min=5.0,
    follow_delay_max=8.0,
)
```

### 2. Fast Internet Connection

```python
config = ScraperConfig(
    # Browser
    headless=True,

    # Fast page loads
    page_load_delay=1.0,
    page_stability_delay=1.0,

    # Quick button responses
    button_click_delay=1.5,
    action_delay_min=1.0,
    action_delay_max=2.0,

    # Fast popups
    popup_open_delay=1.5,
    popup_animation_delay=1.0,

    # Quick scrolling
    scroll_delay_min=1.0,
    scroll_delay_max=1.5,

    # Still be safe with rate limiting
    follow_delay_min=2.0,
    follow_delay_max=4.0,
)
```

### 3. Debugging (Visible Browser)

```python
config = ScraperConfig(
    # Show browser so you can see what's happening
    headless=False,

    # Slower delays so you can observe
    page_load_delay=3.0,
    button_click_delay=3.0,
    action_delay_min=2.0,
    action_delay_max=3.0,
    popup_open_delay=3.0,
)
```

### 4. Maximum Safety (Avoid Blocks)

```python
config = ScraperConfig(
    # Browser
    headless=True,

    # Slow and steady
    page_load_delay=4.0,
    button_click_delay=5.0,
    action_delay_min=4.0,
    action_delay_max=6.0,

    # Be very careful with actions
    popup_open_delay=5.0,

    # Long delays to avoid rate limits
    follow_delay_min=10.0,
    follow_delay_max=15.0,
    message_delay_min=15.0,
    message_delay_max=20.0,
    batch_operation_delay_min=8.0,
    batch_operation_delay_max=12.0,
)
```

---

## 📖 Full Working Examples

### Example 1: Unfollow with Custom Config

```python
from instaharvest import FollowManager
from instaharvest.config import ScraperConfig

# Custom config for slow internet
config = ScraperConfig(
    headless=True,
    page_load_delay=4.0,
    button_click_delay=3.0,
    popup_open_delay=4.0,
    follow_delay_min=5.0,
    follow_delay_max=8.0,
)

# Use the config
manager = FollowManager(config=config)

try:
    session_data = manager.load_session()
    manager.setup_browser(session_data)

    # Now all operations use your custom delays!
    result = manager.unfollow("username")
    print(result)
finally:
    manager.close()
```

### Example 2: Collect Followers with Custom Config

```python
from instaharvest import FollowersCollector
from instaharvest.config import ScraperConfig

# Config for fast internet
config = ScraperConfig(
    headless=True,
    page_load_delay=1.5,
    popup_open_delay=2.0,
    scroll_delay_min=1.0,
    scroll_delay_max=2.0,
)

collector = FollowersCollector(config=config)

try:
    session_data = collector.load_session()
    collector.setup_browser(session_data)

    followers = collector.get_followers("instagram", limit=100)
    print(f"Collected {len(followers)} followers")
finally:
    collector.close()
```

### Example 3: Send Messages with Maximum Safety

```python
from instaharvest import MessageManager
from instaharvest.config import ScraperConfig

# Maximum safety config
config = ScraperConfig(
    headless=True,
    page_load_delay=4.0,
    button_click_delay=4.0,
    popup_open_delay=4.0,
    message_delay_min=15.0,  # Long delays between messages
    message_delay_max=20.0,
)

manager = MessageManager(config=config)

try:
    session_data = manager.load_session()
    manager.setup_browser(session_data)

    result = manager.send_message("username", "Hello!")
    print(result)
finally:
    manager.close()
```

---

## 🎯 Tips and Best Practices

### ✅ DO:
- Start with default config and adjust only if needed
- Increase delays if you see errors or rate limiting
- Use `headless=False` when debugging
- Test with small operations before bulk actions
- Monitor Instagram's response and adjust accordingly

### ❌ DON'T:
- Don't set all delays to minimum (will cause errors)
- Don't ignore rate limiting warnings
- Don't run too many operations too quickly
- Don't decrease delays below `1.0` second unless testing
- Don't use same config for all internet speeds

---

## 🔧 Troubleshooting

### Problem: "Could not unfollow" errors

**Solution:** Increase popup delays
```python
config = ScraperConfig(
    popup_open_delay=4.0,
    popup_animation_delay=2.5,
    button_click_delay=3.0,
)
```

### Problem: Content not loading (followers, posts, etc.)

**Solution:** Increase scroll and load delays
```python
config = ScraperConfig(
    scroll_delay_min=3.0,
    scroll_delay_max=5.0,
    scroll_content_load_delay=2.0,
    scroll_lazy_load_delay=3.0,
)
```

### Problem: Getting rate limited/blocked

**Solution:** Increase rate limiting delays significantly
```python
config = ScraperConfig(
    follow_delay_min=10.0,
    follow_delay_max=15.0,
    message_delay_min=15.0,
    message_delay_max=20.0,
    batch_operation_delay_min=8.0,
    batch_operation_delay_max=12.0,
)
```

### Problem: Pages loading too slowly

**Solution:** Increase page load delays
```python
config = ScraperConfig(
    page_load_delay=5.0,
    page_stability_delay=4.0,
)
```

---

## 📚 See Also

- `examples/example_custom_config.py` - Complete working examples
- `instaharvest/config.py` - Full configuration source code
- `README.md` - Main documentation

---

## 💡 Need Help?

If you're unsure about configuration:
1. Start with defaults
2. If errors occur, increase relevant delays by 50-100%
3. Test again
4. Repeat until stable

**Remember:** Slower is safer! Instagram prefers natural, human-like behavior.
