import sys
import os
import json
import time
import random
import argparse
from dotenv import load_dotenv
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.chrome.service import Service
from selenium_stealth import stealth
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich import box

# Force UTF-8 for Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

console = Console()
load_dotenv()

# Setup Argument Parser
parser = argparse.ArgumentParser(description='Google Workspace Admin Bot')
parser.add_argument('--email', help='Admin Email')
parser.add_argument('--password', help='Admin Password')
parser.add_argument('--domain', help='Workspace Domain')
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--action', choices=['create', 'delete'], help='Action to perform (create or delete)', default=None)
parser.add_argument('--user-count', type=int, default=4, help='Number of users to create')
parser.add_argument('--name-prefix', type=str, default='User', help='Prefix for the generated users first name')
parser.add_argument('--random-names', action='store_true', help='Generate completely random names instead of using a prefix')
args, unknown = parser.parse_known_args()

ADMIN_EMAIL = args.email or os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = args.password or os.getenv("ADMIN_PASSWORD")
ADMIN_CONSOLE_URL = os.getenv("ADMIN_CONSOLE_URL", "https://admin.google.com/")
WORKSPACE_DOMAIN = args.domain or os.getenv("WORKSPACE_DOMAIN", "")

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
    creds_file = "/app/email_credentials.txt" if os.path.exists("/app") else os.path.join(os.getcwd(), "email_credentials.txt")
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
                    return email, password
        except Exception as e:
            print(f"Error reading credentials file: {e}")

    try:
        domains = get_available_domains()
        if not domains: return None, None
        domain = domains[0]['domain']
        username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        password = os.getenv("DEFAULT_PASSWORD") or ''.join(random.choices(string.ascii_letters + string.digits, k=12))
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

def safe_click(driver, element, use_js=False):
    try:
        if use_js:
            driver.execute_script("arguments[0].click();", element)
        else:
            element.click()
    except Exception as e:
        try:
            # Fallback to JS click if normal click fails
            driver.execute_script("arguments[0].click();", element)
        except Exception as e2:
            print(f"[DEBUG] safe_click failed: {e2}")
            raise e2

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def create_bulk_users(driver, user_data_list, secondary_email, domain=""):
    console.print(Panel(f"[bold blue]--- Starting Bulk Creation for {len(user_data_list)} Users ---[/bold blue]", box=box.SIMPLE))
    log_file = "/app/created_users_log.txt" if os.path.exists("/app") else os.path.join(os.getcwd(), "created_users_log.txt")
    try:
        if "/ac/users" not in driver.current_url:
            driver.get("https://admin.google.com/ac/users")
            random_delay(3, 5)
        
        add_floating_btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Tambahkan pengguna baru'], div[aria-label='Add new user']"))
        )
        safe_click(driver, add_floating_btn)
    
        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), BarColumn(), TaskProgressColumn(), TimeRemainingColumn(), console=console) as progress:
            form_task = progress.add_task("[cyan]Filling User Details...", total=len(user_data_list))
            WebDriverWait(driver, 60).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")))
            
            for i, user in enumerate(user_data_list):
                first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
                last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
                sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
                
                if i >= len(first_name_inputs):
                    add_another_btn = driver.find_element(By.XPATH, "//span[contains(text(), 'Tambahkan pengguna lain')]/ancestor::button | //span[contains(text(), 'Add another user')]/ancestor::button")
                    safe_click(driver, add_another_btn)
                    random_delay(1, 2)
                    first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
                    last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
                    sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
                
                human_type(first_name_inputs[i], user['first'])
                human_type(last_name_inputs[i], user['last'])
                if i < len(sec_emails): human_type(sec_emails[i], secondary_email)
                progress.advance(form_task)

            continue_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Lanjutkan')]/ancestor::div[@role='button'] | //span[contains(text(), 'Lanjutkan')]")))
            safe_click(driver, continue_btn)
            
            send_btn = WebDriverWait(driver, 30).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::button | //span[contains(text(), 'Send login instructions')]/ancestor::button")))
            safe_click(driver, send_btn)
            
            WebDriverWait(driver, 30).until(lambda d: "ditambahkan" in d.page_source or "added" in d.page_source)
            finish_btn = driver.find_element(By.XPATH, "//button[contains(., 'Selesai') or contains(., 'Done')]")
            safe_click(driver, finish_btn)
            
        with open(log_file, "a") as f:
            for user in user_data_list:
                safe_domain = domain.lstrip('@') if domain else ""
                workspace_email = f"{user['first'].lower()}@{safe_domain}" if safe_domain else "Unknown"
                f.write(f"{user['first']}|{user['last']}|{workspace_email}|{secondary_email}|BATCH\n")
        return True
    except Exception as e:
        print(f"Failed during bulk creation: {e}")
        return False

def run_batch_creation(driver):
    temp_email, _ = create_temp_mail_account()
    if not temp_email: temp_email = "fallback_recovery@kavera.biz.id"
    domain_name = WORKSPACE_DOMAIN or input("Enter Workspace Domain: ").strip().lstrip('@')
    
    user_list = []
    for _ in range(args.user_count):
        if args.random_names:
            first_name = ''.join(random.choices(string.ascii_letters, k=8)).capitalize()
            last_name = ''.join(random.choices(string.ascii_letters, k=6)).capitalize()
        else:
            first_name = f"{args.name_prefix}{random.randint(100,999)}"
            last_name = "Test"
        user_list.append({'first': first_name, 'last': last_name})
        
    create_bulk_users(driver, user_list, temp_email, domain=domain_name)

def find_chrome_executable():
    # Priority for Linux (Railway)
    if os.path.exists("/usr/bin/google-chrome"): return "/usr/bin/google-chrome"
    if os.path.exists("/usr/bin/google-chrome-stable"): return "/usr/bin/google-chrome-stable"
    # Fallback for Windows (Local)
    win_local = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"
    if os.path.exists(win_local): return win_local
    return None

def handle_suspended_subscription(driver):
    try:
        suspended = driver.find_elements(By.XPATH, "//h1[contains(text(), 'Langganan ditangguhkan')] | //h1[contains(text(), 'Subscription suspended')]")
        if suspended and suspended[0].is_displayed():
            print("[ALERT] Subscription suspended detected. Requesting upgrade...")
            upgrade_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'MINTA UPGRADE')]/ancestor::div[@role='button'] | //span[contains(text(), 'REQUEST UPGRADE')]/ancestor::div[@role='button']")))
            
            main_window = driver.current_window_handle
            safe_click(driver, upgrade_btn)
            random_delay(2, 4)
            
            # Google often opens a Support tab. Close any tab that isn't the main one.
            all_windows = driver.window_handles
            if len(all_windows) > 1:
                for window in all_windows:
                    if window != main_window:
                        driver.switch_to.window(window)
                        print(f"[PROCESS] Closing extra support tab: {driver.current_url}")
                        driver.close()
                driver.switch_to.window(main_window)
            
            # Return to main dashboard link
            driver.get("https://admin.google.com/u/0/")
            random_delay(3, 5)
    except Exception as e:
        print(f"[DEBUG] handle_suspended_subscription error: {e}")

def login_admin_console(action=None, headless=False):
    if not ADMIN_EMAIL:
        print("ERROR: Admin email missing. Please provide --email.")
        return
    
    if not ADMIN_PASSWORD:
        print("WARNING: Admin password missing. Assuming active persistent session exists.")

    is_headless = headless or args.headless

    def create_options():
        opts = webdriver.ChromeOptions()
        # Essential flags for Docker/Linux Native Chrome
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-setuid-sandbox")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--window-size=1920,1080")
        
        # Anti-detection flags
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
        
        # Exclude switches to prevent the "Chrome is being controlled by automated test software" bar
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        
        prof_base = "/app/chrome_profile" if os.path.exists("/app") else os.path.join(os.getcwd(), "chrome_profile")
        os.makedirs(prof_base, exist_ok=True)
        
        # Aggressively clear locks from previous crashes
        for lock_name in ["SingletonLock", "SingletonCookie", "SingletonSocket"]:
            lock_path = os.path.join(prof_base, lock_name)
            if os.path.exists(lock_path):
                try:
                    os.remove(lock_path)
                    print(f"[PROCESS] Cleared {lock_name}.")
                except:
                    pass
        
        opts.add_argument(f"--user-data-dir={prof_base}")
        return opts

    chrome_path = find_chrome_executable()
    print(f"[PROCESS] Chrome Path: {chrome_path}")
    
    try:
        options = create_options()
        if chrome_path:
            options.binary_location = chrome_path
        driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"[PROCESS] Warning: Initial WebDriver initialization failed, retrying... ({e})")
        time.sleep(2)
        options = create_options()
        if chrome_path:
            options.binary_location = chrome_path
        driver = webdriver.Chrome(options=options)
    
    print("[PROCESS] Driver initialized successfully. Applying stealth...")

    # Apply stealth to evade Google's Bot detection
    stealth(driver,
        languages=["en-US", "en"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    try:
        print(f"[PROCESS] Navigating to {ADMIN_CONSOLE_URL}...")
        driver.set_page_load_timeout(30) # Prevent indefinite hanging
        driver.get(ADMIN_CONSOLE_URL)
        print("[PROCESS] Page navigation command sent. Waiting for load...")
        time.sleep(5)
        print(f"[PROCESS] Current URL after load: {driver.current_url}")
        
        # Check if already logged in (look for dashboard elements)
        if "admin.google.com" in driver.current_url and "ServiceLogin" not in driver.current_url and "Logout" not in driver.current_url:
            print("[SUCCESS] Active session found! Proceeding without login.")
            handle_suspended_subscription(driver)
            
            # Verify we are on the final dashboard URL
            WebDriverWait(driver, 20).until(lambda d: "admin.google.com/u/0/" in d.current_url or "ac/home" in d.current_url)
            print(f"[SUCCESS] Final Dashboard reached: {driver.current_url}")
            
            if action == "delete": run_mass_delete(driver)
            elif action == "create": run_batch_creation(driver)
            return True

        if "signin" in driver.current_url or "ServiceLogin" in driver.current_url:
            if not ADMIN_PASSWORD:
                print("ERROR: Reached Google Login page, but no password was provided. Please configure DEFAULT_PASSWORD environment variable.")
                return
                
            print("[PROCESS] Identifying email field...")
            email_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
            human_type(email_input, ADMIN_EMAIL)
            
            print("[PROCESS] Clicking Next...")
            next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "identifierNext")))
            # Use JS click for critical navigation to avoid some uc-related crashes
            random_delay(1, 2)
            safe_click(driver, next_btn, use_js=True)
            
            # Wait for either password field OR an error/security check
            print("[PROCESS] Waiting for password field...")
            try:
                password_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
                human_type(password_input, ADMIN_PASSWORD)
                
                pass_next = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "passwordNext")))
                random_delay(1, 2)
                safe_click(driver, pass_next, use_js=True)
                
                print("[PROCESS] Finalizing login...")
                WebDriverWait(driver, 60).until(lambda d: "admin.google.com" in d.current_url)
            except Exception as e:
                # Diagnostics
                print(f"[DIAGNOSTIC] Current URL: {driver.current_url}")
                print(f"[DIAGNOSTIC] Page Title: {driver.title}")
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                
                if "verifikasi" in body_text or "verify" in body_text or "challenge" in body_text:
                    print("\n" + "="*60)
                    print(" [ATTENTION] GOOGLE IDENTITY VERIFICATION REQUIRED ".center(60, "!"))
                    print("="*60)
                    print("Google is asking to verify your identity. This usually happens")
                    print("on the first run from a new server (Railway).")
                    print("\nACTION REQUIRED:")
                    print("1. Check your Phone or Admin Email for a notification.")
                    print("2. Tap 'Yes, it's me' or enter the code shown on your device.")
                    print("3. The bot will wait for 60 seconds for you to complete this.")
                    print("="*60 + "\n")
                    
                    # Wait longer for manual 2FA completion
                    try:
                        WebDriverWait(driver, 60).until(lambda d: "admin.google.com" in d.current_url and "ServiceLogin" not in d.current_url)
                        print("[SUCCESS] Verification completed! Session is now saved.")
                    except:
                        print("[ERROR] Verification timed out.")
                        raise e
                elif "captcha" in body_text:
                    print("[SECURITY] Google is showing a CAPTCHA. Automation blocked.")
                elif "salah" in body_text or "not find" in body_text or "wrong" in body_text:
                    print("[ERROR] Google rejected the email or password. Please check your credentials.")
                
                raise e # Re-raise to trigger the main exception handler with traceback

        handle_suspended_subscription(driver)
        if action == "delete": run_mass_delete(driver)
        elif action == "create": run_batch_creation(driver)
        elif not action:
            # Manual choice if not automated
            run_batch_creation(driver)
        
    except Exception as e:
        import traceback
        print(f"[ERROR] Selenium Exception: {str(e)}")
        print(f"[TRACEBACK] {traceback.format_exc()}")
    finally:
        if not headless and not args.headless:
            try:
                # Only wait for input if NOT in headless mode (local debugging)
                import sys
                if sys.stdin.isatty():
                    input("Press Enter to close...")
            except: pass
        try:
            driver.quit()
        except: pass

def run_mass_delete(driver):
    console.print(Panel("[bold red]--- Starting Mass Delete Process ---[/bold red]", box=box.SIMPLE))
    try:
        print("[PROCESS] Navigating to Users list...")
        driver.get("https://admin.google.com/ac/users")
        
        # Wait for the table to at least start loading
        WebDriverWait(driver, 20).until(lambda d: d.find_elements(By.TAG_NAME, "table") or "pengguna" in d.page_source.lower() or "users" in d.page_source.lower())
        random_delay(4, 6) # Give it extra time for JS to render the checkboxes
        
        print("[PROCESS] Scanning for selection checkbox...")
        
        # Try multiple selector strategies for "Select all"
        selection_selectors = [
            (By.CSS_SELECTOR, "div[aria-label='Pilih semua baris']"),
            (By.CSS_SELECTOR, "div[aria-label='Select all rows']"),
            (By.CSS_SELECTOR, "th div[role='checkbox']"),
            (By.XPATH, "//th//div[@role='checkbox']"),
            (By.XPATH, "//div[contains(@aria-label, 'Pilih semua')]"),
            (By.CSS_SELECTOR, ".VfPpkd-muoYxb-sMbiTe")
        ]
        
        select_all_cb = None
        for by, selector in selection_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed():
                        select_all_cb = el
                        break
                if select_all_cb: break
            except: continue
            
        if not select_all_cb:
            print("[ERROR] Could not find 'Select All' checkbox. Page might be different or no users exist.")
            # Diagnostic: print aria-labels of all clickable divs
            return

        print("[PROCESS] Clicking 'Select All'...")
        safe_click(driver, select_all_cb)
        random_delay(2, 3)
        
        # Check if "Select all X users" link appears for large lists
        try:
            select_all_mega = driver.find_elements(By.XPATH, "//span[contains(text(), 'Pilih semua') and contains(text(), 'pengguna')] | //span[contains(text(), 'Select all') and contains(text(), 'users')]")
            if select_all_mega:
                print("[PROCESS] Selecting ALL users across all pages...")
                safe_click(driver, select_all_mega[0])
                random_delay(1, 2)
        except: pass

        print("[PROCESS] Searching for Delete button...")
        # Delete buttons can be dynamic
        delete_selectors = [
            (By.XPATH, "//div[@aria-label='Hapus pengguna']"),
            (By.XPATH, "//div[@aria-label='Delete user']"),
            (By.XPATH, "//span[contains(text(), 'Hapus')]/ancestor::button"),
            (By.XPATH, "//span[contains(text(), 'Delete')]/ancestor::button"),
            (By.XPATH, "//div[contains(@class, 'VfPpkd-Bz112c-LgbsSe') and .//span[contains(text(), 'Hapus')]]")
        ]
        
        delete_btn = None
        for by, selector in delete_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed() and el.is_enabled():
                        delete_btn = el
                        break
                if delete_btn: break
            except: continue

        if not delete_btn:
            print("[ERROR] Delete button not found or not active. Make sure users are selected.")
            return
            
        print("[PROCESS] Clicking Delete...")
        safe_click(driver, delete_btn)
        random_delay(2, 3)
        
        print("[PROCESS] Handling confirmation modal...")
        try:
            # Look for confirmation checkboxes inside the modal (e.g., delete data confirmation)
            modals = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
            if modals:
                confirm_boxes = modals[0].find_elements(By.CSS_SELECTOR, "div[role='checkbox']")
                for cb in confirm_boxes:
                    if not cb.get_attribute("aria-checked") == "true":
                        safe_click(driver, cb)
                        random_delay(0.5, 1)
        except: pass
        
        final_delete_selectors = [
            (By.XPATH, "//span[contains(text(), 'HAPUS')]/ancestor::div[@role='button']"),
            (By.XPATH, "//span[contains(text(), 'DELETE')]/ancestor::div[@role='button']"),
            (By.XPATH, "//button[.//span[contains(text(), 'Hapus')]]"),
            (By.XPATH, "//button[.//span[contains(text(), 'Delete')]]")
        ]
        
        final_btn = None
        for by, selector in final_delete_selectors:
            try:
                elements = driver.find_elements(by, selector)
                for el in elements:
                    if el.is_displayed():
                        final_btn = el
                        break
                if final_btn: break
            except: continue
            
        if final_btn:
            safe_click(driver, final_btn)
            print("[SUCCESS] Mass delete command submitted.")
            WebDriverWait(driver, 60).until(lambda d: "dihapus" in d.page_source or "deleted" in d.page_source or "tidak ada" in d.page_source.lower())
            print("[SUCCESS] Process completed.")
        else:
            print("[ERROR] Final confirmation button not found.")
        
    except Exception as e:
        print(f"[ERROR] Mass delete failed: {e}")
    finally:
        print("[SYSTEM] Exiting Mass Delete flow.")

if __name__ == "__main__":
    action_to_run = args.action if args.action else ("create" if args.email else None)
    login_admin_console(action=action_to_run, headless=args.headless)
