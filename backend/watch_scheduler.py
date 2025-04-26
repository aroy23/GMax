import json
import threading
import time
from typing import Dict, List
from datetime import datetime, timedelta

from supabase_db import SupabaseDB
from gmail_service import GmailService

class WatchScheduler:
    """Scheduler to renew Gmail watches before they expire"""
    
    def __init__(self, db: SupabaseDB):
        """
        Initialize the watch scheduler
        
        Args:
            db: Database instance
        """
        self.db = db
        self.running = False
        self.check_interval = 3600  # Check once per hour
    
    def start(self) -> None:
        """Start the watch scheduler in a background thread"""
        if self.running:
            return
        
        self.running = True
        thread = threading.Thread(target=self._run_scheduler)
        thread.daemon = True  # Allow the thread to exit when the main program exits
        thread.start()
        print("Watch scheduler started")
    
    def stop(self) -> None:
        """Stop the watch scheduler"""
        self.running = False
        print("Watch scheduler stopped")
    
    def _run_scheduler(self) -> None:
        """Run the scheduler loop"""
        while self.running:
            try:
                self._check_and_renew_watches()
            except Exception as e:
                print(f"Error in watch scheduler: {e}")
            
            # Sleep for the check interval
            time.sleep(self.check_interval)
    
    def _check_and_renew_watches(self) -> None:
        """Check for expiring watches and renew them"""
        # Get all users with watches
        users = self.db.get_all_users_with_watches()
        
        # Current time plus 1 day for safety margin
        renewal_threshold = datetime.now() + timedelta(days=1)
        
        for user in users:
            try:
                user_id = user.get('user_id')
                watch_expiration = user.get('watch_expiration')
                token_data = user.get('token')
                
                if not user_id or not watch_expiration or not token_data:
                    continue
                
                # Parse expiration time
                expiration_time = datetime.fromtimestamp(int(watch_expiration) / 1000)
                
                # If watch will expire within a day, renew it
                if expiration_time <= renewal_threshold:
                    print(f"Renewing watch for user {user_id}")
                    
                    # Create Gmail service for the user
                    gmail_service = GmailService(user_id, token_data)
                    
                    # Renew the watch
                    watch_response = gmail_service.start_watch()
                    
                    # Store the new watch data
                    self.db.store_watch_data(
                        user_id, 
                        watch_response.get("historyId"), 
                        watch_response.get("expiration")
                    )
                    
                    # Log the renewal event
                    self.db.log_history_event(
                        user_id,
                        watch_response.get("historyId"),
                        "watch_renewed",
                        {
                            "expiration": watch_response.get("expiration"),
                            "expirationTime": watch_response.get("expirationTime"),
                            "automatic": True
                        }
                    )
                    
                    print(f"Watch renewed for user {user_id} until {watch_response.get('expirationTime')}")
            except Exception as e:
                print(f"Error renewing watch for user {user.get('user_id')}: {e}")
    
    def renew_all_watches(self) -> Dict:
        """
        Manually renew all watches
        
        Returns:
            Results of renewal operations
        """
        users = self.db.get_all_users_with_watches()
        results = {
            "succeeded": [],
            "failed": []
        }
        
        for user in users:
            try:
                user_id = user.get('user_id')
                token_data = user.get('token')
                
                if not user_id or not token_data:
                    results["failed"].append({
                        "user_id": user_id,
                        "error": "Missing user ID or token data"
                    })
                    continue
                
                # Create Gmail service for the user
                gmail_service = GmailService(user_id, token_data)
                
                # Renew the watch
                watch_response = gmail_service.start_watch()
                
                # Store the new watch data
                self.db.store_watch_data(
                    user_id, 
                    watch_response.get("historyId"), 
                    watch_response.get("expiration")
                )
                
                # Log the manual renewal event
                self.db.log_history_event(
                    user_id,
                    watch_response.get("historyId"),
                    "watch_renewed",
                    {
                        "expiration": watch_response.get("expiration"),
                        "expirationTime": watch_response.get("expirationTime"),
                        "automatic": False,
                        "manual": True
                    }
                )
                
                results["succeeded"].append({
                    "user_id": user_id,
                    "expiration": watch_response.get("expirationTime")
                })
                
            except Exception as e:
                results["failed"].append({
                    "user_id": user.get('user_id'),
                    "error": str(e)
                })
        
        return results 