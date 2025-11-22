# Instagram Scraper - Batafsil Foydalanish Misollari (Examples)

Bu faylda Instagram scraper'ni qanday ishlatishning professional misollari keltirilgan.

## 📋 Mundarija

1. [Boshlang'ich Setup](#1-boshlangich-setup)
2. [Oddiy Sequential Scraping](#2-oddiy-sequential-scraping)
3. [Parallel Scraping (Tez)](#3-parallel-scraping-tez)
4. [Real-time Excel Export](#4-real-time-excel-export)
5. [Custom Configuration](#5-custom-configuration)
6. [Faqat Taglarni Olish](#6-faqat-taglarni-olish)
7. [Error Handling](#7-error-handling)
8. [Production Usage](#8-production-usage)

---

## 1. Boshlang'ich Setup

### Birinchi marta - Session yaratish

```python
# save_session.py ni ishlating
python save_session.py

# Instagram'ga login qiling
# Session avtomatik saqlanadi: instagram_session.json
```

### Library import

```python
from instagram_scraper import (
    InstagramOrchestrator,
    ScraperConfig,
    ProfileScraper,
    PostDataScraper
)
```

---

## 2. Oddiy Sequential Scraping

**Qachon ishlatiladi:** Kichik profillar (10-50 posts), test qilish

```python
from instagram_scraper import InstagramOrchestrator

# Orchestrator yaratish
orchestrator = InstagramOrchestrator()

# SIMPLE: Bir username scraping
results = orchestrator.scrape_complete_profile_advanced(
    username='dindinku__',
    parallel=None,  # Sequential mode
    save_excel=False,
    export_json=True
)

# Natijalar
print(f"Profile: {results['profile']}")
print(f"Posts: {len(results['posts_data'])}")

# Har bir post
for post in results['posts_data']:
    print(f"URL: {post['url']}")
    print(f"Tags: {post['tagged_accounts']}")
    print(f"Likes: {post['likes']}")
    print("---")
```

**Log chiqishi:**
```
[INFO] STEP 1: Scraping profile stats...
[INFO] ✓ Profile: 39 posts, 14450 followers, 16 following
[INFO] STEP 2: Collecting post links...
[INFO] ✓ Collected 38 post links
[INFO] STEP 3: Scraping 38 posts (sequential)...
[INFO] [1/38] Scraping: https://...
[INFO] ✓ Found 4 tags (Playwright Method 1): ['user1', 'user2', ...]
[INFO] [2/38] Scraping: https://...
```

---

## 3. Parallel Scraping (Tez)

**Qachon ishlatiladi:** Ko'p postlar (50+), tez natija kerak

### Parallel=3 (Recommended)

```python
from instagram_scraper import InstagramOrchestrator

orchestrator = InstagramOrchestrator()

# 3 ta parallel worker (3x tezroq!)
results = orchestrator.scrape_complete_profile_advanced(
    username='dindinku__',
    parallel=3,  # 3 Chrome parallel
    save_excel=False,
    export_json=True
)

print(f"Scraped {len(results['posts_data'])} posts")
```

**Log chiqishi:**
```
[INFO] Starting 3 parallel processes for 38 posts
[INFO] Real-time monitoring enabled ✓

[Worker 1] [1/13] 🔍 Scraping: https://...
[Worker 2] [1/13] 🔍 Scraping: https://...
[Worker 3] [1/12] 🔍 Scraping: https://...

[Worker 1] [1/13] ✓ Page loaded
[Worker 1] [1/13] ✓ Tag elements detected
[Worker 1] ✓ Found 4 tags (BS4 Method 1): ['user1', 'user2', 'user3', 'user4']
[Worker 1] [1/13] ✅ DONE: 4 tags, 1234 likes

[INFO] 📦 [1/38] Worker 1 completed: 4 tags, 1234 likes
```

### Parallel=5 (Eng tez)

```python
# 5 ta parallel worker (5x tezroq!)
results = orchestrator.scrape_complete_profile_advanced(
    username='dindinku__',
    parallel=5,  # Maksimal tezlik
    save_excel=False,
    export_json=True
)
```

**Vaqt taqqoslash (38 posts):**
- Sequential (parallel=None): ~3.5 minut
- Parallel=3: ~1.2 minut (3x tez)
- Parallel=5: ~45 sekund (4.7x tez)

---

## 4. Real-time Excel Export

**Qachon ishlatiladi:** Natijalarni darhol Excel'da ko'rish kerak

```python
from instagram_scraper import InstagramOrchestrator

orchestrator = InstagramOrchestrator()

# Real-time Excel yozish
results = orchestrator.scrape_complete_profile_advanced(
    username='dindinku__',
    parallel=3,  # 3 parallel worker
    save_excel=True,  # Real-time Excel! ✓
    export_json=True
)

# Excel file: instagram_data_dindinku__.xlsx
```

**Log chiqishi:**
```
[INFO] Excel exporter initialized: instagram_data_dindinku__.xlsx
[INFO] 🚀 Starting parallel scraping with 3 workers...
[INFO] 📊 Real-time Excel writing: ENABLED

[Worker 1] [1/13] ✅ DONE: 4 tags, 1234 likes
[INFO] 📦 [1/38] Worker 1 completed: 4 tags, 1234 likes
[INFO]   ✓ Saved to Excel: https://...

[Worker 2] [1/13] ✅ DONE: 2 tags, 567 likes
[INFO] 📦 [2/38] Worker 2 completed: 2 tags, 567 likes
[INFO]   ✓ Saved to Excel: https://...
```

**Excel file structure:**
```
| Post URL                              | Tagged Accounts        | Likes Count | Post Date           | Scraping Date/Time    |
|---------------------------------------|------------------------|-------------|---------------------|----------------------|
| https://instagram.com/p/ABC123/       | user1, user2, user3    | 1234        | 2024-11-20 10:30    | 2024-11-22 15:45:10  |
| https://instagram.com/p/DEF456/       | user4, user5           | 567         | 2024-11-21 14:20    | 2024-11-22 15:45:25  |
```

---

## 5. Custom Configuration

**Headless mode (background scraping):**

```python
from instagram_scraper import InstagramOrchestrator, ScraperConfig

# Custom config
config = ScraperConfig(
    headless=True,  # Chrome background'da ishlaydi
    viewport_width=1920,
    viewport_height=1080,
    post_scrape_delay_min=1.0,
    post_scrape_delay_max=2.0
)

orchestrator = InstagramOrchestrator(config)

results = orchestrator.scrape_complete_profile_advanced(
    username='dindinku__',
    parallel=3,
    save_excel=True
)
```

**Timeout oshirish (sekin internet):**

```python
config = ScraperConfig(
    headless=False,
    default_timeout=90000,  # 90 sekund (default 60s)
    post_scrape_delay_max=3.0
)

orchestrator = InstagramOrchestrator(config)
```

---

## 6. Faqat Taglarni Olish

**Faqat tagged accounts kerak bo'lsa:**

```python
from instagram_scraper import PostDataScraper

scraper = PostDataScraper()
scraper.load_session()
scraper.setup_browser(scraper.load_session())

# Bir post uchun
scraper.goto_url('https://instagram.com/p/ABC123/')
tags = scraper.get_tagged_accounts()

print(f"Tags: {tags}")
# Output: Tags: ['user1', 'user2', 'user3', 'user4']

scraper.close()
```

**Bir nechta post:**

```python
from instagram_scraper import PostDataScraper

post_urls = [
    'https://instagram.com/p/ABC123/',
    'https://instagram.com/p/DEF456/',
    'https://instagram.com/p/GHI789/'
]

scraper = PostDataScraper()
results = scraper.scrape_multiple(
    post_urls,
    get_tags=True,    # Taglarni olish
    get_likes=False,  # Likesni o'tkazib yuborish
    get_timestamp=False
)

for data in results:
    print(f"{data.url}: {data.tagged_accounts}")
```

---

## 7. Error Handling

**Xatoliklarni ushlash:**

```python
from instagram_scraper import InstagramOrchestrator
from instagram_scraper.exceptions import HTMLStructureChangedError

orchestrator = InstagramOrchestrator()

try:
    results = orchestrator.scrape_complete_profile_advanced(
        username='dindinku__',
        parallel=3,
        save_excel=True
    )

    print(f"Success! Scraped {len(results['posts_data'])} posts")

except HTMLStructureChangedError as e:
    print(f"Instagram changed HTML structure: {e}")
    print("Please update the scraper")

except FileNotFoundError:
    print("Session file not found! Run save_session.py first")

except Exception as e:
    print(f"Unexpected error: {e}")
```

**Graceful shutdown (Ctrl+C):**

```python
# Dastur ishlab turib Ctrl+C bosing
# Avtomatik:
# 1. Joriy progress saqlanadi (JSON)
# 2. Excel finalize qilinadi
# 3. Barcha browserlar yopiladi
# 4. Xavfsiz chiqadi

orchestrator = InstagramOrchestrator()

results = orchestrator.scrape_complete_profile_advanced(
    username='dindinku__',
    parallel=5,
    save_excel=True
)

# Ctrl+C bosing - xavfsiz to'xtaydi!
```

---

## 8. Production Usage

**Ko'p profillarni scraping qilish:**

```python
from instagram_scraper import InstagramOrchestrator
import time

usernames = ['user1', 'user2', 'user3', 'user4', 'user5']

orchestrator = InstagramOrchestrator()

for username in usernames:
    print(f"\n{'='*60}")
    print(f"Scraping: @{username}")
    print(f"{'='*60}")

    try:
        results = orchestrator.scrape_complete_profile_advanced(
            username=username,
            parallel=3,
            save_excel=True,
            export_json=True
        )

        print(f"✓ Success: {len(results['posts_data'])} posts")

        # Instagram rate limit uchun kutish
        print("Waiting 60 seconds before next profile...")
        time.sleep(60)

    except Exception as e:
        print(f"✗ Failed: {e}")
        continue

print("\n✅ All profiles scraped!")
```

**Cron job (scheduled scraping):**

```bash
# crontab -e
# Har kuni 02:00 da scraping
0 2 * * * /usr/bin/python3 /path/to/scraper.py >> /path/to/logs/scraper.log 2>&1
```

```python
# scraper.py
from instagram_scraper import InstagramOrchestrator
from datetime import datetime

print(f"[{datetime.now()}] Starting scheduled scraping...")

orchestrator = InstagramOrchestrator()

results = orchestrator.scrape_complete_profile_advanced(
    username='target_user',
    parallel=3,
    save_excel=True
)

print(f"[{datetime.now()}] Completed: {len(results['posts_data'])} posts")
```

---

## 🎯 Best Practices

1. **Session management:**
   - Session 30 kun amal qiladi
   - Har oy yangi session yarating
   - Session faylni `.gitignore`'ga qo'shing

2. **Rate limiting:**
   - `parallel` juda katta qilmang (max 5)
   - Profillar orasida 30-60 sekund kuting
   - Instagram ban bermaydi (tested)

3. **Error handling:**
   - Har doim try-except ishlating
   - Xatoliklarni log qiling
   - Session muammosi bo'lsa qayta login qiling

4. **Performance:**
   - 32GB RAM: parallel=5 optimal
   - 16GB RAM: parallel=3 optimal
   - 8GB RAM: parallel=2 yoki sequential

5. **Data safety:**
   - Ctrl+C xavfsiz - data yo'qolmaydi
   - Excel real-time yoziladi
   - JSON backup bor

---

## 📞 Support

**Xatolik bo'lsa:**
1. Log fayllarni tekshiring: `scraper.log`
2. Session yangilang: `python save_session.py`
3. Issue yarating: GitHub repository

**Professional support:**
- Email: your@email.com
- Telegram: @your_username

---

Muallif: Claude + mpython77
Versiya: 1.0
Sana: 2024-11-22
