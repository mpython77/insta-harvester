# 📦 PyPI'ga Yuklash Bo'yicha To'liq Yo'riqnoma

## O'zbekcha / Uzbek Version

### Bosqich 1: Kerakli kutubxonalarni o'rnatish

```bash
pip install --upgrade pip
pip install --upgrade build twine
```

### Bosqich 2: Eski build fayllarini o'chirish (agar mavjud bo'lsa)

```bash
rm -rf dist/ build/ *.egg-info
```

### Bosqich 3: Yangi paketni build qilish

```bash
python -m build
```

Bu quyidagi fayllarni yaratadi:
- `dist/instaharvest-2.5.1.tar.gz` (source distribution)
- `dist/instaharvest-2.5.1-py3-none-any.whl` (wheel distribution)

### Bosqich 4: Build natijasini tekshirish

```bash
ls -lh dist/
```

Ikkita fayl ko'rinishi kerak:
- `instaharvest-2.5.1-py3-none-any.whl`
- `instaharvest-2.5.1.tar.gz`

### Bosqich 5: PyPI'ga yuklash

**IMPORTANT:** PyPI API token kerak bo'ladi!

#### A) Test PyPI'ga yuklash (birinchi marta sinab ko'rish uchun):

```bash
python -m twine upload --repository testpypi dist/*
```

Username: `__token__`
Password: `pypi-...` (sizning TestPyPI token'ingiz)

Keyin test qilish:
```bash
pip install --index-url https://test.pypi.org/simple/ instaharvest
```

#### B) Real PyPI'ga yuklash:

```bash
python -m twine upload dist/*
```

Username: `__token__`
Password: `pypi-...` (sizning PyPI token'ingiz)

### Bosqich 6: Yuklanganni tekshirish

PyPI sahifasiga kiring:
- https://pypi.org/project/instaharvest/

Yangi versiya (2.5.1) ko'rinishi kerak!

### Bosqich 7: O'rnatib sinab ko'rish

```bash
# Yangi virtual environment yarating
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# yoki
test_env\Scripts\activate  # Windows

# PyPI'dan o'rnating
pip install instaharvest

# Versiyani tekshiring
python -c "import instaharvest; print(instaharvest.__version__)"
# Ko'rsatishi kerak: 2.5.1
```

---

## English Version

### Step 1: Install Required Tools

```bash
pip install --upgrade pip
pip install --upgrade build twine
```

### Step 2: Clean Old Build Files (if exists)

```bash
rm -rf dist/ build/ *.egg-info
```

### Step 3: Build the Package

```bash
python -m build
```

This creates:
- `dist/instaharvest-2.5.1.tar.gz` (source distribution)
- `dist/instaharvest-2.5.1-py3-none-any.whl` (wheel distribution)

### Step 4: Verify Build Results

```bash
ls -lh dist/
```

Should show two files:
- `instaharvest-2.5.1-py3-none-any.whl`
- `instaharvest-2.5.1.tar.gz`

### Step 5: Upload to PyPI

**IMPORTANT:** You need a PyPI API token!

#### A) Upload to Test PyPI (for testing first):

```bash
python -m twine upload --repository testpypi dist/*
```

Username: `__token__`
Password: `pypi-...` (your TestPyPI token)

Then test install:
```bash
pip install --index-url https://test.pypi.org/simple/ instaharvest
```

#### B) Upload to Real PyPI:

```bash
python -m twine upload dist/*
```

Username: `__token__`
Password: `pypi-...` (your PyPI token)

### Step 6: Verify Upload

Visit PyPI page:
- https://pypi.org/project/instaharvest/

New version (2.5.1) should be visible!

### Step 7: Test Installation

```bash
# Create new virtual environment
python -m venv test_env
source test_env/bin/activate  # Linux/Mac
# or
test_env\Scripts\activate  # Windows

# Install from PyPI
pip install instaharvest

# Check version
python -c "import instaharvest; print(instaharvest.__version__)"
# Should show: 2.5.1
```

---

## 🔑 PyPI API Token Olish / Getting PyPI API Token

### 1. PyPI Account yarating
- https://pypi.org/account/register/ ga boring
- Email'ingizni tasdiqlang

### 2. API Token yarating
- https://pypi.org/manage/account/token/ ga boring
- "Add API token" tugmasini bosing
- Token scope'ni tanlang:
  - `Entire account` (barcha proyektlar uchun)
  - yoki `Project: instaharvest` (faqat shu proyekt uchun)
- Token nomini kiriting (masalan: "instaharvest-upload")
- "Create token" bosing
- **IMPORTANT:** Token faqat bir marta ko'rsatiladi! Uni saqlang!

### 3. Token'ni saqlash

`.pypirc` fayl yarating (xavfsizlik uchun):

**Linux/Mac:**
```bash
nano ~/.pypirc
```

**Windows:**
```
notepad %USERPROFILE%\.pypirc
```

Quyidagini yozing:
```ini
[pypi]
username = __token__
password = pypi-AgEIcHl...sizning token'ingiz...

[testpypi]
username = __token__
password = pypi-AgEIcHl...sizning test token'ingiz...
```

Faylni saqlang va ruxsatlarni o'zgartiring (faqat Linux/Mac):
```bash
chmod 600 ~/.pypirc
```

---

## ⚠️ Muhim Eslatmalar / Important Notes

1. **Version raqamini har safar oshiring!** PyPI bir xil version'ni qayta qabul qilmaydi.
   - Increment version number each time! PyPI doesn't accept duplicate versions.

2. **Token'ni hech qayerga commit qilmang!**
   - Never commit your token to git!

3. **Avval Test PyPI'da sinab ko'ring**
   - Test on TestPyPI first before uploading to real PyPI

4. **README.md to'g'ri ko'rinishini tekshiring**
   - Verify README.md displays correctly (check on PyPI page)

5. **Dependencies to'g'ri yozilganini tekshiring**
   - Verify dependencies in setup.py are correct

---

## 🐛 Troubleshooting

### Xato: "File already exists"
- Version raqamini oshiring (setup.py va __init__.py da)
- `rm -rf dist/ build/ *.egg-info` qiling
- Qaytadan build qiling

### Xato: "Invalid token"
- Token'ni to'g'ri nusxaladingizmi tekshiring
- Token'da probel yoki yangi qator yo'qligini tekshiring
- Yangi token yarating

### Xato: "README rendering failed"
- README.md markdown sintaksisini tekshiring
- `python -m build` qayta ishlang

---

## ✅ Tayyor!

Endi foydalanuvchilar quyidagicha o'rnatishlari mumkin:

```bash
pip install instaharvest
```

va eng yangi versiya (2.5.1) o'rnatiladi!
