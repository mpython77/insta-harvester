# 📚 Examples & Test Scripts

Bu papkada Instagram Scraper ning turli funksiyalarini test qilish uchun example kodlar joylashgan.

---

## 📋 Fayllar

### 1️⃣ **test_phase1.py** - Link Collection Test
Phase 1 funksiyasini test qiladi: Post va Reel linklerini to'plash

**Nima qiladi:**
- Profile dan barcha post va reel linklerini yig'adi
- Har bir link ning type ini aniqlaydi (Post/Reel)
- Statistika ko'rsatadi (qancha post, qancha reel)

**Qanday ishlatish:**
```bash
python examples/test_phase1.py

# Input: Instagram username
# Output: Link list with types
```

**Output misoli:**
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
Phase 2 funksiyasini test qiladi: Post va Reel dan ma'lumot olish

**Nima qiladi:**
- Bitta yoki bir necha URL dan ma'lumot oladi
- Reel va Post uchun turli extraction metodlarini ishlatadi
- Tags, likes, date ni ko'rsatadi

**Qanday ishlatish:**
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
Barcha professional xususiyatlarni test qiladi

**Nima qiladi:**
- HTML diagnostics
- Error recovery
- Performance monitoring
- Batafsil statistika

**Qanday ishlatish:**
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

## 🚀 Qachon Qaysi Test Ishlatish Kerak

### Yangi Profile Test Qilish:
```bash
python examples/test_phase1.py
# Tezkor test - faqat linklar yig'iladi
```

### Reel Extraction Test:
```bash
python examples/test_phase2.py
# Reels maxsus extraction ni test qilish
```

### HTML O'zgarishini Tekshirish:
```bash
python examples/test_professional.py
# Instagram HTML o'zgardimi bilish uchun
```

### Full Production Scraping:
```bash
python main_advanced.py
# Bu test emas, to'liq scraping!
```

---

## 💡 Tips

1. **Test qilishdan oldin:**
   - Instagram session yarating: `python save_session.py`
   - Internet connection tekshiring

2. **Qaysi test kerak:**
   - Link collection muammosi → `test_phase1.py`
   - Data extraction muammosi → `test_phase2.py`
   - HTML o'zgarish → `test_professional.py`

3. **Production uchun:**
   - Test emas, `main_advanced.py` ishlatish!

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

Barcha test scriptlar **development va debugging** uchun.

**Production scraping** uchun faqat `main_advanced.py` ishlatish! 🚀
