import requests
import time
import random
import string
import json
import re
import os
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import argparse
import sys

MAIL_TM_API_URL = "https://api.mail.tm"

CHROME_BINARY_PATH = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"

def get_available_domains():
    """Fetches available domains from mail.tm."""
    response = requests.get(f"{MAIL_TM_API_URL}/domains")
    response.raise_for_status()
    return response.json()['hydra:member']

def create_account(domain):
    """Creates a random account on mail.tm."""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
    email = f"{username}@{domain}"
    
    payload = {
        "address": email,
        "password": password
    }
    
    response = requests.post(f"{MAIL_TM_API_URL}/accounts", json=payload)
    response.raise_for_status()
    return email, password

def get_token(email, password):
    """Gets JWT token for the created account."""
    payload = {
        "address": email,
        "password": password
    }
    response = requests.post(f"{MAIL_TM_API_URL}/token", json=payload)
    response.raise_for_status()
    return response.json()['token']

def get_messages(token):
    """Fetches messages for the account."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAIL_TM_API_URL}/messages", headers=headers)
    response.raise_for_status()
    return response.json()['hydra:member']

def get_message_content(token, message_id):
    """Fetches specific message content."""
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{MAIL_TM_API_URL}/messages/{message_id}", headers=headers)
    response.raise_for_status()
    return response.json()

def extract_verification_link(html_content):
    """Extracts the verification link from the email HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        if "google.com" in href and ("setup" in href or "verify" in href or "accept" in href):
             return href
        text = link.get_text().lower()
        if "login" in text or "sign in" in text or "accept" in text:
            return href
            
    return None

def find_chrome_executable():
    """Finds the Chrome executable path. Returns None if not found (auto-download)."""
    if CHROME_BINARY_PATH:
        print(f"DEBUG: Checking configured path: {CHROME_BINARY_PATH}")
        if os.path.exists(CHROME_BINARY_PATH):
            print("DEBUG: Configured path exists.")
            return CHROME_BINARY_PATH
        else:
            print("DEBUG: Configured path NOT found. Switching to Auto-Download mode.")
            return None
    return None

def random_delay(min_s=0.5, max_s=1.5):
    """Sleeps for a random duration to mimic human behavior."""
    time.sleep(random.uniform(min_s, max_s))

def human_type(element, text):
    """Types text into an element with random delays between keystrokes."""
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))

def activate_google_workspace(activation_link, email):
    """Automates the browser steps to activate the account using Selenium (Headless)."""
    print(f"Opening browser to: {activation_link}")
    
    chrome_path = find_chrome_executable()
    print(f"Using Chrome at: {chrome_path}")

    options = uc.ChromeOptions()
    options.binary_location = chrome_path
    
    options.add_argument("--headless=new") 
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    try:
        if chrome_path:
            print(f"Initializing Chrome (Local) with version match 141...")
            driver = uc.Chrome(
                options=options, 
                browser_executable_path=chrome_path,
                version_main=141
            )
        else:
            print(f"Initializing Chrome (Cloud/Auto) with latest version...")
            driver = uc.Chrome(
                options=options
            )
    except Exception as e:
        print(f"Failed to initialize Chrome: {e}")
        return
    
    try:
        if not driver: return
        driver.get(activation_link)
        print(f"Page Title: {driver.title}")
        
        print("Waiting for Welcome page...")
        random_delay(2, 4)
        
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_delay(1, 2)
        
        print("Looking for 'I understand' button...")
        try:
            accept_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='confirm'], input[id='confirm'], input[value='Saya mengerti'], input[value='I understand']"))
            )
            random_delay()
            accept_button.click()
            print("Clicked 'I understand' (Input Match)")
            
        except Exception as e:
            print(f"Standard selector failed: {e}. Trying fallbacks...")
            try:
                accept_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Saya mengerti') or contains(text(), 'I understand')]/ancestor::button | //button[contains(text(), 'Saya mengerti') or contains(text(), 'I understand')]"))
                )
                random_delay()
                accept_button.click()
                print("Clicked 'I understand' (Button Match)")
            except:
                try:
                    submit_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='submit']")
                    if submit_inputs:
                        driver.execute_script("arguments[0].click();", submit_inputs[0])
                        print("Clicked 'I understand' (Generic Submit JS)")
                    else:
                        print("No submit inputs found.")
                except Exception as e3:
                     print(f"All click attempts failed: {e3}")
        
        random_delay(2, 3)

        print("Waiting for Password input...")
        password_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='Password'], input[name='password'], input[type='password']"))
        )
        
        human_type(password_input, "Sadewa123")
        random_delay()
        
        try:
             confirm_input = driver.find_element(By.CSS_SELECTOR, "input[name='ConfirmPassword'], input[name='confirm_password'], input[name='password_confirmation']")
             human_type(confirm_input, "Sadewa123")
        except:
             inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='password']")
             if len(inputs) > 1:
                 human_type(inputs[1], "Sadewa123")
        
        print("Passwords entered.")
        random_delay()
        
        print("Looking for Submit button...")
        try:
            submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit'], input[id='submit'], button[type='submit']")
            submit_btn.click()
            print("Submitted password (Standard)")
        except:
            try:
                submit_btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                driver.execute_script("arguments[0].click();", submit_btn)
                print("Submitted password (JS)")
            except Exception as e:
                print(f"Could not click submit: {e}")
        
        random_delay(3, 5) 
        print(f"Page Title after submit: {driver.title}")
        
        confirmed_email = email 
        if "Unknown" in confirmed_email: confirmed_email = None 
        
        found_in_ui = False
        
        if not found_in_ui:
            try:
                 email_element = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.eYSAde"))
                 )
                 if email_element and "@" in email_element.text:
                     confirmed_email = email_element.text.strip()
                     print(f"Confirmed Account Email from UI (div.eYSAde): {confirmed_email}")
                     found_in_ui = True
            except:
                 pass
        
        if not found_in_ui:
            try:
                print("Checking iframe 'account' for email...")
                driver.switch_to.frame("account")
                body_text = driver.find_element(By.TAG_NAME, "body").text
                match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", body_text)
                if match:
                    confirmed_email = match.group(1)
                    print(f"Confirmed Account Email from UI (iframe): {confirmed_email}")
                    found_in_ui = True
            except Exception as e:
                 print(f"Iframe check failed: {e}")
                 driver.switch_to.default_content()

        if not found_in_ui:
            try:
                print("Checking 'Dikelola oleh' in dialog...")
                dialogs = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
                for dialog in dialogs:
                    links = dialog.find_elements(By.TAG_NAME, "a")
                    for link in links:
                        if "Dikelola oleh" in link.text or "Managed by" in link.text:
                            found_id = link.get_attribute("id")
                            print(f"Found 'Dikelola oleh' link ID: {found_id}")
                            
                            aria_label_ids = link.get_attribute("aria-labelledby")
                            if aria_label_ids:
                                print(f"Found aria-labelledby: {aria_label_ids}")
                                ids = aria_label_ids.split()
                                for aid in ids:
                                    if aid != found_id: 
                                        try:
                                            related_elem = driver.find_element(By.ID, aid)
                                            print(f"DEBUG: Found object with ID '{aid}'. Text Content: '{related_elem.text}'")
                                            
                                            content_match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", related_elem.text)
                                            if content_match:
                                                confirmed_email = content_match.group(1)
                                                print(f"Confirmed Account Email from Object (Strategy 3 - Aria): {confirmed_email}")
                                                found_in_ui = True
                                        except Exception as e_inner:
                                            print(f"DEBUG: Could not read object '{aid}': {e_inner}")
                            
                            if found_in_ui: break
                            
                    if found_in_ui: break
            except Exception as e:
                print(f"Strategy 3 failed: {e}")

        if not found_in_ui:
            try:
                print("Strategy 4: Scanning entire dialog text...")
                dialogs = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
                for dialog in dialogs:
                    print(f"DEBUG: Dialog Text: {dialog.text[:100]}...") 
                    match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", dialog.text)
                    if match:
                         confirmed_email = match.group(1)
                         print(f"Confirmed Account Email from Dialog Text (Strategy 4): {confirmed_email}")
                         found_in_ui = True
                         break
            except:
                pass

        if not confirmed_email:
            confirmed_email = "Unknown_Email_Check_Manually"

        print("Process completed.")
        
        try:
            with open(r"c:\hotspot\autologin\completed_accounts.txt", "a") as f:
                f.write(f"{confirmed_email}\n")
            print(f"SUCCESS: Saved {confirmed_email} to completed_accounts.txt")
        except Exception as e:
            print(f"Failed to save log: {e}")

    except Exception as e:
        print(f"An error occurred during browser automation: {e}")
    finally:
        try:
            if 'driver' in locals() and driver:
                driver.quit()
        except OSError:
            pass 
        except Exception:
            pass
        
        try:
             import psutil
             for proc in psutil.process_iter():
                 if "chrome" in proc.name().lower() and "--headless" in " ".join(proc.cmdline()):
                      proc.kill()
        except:
             pass

def cleanup_driver():
    """Forcefully cleans up lingering chrome/driver processes."""
    print("Performing pre-run cleanup...")
    try:
        os.system("taskkill /F /IM chromedriver.exe /T >nul 2>&1")
    except:
        pass

def login(email, password):
    """Logs in to an existing account to get a token."""
    payload = {
        "address": email,
        "password": password
    }
    response = requests.post(f"{MAIL_TM_API_URL}/token", json=payload)
    if response.status_code == 401:
        return None
    response.raise_for_status()
    return response.json()['token']

def load_credentials():
    """Loads credentials from file if they exist."""
    try:
        with open("c:\\hotspot\\autologin\\email_credentials.txt", "r") as f:
            lines = f.readlines()
            email = None
            password = None
            for line in lines:
                if line.startswith("Email:"):
                    email = line.split("Email:")[1].strip()
                elif line.startswith("Password:"):
                    password = line.split("Password:")[1].strip()
            return email, password
    except FileNotFoundError:
        return None, None

def extract_workspace_email(html_content, text_content):
    """Extracts the Google Workspace email from the message."""
    patterns = [
        r"Welcome to your new Google Account for\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"Selamat datang di Akun Google baru Anda untuk\s+([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"Username:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"Nama pengguna:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"Email:\s*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"
    ]
    
    for content in [html_content, text_content]:
        if not content: continue
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
    
    print("DEBUG: Could not extract email. Dumping content snippet:")
    print(text_content[:200] if text_content else "No Text Content")
    return None

def load_processed_ids():
    try:
        if os.path.exists("c:\\hotspot\\autologin\\processed_ids.txt"):
            with open("c:\\hotspot\\autologin\\processed_ids.txt", "r") as f:
                return set(line.strip() for line in f if line.strip())
    except:
        pass
    return set()

def save_processed_id(msg_id):
    try:
        with open("c:\\hotspot\\autologin\\processed_ids.txt", "a") as f:
            f.write(f"{msg_id}\n")
    except:
        pass

def main():
    time.sleep(1)
    
    try:
        print("Initializing Mail.tm...")
        
        email, password = load_credentials()
        token = None
        
        if email and password:
            print(f"Found existing credentials for: {email}")
            print("Attempting to login...")
            token = login(email, password)
            if token:
                print("Login successful.")
            else:
                print("Login failed. Creating new account...")
                email = None 
        
        if not email or not token:
            domains = get_available_domains()
            if not domains:
                print("No domains available on mail.tm")
                return
    
            domain = domains[0]['domain']
            email, password = create_account(domain)
            token = get_token(email, password)
            
            print(f"\n--- CREATED ACCOUNT ---")
            print(f"Email: {email}")
            print(f"Password: {password}")
            print(f"-----------------------\n")
            
            with open("c:\\hotspot\\autologin\\email_credentials.txt", "w") as f:
                f.write(f"Email: {email}\nPassword: {password}")
    
        print("Please enter this email into your Google Admin Console to send the activation invitations.")
        print(f"Current Email: {email}") 
        
        parser = argparse.ArgumentParser(description='Google Workspace Activator Bot')
        parser.add_argument('--limit', type=int, default=0, help='Number of accounts to activate (0 for unlimited)')
        parser.add_argument('--reset', action='store_true', help='Reset processed history')
        parser.add_argument('--headless', action='store_true', default=True, help='Run in headless mode (default)')
    
        
        args, unknown = parser.parse_known_args()
    
        if args.limit > 0:
            activation_limit = args.limit
            print(f"Activation limit set to {activation_limit} (via CLI).")
        elif args.limit == 0 and any(arg.startswith('--') for arg in sys.argv):
            activation_limit = float('inf')
            print("Activation limit set to Unlimited (via CLI).")
        else:
            try:
                print("\nPress Enter for Unlimited (Default)...")
                limit_input = input("How many accounts? ").strip()
                activation_limit = int(limit_input) if limit_input.isdigit() else float('inf')
            except Exception as e_input:
                 print(f"Input error: {e_input}. Defaulting to unlimited.")
                 activation_limit = float('inf')
            
        if activation_limit != float('inf'):
             print(f"Will stop after {activation_limit} successful activations.")
    
        print("Waiting for NEW emails from Google... (Polling every 10 seconds)")
        print("Press Ctrl+C to stop the script.")
        
        processed_ids = load_processed_ids()
        print(f"Loaded {len(processed_ids)} processed email IDs.")
    except Exception as e_start:
        print(f"Startup Error: {e_start}")
        import traceback
        traceback.print_exc()
        return

    try:
        should_reset = args.reset
        if not should_reset and not any(arg.startswith('--') for arg in sys.argv):
             try:
                 reset_choice = input("Reset processed history? (y/n): ").strip().lower()
                 if reset_choice == 'y':
                     should_reset = True
             except:
                 pass
                 
        if should_reset:
            print("History reset. Will process ALL matching emails found.")
            processed_ids = set()
            if os.path.exists(r"c:\hotspot\autologin\processed_ids.txt"):
                 try:
                     os.rename(r"c:\hotspot\autologin\processed_ids.txt", r"c:\hotspot\autologin\processed_ids.bak")
                     print("Backed up old history to processed_ids.bak")
                 except:
                     pass
        
        session_activations = 0
    
        print("DEBUG: Entering main loop...")
        while True:
            try:
                if session_activations >= activation_limit:
                    print(f"\nReached limit of {activation_limit} activations. Stopping script.")
                    break

                messages = get_messages(token)
                messages.sort(key=lambda x: x['createdAt'], reverse=True)
                
                new_activation_found = False
                
                for msg in messages:
                    if msg['id'] in processed_ids:
                        continue
                    
                    if "google.com" in msg['from']['address'] or "Google" in msg['from']['name']:
                         print(f"Processing new email from: {msg['from']['address']} (ID: {msg['id']})")
                         full_msg = get_message_content(token, msg['id'])
                         
                         html = full_msg.get('html') or ""
                         if isinstance(html, list): html = "".join(html)
                         
                         text = full_msg.get('text') or ""
                         if isinstance(text, list): text = "".join(text)
                         
                         link = extract_verification_link(html) or extract_verification_link(text)
                         workspace_email = extract_workspace_email(html, text)
                         
                         if link:
                             print(f"Found activation link: {link}")
                             target_email = workspace_email if workspace_email else f"Unknown_Workspace_Email"
                             
                             activate_google_workspace(link, target_email)
                             
                             processed_ids.add(msg['id'])
                             save_processed_id(msg['id'])
                             new_activation_found = True
                             
                             session_activations += 1
                             
                             success_msg = f"✅ Activated: `{target_email}`"
                             print(success_msg)
                             
                             print(f"Session Activations: {session_activations}/{activation_limit if activation_limit != float('inf') else 'Unlimited'}")
                             
                             if session_activations >= activation_limit:
                                 print("Limit reached in inner loop.")
                                 print(f"🛑 **Batch Completed**: {session_activations} accounts activated.")
                                 break
                                 
                             print("Waiting for NEXT email...")
                         else:
                             print("Google email found but no activation link. Marking processed.")
                             processed_ids.add(msg['id'])
                             save_processed_id(msg['id'])
                
                if not new_activation_found and session_activations < activation_limit:
                     print(f"\rWaiting for new emails... (Checked at {time.strftime('%H:%M:%S')})", end="", flush=True)
                     time.sleep(10)
                 
            except KeyboardInterrupt:
                print("\nStopping script...")
                break
            except Exception as e:
                print(f"Error polling messages: {e}")
                time.sleep(10)

    except Exception as e_main:
        print(f"Critical Error in Main Loop: {e_main}")
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript cancelled by user.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
