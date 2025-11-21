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

## 3. Post linklarini yig'ish

Profile dagi barcha post linklarini yig'ish (scroll qilish bilan):

```bash
python scrape_post_links.py
```

**Xususiyatlari:**
- 🔄 Avtomatik scroll qilish (odamga o'xshab)
- 📊 Real-time progress ko'rsatish
- 💾 Linklar `post_links.txt` ga saqlanadi
- ✅ Posts soniga yetganda yoki yangi content yuklanmasa to'xtaydi

**Misol:**
```
Instagram username kiriting: cristiano

📸 Jami postlar: 3,970
📜 Scroll qilib linklar yig'ish...
📊 To'plangan linklar: 3970/3970
✅ Barcha postlar to'plandi!
💾 Linklar saqlandi: post_links.txt
```

## 4. Post ma'lumotlarini scraping qilish

`post_links.txt` dagi har bir postdan ma'lumotlar olish:

```bash
python scrape_post_data.py
```

**Har bir postdan olinadi:**
- 👥 Tagged akkauntlar
- ❤️ Likes soni
- 🕐 Post vaqti

**Xususiyatlari:**
- 🔄 Har bir linkni ketma-ket ochadi
- ⏳ Instagram limiting uchun 2-4s kutish
- 📊 Real-time ma'lumotlar ko'rsatish

**Misol chiqish:**
```
[1/38] 🔍 Scraping: https://instagram.com/dindinku__/p/DNf6enYgUym/

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔗 URL: https://instagram.com/dindinku__/p/DNf6enYgUym/
👥 Tagged: santiagobelizon, v_vovk, marieclairespain, generation.models
❤️  Likes: 44
🕐 Time: Nov 17, 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Fayllar

- `save_session.py` - Instagram sessiyasini saqlash
- `scrape_profile.py` - Profile ma'lumotlarini olish
- `scrape_post_links.py` - Post linklarini yig'ish (scroll bilan)
- `scrape_post_data.py` - Postlardan ma'lumotlar olish
- `instagram_session.json` - Saqlangan session ma'lumotlari (git ignore)
- `post_links.txt` - To'plangan post linklar (git ignore)

## Eslatma

⚠️ `instagram_session.json` faylini hech kimga bermang - bu sizning login ma'lumotlaringiz!
