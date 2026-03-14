import os
import time
import random
import sys
import argparse
from dotenv import load_dotenv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import requests
import json
import string
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

def safe_click(driver, element):
    try:
        element.click()
    except Exception:
        driver.execute_script("arguments[0].click();", element)

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

CHROME_BINARY_PATH = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"
def find_chrome_executable():
    if os.path.exists(CHROME_BINARY_PATH): return CHROME_BINARY_PATH
    if os.path.exists("/usr/bin/google-chrome"): return "/usr/bin/google-chrome"
    if os.path.exists("/usr/bin/google-chrome-stable"): return "/usr/bin/google-chrome-stable"
    return None

def handle_suspended_subscription(driver):
    try:
        suspended = driver.find_elements(By.XPATH, "//h1[contains(text(), 'Langganan ditangguhkan')]")
        if suspended and suspended[0].is_displayed():
            upgrade_btn = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'MINTA UPGRADE')]/ancestor::div[@role='button']")))
            safe_click(driver, upgrade_btn)
            time.sleep(2)
            driver.get("https://admin.google.com/u/0/")
    except: pass

def login_admin_console(action=None, headless=False):
    if not ADMIN_EMAIL:
        print("ERROR: Admin email missing. Please provide --email.")
        return
    
    if not ADMIN_PASSWORD:
        print("WARNING: Admin password missing. Assuming active persistent session exists.")

    options = uc.ChromeOptions()
    if headless or args.headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
    
    profile_path = "/app/chrome_profile" if os.path.exists("/app") else os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")

    chrome_path = find_chrome_executable()
    try:
        driver = uc.Chrome(options=options, browser_executable_path=chrome_path)
    except:
        driver = uc.Chrome(options=options)

    try:
        print("[PROCESS] Checking current login session...")
        driver.get(ADMIN_CONSOLE_URL)
        time.sleep(5)
        
        # Check if already logged in (look for dashboard elements)
        if "admin.google.com" in driver.current_url and "ServiceLogin" not in driver.current_url:
            print("[SUCCESS] Active session found! Proceeding without login.")
            handle_suspended_subscription(driver)
            if action == "delete": run_mass_delete(driver)
            elif action == "create": run_batch_creation(driver)
            return

        if "signin" in driver.current_url or "ServiceLogin" in driver.current_url:
            if not ADMIN_PASSWORD:
                print("ERROR: Reached Google Login page, but no password was provided. Please configure DEFAULT_PASSWORD environment variable.")
                return
                
            print("[PROCESS] Identifying email field...")
            email_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
            human_type(email_input, ADMIN_EMAIL)
            
            print("[PROCESS] Clicking Next...")
            next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "identifierNext")))
            safe_click(driver, next_btn)
            
            # Wait for either password field OR an error/security check
            print("[PROCESS] Waiting for password field...")
            try:
                password_input = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
                human_type(password_input, ADMIN_PASSWORD)
                
                pass_next = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "passwordNext")))
                safe_click(driver, pass_next)
                
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
            input("Press Enter to close...")
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
