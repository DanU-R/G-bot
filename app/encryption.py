import os
import json
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

MASTER_KEY = os.getenv("MASTER_KEY")
if not MASTER_KEY:
    # Generasi key jika tidak ada (untuk pengembangan)
    MASTER_KEY = Fernet.generate_key().decode()
    print(f"WARNING: MASTER_KEY not found in env. Generated temporary key: {MASTER_KEY}")

cipher_suite = Fernet(MASTER_KEY.encode())

CREDENTIALS_PATH = "/app/chrome_profile/credentials.json"
# Fallback untuk local testing di luar Docker
if os.name == 'nt' or not os.path.exists("/app"):
    CREDENTIALS_PATH = os.path.join(os.getcwd(), "chrome_profile", "credentials.json")

def encrypt_password(password: str) -> str:
    """Encrypts a password using the MASTER_KEY."""
    return cipher_suite.encrypt(password.encode()).decode()

def decrypt_password(encrypted_password: str) -> str:
    """Decrypts a password using the MASTER_KEY."""
    return cipher_suite.decrypt(encrypted_password.encode()).decode()

def save_admin_credentials(domain: str, email: str, password: str):
    """Saves encrypted credentials to the JSON file."""
    os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
    
    data = {}
    if os.path.exists(CREDENTIALS_PATH):
        try:
            with open(CREDENTIALS_PATH, "r") as f:
                data = json.load(f)
        except:
            data = {}
            
    encrypted_pwd = encrypt_password(password)
    data[domain] = {
        "email": email,
        "password": encrypted_pwd
    }
    
    with open(CREDENTIALS_PATH, "w") as f:
        json.dump(data, f, indent=4)

def get_admin_credentials(domain: str):
    """Retrieves and decrypts credentials for a specific domain."""
    if not os.path.exists(CREDENTIALS_PATH):
        return None
        
    try:
        with open(CREDENTIALS_PATH, "r") as f:
            data = json.load(f)
            
        if domain in data:
            creds = data[domain]
            decrypted_pwd = decrypt_password(creds["password"])
            return {
                "email": creds["email"],
                "password": decrypted_pwd
            }
    except:
        pass
    return None
