<div align="center">
  <h1>🚀 Google Workspace AutoBot</h1>
  <p><i>A powerful, automated, and elegant toolkit for Google Workspace Administrators</i></p>
  
  ![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
  ![Selenium](https://img.shields.io/badge/Selenium-Automated-green.svg)
  ![Rich](https://img.shields.io/badge/Rich-Terminal_UI-purple.svg)
</div>

---

## ✨ Features

**Google Workspace AutoBot** is designed to save administrators hours of tedious clicking by automating bulk user management and email invitation handling directly in the Google Admin Console.

### 👥 1. Admin Console Bot (`admin_login.py`)
Interact directly with `admin.google.com` seamlessly.
- **🛡️ Session Persistence**: Saves your login session (bypasses repetitive log-ins).
- **⚡ Bulk User Creation**: Generate and deploy dozens of users in seconds (supports sequential naming or realistic Indonesian/International name generation).
- **🗑️ Mass Delete**: One-click cleanup. Automatically selects, safely unchecks the active Admin, and bulk-deletes all users.

### 📨 2. Invitation Activator (`google_workspace_activator.py`)
A background polling bot that catches Google Workspace invites and activates them automatically.
- **📧 Temp Email Integration**: Uses the Mail.tm API for disposable incoming emails.
- **🤖 Auto-Acceptance**: Instantly detects invites, extracts verification links, and sets up the account password on autopilot.
- **⚙️ Smart Sync Logic**: 100% accurate queueing system prevents duplicate activations by syncing directly with the creation logs.

---

## 🛠️ Prerequisites

Ensure your system is ready before launching the bot:
- **Python 3.9** or higher
- **Google Chrome** (Standard desktop installation)
- **Stable Internet Connection**

---

## 🚀 Quick Start

### 1. Installation
Clone the repository and install the required dependencies:
```bash
git clone https://github.com/DanU-R/google-activator-bot.git
cd google-activator-bot
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Create a `.env` file in the root directory to store your credentials securely:
```env
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=your_super_secret_password
ADMIN_CONSOLE_URL=https://admin.google.com/

# Fallback Settings
WORKSPACE_DOMAIN=yourdomain.com       
DEFAULT_PASSWORD=Sadewa123            
```

---

## 💻 Usage: The Unified Dashboard

Launch the gorgeous `rich`-powered CLI dashboard:
```bash
python main.py
```

### Dashboard Menu:
1. **➕ Add New Users**: Create batches of users rapidly.
2. **🔥 Mass Delete**: Wipe all non-admin users from the workspace safely.
3. **✅ Activate Accounts**: Start the listener to auto-accept and verify incoming invites.
4. **🧹 Reset Data**: Purge cache and temporary emails.
> **💡 Pro Tip:** Toggle **Headless Mode** directly from the dashboard to hide the browser and run tasks silently in the background!

---

## 📁 Project Structure

```text
📦 google-activator-bot
 ┣ 📜 main.py                       # The unified CLI Dashboard
 ┣ 📜 admin_login.py                # Admin Console automation scripts
 ┣ 📜 google_workspace_activator.py # Email polling & auto-activation
 ┣ 📜 reset_email.py                # Cache wiping utility
 ┣ 📜 .env                          # Configuration (DO NOT SHARE)
 ┣ 📜 requirements.txt              # Dependencies
 ┗ 📂 chrome_profile/               # Saved Chrome session data
```

---

## 🍪 Session Management (Avoiding CAPTCHAs)

The bot creates a `chrome_profile` folder to store your active Google session. 
- **The Magic**: You only log in once.
- **Troubleshooting**: Stuck in a login loop, need to change admin accounts, or facing strict CAPTCHAs? Simply **delete the `chrome_profile` folder** to force a clean, fresh login on the next run.

---

## ❓ FAQ & Troubleshooting

| Issue | Quick Fix |
| :--- | :--- |
| **"Chrome Not Found"** | Verify Chrome is installed in `%LOCALAPPDATA%` or `Program Files`. |
| **Browser doesn't open** | Run `pip install --upgrade undetected-chromedriver`. |
| **Script freezes/crashes** | Press `Ctrl+C` to abort safely. Check the terminal for logs. |
| **Mass Delete Errors** | Ensure the browser language is set to English or Indonesian. |

---
