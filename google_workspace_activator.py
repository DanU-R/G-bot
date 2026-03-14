import os
import sys
import time
import random
import requests
import string
import json
import re
import argparse
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich import box
from dotenv import load_dotenv

# Force UTF-8 for Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

console = Console()
load_dotenv()

# Setup Argument Parser
parser = argparse.ArgumentParser(description='Google Workspace Activator Bot')
parser.add_argument('--email', help='Admin Email (not used for polling but for log)')
parser.add_argument('--password', help='Default User Password')
parser.add_argument('--domain', help='Workspace Domain')
parser.add_argument('--headless', action='store_true', help='Run in headless mode')
parser.add_argument('--limit', type=int, default=0, help='Number of accounts to activate')
parser.add_argument('--reset', action='store_true', help='Reset processed history')
args, unknown = parser.parse_known_args()

WORKSPACE_DOMAIN = args.domain or os.getenv("WORKSPACE_DOMAIN", "")
DEFAULT_USER_PWD = args.password or os.getenv("DEFAULT_USER_PASSWORD", "Sadewa123")

MAIL_TM_API_URL = "https://api.mail.tm"
CHROME_BINARY_PATH = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"

def get_available_domains():
    response = requests.get(f"{MAIL_TM_API_URL}/domains")
    response.raise_for_status()
    return response.json()['hydra:member']

def create_account(domain):
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    email = f"{username}@{domain}"
    payload = {"address": email, "password": password}
    response = requests.post(f"{MAIL_TM_API_URL}/accounts", json=payload)
    response.raise_for_status()
    return email, password

def get_token(email, password):
    payload = {"address": email, "password": password}
    response = requests.post(f"{MAIL_TM_API_URL}/token", json=payload)
    response.raise_for_status()
    return response.json()['token']

def get_messages(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAIL_TM_API_URL}/messages", headers=headers)
    response.raise_for_status()
    return response.json()['hydra:member']

def get_message_content(token, message_id):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAIL_TM_API_URL}/messages/{message_id}", headers=headers)
    response.raise_for_status()
    return response.json()

def extract_verification_link(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        if "google.com" in href and ("setup" in href or "verify" in href or "accept" in href):
            return href
    return None

def find_chrome_executable():
    if os.path.exists(CHROME_BINARY_PATH): return CHROME_BINARY_PATH
    if os.path.exists("/usr/bin/google-chrome"): return "/usr/bin/google-chrome"
    if os.path.exists("/usr/bin/google-chrome-stable"): return "/usr/bin/google-chrome-stable"
    return None

def random_delay(min_s=0.5, max_s=1.5):
    time.sleep(random.uniform(min_s, max_s))

def human_type(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def activate_google_workspace(activation_link, email, headless=False):
    options = uc.ChromeOptions()
    if headless or args.headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
    
    profile_path = "/app/chrome_profile" if os.path.exists("/app") else os.path.join(os.getcwd(), "chrome_profile")
    options.add_argument(f"--user-data-dir={profile_path}")

    chrome_path = find_chrome_executable()
    try:
        driver = uc.Chrome(options=options, browser_executable_path=chrome_path)
    except:
        driver = uc.Chrome(options=options)
    
    try:
        driver.get(activation_link)
        time.sleep(3)
        # Handle 'I understand'
        try:
            btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[value='Saya mengerti'], input[value='I understand'], button")))
            btn.click()
        except: pass
        
        # Set Password
        pwd_field = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
        human_type(pwd_field, DEFAULT_USER_PWD)
        confirm_field = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")[1]
        human_type(confirm_field, DEFAULT_USER_PWD)
        driver.find_element(By.CSS_SELECTOR, "input[type='submit'], button[type='submit']").click()
        time.sleep(5)
        
        completed_file = "/app/completed_accounts.txt" if os.path.exists("/app") else os.path.join(os.getcwd(), "completed_accounts.txt")
        with open(completed_file, "a") as f:
            f.write(f"{email}\n")
        print(f"SUCCESS: Activated {email}")
    except Exception as e:
        print(f"Activation failed: {e}")
    finally:
        driver.quit()

def main():
    console.print(Panel("[bold blue]--- Starting Google Workspace Activator ---[/bold blue]", box=box.SIMPLE))
    
    creds_file = "/app/email_credentials.txt" if os.path.exists("/app") else os.path.join(os.getcwd(), "email_credentials.txt")
    processed_id_file = "/app/processed_ids.txt" if os.path.exists("/app") else os.path.join(os.getcwd(), "processed_ids.txt")
    
    if args.reset and os.path.exists(processed_id_file):
        os.remove(processed_id_file)
        print("[SYSTEM] Processed history reset.")

    if not os.path.exists(creds_file):
        print("[ERROR] email_credentials.txt not found. Please run the Admin Bot first to create an account.")
        return

    email = ""
    password = ""
    with open(creds_file, "r") as f:
        for line in f:
            if line.startswith("Email:"): email = line.split("Email:")[1].strip()
            if line.startswith("Password:"): password = line.split("Password:")[1].strip()

    if not email or not password:
        print("[ERROR] Could not parse credentials from file.")
        return

    print(f"[PROCESS] Obtained credentials for polling: {email}")
    try:
        token = get_token(email, password)
    except Exception as e:
        print(f"[ERROR] Failed to get mail.tm token: {e}")
        return

    processed_ids = set()
    if os.path.exists(processed_id_file):
        with open(processed_id_file, "r") as f:
            processed_ids = set(line.strip() for line in f)

    activation_count = 0
    print("[SYSTEM] Entering polling loop (Ctrl+C to stop)...")
    
    try:
        while True:
            if args.limit > 0 and activation_count >= args.limit:
                print(f"[SYSTEM] Limit of {args.limit} activations reached.")
                break

            try:
                messages = get_messages(token)
                for msg in messages:
                    msg_id = msg['id']
                    if msg_id in processed_ids:
                        continue

                    print(f"[NOTIFICATION] New message found: {msg['subject']}")
                    content = get_message_content(token, msg_id)
                    html = content.get('html', [])
                    if isinstance(html, list): html = "".join(html)
                    
                    link = extract_verification_link(html)
                    if link:
                        print(f"[PROCESS] Activating Workspace via link...")
                        activate_google_workspace(link, email, headless=args.headless)
                        
                        with open(processed_id_file, "a") as f:
                            f.write(f"{msg_id}\n")
                        processed_ids.add(msg_id)
                        activation_count += 1
                        
                        if args.limit > 0 and activation_count >= args.limit:
                            break
                    else:
                        # Mark as processed even if no link, to avoid re-checking non-google emails
                        processed_ids.add(msg_id)
                        with open(processed_id_file, "a") as f:
                            f.write(f"{msg_id}\n")

            except Exception as e:
                print(f"[WARNING] Error in polling loop: {e}")
            
            time.sleep(10) # Poll every 10 seconds
            
    except KeyboardInterrupt:
        print("\n[SYSTEM] Activator stopped by user.")

if __name__ == "__main__":
    main()
