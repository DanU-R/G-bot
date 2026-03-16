import undetected_chromedriver as uc
import os
import sys

def warmup():
    print("Pre-caching Chrome driver for undetected-chromedriver...")
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Force download of the driver during build
    try:
        driver = uc.Chrome(options=options, headless=True)
        print(f"Successfully cached driver at: {driver.patcher.exe_path}")
        driver.quit()
    except Exception as e:
        print(f"Warmup warning: {e}")
        # Even if it fails here due to no display, the patcher often still downloads the exe

if __name__ == "__main__":
    warmup()
