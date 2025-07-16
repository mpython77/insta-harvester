# Railway uchun Dockerfile
FROM python:3.11-slim

# Kerakli system packages o'rnatish
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    libxss1 \
    libgconf-2-4 \
    && rm -rf /var/lib/apt/lists/*

# Google Chrome o'rnatish
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Working directory yaratish
WORKDIR /app

# Requirements faylini copy qilish va dependencies o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser o'rnatish
RUN python -m playwright install chromium
RUN python -m playwright install-deps

# Barcha fayllarni copy qilish
COPY . .

# Port expose qilish (Railway uchun)
EXPOSE $PORT

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Bot ishga tushirish
CMD ["python", "main.py"]
