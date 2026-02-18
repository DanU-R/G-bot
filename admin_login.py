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

# Load environment variables
load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_CONSOLE_URL = os.getenv("ADMIN_CONSOLE_URL", "https://admin.google.com/")

def random_delay(min_s=1.0, max_s=3.0):
    time.sleep(random.uniform(min_s, max_s))

# Mail.tm API Configuration
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
    
    # 1. Try reading existing credentials
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

    # 2. Create new if not found
    print("Generating NEW content from Mail.tm...")
    try:
        domains = get_available_domains()
        if not domains:
            return None, None
            
        domain = domains[0]['domain']
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        email = f"{username}@{domain}"
        
        payload = {"address": email, "password": password}
        response = requests.post(f"{MAIL_TM_API_URL}/accounts", json=payload)
        response.raise_for_status()
        
        # Save to file
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
    
    # 1. Navigate/Click "Add User" (Same detection logic)
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
             # Ensure we are on the users list 
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

    # 2. Fill Forms loop
    try:
        print("Waiting for User Details Form...")
        WebDriverWait(driver, 60).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']"))
        )
        
        for i, user in enumerate(user_data_list):
            print(f"  > Filling data for User {i+1}: {user['first']} {user['last']}")
            
            # Re-fetch input lists every iteration to ensure we have fresh references and count
            first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
            last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
            sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
            
            # Check if we need to add a new row
            if i >= len(first_name_inputs):
                print("    Not enough rows. Clicking 'Tambahkan pengguna lain'...")
                try:
                    # Based on user snippet: <button ...><span ...>Tambahkan pengguna lain</span></button>
                    add_another_btn = driver.find_element(By.XPATH, 
                        "//span[contains(text(), 'Tambahkan pengguna lain')]/ancestor::button | " +
                        "//span[contains(text(), 'Add another user')]/ancestor::button"
                    )
                    safe_click(driver, add_another_btn)
                    random_delay(1, 2)
                    
                    # Refresh lists
                    first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
                    last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
                    sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
                except Exception as e_add_row:
                    print(f"    ❌ Failed to add new row: {e_add_row}")
                    break # Stop if we can't add more rows
            
            # Fill Data
            human_type(first_name_inputs[i], user['first'])
            random_delay(0.5)
            human_type(last_name_inputs[i], user['last'])
            random_delay(0.5)
            
            # Fill secondary email if available in this row
            if i < len(sec_emails):
                 # Clear if pre-filled (though usually empty)
                 human_type(sec_emails[i], secondary_email)
            
            random_delay(0.5)

        print("All users filled.")
        
        # 3. Click "Lanjutkan" (Continue)
        print("Looking for 'Lanjutkan' button...")
        continue_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Lanjutkan')]/ancestor::div[@role='button'] | //span[contains(text(), 'Lanjutkan')]"))
        )
        safe_click(driver, continue_btn)
        print("Clicked 'Lanjutkan'.")
        
        # 4. Handle "Send login instructions"
        print("Waiting for 'Kirim petunjuk login' button (Up to 30s)...")
        # No hard delay needed if we use a long timeout. The bot will check every 500ms.
        
        try:
             # Wait for button to be clickable (Dynamic)
             send_btn = WebDriverWait(driver, 30).until(
                 EC.element_to_be_clickable((By.XPATH, 
                    "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::button | " + 
                    "//span[contains(text(), 'Send login instructions')]/ancestor::button | " +
                    "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::div[@role='button']"
                 ))
             )
             
             # STAGE 1: Wait for "Blue Checks" (User Created) - Class: E9QP5b
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
             
             # Click "Send login instructions"
             safe_click(driver, send_btn)
             print("Clicked 'Kirim petunjuk login'.")
             
             # STAGE 2: Wait for "Green Checks" (Email Sent) - Class: L5gqXc
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

        # 5. Handle Final Confirmation (Done / Selesai)
        print("Waiting for final result...")
        WebDriverWait(driver, 30).until(
            lambda d: "ditambahkan" in d.page_source or "added" in d.page_source
        )
        print("✅ Bulk Users created successfully!")
        
        # Save to log
        with open(r"c:\hotspot\autologin\created_users_log.txt", "a") as log:
            for user in user_data_list:
                log.write(f"{user['first']}|{user['last']}|{secondary_email}|BATCH\n")

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
    
    # 1. Get/Create Temp Email
    temp_email, _ = create_temp_mail_account()
    if not temp_email:
        temp_email = "fallback_recovery@kavera.biz.id"
    
    # 2. Generate User List
    NUM_USERS = 4 # Lets try 4 to force adding a new row (usually default is 3)
    user_list = []
    
    for _ in range(NUM_USERS):
        f_name = f"User{random.randint(100, 999)}"
        l_name = f"Auto{random.randint(1000, 9999)}"
        user_list.append({'first': f_name, 'last': l_name})
    
    create_bulk_users(driver, user_list, temp_email)

# Chrome Binary Path (Same as in google_workspace_activator.py)
CHROME_BINARY_PATH = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"

def find_chrome_executable():
    """Finds the Chrome executable path."""
    if os.path.exists(CHROME_BINARY_PATH):
        return CHROME_BINARY_PATH
    return None

def login_admin_console():
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("ERROR: Please set ADMIN_EMAIL and ADMIN_PASSWORD in .env file.")
        return

    print("Initializing Browser for Admin Console Login...")
    
    chrome_path = find_chrome_executable()
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,720")
    
    # Session Persistence
    profile_path = os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")
    print(f"Using Chrome Profile at: {profile_path}")
    
    if chrome_path:
        options.binary_location = chrome_path
        print(f"Using Chrome binary at: {chrome_path}")

    try:
        if chrome_path:
             # version_main=141 is used in the other script, usually good to match if using that binary
             driver = uc.Chrome(options=options, browser_executable_path=chrome_path, version_main=141)
        else:
             driver = uc.Chrome(options=options)

    except Exception as e:
        print(f"Failed to initialize Chrome: {e}")
        return

    try:
        print(f"Navigating to {ADMIN_CONSOLE_URL}...")
        driver.get(ADMIN_CONSOLE_URL)
        
        # Check for existing session
        print("Checking for existing session...")
        try:
             # 1. Check URL
             WebDriverWait(driver, 5).until(
                lambda d: "admin.google.com" in d.current_url and "ServiceLogin" not in d.current_url
            )
             
             # 2. CRITICAL: Check if Password field is visible. If yes, we are NOT logged in.
             password_fields = driver.find_elements(By.CSS_SELECTOR, "input[name='Passwd'], input[name='password'], input[type='password']")
             if len(password_fields) > 0 and password_fields[0].is_displayed():
                 raise Exception("Password field detected! Session requires re-authentication.")
                 
             print("✅ Existing session found! Skipping credentials entry.")
             # START BATCH or MASS DELETE
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
                 
             return # Exit login function
        except Exception as e_session:
             print(f"No active session found ({e_session}). Proceeding to login...")

        # Check if we are already at the Password stage (Session expired / Verify it's you)
        print("Checking if Password field is already visible...")
        skip_email = False
        try:
             password_input_check = WebDriverWait(driver, 5).until(
                 EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[name='Passwd']"))
             )
             print("✅ Password field found immediately! Skipping Email entry.")
             skip_email = True
        except:
             print("Password field not found. Proceeding to Email entry...")

        # 1. Email / Identifier Stage
        if not skip_email:
            print("Waiting for Email input...")
            try:
                email_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='email'], input[name='identifier']"))
                )
                human_type(email_input, ADMIN_EMAIL)
                random_delay()
                
                # Click Next
                next_button = driver.find_element(By.ID, "identifierNext")
                if not next_button:
                     next_button = driver.find_element(By.CSS_SELECTOR, "button[type='button']") # Fallback
                
                next_button.click()
                print("Email entered. Clicked Next.")
            except Exception as e:
                print(f"Email stage skipped or failed (might be already logged in or different flow): {e}")

        random_delay(2, 4)

        # 2. Password Stage
        print("Waiting for Password input...")
        try:
            password_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password'], input[name='password'], input[name='Passwd']"))
            )
            
            human_type(password_input, ADMIN_PASSWORD)
            random_delay()
            
            # Click Next (Password)
            password_next_button = driver.find_element(By.ID, "passwordNext")
            if not password_next_button:
                 password_next_button = driver.find_element(By.CSS_SELECTOR, "div#passwordNext button") # Selector often used
            
            if not password_next_button: # Ultimate fallback
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

        # 3. Verify Login & Navigate to Users
        print("Waiting for Admin Console to load (checking URL)...")
        try:
            # Wait for URL to contain 'admin.google.com' which is language-independent
            WebDriverWait(driver, 60).until(
                lambda d: "admin.google.com" in d.current_url
            )
            print(f"SUCCESS: Logged in! Current URL: {driver.current_url}")
            
            print(f"SUCCESS: Logged in! Current URL: {driver.current_url}")
            
            # Start User Creation Flow (Batch) or Mass Delete
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

        # Keep browser open for user to see/interact
        print("\nScript finished. Press Enter to close browser...")
        input()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            driver.quit()
        except OSError:
            pass # Ignore standard WinError 6
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
    
    # 1. Navigate to Users List
    if "/ac/users" not in driver.current_url:
        print("Navigating to Users list...")
        driver.get("https://admin.google.com/ac/users")
        random_delay(3, 5)
    
    try:
        # 2. Select All
        print("Clicking 'Select All'...")
        select_all_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Pilih semua baris']"))
        )
        safe_click(driver, select_all_btn)
        random_delay(1, 2)
        
        # 3. Uncheck Admin (admin@kavera.biz.id)
        # Strategy: Find the EMAIL element, then find the CHECKBOX in the same row.
        # User snippet: <div class="MHH3bd" title="admin@kavera.biz.id">
        print("Looking for Admin account to uncheck...")
        try:
            print("  - Looking for Admin Checkbox using DIRECT XPath...")
            
            # Direct XPath Strategy based on User Snippet
            # Find TR that contains the email, then find the checkbox inside it
            # User Snippet Email: <div class="MHH3bd" title="admin@kavera.biz.id">admin@kavera.biz.id</div>
            # User Snippet Checkbox: <div ... role="checkbox" aria-label="Pilih baris" ...>
            
            admin_row_checkbox = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//tr[.//div[@title='admin'] or .//*[contains(text(), 'admin@kavera.biz.id')]]//div[@role='checkbox']"))
            )
            
            print(f"  - Found Checkbox directly: <{admin_row_checkbox.tag_name} aria-label='{admin_row_checkbox.get_attribute('aria-label')}'>")

            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", admin_row_checkbox)
            time.sleep(0.5)

            # Check status and uncheck if needed
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

        # 4 & 5. Iterate ALL "Opsi lainnya" buttons until we find the one with "Hapus pengguna"
        print("Iterating all 'Opsi lainnya' buttons to find the Delete option...")
        
        found_delete = False
        
        # Get all buttons (re-fetch each iteration to avoid stale references)
        all_btns = driver.find_elements(By.XPATH, "//*[@aria-label='Opsi lainnya'][@aria-haspopup='true']")
        print(f"  - Found {len(all_btns)} 'Opsi lainnya' buttons.")
        
        for i in range(len(all_btns)):
            try:
                # Re-fetch buttons each time to avoid stale element errors
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
                
                # Wait for menu to render, then check for "Hapus pengguna yang dipilih"
                try:
                    # Wait up to 3 seconds for the delete item to appear
                    # jsname='mV7xqd' is the clickable container div (from user snippet)
                    hapus_el = WebDriverWait(driver, 3).until(
                        EC.visibility_of_element_located((By.XPATH,
                            "//*[@jsname='mV7xqd'] | "
                            "//*[contains(text(), 'Hapus pengguna yang dipilih')]"
                        ))
                    )
                    print(f"  - ✅ Button {i+1} opened the correct menu! Clicking 'Hapus pengguna yang dipilih'...")
                    # Click the jsname='mV7xqd' container (the actual clickable element)
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
        
        # 6. Confirmation Dialog
        print("Waiting for Confirmation Dialog...")
        try:
            # Wait for the confirmation checkbox: div.t5nRo.Id5V1 (from user snippet)
            confirm_checkbox = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div.t5nRo.Id5V1"))
            )
            print("  - Confirmation Dialog appeared! Clicking checkbox...")
            driver.execute_script("arguments[0].click();", confirm_checkbox)
            print("  - Clicked Confirmation Checkbox.")
            
            random_delay(1, 2)
            
            # Look for Final Delete Button (any button with 'Hapus' text)
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
        
        # Wait for completion? User didn't specify, but usually good to wait a bit.
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
