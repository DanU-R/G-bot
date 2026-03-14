import asyncio
import os
import sys
from typing import List
from fastapi import BackgroundTasks, WebSocket
from .encryption import get_admin_credentials

active_connections: List[WebSocket] = []

async def broadcast_log(message: str):
    # Print to console as well
    print(message)
    # Broadcast to all connected websockets
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_text(message)
        except Exception:
            disconnected.append(connection)
            
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)

async def run_script_in_background(script_name: str, email: str = None, password: str = None, domain: str = None, **kwargs):
    """Executes a selenium script in the background with credentials as arguments."""
    script_path = os.path.join(os.getcwd(), script_name)
    
    # Menentukan binary python
    python_exe = sys.executable
    
    cmd = [
        python_exe, script_path
    ]
    if email:
        cmd.extend(["--email", email])
    if password:
        cmd.extend(["--password", password])
    if domain:
        cmd.extend(["--domain", domain])
    cmd.append("--headless")
    
    if "admin_login" in script_name:
        if "delete" in kwargs.get("action", ""):
            cmd.extend(["--action", "delete"])
        else:
            if kwargs.get("user_count"):
                cmd.extend(["--user-count", str(kwargs.get("user_count"))])
            if kwargs.get("name_prefix"):
                cmd.extend(["--name-prefix", str(kwargs.get("name_prefix"))])
            if kwargs.get("random_names"):
                cmd.extend(["--random-names"])
    
    # Check if reset_email.py and force
    if "reset_email" in script_name:
        cmd = [python_exe, script_path, "--force"]

    # Force unbuffered output for Python so logs stream immediately
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    msg = f"Triggering bot: {' '.join(cmd)}"
    await broadcast_log(f"\n[SYSTEM] {msg}")
    
    # Run async subprocess to capture logs in real-time
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env
    )
    
    log_file = os.path.join(os.getcwd(), f"{script_name}.log")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n--- Bot Started: {script_name} ---\n")
    
    # Read output line by line
    while True:
        line = await process.stdout.readline()
        if not line:
            break
            
        decoded_line = line.decode('utf-8', errors='replace').rstrip('\r\n')
        
        # Broadcast to web UI
        if decoded_line:
            await broadcast_log(decoded_line)
            
            # Save to file
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(decoded_line + "\n")
                
    await process.wait()
    await broadcast_log(f"[SYSTEM] Bot finished with code {process.returncode}\n")

def trigger_admin_bot(domain: str, admin_email: str, background_tasks: BackgroundTasks, user_count: int = 4, name_prefix: str = "User", random_names: bool = False):
    password = os.getenv("DEFAULT_PASSWORD", "")
    
    background_tasks.add_task(
        run_script_in_background, 
        "admin_login.py", 
        admin_email, 
        password, 
        domain,
        user_count=user_count,
        name_prefix=name_prefix,
        random_names=random_names
    )
    return True, "Admin bot triggered in background."

def trigger_activator_bot(domain: str, admin_email: str, background_tasks: BackgroundTasks):
    password = os.getenv("DEFAULT_PASSWORD", "")
    
    background_tasks.add_task(
        run_script_in_background, 
        "google_workspace_activator.py", 
        admin_email, 
        password, 
        domain
    )
    return True, "Activator bot triggered in background."

def trigger_mass_delete(domain: str, admin_email: str, background_tasks: BackgroundTasks):
    password = os.getenv("DEFAULT_PASSWORD", "")
    
    background_tasks.add_task(
        run_script_in_background, 
        "admin_login.py", 
        admin_email, 
        password, 
        domain,
        action="delete"
    )
    return True, "Mass Delete bot triggered in background."

def trigger_reset_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(
        run_script_in_background, 
        "reset_email.py"
    )
    return True, "Local data reset triggered in background."
