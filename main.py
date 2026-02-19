import os
import sys
import time

# Import modules
# We need to make sure the current directory is in sys.path to import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import admin_login
import google_workspace_activator
import reset_email

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_menu():
    while True:
        clear_screen()
        print("="*50)
        print(" GOOGLE WORKSPACE AUTOMATION TOOL PRO")
        print("="*50)
        print(" [1] Add User (Login Required)")
        print(" [2] Delete User (Login Required)")
        print(" [3] Activate Accounts (No Login Required)")
        print(" [4] Reset Email Data (No Login Required)")
        print(" [0] Exit")
        print("="*50)
        
        choice = input(" Select an option: ").strip()
        
        if choice == "1":
            print("\n🚀 Starting Add User Flow...")
            admin_login.login_admin_console(action="create")
            input("\nPress Enter to return to menu...")
            
        elif choice == "2":
            print("\n🗑️ Starting Mass Delete Flow...")
            admin_login.login_admin_console(action="delete")
            input("\nPress Enter to return to menu...")
            
        elif choice == "3":
            print("\n📧 Starting Account Activation...")
            google_workspace_activator.main()
            input("\nPress Enter to return to menu...")
            
        elif choice == "4":
            print("\n⚠️ Starting Data Reset...")
            reset_email.reset_data()
            input("\nPress Enter to return to menu...")
            
        elif choice == "0":
            print("\nExiting... Goodbye!")
            time.sleep(1)
            break
            
        else:
            print("\n❌ Invalid option. Please try again.")
            time.sleep(1.5)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nProgram interrupted. Exiting.")
