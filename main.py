import os
import sys
import time

# Force UTF-8 for Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich import box
from rich.style import Style

# Import modules
import undetected_chromedriver as uc
original_del = getattr(uc.Chrome, "__del__", None)
def safe_del(self):
    try:
        if original_del:
            original_del(self)
    except (OSError, Exception):
        pass
uc.Chrome.__del__ = safe_del

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

import admin_login
import google_workspace_activator
import reset_email

console = Console()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def draw_interface(headless_mode):
    clear_screen()
    
    # Header
    title = Text("AUTOMATION PRO", style="bold white", justify="center")
    subtitle = Text("Google Workspace Management Suite", style="dim", justify="center")
    header_content = Text.assemble(title, "\n", subtitle)
    console.print(Panel(header_content, border_style="bright_black", padding=(1, 2)))

    # Status Bar
    h_status = "ENABLED" if headless_mode else "DISABLED"
    h_style = "green" if headless_mode else "red"
    status_text = Text.assemble(
        (" STATUS ", "bold white on blue"),
        " Headless: ", (h_status, f"bold {h_style}"),
        "  |  Environment: ", ("OK", "bold cyan"),
        "  |  Session: ", ("ACTIVE", "bold magenta")
    )
    console.print(status_text, justify="center")
    console.print("-" * console.width, style="dim")

    # Menu
    menu = Table(show_header=False, box=box.SIMPLE, expand=True)
    menu.add_column("Command", style="bold cyan", width=10)
    menu.add_column("Description", style="white")

    menu.add_row("1", "Add New Users [dim]• Multiple account creation[/dim]")
    menu.add_row("2", "Mass Delete [dim]• Clean up workspace[/dim]")
    menu.add_row("3", "Activation [dim]• Polling & Verification[/dim]")
    menu.add_row("4", "Reset Data [dim]• Purge local cache[/dim]")
    menu.add_row("H", f"Toggle Headless [dim]• Currently {h_status}[/dim]")
    menu.add_row("Q", "Quit Application")

    console.print(menu)
    console.print("\n" + "─" * console.width, style="dim")

def main_menu():
    headless_mode = True 
    while True:
        draw_interface(headless_mode)
        
        choice = console.input("[bold]» [/bold]").strip().lower()
        
        if choice == "1":
            console.print("\n[bold green]➜ INITIALIZING USER CREATION[/bold green]")
            admin_login.login_admin_console(action="create", headless=headless_mode)
            console.input("\n[dim]Press Enter to continue...[/dim]")
            
        elif choice == "2":
            console.print("\n[bold red]➜ INITIALIZING MASS DELETE[/bold red]")
            admin_login.login_admin_console(action="delete", headless=headless_mode)
            console.input("\n[dim]Press Enter to continue...[/dim]")

        elif choice == "h":
            headless_mode = not headless_mode
            
        elif choice == "3":
            console.print("\n[bold blue]➜ INITIALIZING ACTIVATION BOT[/bold blue]")
            google_workspace_activator.main()
            console.input("\n[dim]Press Enter to continue...[/dim]")
            
        elif choice == "4":
            console.print("\n[bold yellow]➜ INITIALIZING DATA RESET[/bold yellow]")
            reset_email.reset_data()
            console.input("\n[dim]Press Enter to continue...[/dim]")
            
        elif choice in ["0", "q", "exit"]:
            console.print("\n[dim]Shutting down...byebye!![/dim]")
            time.sleep(0.5)
            break
            
        else:
            console.print("[red]Invalid Command[/red]")
            time.sleep(0.5)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        console.print("\n[bold red]Terminated by user.[/bold red]")
