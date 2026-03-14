import subprocess
import os
import sys
from fastapi import BackgroundTasks
from .encryption import get_admin_credentials

def run_script_in_background(script_name: str, email: str, password: str, domain: str):
    """Executes a selenium script in the background with credentials as arguments."""
    script_path = os.path.join(os.getcwd(), script_name)
    
    # Menentukan binary python
    python_exe = sys.executable
    
    cmd = [
        python_exe, script_path,
        "--email", email,
        "--password", password,
        "--domain", domain,
        "--headless"
    ]
    
    print(f"Triggering bot: {' '.join(cmd[:3])} --email {email} ...")
    
    # Menggunakan subprocess.Popen agar run di background tanpa memblokir FastAPI
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # Optional: Log output ke file
    log_file = os.path.join(os.getcwd(), f"{script_name}.log")
    with open(log_file, "a") as f:
        f.write(f"\n--- Bot Started for {domain} ---\n")
        # Kita tidak memblokir di sini, tapi di Docker real-world 
        # kita mungkin ingin menaruh output ke logger sistem

def trigger_admin_bot(domain: str, background_tasks: BackgroundTasks):
    creds = get_admin_credentials(domain)
    if not creds:
        return False, "Credentials not found for this domain."
    
    background_tasks.add_task(
        run_script_in_background, 
        "admin_login.py", 
        creds["email"], 
        creds["password"], 
        domain
    )
    return True, "Admin bot triggered in background."

def trigger_activator_bot(domain: str, background_tasks: BackgroundTasks):
    creds = get_admin_credentials(domain)
    if not creds:
        return False, "Credentials not found for this domain."
    
    background_tasks.add_task(
        run_script_in_background, 
        "google_workspace_activator.py", 
        creds["email"], 
        creds["password"], 
        domain
    )
    return True, "Activator bot triggered in background."
