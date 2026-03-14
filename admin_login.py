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
        driver.get(ADMIN_CONSOLE_URL)
        time.sleep(3)
        if "signin" in driver.current_url or "ServiceLogin" in driver.current_url:
            if not ADMIN_PASSWORD:
                print("ERROR: Reached Google Login page, but no password was provided. Please configure DEFAULT_PASSWORD environment variable.")
                return
                
            # Login flow
            email_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='email']")))
            human_type(email_input, ADMIN_EMAIL)
            driver.find_element(By.ID, "identifierNext").click()
            password_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            human_type(password_input, ADMIN_PASSWORD)
            driver.find_element(By.ID, "passwordNext").click()
            WebDriverWait(driver, 60).until(lambda d: "admin.google.com" in d.current_url)

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
        random_delay(3, 5)
        
        print("[PROCESS] Selecting all users...")
        select_all_cb = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Pilih semua baris'], div[aria-label='Select all rows'], .VfPpkd-muoYxb-sMbiTe"))
        )
        safe_click(driver, select_all_cb)
        random_delay(1, 2)
        
        # Check if "Select all X users" link appears for large lists
        try:
            select_all_mega = driver.find_elements(By.XPATH, "//span[contains(text(), 'Pilih semua') and contains(text(), 'pengguna')] | //span[contains(text(), 'Select all') and contains(text(), 'users')]")
            if select_all_mega:
                print("[PROCESS] Selecting ALL users across all pages...")
                safe_click(driver, select_all_mega[0])
                random_delay(1, 2)
        except: pass

        print("[PROCESS] Clicking Delete button...")
        # Delete button is often a trash icon or in a menu
        delete_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Hapus pengguna'] | //div[@aria-label='Delete user'] | //span[contains(text(), 'Hapus')]/ancestor::button | //span[contains(text(), 'Delete')]/ancestor::button"))
        )
        safe_click(driver, delete_btn)
        random_delay(2, 3)
        
        print("[PROCESS] Confirming deletion in modal...")
        # Check for the checkbox to confirm in the modal
        try:
            confirm_box = driver.find_elements(By.CSS_SELECTOR, "div[role='checkbox']")
            for cb in confirm_box:
                safe_click(driver, cb)
        except: pass
        
        final_delete = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'HAPUS')]/ancestor::div[@role='button'] | //span[contains(text(), 'DELETE')]/ancestor::div[@role='button']"))
        )
        safe_click(driver, final_delete)
        
        print("[SUCCESS] Mass delete command submitted.")
        WebDriverWait(driver, 60).until(lambda d: "dihapus" in d.page_source or "deleted" in d.page_source)
        print("[SUCCESS] All users have been deleted.")
        
    except Exception as e:
        print(f"[ERROR] Mass delete failed: {e}")
    finally:
        print("[SYSTEM] Exiting Mass Delete flow.")

if __name__ == "__main__":
    action_to_run = args.action if args.action else ("create" if args.email else None)
    login_admin_console(action=action_to_run, headless=args.headless)
