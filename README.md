# 🚀 Instagram Scraper - Professional Edition

Professional Instagram scraper with **automatic** post & reel data extraction, advanced diagnostics, error recovery, and performance monitoring.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## ✨ Features

### 🎯 Core Features
- ✅ **Full Automatic Scraping** - Just enter username, everything else is automatic
- ✅ **Post & Reel Support** - Handles both content types intelligently
- ✅ **Real-time Excel Export** - Live export with Type column (Post/Reel)
- ✅ **Parallel Processing** - 3 concurrent tabs for faster scraping
- ✅ **Smart Type Detection** - Automatically identifies posts vs reels

### 🔍 Professional Features
- ✅ **HTML Diagnostics** - Detects Instagram HTML changes automatically
- ✅ **Error Recovery** - 90%+ recovery rate with fallback methods
- ✅ **Performance Monitoring** - Real-time CPU, memory, and speed tracking
- ✅ **Memory Optimization** - Automatic garbage collection
- ✅ **Detailed Statistics** - Comprehensive reports after scraping

### 📊 Data Extraction
- **Posts:** Tags, Likes, Date
- **Reels:** Tags (via popup), Likes, Date
- **Profile:** Posts count, Followers, Following
- **Output:** Excel + JSON with Type column

---

## 🚀 Quick Start

### 1️⃣ Installation

```bash
# Clone repository
git clone https://github.com/yourusername/ArtemInsta.git
cd ArtemInsta

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2️⃣ Setup Instagram Session

```bash
# Run once to save your Instagram session
python save_session.py

# Follow the prompts:
# - Enter username
# - Enter password
# - Complete 2FA if enabled
# Session saved to: instagram_session.json
```

### 3️⃣ Run Full Auto Scraping

```bash
# Just run and enter username!
python main_advanced.py

# That's it! 🎉
# Output:
# - instagram_data_USERNAME.xlsx (with Type column)
# - instagram_data_USERNAME.json
# - instagram_scraper_USERNAME.log
```

---

## 📖 Usage

### FULL AUTO MODE (Recommended)

```bash
python main_advanced.py
```

**Input:** Username only!

**What it does:**
1. ✅ Collects ALL post & reel links (Phase 1)
2. ✅ Extracts data from each item (Phase 2)
3. ✅ Saves to Excel with Type column
4. ✅ Shows detailed statistics

**Example:**
```
🚀 INSTAGRAM SCRAPER - PROFESSIONAL FULL AUTO MODE

📝 Enter Instagram username: cristiano
🎯 Target: @cristiano

⚙️  Configuration (OPTIMIZED):
   - Parallel: 3 tabs (fast & stable)
   - Excel: Real-time export
   - Diagnostics: Enabled
   - Error Recovery: Enabled
   - Performance Monitoring: Enabled

🚀 Press ENTER to start...

[Automatic scraping starts...]

✅ FULL AUTOMATIC SCRAPING COMPLETE!

📊 RESULTS:
   Username: @cristiano
   Total Posts: 3,567
   Links Collected: 3,567 items
     - Posts: 2,234
     - Reels: 1,333
   Data Extracted: 3,567 items
   Successful: 3,545/3,567 (99.4%)

💾 Output Files:
   📊 Excel: instagram_data_cristiano.xlsx
   📄 JSON: instagram_data_cristiano.json
   📋 Log: instagram_scraper_cristiano.log
```

---

## 📊 Output Format

### Excel File Structure

| Post URL | Type | Tagged Accounts | Likes Count | Post Date | Scraping Date/Time |
|----------|------|-----------------|-------------|-----------|-------------------|
| https://... | Post | user1, user2 | 1234 | Nov 17, 2025 | 2025-11-22 10:30:15 |
| https://... | Reel | user3, user4 | 5678 | Nov 18, 2025 | 2025-11-22 10:32:45 |

### JSON File Structure

```json
{
  "username": "cristiano",
  "profile": {
    "posts": 3567,
    "followers": "500M",
    "following": "500"
  },
  "post_links": [
    {"url": "https://...", "type": "Post"},
    {"url": "https://...", "type": "Reel"}
  ],
  "posts_data": [
    {
      "url": "https://...",
      "tagged_accounts": ["user1", "user2"],
      "likes": "1234",
      "timestamp": "Nov 17, 2025",
      "content_type": "Post"
    }
  ]
}
```

---

## 🔍 Advanced Features

### HTML Diagnostics

Automatically detects when Instagram changes their HTML structure:

```
🔍 Running POST diagnostics...
  ✓ tags_primary: Found 3 elements (0.042s)
  ✓ likes_button: Found 1 elements (0.031s)
  ✗ timestamp: NOT FOUND (0.028s)

⚠️ HTML CHANGE DETECTED: 'timestamp' selector failed!
   Selector: time
   Instagram may have updated HTML structure
```

### Error Recovery

Automatic fallback methods:

```
⚠️ likes: Primary method failed - TimeoutError
✓ likes: Fallback method succeeded

ERROR STATISTICS:
  Total Errors: 15
  Recovered: 14
  Failed: 1
  Recovery Rate: 93.3%
```

### Performance Monitoring

Real-time monitoring:

```
💻 SYSTEM INFO:
  CPU: 8 cores @ 15.2%
  RAM: 12.3/16.0 GB available
  Process: 342.15 MB, CPU: 8.3%

♻️ Memory optimized: Freed 45.23 MB

📊 PERFORMANCE REPORT:
  Total Time: 45.32s
  Operations/Second: 0.55
  Peak Memory: 342.15 MB
```

---

## 🧪 Testing & Examples

Check the `examples/` directory for test scripts:

```bash
# Test link collection
python examples/test_phase1.py

# Test data extraction
python examples/test_phase2.py

# Test professional features
python examples/test_professional.py
```

See [examples/README.md](examples/README.md) for detailed documentation.

---

## 📁 Project Structure

```
ArtemInsta/
├── main_advanced.py           # FULL AUTO SCRAPING (main script)
├── save_session.py            # Instagram login session manager
├── requirements.txt           # Python dependencies
├── instagram_scraper/         # Core library
│   ├── __init__.py
│   ├── base.py               # Base scraper class
│   ├── config.py             # Configuration
│   ├── post_links.py         # Link collection (Phase 1)
│   ├── post_data.py          # Data extraction (Phase 2) - PROFESSIONAL
│   ├── diagnostics.py        # HTML diagnostics system
│   ├── error_handler.py      # Error recovery system
│   ├── performance.py        # Performance monitoring
│   ├── parallel_scraper.py   # Parallel processing
│   ├── excel_export.py       # Real-time Excel export
│   └── orchestrator.py       # Workflow coordinator
├── examples/                  # Test & example scripts
│   ├── README.md
│   ├── test_phase1.py        # Link collection test
│   ├── test_phase2.py        # Data extraction test
│   └── test_professional.py  # Professional features test
└── PROFESSIONAL_FEATURES.md   # Documentation (Uzbek)
```

---

## ⚙️ Configuration

### Default Configuration (Optimized)

```python
from instagram_scraper import ScraperConfig

config = ScraperConfig(
    headless=False,           # Visual mode
    log_level='INFO',         # Detailed logs
    log_to_console=True,      # Console output
    parallel=3,               # 3 concurrent tabs
    enable_diagnostics=True,  # HTML diagnostics
)
```

### Headless Mode (Server/Production)

```python
config = ScraperConfig(
    headless=True,  # No browser window
    log_level='INFO',
)
```

---

## 🛠️ Requirements

- **Python:** 3.8+
- **OS:** Windows, macOS, Linux
- **RAM:** 4GB+ (8GB recommended for parallel processing)
- **Disk:** 500MB for dependencies

### Dependencies

```
playwright==1.48.0      # Browser automation
beautifulsoup4==4.12.3  # HTML parsing
openpyxl==3.1.2        # Excel export
pandas==2.2.0          # Data manipulation
lxml==5.1.0            # Fast XML/HTML parsing
psutil==5.9.8          # Performance monitoring
```

---

## 🐛 Troubleshooting

### Session Expired

```bash
# Re-run session setup
python save_session.py
```

### "Profile not found"

- Check username spelling
- Make sure profile is public or you follow it

### Slow Scraping

- Reduce parallel tabs: `parallel=2`
- Check internet speed
- Close other browser tabs

### HTML Structure Changed

The scraper will automatically detect and report HTML changes:

```
❌ CRITICAL HTML STRUCTURE CHANGE DETECTED!
   Failed selectors: timestamp, likes_button

💡 Solution:
   - Check GitHub for updates
   - Report issue with diagnostic report
```

---

## 📈 Performance

Tested with real Instagram profiles:

| Profile Size | Time (3 tabs) | Memory | Success Rate |
|--------------|---------------|--------|--------------|
| 100 posts    | ~8 min        | 350 MB | 98-100%      |
| 500 posts    | ~40 min       | 450 MB | 97-99%       |
| 1000 posts   | ~80 min       | 550 MB | 96-98%       |

*Average: 4-5 seconds per post/reel with parallel processing*

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## ⚠️ Legal & Ethics

**Important:** This tool is for educational and research purposes only.

- ✅ Use on your own account or with permission
- ✅ Respect Instagram's Terms of Service
- ✅ Don't abuse rate limits
- ❌ Don't use for spam or harassment
- ❌ Don't scrape private accounts without permission

**Rate Limiting:** The scraper includes built-in delays to be respectful of Instagram's servers.

---

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

---

## 🌟 Credits

Developed with ❤️ using:
- [Playwright](https://playwright.dev/) - Browser automation
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing
- [Pandas](https://pandas.pydata.org/) - Data manipulation

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/ArtemInsta/issues)
- **Documentation:** See `PROFESSIONAL_FEATURES.md` (Uzbek)
- **Examples:** See `examples/README.md`

---

## 🎯 Roadmap

- [ ] Support for Stories
- [ ] Support for Comments extraction
- [ ] GUI interface
- [ ] Multiple account support
- [ ] Scheduled scraping

---

**Made with ❤️ for the Instagram scraping community**

⭐ **Star this repo if you find it useful!**
