import os

FILES_TO_RESET = [
    r"c:\hotspot\autologin\email_credentials.txt",
    r"c:\hotspot\autologin\processed_ids.txt",
    r"c:\hotspot\autologin\processed_ids.bak",
    r"c:\hotspot\autologin\completed_accounts.txt"
]

def reset_data():
    print("WARNING: This will delete your current email session AND all processing history.")
    confirmation = input("Are you sure you want to completely RESET the bot data? (y/n): ").strip().lower()
    
    if confirmation == 'y':
        for file_path in FILES_TO_RESET:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    print(f"✅ Deleted: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"❌ Failed to delete {os.path.basename(file_path)}: {e}")
            else:
                print(f"ℹ️ Not found (skipped): {os.path.basename(file_path)}")
        
        print("\nAll data reset. Run 'python google_workspace_activator.py' to start fresh.")
    else:
        print("Reset cancelled.")

if __name__ == "__main__":
    reset_data()
