import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# --- KONFIGURASI ---
# Ganti dengan path folder kosong yang Anda buat
CHROME_PROFILE_PATH = r"C:\bot_chrome_profile" 

# Data User yang mau diinput (Nantinya bisa dari hasil generate mail.tm)
FIRST_NAME = "User"
LAST_NAME = "Baru01"
SECONDARY_EMAIL = "9wc9bjrpw7@dollicons.com" # Email dari mail.tm

def admin_console_bot():
    print("[*] Memulai Browser dengan Profile Tersimpan...")
    
    options = uc.ChromeOptions()
    # Ini kuncinya: menyimpan session login
    options.add_argument(f"--user-data-dir={CHROME_PROFILE_PATH}") 
    
    driver = uc.Chrome(options=options)
    wait = WebDriverWait(driver, 20)

    try:
        # 1. Buka Halaman User Langsung
        # Tips: Langsung ke URL list user biar lebih cepat
        driver.get("https://admin.google.com/ac/users")
        
        # CEK LOGIN: Jika diminta login, script akan pause biarkan user login manual
        if "ServiceLogin" in driver.current_url or "signin" in driver.current_url:
            print("\n" + "!"*50)
            print("SILAKAN LOGIN MANUAL DI BROWSER YANG TERBUKA.")
            print("Setelah login dan masuk dashboard, script akan lanjut otomatis.")
            print("!"*50 + "\n")
            # Tunggu sampai URL berubah ke dashboard admin
            wait.until(EC.url_contains("admin.google.com/ac"))
            print("[*] Login terdeteksi! Melanjutkan...")

        # 2. Klik "Tambahkan pengguna baru"
        print("[*] Mencari tombol Tambah Pengguna...")
        # Mencari element yang berisi teks "Tambahkan pengguna baru"
        add_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), 'Tambahkan pengguna baru')]")))
        add_btn.click()
        
        # 3. Mengisi Form (Berdasarkan HTML yang Anda kirim)
        print("[*] Mengisi form...")
        
        # Nama Depan (aria-label="Nama depan")
        f_name = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[aria-label='Nama depan']")))
        f_name.send_keys(FIRST_NAME)
        
        # Nama Belakang (aria-label="Nama belakang")
        l_name = driver.find_element(By.CSS_SELECTOR, "input[aria-label='Nama belakang']")
        l_name.send_keys(LAST_NAME)
        
        # Email Sekunder (aria-label="Alamat email sekunder")
        # Ini input paling penting agar invite terkirim ke email mail.tm
        sec_email = driver.find_element(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder']")
        sec_email.send_keys(SECONDARY_EMAIL)
        
        print(f"[*] Data diisi: {FIRST_NAME} {LAST_NAME} | {SECONDARY_EMAIL}")
        time.sleep(1) # Jeda sebentar agar validasi form Google jalan (tombol Lanjutkan aktif)

        # 4. Klik "Lanjutkan"
        print("[*] Klik Lanjutkan...")
        # Mencari tombol Button yang didalamnya ada span bertuliskan "Lanjutkan"
        continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Lanjutkan']/ancestor::button")))
        
        # Cek apakah tombol masih disabled
        if continue_btn.get_attribute("disabled"):
            print("[!] Tombol masih disabled, mencoba klik body dulu...")
            driver.find_element(By.TAG_NAME, "body").click() # Trigger blur event
            time.sleep(1)
        
        continue_btn.click()
        
        print("[SUCCESS] Tombol Lanjutkan diklik. Invite sedang diproses.")
        
        # Jeda waktu untuk memastikan request terkirim sebelum browser tutup
        time.sleep(5)

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        # driver.quit() # Uncomment jika ingin browser tutup otomatis
        pass

if __name__ == "__main__":
    admin_console_bot()