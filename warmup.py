from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import os
import sys

def warmup():
    print("Pre-caching Chrome driver for standard selenium...")
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    
    # In standard selenium, the driver binary isn't downloaded by a patcher like uc.
    # Selenium 4+ automatically uses Selenium Manager to provision the driver if missing.
    try:
        driver = webdriver.Chrome(options=options)
        print("Successfully cached driver via Selenium Manager.")
        driver.quit()
    except Exception as e:
        print(f"Warmup warning: {e}")

if __name__ == "__main__":
    warmup() # Even if it fails here due to no display, the patcher often still downloads the exe
