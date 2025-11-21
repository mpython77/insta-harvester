# Instagram Tag Scraper

Instagram postlardan taglarni scraping qilish dasturi.

## O'rnatish

```bash
npm install
npx playwright install chromium
```

## 1. Session saqlash

Birinchi marta foydalanishdan oldin Instagram sessiyasini saqlash kerak:

```bash
npm run save-session
```

**Qadamlar:**
1. Dastur avtomatik ravishda browser ochadi va Instagram ga kiradi
2. Manual ravishda login qiling (username va parol kiriting)
3. "Eslab qolish" variantini tanlang
4. Login tugagandan keyin terminalga qaytib **ENTER** tugmasini bosing
5. Session `instagram_session.json` faylga saqlanadi

## 2. Tag scraping qilish

Session saqlangandan keyin tag scraping qilish mumkin (keyingi qadamda qo'shiladi):

```bash
npm run scrape
```

## Fayllar

- `save_session.js` - Instagram sessiyasini saqlash
- `scrape_tags.js` - Taglarni scraping qilish (keyingi qadamda)
- `instagram_session.json` - Saqlangan session ma'lumotlari (git ignore)

## Eslatma

⚠️ `instagram_session.json` faylini hech kimga bermang - bu sizning login ma'lumotlaringiz!
