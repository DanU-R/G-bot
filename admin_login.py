import os
import time
import random
import sys

# Force UTF-8 for Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

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

console = Console()

load_dotenv()

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_CONSOLE_URL = os.getenv("ADMIN_CONSOLE_URL", "https://admin.google.com/")
WORKSPACE_DOMAIN = os.getenv("WORKSPACE_DOMAIN", "")

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

def create_bulk_users(driver, user_data_list, secondary_email, domain=""):
    """
    Fills the 'Add new user' form for MULTIPLE users in one go.
    user_data_list: list of dicts [{'first': 'A', 'last': 'B'}, ...]
    """
    console.print(Panel(f"[bold blue]--- Starting Bulk Creation for {len(user_data_list)} Users ---[/bold blue]", box=box.SIMPLE))
    
    # Log directory
    log_file = r"c:\hotspot\autologin\created_users_log.txt"
    
    try:
        with console.status("[bold blue]Navigating to 'Add User' form...", spinner="dots"):
            try:
                add_user_btn = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//div[@role='button']//span[contains(text(), 'Tambahkan pengguna') or contains(text(), 'Add user')] | " +
                        "//div[aria-label='Tambahkan pengguna baru'] | " +
                        "//div[aria-label='Add new user']"
                    ))
                )
                safe_click(driver, add_user_btn)
            except:
                 if "/ac/users" not in driver.current_url:
                     driver.get("https://admin.google.com/ac/users")
                     random_delay(3, 5)

                 try:
                     add_floating_btn = WebDriverWait(driver, 15).until(
                         EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Tambahkan pengguna baru'], div[aria-label='Add new user']"))
                     )
                     safe_click(driver, add_floating_btn)
                 except Exception as wait_e:
                     try:
                         driver.save_screenshot("error_dashboard.png")
                         with open("error_dashboard.html", "w", encoding="utf-8") as f:
                             f.write(driver.page_source)
                     except: pass
                     raise Exception("Failed to find the 'Add User' button on the dashboard. Saved 'error_dashboard.png' for debugging.")
    
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            form_task = progress.add_task("[cyan]Filling User Details...", total=len(user_data_list))
            
            try:
                WebDriverWait(driver, 60).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']"))
                )
            except Exception as form_e:
                try:
                    driver.save_screenshot("error_form_load.png")
                    with open("error_form_load.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                except: pass
                raise Exception("Timed out waiting for the Add User form to load. Saved 'error_form_load.png'.")
            
            for i, user in enumerate(user_data_list):
                progress.update(form_task, description=f"[cyan]Filling: {user['first']} {user['last']}")
                
                first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
                last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
                sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
                
                if i >= len(first_name_inputs):
                    add_another_btn = driver.find_element(By.XPATH, 
                        "//span[contains(text(), 'Tambahkan pengguna lain')]/ancestor::button | " +
                        "//span[contains(text(), 'Add another user')]/ancestor::button"
                    )
                    safe_click(driver, add_another_btn)
                    random_delay(1, 2)
                    
                    first_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama depan'], input[aria-label='First name']")
                    last_name_inputs = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Nama belakang'], input[aria-label='Last name']")
                    sec_emails = driver.find_elements(By.CSS_SELECTOR, "input[aria-label='Alamat email sekunder'], input[aria-label='Secondary email']")
                
                human_type(first_name_inputs[i], user['first'])
                human_type(last_name_inputs[i], user['last'])
                
                if i < len(sec_emails):
                     human_type(sec_emails[i], secondary_email)
                
                progress.advance(form_task)

            progress.update(form_task, description="[bold green]Form Completed[/bold green]")
            
            # Continue
            continue_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Lanjutkan')]/ancestor::div[@role='button'] | //span[contains(text(), 'Lanjutkan')]"))
            )
            safe_click(driver, continue_btn)
            
            # Process & Send
            creation_task = progress.add_task("[magenta]Verifying Creation...", total=2)
            
            try:
                 send_btn = WebDriverWait(driver, 30).until(
                     EC.element_to_be_clickable((By.XPATH, 
                        "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::button | " + 
                        "//span[contains(text(), 'Send login instructions')]/ancestor::button | " +
                        "//span[contains(text(), 'Kirim petunjuk login')]/ancestor::div[@role='button']"
                     ))
                 )
                 
                 expected_count = len(user_data_list)
                 try:
                     WebDriverWait(driver, 60).until(
                         lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.Y6ROV.E9QP5b")) >= expected_count
                     )
                     progress.advance(creation_task)
                     progress.update(creation_task, description="[magenta]Users created (Stage 1)")
                 except:
                     pass
                 
                 safe_click(driver, send_btn)
                 
                 try:
                     WebDriverWait(driver, 60).until(
                         lambda d: len(d.find_elements(By.CSS_SELECTOR, "div.Y6ROV.L5gqXc")) >= expected_count
                     )
                     progress.advance(creation_task)
                     progress.update(creation_task, description="[bold green]Emails sent (Stage 2)")
                 except:
                     pass
            except:
                 pass

            # Final Finish
            finish_task = progress.add_task("[yellow]Finalizing...", total=1)
            WebDriverWait(driver, 30).until(
                lambda d: "ditambahkan" in d.page_source or "added" in d.page_source
            )
            
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
            except:
                 broad_btn = driver.find_element(By.XPATH, "//button[contains(., 'Selesai') or contains(., 'Done')]")
                 safe_click(driver, broad_btn)
            
            progress.advance(finish_task)
            
        # Log users after filling form (assuming they will be created successfully)
        try:
            with open(log_file, "a") as f:
                for user in user_data_list:
                    # Construct expected email if domain provided
                    safe_domain = domain.lstrip('@') if domain else ""
                    workspace_email = f"{user['first'].lower()}@{safe_domain}" if safe_domain else "Unknown"
                    f.write(f"{user['first']}|{user['last']}|{workspace_email}|{secondary_email}|BATCH\n")
        except Exception as e_log:
             print(f"Warning: Could not log to file: {e_log}")

        console.print("\n[bold green]✅ ALL TASKS COMPLETED SUCCESSFULLY[/bold green]")

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
    
    console.print(Panel("[bold cyan]USER GENERATION CONFIGURATION[/bold cyan]", expand=False, border_style="cyan"))
    
    try:
        base_name = input("Enter Base Name (Leave empty to use 'User' or random): ").strip()
        
        print("\nSelect Mode:")
        print("[1] Sequential (e.g. Test1, Test2, Test3...)")
        print("[2] Random Suffix (e.g. Test849, Test102...)")
        mode_input = input("Choice (1/2, default 2): ").strip()
        
        domain_prompt = f"Enter Workspace Domain (e.g. {WORKSPACE_DOMAIN if WORKSPACE_DOMAIN else 'yourdomain.com'}): "
        domain_name = input(domain_prompt).strip()
        if not domain_name and WORKSPACE_DOMAIN:
            domain_name = WORKSPACE_DOMAIN
        domain_name = domain_name.lstrip('@') # Prevent double @
        
        user_list = []
        
        common_first_names = [
            "Budi", "Andi", "Joko", "Siti", "Ani", "Dwi", "Tri", "Eko",
            "Arief", "Ahmad", "Rina", "Nina", "Dimas", "Rizky", "Putra",
            "Nur", "Sri", "Wahyu", "Agus", "Iwan", "Hendra", "Beni",
            "Gilang", "Aditya", "Fajar", "Ilham", "Indra", "Surya",
            "Yudi", "Roni", "Doni", "Reza", "Rio", "Kevin", "Bagus"
        ]
        
        common_last_names = [
            "Santoso", "Wijaya", "Putri", "Pratama", "Saputra", 
            "Hidayat", "Nugroho", "Wibowo", "Kusuma", "Lestari",
            "Wahyuni", "Setiawan", "Kurniawan", "Sari", "Indah",
            "Megawati", "Sukarno", "Hatta", "Pangestu", "Wardhani",
            "Siregar", "Simanjuntak", "Pasaribu", "Nasution", "Lubis",
            # International
            "Smith", "Johnson", "Williams", "Brown", "Jones",
            "Garcia", "Martinez", "Rodriguez", "Hernandez", "Lopez",
            "Lee", "Kim", "Chen", "Wang", "Singh",
            "Muller", "Schmidt", "Silva", "Santos", "Oliver"
        ]

        if mode_input == "1":
            if not base_name:
                base_name = "User"
                
            start_str = input("Start Number (default 1): ").strip()
            start_num = int(start_str) if start_str.isdigit() else 1
            
            count_str = input("How many users (default 4): ").strip()
            count = int(count_str) if count_str.isdigit() else 4
            
            for i in range(count):
                current_num = start_num + i
                f_name = f"{base_name}{current_num}"
                l_name = random.choice(common_last_names)
                user_list.append({'first': f_name, 'last': l_name})
                
        else:
            count_str = input("How many users (default 4): ").strip()
            count = int(count_str) if count_str.isdigit() else 4
            
            for _ in range(count):
                if base_name:
                    f_name = f"{base_name}{random.randint(100, 999)}"
                else:
                    # Random human name + short random number to ensure uniqueness
                    f_name = f"{random.choice(common_first_names)}{random.randint(10, 99)}"
                
                l_name = random.choice(common_last_names)
                user_list.append({'first': f_name, 'last': l_name})

        table = Table(title="Users to Create", box=box.SIMPLE)
        table.add_column("#", justify="right", style="cyan", no_wrap=True)
        table.add_column("First Name", style="magenta")
        table.add_column("Last Name", style="magenta")
        
        for i, u in enumerate(user_list):
            table.add_row(str(i+1), u['first'], u['last'])
            
        console.print(table)
        
        console.print("\n[bold yellow]Proceeding to creation in 3 seconds...[/bold yellow]")
        time.sleep(3)
        
        create_bulk_users(driver, user_list, temp_email, domain=domain_name)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return

CHROME_BINARY_PATH = r"C:\Users\LENOVO\AppData\Local\ms-playwright\chromium-1194\chrome-win\chrome.exe"

def find_chrome_executable():
    """Finds the Chrome executable path."""
    if os.path.exists(CHROME_BINARY_PATH):
        return CHROME_BINARY_PATH
    return None

def login_admin_console(action=None, headless=False):
    if not ADMIN_EMAIL or not ADMIN_PASSWORD:
        print("ERROR: Please set ADMIN_EMAIL and ADMIN_PASSWORD in .env file.")
        return

    print(f"Initializing Browser for Admin Console Login{' (HEADLESS)' if headless else ''}...")
    
    chrome_path = find_chrome_executable()
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1280,720")
    
    with console.status(f"[bold blue]Initializing Browser{' (HEADLESS)' if headless else ''}...", spinner="dots"):
        chrome_path = find_chrome_executable()
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1280,720")
        
        if headless:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        profile_path = os.path.join(os.getcwd(), "chrome_profile")
        options.add_argument(f"--user-data-dir={profile_path}")

        try:
            if chrome_path:
                 driver = uc.Chrome(options=options, browser_executable_path=chrome_path, version_main=141)
            else:
                 driver = uc.Chrome(options=options)
        except Exception as e:
            console.print(f"[bold red]Failed to initialize Chrome: {e}[/bold red]")
            return

    try:
        with console.status(f"[bold cyan]Connecting to {ADMIN_CONSOLE_URL}...", spinner="dots"):
            driver.get(ADMIN_CONSOLE_URL)
            
            WebDriverWait(driver, 5).until(
                lambda d: d.current_url.startswith("https://admin.google.com/") and "signin" not in d.current_url and "ServiceLogin" not in d.current_url
            )
             
            time.sleep(1) # Give time for potential re-auth prompts to render
            password_fields = driver.find_elements(By.CSS_SELECTOR, "input[name='Passwd'], input[name='password'], input[type='password']")
            if len(password_fields) > 0 and password_fields[0].is_displayed():
                raise Exception("Re-auth required")
                 
            console.print("[bold green]✅ Authenticated session found.[/bold green]")
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
            
        if not headless:
            print("\nScript finished. Press Enter to close browser...")
            input()
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

        if not headless:
            print("\nScript finished. Press Enter to close browser...")
            input()

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        try:
            if 'driver' in locals() and driver:
                driver.quit()
                driver = None
        except Exception:
            pass

def run_mass_delete(driver):
    """
    Executes the Mass Delete flow:
    1. Select All residents
    2. Uncheck Admin
    3. Delete
    """
    console.print(Panel("[bold red]--- Starting Mass Delete Sequence ---[/bold red]", box=box.SIMPLE))
    
    if "/ac/users" not in driver.current_url:
        with console.status("[cyan]Navigating to Users list...", spinner="dots"):
            driver.get("https://admin.google.com/ac/users")
            random_delay(3, 5)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task_id = progress.add_task("[cyan]Initializing mass delete...", total=None)
        
        try:
            progress.update(task_id, description="[cyan]Clicking 'Select All'...")
            select_all_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[aria-label='Pilih semua baris']"))
            )
            safe_click(driver, select_all_btn)
            random_delay(1, 2)
            progress.update(task_id, description="[bold green]✅ All users selected")
            
            progress.update(task_id, description="[cyan]Looking for Admin account to uncheck...")
            try:
                admin_row_checkbox = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, f"//tr[.//div[@title='admin'] or .//*[contains(text(), '{ADMIN_EMAIL}')]]//div[@role='checkbox']"))
                )
                
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", admin_row_checkbox)
                time.sleep(0.5)

                is_checked = admin_row_checkbox.get_attribute("aria-checked") == "true" or \
                             admin_row_checkbox.get_attribute("checked") == "true" or \
                             "true" in (admin_row_checkbox.get_attribute("class") or "") 
                
                if is_checked:
                    progress.update(task_id, description="[cyan]Unchecking Admin row...")
                    safe_click(driver, admin_row_checkbox)
                    
            except Exception as e_admin:
                progress.stop()
                console.print(f"\n[bold yellow]⚠️ Failed to uncheck Admin row automatically.[/bold yellow]")
                console.print(f"[bold red]Please MANUALLY uncheck {ADMIN_EMAIL} now![/bold red]")
                try: print("\a") 
                except: pass
                console.input("[dim]Press Enter after verifying Admin is unchecked...[/dim]")
                progress.start()

            progress.update(task_id, description="[cyan]Waiting for UI to settle...")
            time.sleep(5) 

            progress.update(task_id, description="[magenta]Iterating menus to find Delete option...")
            found_delete = False
            all_btns = driver.find_elements(By.XPATH, "//*[@aria-label='Opsi lainnya'][@aria-haspopup='true']")
            
            for i in range(len(all_btns)):
                try:
                    btns = driver.find_elements(By.XPATH, "//*[@aria-label='Opsi lainnya'][@aria-haspopup='true']")
                    if i >= len(btns):
                        break
                    btn = btns[i]
                    
                    if not btn.is_displayed():
                        continue
                    
                    progress.update(task_id, description=f"[magenta]Checking menu {i+1}/{len(all_btns)}...")
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
                    time.sleep(0.3)
                    driver.execute_script("arguments[0].click();", btn)
                    time.sleep(1.5)
                    
                    try:
                        time.sleep(1)
                        hapus_els = driver.find_elements(By.XPATH, 
                            "//*[@jsname='mV7xqd'] | "
                            "//*[contains(text(), 'Hapus pengguna yang dipilih')] | "
                            "//*[contains(text(), 'Delete selected users')]"
                        )
                        
                        hapus_el = None
                        for el in hapus_els:
                            if el.is_displayed():
                                hapus_el = el
                                break
                                
                        if not hapus_el:
                            raise Exception("Not visible")
                            
                        progress.update(task_id, description="[magenta]Clicking 'Hapus pengguna yang dipilih'...")
                        
                        try:
                            hapus_el.click()
                        except:
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                ActionChains(driver).move_to_element(hapus_el).click().perform()
                            except:
                                driver.execute_script("arguments[0].click();", hapus_el)
                                
                        found_delete = True
                        break
                    except Exception as click_err:
                        try:
                            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        except: pass
                        time.sleep(0.5)
                        
                except Exception as e_btn:
                    try:
                        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    except: pass
                    time.sleep(0.5)

            if not found_delete:
                progress.stop()
                console.print(f"[bold red]❌ Could not find Delete option in any menu.[/bold red]")
                with open("debug_page_source.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                raise Exception("Could not find 'Hapus pengguna yang dipilih' in any 'Opsi lainnya' menu.")
                
            progress.update(task_id, description="[bold green]✅ Initiated deletion")
            random_delay(2, 3)
            
            progress.update(task_id, description="[yellow]Waiting for Data Transfer Dialog...")
            try:
                dont_transfer_radio = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, 
                        "//label[contains(., 'Jangan transfer data')] | "
                        "//div[@aria-label='Jangan transfer data']"
                    ))
                )
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", dont_transfer_radio)
                time.sleep(0.5)
                safe_click(driver, dont_transfer_radio)
                progress.update(task_id, description="[yellow]Selected 'Jangan transfer data'")

                random_delay(1, 2)
                
                progress.update(task_id, description="[yellow]Looking for Final 'Hapus Pengguna' button...")
                final_delete_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH,
                        "//div[@role='button'][@aria-label='Hapus Pengguna'] | "
                        "//div[@role='button'][.//span[text()='Hapus Pengguna']] | "
                        "//span[text()='Hapus Pengguna']/ancestor::div[@role='button']"
                    ))
                )
                driver.execute_script("arguments[0].click();", final_delete_btn)
                progress.update(task_id, description="[bold green]✅ Final Delete Confirmed!")
                 
            except Exception as e_conf:
                progress.stop()
                console.print(f"[bold red]❌ Failed during Confirmation Dialog: {e_conf}[/bold red]")
                try:
                    with open("debug_confirm_dialog.html", "w", encoding="utf-8") as f:
                        f.write(driver.page_source)
                except: pass
                raise e_conf
            
            progress.update(task_id, description="[bold cyan]Waiting for deletion to process...")
            random_delay(5, 8)
            progress.update(task_id, description="[bold green]✅ Deletion completed successfully!", completed=True)
            time.sleep(1)
            
        except Exception as e:
            progress.stop()
            console.print(f"\n[bold red]❌ Mass Delete Failed: {e}[/bold red]")
            import traceback
            console.print(f"[dim]{traceback.format_exc()}[/dim]")
            try:
                console.input("[dim]Press Enter to close...[/dim]")
            except KeyboardInterrupt:
                console.print("\n[dim]Script cancelled by user.[/dim]")

    console.print("\n[bold green]✨ MASS DELETE SEQUENCE FINISHED[/bold green]")


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
