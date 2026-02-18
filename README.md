# Google Workspace Activator Bot (Local Version)

## 📌 Overview
This Python tool automates the activation of Google Workspace accounts. It is designed to run locally on your machine, using a **Mail.tm** temporary email address to receive activation links and **Undetected-Chromedriver** to process them automatically.

> **Note**: This version is optimized for local usage and does not require Telegram integration.

## ✨ Features
- **Auto-Email Generation**: Automatically creates a persistent temporary email on the first run.
- **Smart Activation**: Detects activation emails from Google and processes the "Accept" and "Password Creation" steps.
- **Headless Operation**: Runs silently in the background (default) or visible mode.
- **Full Data Reset**: Includes a utility to completely wipe credentials and history for a fresh start.
- **Duplicate Prevention**: Tracks processed email IDs to confirm each account is only activated once.

## 🛠 Prerequisites
- **Python 3.9+** installed.
- **Google Chrome** browser installed.
- **Internet Connection** (stable).

## 🚀 Installation

1.  **Clone the Repository** (or download the files).
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *If `requirements.txt` is missing, run:*
    ```bash
    pip install requests beautifulsoup4 undetected-chromedriver
    ```

## 📖 Usage Workflow

1.  **Start the Bot**:
    ```bash
    python google_workspace_activator.py
    ```
2.  **Get the Email**:
    - On the first run, the bot will generate a new email (e.g., `user@domain.com`).
    - **Copy this email** and invite it from your **Google Admin Console**.
3.  **Wait for Activation**:
    - The bot polls the inbox every 10 seconds.
    - When an invitation arrives, it opens the link and sets up the account with a default password (usually `Sadewa123`).
4.  **Completion**:
    - Successful activations are logged in `completed_accounts.txt`.

## ⚙️ Command Line Options

| Command | Description |
| :--- | :--- |
| `python google_workspace_activator.py` | Standard run (Interactive limit selection). |
| `python google_workspace_activator.py --limit 10` | Stop after 10 successful activations. |
| `python google_workspace_activator.py --reset` | **Re-process** all emails in the inbox (ignore history). |
| `python google_workspace_activator.py --headless` | Run without opening the browser window (Default). |

## 🔄 Full Data Reset (Factory Reset)

If you need to switch to a **new email address** or clear all history:

```bash
python reset_email.py
```

This utility will:
1.  Ask for confirmation.
2.  **Delete** your current Mail.tm credentials (`email_credentials.txt`).
3.  **Delete** processing history (`processed_ids.txt`, `completed_accounts.txt`).
4.  **Clean** temporary cache files (`__pycache__`).

**Next Run**: The main script will generate a brand new email address and start fresh.

## 🔐 Changing the Default Password

By default, the bot sets the password for new accounts to `Sadewa123`. To change this:

1.  Open `google_workspace_activator.py` in a text editor.
2.  Search for the function `human_type(password_input, "Sadewa123")` (around line 211).
3.  Replace `"Sadewa123"` with your desired password.
4.  Also update the confirmation line shortly after: `human_type(confirm_input, "Sadewa123")`.


## 📂 File Structure
- `google_workspace_activator.py`: Main bot script.
- `reset_email.py`: Utility for cleaning data.
- `email_credentials.txt`: Stores your current temp email login.
- `completed_accounts.txt`: Log of activated accounts.
- `processed_ids.txt`: Database of processed email IDs.

## ❓ Troubleshooting

- **Browser Closes Immediately**: Typically a version mismatch. Run `pip install --upgrade undetected-chromedriver`.
- **"Chrome Not Found"**: Ensure Google Chrome is installed in the default location.
- **Stuck on "Waiting..."**: Check if the email was actually sent to the correct address shown in the terminal.
