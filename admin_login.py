import os
import time
import random
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import requests
import json
import string

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_CONSOLE_URL = os.getenv("ADMIN_CONSOLE_URL", "https://admin.google.com/")

def random_delay(min_s=1.0, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))

MAIL_TM_API_URL = "https://api.mail.tm"

def get_available_domains():
    """Fetches available domains from mail.tm."""
    try:
        response = requests.get(f"{MAIL_TM_API_URL}/domains")
        response.raise_for_status()
        return response.json()['hydra:member']
    except Exception as e:
        print(f"Error fetching domains: {e}")
        return []

def create_temp_mail_account():
    """
    Checks for existing credentials in email_credentials.txt.
    If found, returns them.
    If not, creates a random account on mail.tm and saves to file.
    """
    creds_file = r"c:\hotspot\autologin\email_credentials.txt"
    
    if os.path.exists(creds_file):
        try:
            with open(creds_file, "r") as f:
                lines = f.readlines()
                email = None
                password = None
                for line in lines:
                    if line.startswith("Email:"):
                        email = line.split("Email:")[1].strip()
                    elif line.startswith("Password:"):
                        password = line.split("Password:")[1].strip()
                
                if email and password:
                    print(f"Found existing temp email: {email}")
                    return email, password
        except Exception as e:
            print(f"Error reading credentials file: {e}")

    print("Generating NEW content from Mail.tm...")
    try:
        domains = get_available_domains()
        if not domains:
            return None, None
            
        domain = domains[0]['domain']
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        
        default_pwd = os.getenv("DEFAULT_PASSWORD")
        if default_pwd:
             password = default_pwd
        else:
             password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
             
        email = f"{username}@{domain}"
        
        payload = {"address": email, "password": password}
        response = requests.post(f"{MAIL_TM_API_URL}/accounts", json=payload)
        response.raise_for_status()
        
        with open(creds_file, "w") as f:
            f.write(f"Email: {email}\nPassword: {password}\n")
            
        return email, password
    except Exception as e:
        print(f"Error creating temp mail: {e}")
        return None, None

def safe_click(driver, element):
    """Clicks an element using JS to avoid interception."""
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)

def create_bulk_users(driver, user_data_list, secondary_email):
    """
    Fills the 'Add new user' form for MULTIPLE users in one go.
    user_data_list: list of dicts [{'first': 'A', 'last': 'B'}, ...]
    """
    print(f"\n--- Starting Bulk Creation for {len(user_data_list)} Users ---")
    
    try:
        print("Looking for 'Add user' / 'Tambahkan pengguna' button...")
        add_user_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, 
                "//div[@role='button']//span[contains(text(), 'Tambahkan pengguna') or contains(text(), 'Add user')] | " +
                "//div[aria-label='Tambahkan pengguna baru'] | " +
                "//div[aria-label='Add new user']"
            ))
        )
        safe_click(driver, add_user_btn)
        print("Clicked 'Add User'.")
    except:
        print("Direct Add button not found. ensuring we are on Users list or attempting Sidebar...")
        try:
             if "/ac/users" not in driver.current_url:
                 driver.get("https://admin.google.com/ac/users")
                 random_delay(3, 5)

             print("Scanning for 'Add new user' button on Users page...")
             add_floating_btn = WebDriverWait(driver, 10).until(
                 EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Tambahkan pengguna baru'], div[aria-label='Add new user']"))
             )
             safe_click(driver, add_floating_btn)
             print("Clicked 'Tambahkan pengguna baru' (Floating).")
        except Exception as e_sidebar:
             print(f"⚠️ Could not find Add button: {e_sidebar}")
             print("👉 Please MANUALLY click 'Add new user' now if possible...")
    
    random_delay()

    try:
        print("Waiting for User Details Form...")
        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']"))
        )
        
        for i, user in enumerate(user_data_list):
            print(f"  > Filling data for User {i+1}: {user['first']} {user['last']}")
            
            first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
            last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
            sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
            
            if i >= len(first_name_inputs):
                print("    Not enough rows. Clicking 'Tambahkan pengguna lain'...")
                try:
                    add_another_btn = driver.find_element(By.XPATH, 
                        "//span[contains(text(), 'Tambahkan pengguna lain')]/ancestor::button | " +
                        "//span[contains(text(), 'Add another user')]/ancestor::button"
                    )
                    safe_click(driver, add_another_btn)
                    random_delay(1, 2)
                    
                    first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
                    last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
                    sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
                except Exception as e_add_row:
                    print(f"    ❌ Failed to add new row: {e_add_row}")
                    break 
            
            human_type(first_name_inputs[i], user['first'])
            random_delay(0.5)
            human_type(last_name_inputs[i], user['last'])
            random_delay(0.5)
            
            if i < len(sec_emails):
                 human_type(sec_emails[i], secondary_email)
            
            random_delay(0.5)

        print("All users filled.")
        
        print("Looking for 'Lanjutkan' button...")
        continue_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Lanjutkan')]/ancestor::div[@role='button'] | //span[contains(text(), 'Lanjutkan')]"))
        )
        safe_click(driver, continue_btn)
        print("Clicked 'Lanjutkan'.")
        
        print("Waiting for 'Kirim petunjuk login' button (Up to 30s)...")
        
        try:
             send_btn = WebDriverWait(driver, 30).until(
                 EC.element_to_be_clickable((By.XPATH, 
                    "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::button | " + 
                    "//span[contains(text(), 'Send login instructions')]/ancestor::button | " +
                    "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::div[@role='button']"
                 ))
             )
             
             expected_count = len(user_data_list)
             print(f"Stage 1: Waiting for {expected_count} BLUE checkmarks (class 'E9QP5b') to confirm creation...")
             
             try:
                 WebDriverWait(driver, 60).until(
                     lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.Y6ROV.E9QP5b")) >= expected_count
                 )
                 print(f"✅ Stage 1 Complete: All {expected_count} users created (Blue Checks detected).")
                 random_delay(1, 2)
             except Exception:
                 print(f"⚠️ Stage 1 Message: Not all blue checks appeared (Found {len(driver.find_elements(By.CSS_SELECTOR, 'div.Y6ROV.E9QP5b'))}). Proceeding to send email anyway...")
             
             safe_click(driver, send_btn)
             print("Clicked 'Kirim petunjuk login'.")
             
             print(f"Stage 2: Waiting for {expected_count} GREEN checkmarks (class 'L5gqXc') to confirm emails sent...")
             try:
                 WebDriverWait(driver, 60).until(
                     lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.Y6ROV.L5gqXc")) >= expected_count
                 )
                 print(f"✅ Stage 2 Complete: All {expected_count} users confirmed with GREEN checkmarks.")
                 random_delay(2, 4)
             except Exception:
                 print(f"⚠️ Stage 2 Timeout: Not all green checks appeared (Found {len(driver.find_elements(By.CSS_SELECTOR, 'div.Y6ROV.L5gqXc'))}). Finishing...")
        except Exception:
             print("Did not find 'Kirim petunjuk login' button (optional/skipped).")

        print("Waiting for final result...")
        WebDriverWait(driver, 30).until(
            lambda d: "ditambahkan" in d.page_source or "added" in d.page_source
        )
        print("✅ Bulk Users created successfully!")
        
        domain = "gmail.com"
        if ADMIN_EMAIL and "@" in ADMIN_EMAIL:
            domain = ADMIN_EMAIL.split("@")[1]
            
        default_password = os.getenv("DEFAULT_PASSWORD", "Sadewa123")

        with open(r"c:\hotspot\autologin\created_users_log.txt", "a") as log:
            for user in user_data_list:
                user_email = f"{user['first']}@{domain}"
                log.write(f"{user['first']}|{user['last']}|{user_email}|{default_password}\n")

        print("Looking for 'Selesai' / 'Done' button...")
        finish_btn_xpath = (
            "//span[contains(@class, 'UTNHae') and contains(@jsname, 'm9ZlFb')]/ancestor::button | " +
            "//span[contains(@class, 'UTNHae') and contains(@jsname, 'm9ZlFb')]/ancestor::div[@role='button'] | " + 
            "//span[contains(text(), 'Selesai')]/ancestor::button | " + 
            "//span[contains(text(), 'Done')]/ancestor::button | " +
            "//div[text()='Selesai'] | //div[text()='Done']"
        )
        
        try:
            done_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, finish_btn_xpath))
            )
            safe_click(driver, done_btn)
            print("Clicked 'Selesai' / 'Done'.")
        except Exception:
             broad_btn = driver.find_element(By.XPATH, "//button[contains(., 'Selesai') or contains(., 'Done')]")
             safe_click(driver, broad_btn)
             print("Clicked 'Done' button (broad search).")

        return True
    
    except Exception as e:
        print(f"Failed during bulk creation: {e}")
        return False

def human_type(element, text):
    """Types text into an element with random delays between keystrokes."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def run_batch_creation(driver):
    """Prepares list of users and runs bulk creation."""
    
    temp_email, _ = create_temp_mail_account()
    if not temp_email:
        print("Fallback to default recovery email.")
        temp_email = "fallback_recovery@kavera.biz.id"
    
    print("\n" + "="*40)
    print(" USER GENERATION CONFIGURATION")
    print("="*40)
    
    try:
        base_name = input("Enter Base Name (Leave empty to use 'User' or random): ").strip()
        
        print("\nSelect Mode:")
        print("[1] Sequential (e.g. Test1, Test2, Test3...)")
        print("[2] Random Suffix (e.g. Test849, Test102...)")
        mode_input = input("Choice (1/2, default 2): ").strip()
        
        user_list = []
        
        if mode_input == "1":
            if not base_name:
                base_name = "User"
                
            start_str = input("Start Number (default 1): ").strip()
            start_num = int(start_str) if start_str.isdigit() else 1
            
            count_str = input("How many users (default 4): ").strip()
            count = int(count_str) if count_str.isdigit() else 4
            
            common_last_names = [
                "Santoso", "Wijaya", "Putri", "Pratama", "Saputra", 
                "Hidayat", "Nugroho", "Wibowo", "Kusuma", "Lestari",
                "Wahyuni", "Setiawan", "Kurniawan", "Sari", "Indah",
                "Megawati", "Sukarno", "Hatta", "Pangestu", "Wardhani",
                "Siregar", "Simanjuntak", "Pasaribu", "Nasution", "Lubis"
            ]
            
            for i in range(count):
                current_num = start_num + i
                f_name = f"{base_name}{current_num}"
                l_name = random.choice(common_last_names)
                user_list.append({'first': f_name, 'last': l_name})
                
        else:
            count_str = input("How many users (default 4): ").strip()
            count = int(count_str) if count_str.isdigit() else 4
            
            common_last_names = [
                "Santoso", "Wijaya", "Putri", "Pratama", "Saputra", 
                "Hidayat", "Nugroho", "Wibowo", "Kusuma", "Lestari",
                "Wahyuni", "Setiawan", "Kurniawan", "Sari", "Indah",
                "Megawati", "Sukarno", "Hatta", "Pangestu", "Wardhani",
                "Siregar", "Simanjuntak", "Pasaribu", "Nasution", "Lubis"
            ]
            
            for _ in range(count):
                if base_name:
                    f_name = f"{base_name}{random.randint(100, 999)}"
                else:
                    f_name = ''.join(random.choices(string.ascii_letters, k=6))
                
                l_name = random.choice(common_last_names)
                user_list.append({'first': f_name, 'last': l_name})

        print(f"\nGenerated {len(user_list)} users to create:")
        for u in user_list:
            print(f" - {u['first']} {u['last']}")
        
        print("\nProceeding to creation in 3 seconds...")
        time.sleep(3)
        
        create_bulk_users(driver, user_list, temp_email)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

CHROME_BINARY_PATH = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"

def find_chrome_executable():
    """Finds the Chrome executable path."""
    if os.path.exists(CHROME_BINARY_PATH):
        return CHROME_BINARY_PATH
    return None

def login_admin_console(action=None):
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("ERROR: Please set ADMIN_EMAIL and ADMIN_PASSWORD in .env file.")
        return

    print("Initializing Browser for Admin Console Login...")
    
    chrome_path = find_chrome_executable()
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,720")
    
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")
    print(f"Using Chrome Profile at: {profile_path}")
    
    if chrome_path:
        options.binary_location = chrome_path
        print(f"Using Chrome binary at: {chrome_path}")

    try:
        if chrome_path:
             driver = uc.Chrome(options=options, browser_executable_path=chrome_path, version_main=141)
        else:
             driver = uc.Chrome(options=options)

    except Exception as e:
        print(f"Failed to initialize Chrome: {e}")
        return

    try:
        print(f"Navigating to {ADMIN_CONSOLE_URL}...")
        driver.get(ADMIN_CONSOLE_URL)
        
        print("Checking for existing session...")
        try:
             WebDriverWait(driver, 5).until(
                lambda d: "admin.google.com" in d.current_url and "ServiceLogin" not in d.current_url
            )
             
             password_fields = driver.find_elements(By.CSS_SELECTOR, "input[name='Passwd'], input[name='password'], input[type='password']")
             if len(password_fields) > 0 and password_fields[0].is_displayed():
                 raise Exception("Password field detected! Session requires re-authentication.")
                 
             print("✅ Existing session found! Skipping credentials entry.")
             
             if action:
                 print(f"Action '{action}' pre-selected.")
                 if action == "delete":
                     run_mass_delete(driver)
                 elif action == "create":
                     run_batch_creation(driver)
                 else:
                     print(f"Unknown action: {action}")
             else:
                 print("\n" + "="*40)
                 print(" MODE SELECTION")
                 print("="*40)
                 print("[1] Create Bulk Users (Buat User Baru)")
                 print("[2] Mass Delete Users (Hapus Masal)")
                 
                 mode_choice = input("Select Mode (1/2): ").strip()
                 
                 if mode_choice == "2":
                     run_mass_delete(driver)
                 else:
                     run_batch_creation(driver)
                 
             return 
        except Exception as e_session:
             print(f"No active session found ({e_session}). Proceeding to login...")

        print("Checking if Password field is already visible...")
        skip_email = False
        try:
             password_input_check = WebDriverWait(driver, 5).until(
                 EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[name='Passwd']"))
             )
             print("✅ Password field found immediately! Skipping Email entry.")
             skip_email = True
        except:
             print("Password field not found. Proceeding to Email entry...")

        if not skip_email:
            print("Waiting for Email input...")
            try:
                email_input = WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='identifier']"))
                )
                human_type(email_input, ADMIN_EMAIL)
                random_delay()
                
                next_button = driver.find_element(By.ID, "identifierNext")
                if not next_button:
                     next_button = driver.find_element(By.CSS_SELECTOR, "button[type='button']") 
                
                next_button.click()
                print("Email entered. Clicked Next.")
            except Exception as e:
                print(f"Email stage skipped or failed (might be already logged in or different flow): {e}")

        random_delay(2, 4)

        print("Waiting for Password input...")
        try:
            password_input = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[name='Passwd']"))
            )
            
            human_type(password_input, ADMIN_PASSWORD)
            random_delay()
            
            password_next_button = driver.find_element(By.ID, "passwordNext")
            if not password_next_button:
                 password_next_button = driver.find_element(By.CSS_SELECTOR, "div#passwordNext button") 
            
            if not password_next_button: 
                 buttons = driver.find_elements(By.CSS_SELECTOR, "button")
                 for btn in buttons:
                     if "next" in btn.text.lower() or "berikutnya" in btn.text.lower():
                         password_next_button = btn
                         break
            
            if password_next_button:
                password_next_button.click()
                print("Password entered. Clicked Next.")
            else:
                print("Could not find Password Next button!")
                
        except Exception as e:
             print(f"Password stage failed: {e}")

        print("Waiting for Admin Console to load (checking URL)...")
        try:
            WebDriverWait(driver, 60).until(
                lambda d: d.current_url.startswith("https://admin.google.com/") 
                          and "ServiceLogin" not in d.current_url
                          and "signin" not in d.current_url
            )
            print(f"SUCCESS: Logged in! Current URL: {driver.current_url}")
            
            print(f"SUCCESS: Logged in! Current URL: {driver.current_url}")
            
            if action:
                 print(f"Action '{action}' pre-selected.")
                 if action == "delete":
                     run_mass_delete(driver)
                 elif action == "create":
                     run_batch_creation(driver)
                 else:
                     print(f"Unknown action: {action}")
            else:
                print("\n" + "="*40)
                print(" MODE SELECTION")
                print("="*40)
                print("[1] Create Bulk Users (Buat User Baru)")
                print("[2] Mass Delete Users (Hapus Masal)")
                
                mode_choice = input("Select Mode (1/2): ").strip()
                
                if mode_choice == "2":
                    run_mass_delete(driver)
                else:
                    run_batch_creation(driver)
            
        except Exception as e:
             print(f"Login verification failed (Timeout or Error): {e}")
             print(f"Current Title: {driver.title}")
             print(f"Current URL: {driver.current_url}")
             print("Please check if manual intervention is possible.")

        print("\nScript finished. Press Enter to close browser...")
        input()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            driver.quit()
        except OSError:
            pass 
        except Exception:
            pass

def run_mass_delete(driver):
    """
    Executes the Mass Delete flow:
    1. Select All residents
    2. Uncheck Admin
    3. Delete
    """
    print("\n--- Starting Mass Delete Sequence ---")
    
    if "/ac/users" not in driver.current_url:
        print("Navigating to Users list...")
        driver.get("https://admin.google.com/ac/users")
        random_delay(3, 5)
    
    try:
        print("Clicking 'Select All'...")
        select_all_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Pilih semua baris']"))
        )
        safe_click(driver, select_all_btn)
        random_delay(1, 2)
        
        print("Looking for Admin account to uncheck...")
        try:
            print("  - Looking for Admin Checkbox using DIRECT XPath...")
            
            admin_row_checkbox = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//tr[.//div[@title='admin'] or .//*[contains(text(), 'admin@kavera.biz.id')]]//div[@role='checkbox']"))
            )
            
            print(f"  - Found Checkbox directly: <{admin_row_checkbox.tag_name} aria-label='{admin_row_checkbox.get_attribute('aria-label')}'>")

            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", admin_row_checkbox)
            time.sleep(0.5)

            is_checked = admin_row_checkbox.get_attribute("aria-checked") == "true" or \
                         admin_row_checkbox.get_attribute("checked") == "true" or \
                         "true" in (admin_row_checkbox.get_attribute("class") or "") 
            
            if is_checked:
                print(f"  - Unchecking Admin row...")
                safe_click(driver, admin_row_checkbox)
            else:
                 print(f"  - Admin row was ALREADY unchecked (State: aria-checked={admin_row_checkbox.get_attribute('aria-checked')})")
                
        except Exception as e_admin:
            print(f"⚠️ Failed to uncheck Admin row. Error details: {e_admin}")
            print("Please MANUALLY uncheck admin@kavera.biz.id now!")
            try: print("\a") 
            except: pass
            input("Press Enter after verifying Admin is unchecked...")

        print("Waiting for UI to settle after uncheck (5 seconds)...")
        time.sleep(5) 

        print("Iterating all 'Opsi lainnya' buttons to find the Delete option...")
        
        found_delete = False
        
        all_btns = driver.find_elements(By.XPATH, "//*[@aria-label='Opsi lainnya'][@aria-haspopup='true']")
        print(f"  - Found {len(all_btns)} 'Opsi lainnya' buttons.")
        
        for i in range(len(all_btns)):
            try:
                btns = driver.find_elements(By.XPATH, "//*[@aria-label='Opsi lainnya'][@aria-haspopup='true']")
                if i >= len(btns):
                    break
                btn = btns[i]
                
                if not btn.is_displayed():
                    print(f"  - Button {i+1}: hidden, skip.")
                    continue
                
                print(f"  - Clicking button {i+1} (jsname={btn.get_attribute('jsname')})...")
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.3)
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(1.5)
                
                try:
                    hapus_el = WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.XPATH,
                            "//*[@jsname='mV7xqd'] | "
                            "//*[contains(text(), 'Hapus pengguna yang dipilih')]"
                        ))
                    )
                    print(f"  - ✅ Button {i+1} opened the correct menu! Clicking 'Hapus pengguna yang dipilih'...")
                    driver.execute_script("arguments[0].click();", hapus_el)
                    found_delete = True
                    break
                except:
                    print(f"  - Button {i+1}: 'Hapus pengguna yang dipilih' not visible. Closing...")
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    except: pass
                    time.sleep(0.5)
                    
            except Exception as e_btn:
                print(f"  - Button {i+1} error: {e_btn}")
                try:
                    driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                except: pass
                time.sleep(0.5)

        if not found_delete:
            print("❌ Could not find Delete option in any menu. Dumping Page Source...")
            with open("debug_page_source.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            raise Exception("Could not find 'Hapus pengguna yang dipilih' in any 'Opsi lainnya' menu.")
            
        random_delay(2, 3)
        
        print("Waiting for Confirmation Dialog...")
        try:
            confirm_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.t5nRo.Id5V1"))
            )
            print("  - Confirmation Dialog appeared! Clicking checkbox...")
            driver.execute_script("arguments[0].click();", confirm_checkbox)
            print("  - Clicked Confirmation Checkbox.")
            
            random_delay(1, 2)
            
            print("  - Looking for Final 'Hapus' button...")
            final_delete_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//*[@role='button'][.//*[contains(text(), 'Hapus')]] | "
                    "//button[contains(., 'Hapus')]"
                ))
            )
            driver.execute_script("arguments[0].click();", final_delete_btn)
            print("✅ CLICKED FINAL DELETE BUTTON.")
             
        except Exception as e_conf:
            print(f"❌ Failed during Confirmation Dialog: {e_conf}")
            try:
                with open("debug_confirm_dialog.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
            except: pass
            raise e_conf
        
        print("Waiting for deletion to process...")
        random_delay(5, 8)
        print("Mass Delete Sequence Finished.")
        input("DEBUG: Press Enter to close browser...")
        
    except Exception as e:
        print(f"❌ Mass Delete Failed: {e}")
        import traceback
        traceback.print_exc()
        try:
            input("DEBUG: Script crashed. Press Enter to close...")
        except KeyboardInterrupt:
            print("\nScript cancelled by user.")

if __name__ == "__main__":
    try:
        login_admin_console()
    except KeyboardInterrupt:
        print("\nScript cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        try:
           input("Press Enter to close...")
        except KeyboardInterrupt:
           pass
