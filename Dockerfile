# Menggunakan base image Python yang stabil
FROM python:3.9-slim

# Mencegah Python membuat file .pyc dan memastikan log langsung muncul
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# 1. Instal dependensi dasar sistem termasuk gnupg, curl, dan Xvfb (Virtual Display)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    curl \
    unzip \
    xvfb \
    x11-utils \
    libnss3 \
    libgbm1 \
    libasound2 \
    libglib2.0-0 \
    --no-install-recommends

# 2. Instal Google Chrome Stable dengan cara modern
RUN curl -fSsL https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor | tee /usr/share/keyrings/google-chrome.gpg > /dev/null \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set direktori kerja
WORKDIR /app

# 3. Instal dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Salin seluruh kode proyek
COPY . .

# Warm up Selenium (Pre-cache driver)
RUN python warmup.py || true

# Pastikan folder profile ada (untuk Railway Volume)
RUN mkdir -p /app/chrome_profile

# Ekspos port default Railway
EXPOSE 8080

# Jalankan FastAPI menggunakan uvicorn (dengan Xvfb untuk Headful Stealth)
CMD Xvfb :99 -ac -screen 0 1920x1080x24 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}