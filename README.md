# Instagram Tag Scraper

Instagram postlardan taglarni scraping qilish dasturi.

## O'rnatish

```bash
pip install -r requirements.txt
playwright install chromium
```

## 1. Session saqlash

Birinchi marta foydalanishdan oldin Instagram sessiyasini saqlash kerak:

```bash
python save_session.py
```

**Qadamlar:**
1. Dastur avtomatik ravishda browser ochadi va Instagram ga kiradi
2. Manual ravishda login qiling (username va parol kiriting)
3. "Eslab qolish" variantini tanlang
4. Login tugagandan keyin terminalga qaytib **ENTER** tugmasini bosing
5. Session `instagram_session.json` faylga saqlanadi

## 2. Profile ma'lumotlarini olish

Session saqlangandan keyin istalgan profile ma'lumotlarini olish mumkin:

```bash
python scrape_profile.py
```

Dastur quyidagi ma'lumotlarni oladi:
- 📸 Posts soni
- 👥 Followers soni
- ➕ Following soni

**Misol:**
```
Instagram username kiriting: castawaymodelmanagement

👤 Username:  @castawaymodelmanagement
📸 Posts:     1,870
👥 Followers: 32,757
➕ Following: 5,447
```

## 3. Tag scraping qilish

Postlardan tag scraping qilish (keyingi qadamda qo'shiladi):

```bash
python scrape_tags.py
```

## Fayllar

- `save_session.py` - Instagram sessiyasini saqlash
- `scrape_profile.py` - Profile ma'lumotlarini olish
- `scrape_tags.py` - Taglarni scraping qilish (keyingi qadamda)
- `instagram_session.json` - Saqlangan session ma'lumotlari (git ignore)

## Eslatma

⚠️ `instagram_session.json` faylini hech kimga bermang - bu sizning login ma'lumotlaringiz!
