# Menggunakan base image Python yang stabil
FROM python:3.9-slim

# Mencegah Python membuat file .pyc dan memastikan log langsung muncul
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Instal dependensi dasar sistem
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
    libxss1 \
    libxtst6 \
    fonts-liberation \
    libappindicator3-1 \
    libxdamage1 \
    libglib2.0-0 \
    --no-install-recommends

# Instal Google Chrome Stable secara resmi
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set direktori kerja
WORKDIR /app

# Instal dependensi Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Salin seluruh kode proyek
COPY . .

# Warm up Selenium to pre-cache driver
RUN python warmup.py || true

# Pastikan folder profile ada (untuk Volume)
RUN mkdir -p /app/chrome_profile

# Ekspos port yang digunakan Railway
EXPOSE 8080

# Perintah untuk menjalankan FastAPI dengan Xvfb
CMD Xvfb :99 -ac -screen 0 1920x1080x24 & uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}