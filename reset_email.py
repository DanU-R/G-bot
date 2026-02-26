import os
import sys

# Force UTF-8 for Windows Terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich import box

console = Console()

FILES_TO_RESET = [
    r"c:\hotspot\autologin\email_credentials.txt",
    r"c:\hotspot\autologin\processed_ids.txt",
    r"c:\hotspot\autologin\processed_ids.bak",
    r"c:\hotspot\autologin\completed_accounts.txt"
]

def reset_data():
    console.print(Panel("[bold red]⚠️  WARNING: DATA PURGE[/bold red]\n[white]This will permanently delete your session credentials and processing history.[/white]", border_style="red"))
    
    if Confirm.ask("[bold yellow]Are you sure you want to completely RESET all local data?[/bold yellow]", default=False):
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Status", width=4)
        table.add_column("File")

        for file_path in FILES_TO_RESET:
            fname = os.path.basename(file_path)
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    table.add_row("[green]✔[/green]", f"[dim]{fname}[/dim]")
                except Exception as e:
                    table.add_row("[red]✘[/red]", f"[bold red]{fname} ({e})[/bold red]")
            else:
                table.add_row("[blue]ℹ[/blue]", f"[dim]{fname} (skipped)[/dim]")
        
        console.print(table)
        console.print("\n[bold green]✅ SYSTEM RESET COMPLETE[/bold green]")
        console.print("[dim]Run the activation bot to start a fresh session.[/dim]")
    else:
        console.print("[dim]Reset operation aborted.[/dim]")

if __name__ == "__main__":
    try:
        reset_data()
    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled.[/red]")
