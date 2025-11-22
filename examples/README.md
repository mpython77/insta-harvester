# 📚 Examples Directory

This folder contains all example scripts and usage demonstrations for InstaHarvest.

---

## 📁 Directory Structure

```
examples/
├── README.md                    # This file
├── save_session.py             # Create Instagram session
├── example_custom_config.py    # Configuration examples
│
├── Basic Operations:
│   ├── follow_user.py          # Follow users
│   ├── unfollow_user.py        # Unfollow users
│   ├── send_message.py         # Send direct messages
│   ├── get_followers.py        # Collect followers
│   └── get_following.py        # Collect following
│
├── Testing Scripts:
│   ├── test_phase1.py          # Test link collection
│   ├── test_phase2.py          # Test data extraction
│   ├── test_professional.py    # Test professional features
│   ├── test_follow.py          # Test follow operations
│   ├── test_followers.py       # Test follower collection
│   ├── test_message.py         # Test messaging
│   └── test_shared_browser.py  # Test shared browser
│
└── Complete Examples:
    ├── main.py                  # Simple scraping example
    ├── main_advanced.py         # Advanced scraping
    └── all_in_one.py           # All features demo
```

---

## 🚀 Quick Start

### 1. Create Session (Required First!)
```bash
cd examples
python save_session.py
```

### 2. Try Basic Operations

**Follow/Unfollow:**
```bash
python follow_user.py     # Follow a user
python unfollow_user.py   # Unfollow a user
```

**Messaging:**
```bash
python send_message.py    # Send a DM
```

**Collect Data:**
```bash
python get_followers.py   # Get followers list
python get_following.py   # Get following list
```

### 3. Advanced Usage

**Custom Configuration:**
```bash
python example_custom_config.py
```

**Full Scraping:**
```bash
python main_advanced.py   # Production scraping
```

---

## 📖 Detailed Examples

### 1️⃣ **test_phase1.py** - Link Collection Test
Tests Phase 1 functionality: Collecting Post and Reel links

**What it does:**
- Collects all post and reel links from profile
- Identifies type of each link (Post/Reel)
- Shows statistics (how many posts, how many reels)

**How to use:**
```bash
python examples/test_phase1.py

# Input: Instagram username
# Output: Link list with types
```

**Output example:**
```
📋 First 10 links (with types):
  1. [Post] https://instagram.com/p/ABC123/
  2. [Reel] https://instagram.com/reel/XYZ789/
  3. [Post] https://instagram.com/p/DEF456/
  ...

Statistics:
  📸 Posts: 15
  🎬 Reels: 8
```

---

### 2️⃣ **test_phase2.py** - Data Extraction Test
Tests Phase 2 functionality: Extracting data from Posts and Reels

**What it does:**
- Extracts data from one or more URLs
- Uses different extraction methods for Reels and Posts
- Shows tags, likes, date

**How to use:**
```bash
python examples/test_phase2.py

# Mode 1: Test single reel
# Mode 2: Test mixed content (posts + reels)
```

**Test Mode 1 - Single reel:**
```
Enter Instagram reel URL: https://instagram.com/reel/ABC123/

Output:
✅ REEL EXTRACTION TEST COMPLETE!
Content Type: Reel
Likes: 1234
Date: Nov 17, 2025
Tagged Accounts: ['user1', 'user2']
```

**Test Mode 2 - Multiple URLs:**
```
Enter URLs:
  URL 1: https://instagram.com/p/ABC123/
  URL 2: https://instagram.com/reel/XYZ789/
  URL 3: [Enter - empty]

Output:
✅ MIXED CONTENT TEST COMPLETE!
Total URLs: 2
Successfully scraped: 2/2
  📸 Posts: 1
  🎬 Reels: 1
```

---

### 3️⃣ **test_professional.py** - Professional Features Test
Tests all professional features

**What it does:**
- HTML diagnostics
- Error recovery
- Performance monitoring
- Detailed statistics

**How to use:**
```bash
python examples/test_professional.py

# Mode 1: Test multiple URLs (full statistics)
# Mode 2: Test single URL (detailed diagnostics)
```

**Test Mode 1 - Multiple URLs:**
```
📦 Scraping 5 posts/reels...
💻 SYSTEM INFO:
  CPU: 8 cores @ 15.2%
  RAM: 12.3/16.0 GB available

[1/5] Processing [Post]: https://...
🔍 Running diagnostics...
  ✓ tags_primary: Found 3 elements
  ✓ likes_button: Found 1 elements
✅ Extracted: 3 tags, 1234 likes

📊 SCRAPING COMPLETE
Success Rate: 100.0%
Performance: 4.5s per item
Recovery Rate: 95.3%
```

**Test Mode 2 - Single URL with diagnostics:**
```
🔍 Running full diagnostics on: https://...

POST diagnostics:
  ✓ tags_primary -> div._aa1y (Found 3)
  ✓ likes_button -> span[role="button"] (Found 1)
  ✗ timestamp -> time (NOT FOUND)

Diagnostics: PARTIAL (83.3% success rate)
⚠️ Some HTML selectors may have changed
```

---

### 4️⃣ **test_follow.py** - Follow/Unfollow Management Test
Tests Follow/Unfollow functionality

**What it does:**
- Follow Instagram users
- Unfollow Instagram users
- Check following status
- Batch follow multiple users
- Smart follow with status check

**How to use:**
```bash
python examples/test_follow.py

# Choose from 5 examples:
# 1. Follow a single user
# 2. Check if following a user
# 3. Unfollow a user
# 4. Batch follow multiple users
# 5. Smart follow (check status first)
```

**Example 1 - Single Follow:**
```
Enter username to follow (without @): instagram

🔄 Following @instagram...
✅ Successfully followed @instagram
Status: followed
```

**Example 2 - Check Status:**
```
Enter username to check (without @): instagram

🔍 Checking status for @instagram...
✅ You are following @instagram
```

**Example 3 - Unfollow:**
```
Enter username to unfollow (without @): instagram

🔄 Unfollowing @instagram...
✅ Successfully unfollowed @instagram
Status: unfollowed
```

**Example 4 - Batch Follow:**
```
Enter usernames to follow (one per line, empty line to finish):
  Username 1: user1
  Username 2: user2
  Username 3: user3
  Username 4: [Enter]

🔄 Following 3 users...

📊 BATCH FOLLOW SUMMARY
Total users: 3
Successfully followed: 2
Already following: 1
Failed: 0

Individual results:
  ✅ @user1: followed
  ✅ @user2: already_following
  ✅ @user3: followed
```

**Example 5 - Smart Follow:**
```
Enter username (without @): instagram

🔍 Checking current status for @instagram...
ℹ️ You are not following @instagram

Do you want to follow? (yes/no): yes

🔄 Following @instagram...
✅ Successfully followed @instagram
```

---

### 5️⃣ **test_message.py** - Direct Message Management Test
Tests direct messaging functionality

**What it does:**
- Send DM to single user
- Batch send to multiple users
- Send personalized messages
- Smart rate limiting

**How to use:**
```bash
python examples/test_message.py

# Choose from 3 examples:
# 1. Send single message
# 2. Batch send same message to multiple users
# 3. Send personalized messages to different users
```

**Example 1 - Single Message:**
```
Enter username to message (without @): instagram
Enter your message: Hello from Python!

📨 Sending message to @instagram...
✅ Successfully sent message to @instagram
Status: sent
```

**Example 2 - Batch Send:**
```
Enter message to send to all: Check out my new project!

Enter usernames (one per line, empty line to finish):
  Username 1: user1
  Username 2: user2
  Username 3: user3
  Username 4: [Enter]

📨 Sending message to 3 users...

📊 BATCH SEND SUMMARY
Total users: 3
Successfully sent: 3
Failed: 0

Individual results:
  ✅ @user1: sent
  ✅ @user2: sent
  ✅ @user3: sent
```

**Example 3 - Personalized Messages:**
```
Enter username and message pairs (empty username to finish):

  Username 1: john
  Message for @john: Hey John, thanks for the follow!

  Username 2: alice
  Message for @alice: Alice, loved your recent post!

  Username 3: [Enter]

📨 Sending 2 personalized messages...

📊 PERSONALIZED SEND SUMMARY
Total messages: 2
Successfully sent: 2
Failed: 0

Results:
  ✅ @john: sent
  ✅ @alice: sent
```

---

## 🚀 When to Use Which Test

### Testing New Profile:
```bash
python examples/test_phase1.py
# Quick test - only collects links
```

### Testing Reel Extraction:
```bash
python examples/test_phase2.py
# Test specific reel extraction
```

### Checking HTML Changes:
```bash
python examples/test_professional.py
# Find out if Instagram HTML changed
```

### Testing Follow/Unfollow:
```bash
python examples/test_follow.py
# Test follow and unfollow operations
```

### Testing Direct Messaging:
```bash
python examples/test_message.py
# Test sending DMs
```

### Full Production Scraping:
```bash
python examples/main_advanced.py
# This is not a test, full scraping!
```

---

## 🎯 Configuration Examples

### Using Custom Configuration:
```bash
python examples/example_custom_config.py
```

This shows:
- Custom delays for slow/fast internet
- Headless mode control
- Rate limiting configuration
- All 41+ configurable parameters

See `../CONFIGURATION_GUIDE.md` for complete documentation.

---

## 💡 Tips

1. **Before testing:**
   - Create Instagram session: `python examples/save_session.py`
   - Check internet connection

2. **Which script to use:**
   - Link collection issue → `test_phase1.py`
   - Data extraction issue → `test_phase2.py`
   - HTML changes → `test_professional.py`
   - Follow/Unfollow testing → `test_follow.py`
   - Direct messaging testing → `test_message.py`
   - Configuration testing → `example_custom_config.py`

3. **For production:**
   - Scraping: use `main_advanced.py`
   - Following: use `follow_user.py` or `unfollow_user.py`
   - Messaging: use `send_message.py`
   - Custom config: see `example_custom_config.py`

4. **All scripts must be run from root directory:**
   ```bash
   # From project root
   python examples/script_name.py
   ```

---

## 📊 Test vs Production

| Feature | Test Scripts | main_advanced.py |
|---------|-------------|------------------|
| Purpose | Debug & testing | Full scraping |
| Input | Manual URLs | Only username |
| Output | Console only | Excel + JSON |
| Diagnostics | Detailed | Auto |
| Use Case | Development | Production |

---

## 🎯 Example Workflow

```bash
# From project root directory:

# 1. Create session (required!)
python examples/save_session.py

# 2. Test Phase 1 (link collection)
python examples/test_phase1.py
# Check: Are links collected correctly?

# 3. Test Phase 2 (data extraction)
python examples/test_phase2.py
# Check: Is data extracted correctly?

# 4. Test Professional features
python examples/test_professional.py
# Check: Do diagnostics work?

# 5. Try custom configuration
python examples/example_custom_config.py
# Learn how to customize delays

# 6. Full production scraping
python examples/main_advanced.py
# Real scraping with all features!
```

---

## 📚 Related Documentation

- `../CONFIGURATION_GUIDE.md` - Complete configuration guide (300+ lines)
- `../README.md` - Main project documentation
- `../instaharvest/` - Library source code

---

All scripts in this directory are **examples and demonstrations**.

For **library usage** in your code, import from `instaharvest`:
```python
from instaharvest import FollowManager, MessageManager
from instaharvest.config import ScraperConfig
```

For **production scraping** use `examples/main_advanced.py`! 🚀
