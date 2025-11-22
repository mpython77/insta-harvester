# InstaHarvest O'rnatish Ko'rsatmasi 📦

## Muammo:
```
ModuleNotFoundError: No module named 'instaharvest'
```

Bu xatolik package o'rnatilmagan bo'lsa chiqadi.

## Yechim:

### 1-usul: Development rejimida o'rnatish (Tavsiya etiladi) ⭐

Repository papkasida quyidagi buyruqni bajaring:

```bash
# Windows
cd C:\Users\TROLL\Downloads\ArtemInsta-claude-instagram-tag-scraper-01PzBKtA4KzLWRAU975d4WA5\ArtemInsta-claude-instagram-tag-scraper-01PzBKtA4KzLWRAU975d4WA5

# Package va bog'liqliklarni o'rnatish
pip install -e .

# Playwright browserlarini o'rnatish
playwright install chromium
```

**Afzalliklari:**
- Kodni o'zgartirsangiz, qayta o'rnatish shart emas
- Development uchun qulay

### 2-usul: Dependencies'larni o'rnatish va PYTHONPATH ishlatish

```bash
# Faqat bog'liqliklarni o'rnatish
pip install -r requirements.txt

# Playwright browserlarini o'rnatish
playwright install chromium
```

Keyin Python kodingizda:

```python
import sys
sys.path.insert(0, r'C:\Users\TROLL\Downloads\ArtemInsta-...\ArtemInsta-...')

# Endi import ishlaydi
from instaharvest import MessageManager, ScraperConfig
```

### 3-usul: Build va o'rnatish

```bash
# Package qurish
pip install build
python -m build

# O'rnatish
pip install dist/instaharvest-2.5.0-py3-none-any.whl
```

## Tekshirish:

O'rnatish muvaffaqiyatli bo'lganini tekshiring:

```bash
python -c "import instaharvest; print('✅ InstaHarvest installed!')"
```

Agar "✅ InstaHarvest installed!" chiqsa, hammasi joyida!

## Endi ishlatishingiz mumkin:

```bash
cd examples
python test_message.py
```

---

**Maslahat:** 1-usulni ishlating - eng oddiy va qulay! 🎯
