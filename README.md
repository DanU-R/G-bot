# Google Workspace Admin Bot

A powerful Python toolkit for automating Google Workspace admin tasks and user management. This project helps you bulk create users, mass delete them, and automatically accept workspace invitations.

## 📌 Overview

This project consists of two main scripts:

### 1. `admin_login.py` (Admin Console Bot)
Automates tasks directly in the Google Admin Console (admin.google.com).
- **Session Persistence**: Saves your login session so you don't need to re-enter credentials every time.
- **Mode 1: Bulk User Creation**: Creates multiple users in a single batch.
- **Mode 2: Mass Delete**: Automatically selects all users (except admin) and deletes them via bulk actions.

### 2. `google_workspace_activator.py` (Invitation Activator)
Automates the acceptance of Google Workspace invitations sent to external email addresses.
- **Temp Email Integration**: Uses Mail.tm API to generate and manage a temporary email address.
- **Auto-Activation**: Detects invitation emails, clicks the link, and sets up the account password.
- **Smart Logic**: Handles different invitation formats and prevents duplicate activations.

## 🛠 Prerequisites

- **Python 3.9+** installed.
- **Google Chrome** installed.
- **Internet Connection** (stable).

## 🚀 Installation

1. **Clone/Download** this repository.
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Configure Environment**:
   Create a `.env` file in the project folder:
   ```env
   ADMIN_EMAIL=admin@yourdomain.com
   ADMIN_PASSWORD=your_password_here
   ADMIN_CONSOLE_URL=https://admin.google.com/
   DEFAULT_PASSWORD=Sadewa123  # Optional: Password for created gsuite accounts
   ```

## 📖 How to Use

### 1. Managing Users (`admin_login.py`)
Run the admin bot:
```bash
python admin_login.py
```
You will be prompted to select a mode:
- **[1] Create Bulk Users**:  
  Useful for populating the workspace with test users.
  - **Base Name**: Enter a prefix (e.g., "Student"). Leave empty for defaults.
  - **Mode Selection**:
    - `1` **Sequential**: Creates `Student1`, `Student2`, etc.
    - `2` **Random**: Creates `Student849`, `Student102`, etc. (or purely random if no base name).
  - **Count**: Specify how many users to create.
- **[2] Mass Delete Users**:  
  **Warning**: This deletes all users *except* the admin account defined in `.env`.
  > **Note**: Fitur ini belum berjalan dengan sempurna (This feature is not fully stable yet). Use with caution.
  - It selects all users.
  - Unchecks the admin account.
  - Clicks "More Options" -> "Delete selected users".
  - Confirms the deletion dialog.

### 2. Activating Accounts (`google_workspace_activator.py`)
Run the activator bot:
```bash
python google_workspace_activator.py
```
- On the first run, it generates a new email address (saved in `email_credentials.txt`).
- **Copy this email** and invite it from your Google Admin Console.
- The bot will poll for emails and auto-activate the account when the invitation arrives.

**Options**:
- `--limit N`: Stop after N successful activations.
- `--reset`: Ignore history and re-process all emails.
- `--headless`: Run without visible browser (default).

## � File Structure

- **Core Scripts**:
  - `admin_login.py`: Main Admin Console automation script.
  - `google_workspace_activator.py`: Account activation automation script.
  - `reset_email.py`: Utility to wipe data and start fresh.

- **Data Files**:
  - `.env`: Your admin credentials (keep secret!).
  - `email_credentials.txt`: Generated temp email login.
  - `completed_accounts.txt`: Log of successfully activated accounts.
  - `created_users_log.txt`: Log of users created via bulk creation (Format: `First|Last|Email|Password`).
  - `processed_ids.txt`: History of processed email IDs to prevent duplicates.

  - `chrome_profile/`: Folder storing your browser session.

## 🍪 Managing the Chrome Profile

The script creates a folder named `chrome_profile` to **save your login session**.
- **Benefit**: You don't need to sign in every time you run the script.
- **Troubleshooting**: If you need to **switch accounts**, get stuck in a **login loop**, or face **CAPTCHA issues**:
  1. Stop the script (`Ctrl + C`).
  2. **Delete the `chrome_profile` folder**.
  3. Run the script again to force a fresh login.

## ❓ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **Browser doesn't open** | Run `pip install --upgrade undetected-chromedriver` setup. |
| **"Chrome Not Found"** | Check if Chrome is installed in the standard location. |
| **Script stops/crashes** | Press `Ctrl+C` to cancel safely. Check error logs. |
| **Login Loop/Captcha** | Delete the `chrome_profile` folder and try again to clear session cache. |
| **Mass Delete Fails** | Ensure language is English or Indonesian (script supports both). |

## 🔐 Security Note
- Credentials in `.env` and `email_credentials.txt` are stored locally in plain text. Do not share these files.
- This tool is for educational and authorized administrative use only.
