FROM python:3.9-slim

# Instal dependensi untuk Google Chrome (versi modern)
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    libnss3 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libvulkan1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Install Google Chrome Stable
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set environment
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Copy requirement files and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create directory for chrome profile
RUN mkdir -p /app/chrome_profile && chmod 777 /app/chrome_profile

EXPOSE 8000

# Use shell form to allow variable expansion for Railway PORT
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
