import json
from supabase_db import SupabaseDB
from rich import print
from rich.table import Table
from rich.console import Console

def view_pubsub_logs():
    """View recent Pub/Sub notifications from the database"""
    console = Console()
    
    try:
        # Connect to database
        db = SupabaseDB()
        
        # Get history events related to Pub/Sub
        result = db.supabase.table("gmail_history").select("*").eq("event_type", "notification_received").order("created_at", desc=True).limit(10).execute()
        
        if not result.data or len(result.data) == 0:
            console.print("[yellow]No Pub/Sub notification logs found[/yellow]")
            return
            
        # Create a table to display the logs
        table = Table(title="Recent Pub/Sub Notifications")
        table.add_column("Created At", style="cyan")
        table.add_column("User ID", style="green")
        table.add_column("History ID", style="blue")
        table.add_column("Details", style="yellow")
        
        for log in result.data:
            details = json.dumps(log.get("details", {}), indent=2)
            table.add_row(
                log.get("created_at", ""),
                log.get("user_id", ""),
                log.get("history_id", ""),
                details[:100] + "..." if len(details) > 100 else details
            )
            
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error viewing logs: {e}[/red]")

if __name__ == "__main__":
    print("""
╭─────────────────────────────────────────────────╮
│         EmailBot Pub/Sub Log Viewer             │
╰─────────────────────────────────────────────────╯
    """)
    view_pubsub_logs() 