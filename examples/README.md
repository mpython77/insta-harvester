# 📚 Examples & Test Scripts

This folder contains example code for testing various functions of Instagram Scraper.

---

## 📋 Files

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

### Full Production Scraping:
```bash
python main_advanced.py
# This is not a test, full scraping!
```

---

## 💡 Tips

1. **Before testing:**
   - Create Instagram session: `python save_session.py`
   - Check internet connection

2. **Which test to use:**
   - Link collection issue → `test_phase1.py`
   - Data extraction issue → `test_phase2.py`
   - HTML changes → `test_professional.py`
   - Follow/Unfollow testing → `test_follow.py`

3. **For production:**
   - Scraping: use `main_advanced.py`
   - Following: use `follow_user.py` or `unfollow_user.py`

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
# 1. Test Phase 1 (link collection)
python examples/test_phase1.py
# Check: Are links collected correctly?

# 2. Test Phase 2 (data extraction)
python examples/test_phase2.py
# Check: Is data extracted correctly?

# 3. Test Professional features
python examples/test_professional.py
# Check: Do diagnostics work?

# 4. Full production scraping
python main_advanced.py
# Real scraping with all features!
```

---

All test scripts are for **development and debugging** purposes.

For **production scraping** use only `main_advanced.py`! 🚀
