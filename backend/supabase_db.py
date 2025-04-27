from typing import Dict, Optional, List, Any
from datetime import datetime
from supabase import create_client, Client
import json

from config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_USER_TABLE, SUPABASE_HISTORY_TABLE, SUPABASE_CONFIRMATIONS_TABLE, SUPABASE_ACTIONS_TABLE

class SupabaseDB:
    """Supabase database for storing user data and Gmail history"""
    
    def __init__(self):
        """Initialize the Supabase client"""
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Verify connection
        try:
            self._health_check()
        except Exception as e:
            print(f"Error connecting to Supabase: {e}")
            raise
            
    def _health_check(self) -> bool:
        """Verify connection to Supabase"""
        result = self.supabase.table(SUPABASE_USER_TABLE).select("id").limit(1).execute()
        return True
    
    def save_user_data(self, user_id: str, data: Dict) -> None:
        """
        Save or update user data
        
        Args:
            user_id: The unique identifier for the user (email)
            data: The data to save
        """
        # Read token from token.json
        try:
            with open('token.json', 'r') as f:
                token_data = json.load(f)
        except FileNotFoundError:
            token_data = {}
            
        # Prepare the data for insertion/update
        user_data = {
            "user_id": user_id,
            "updated_at": datetime.now().isoformat(),
            "token": token_data,
            **data
        }
        
        # Upsert the user data (insert if not exists, update if exists)
        result = self.supabase.table(SUPABASE_USER_TABLE).upsert(
            user_data, 
            on_conflict="user_id"
        ).execute()
    
    def get_user_data(self, user_id: str) -> Optional[Dict]:
        """
        Get user data
        
        Args:
            user_id: The unique identifier for the user (email)
            
        Returns:
            User data dict or None if not found
        """
        result = self.supabase.table(SUPABASE_USER_TABLE).select("*").eq("user_id", user_id).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        
        return None
    
    def update_user_data(self, user_id: str, updates: Dict) -> Dict:
        """
        Update specific fields in user data
        
        Args:
            user_id: The unique identifier for the user (email)
            updates: Fields to update
            
        Returns:
            Updated user data
        """
        # Add timestamp to updates
        updates["updated_at"] = datetime.now().isoformat()
        
        # Update the user data
        result = self.supabase.table(SUPABASE_USER_TABLE).update(
            updates
        ).eq("user_id", user_id).execute()
        
        # Get and return the updated data
        if result.data and len(result.data) > 0:
            return result.data[0]
        else:
            # If update didn't return data, fetch the latest
            return self.get_user_data(user_id) or {}
    
    def store_token(self, user_id: str, token_data: Dict) -> Dict:
        """
        Store OAuth token data for a user
        
        Args:
            user_id: The unique identifier for the user (email)
            token_data: The OAuth token data
            
        Returns:
            Updated user data
        """
        # Store tokens securely - in a real implementation, you might want to encrypt these
        user_data = {
            "token": token_data,
            "token_updated_at": datetime.now().isoformat()
        }
        
        # Check if user exists
        existing_user = self.get_user_data(user_id)
        
        if existing_user:
            # Update existing user
            return self.update_user_data(user_id, user_data)
        else:
            # Create new user
            user_data["user_id"] = user_id
            self.save_user_data(user_id, user_data)
            return self.get_user_data(user_id) or {}
    
    def store_watch_data(self, user_id: str, history_id: str, expiration: str) -> Dict:
        """
        Store Gmail watch data for a user
        
        Args:
            user_id: The unique identifier for the user (email)
            history_id: The history ID from the watch response
            expiration: The expiration timestamp
            
        Returns:
            Updated user data
        """
        # Update user with watch data
        watch_data = {
            "last_history_id": history_id,
            "watch_expiration": expiration,
            "updated_at": datetime.now().isoformat()
        }
        
        return self.update_user_data(user_id, watch_data)
    
    def update_history_id(self, user_id: str, history_id: str) -> Dict:
        """
        Update the last processed history ID for a user
        
        Args:
            user_id: The unique identifier for the user (email)
            history_id: The new history ID
            
        Returns:
            Updated user data
        """
        return self.update_user_data(user_id, {
            "last_history_id": history_id,
            "updated_at": datetime.now().isoformat()
        })
    
    def log_history_event(self, user_id: str, history_id: str, event_type: str, details: Dict = None) -> Dict:
        """
        Log a history event for tracking purposes
        
        Args:
            user_id: The unique identifier for the user (email)
            history_id: The history ID associated with the event
            event_type: The type of event (e.g., 'notification', 'processed')
            details: Additional details about the event
            
        Returns:
            The created history record
        """
        history_data = {
            "user_id": user_id,
            "history_id": history_id,
            "event_type": event_type,
            "details": details or {},
            "created_at": datetime.now().isoformat()
        }
        
        result = self.supabase.table(SUPABASE_HISTORY_TABLE).insert(history_data).execute()
        
        if result.data and len(result.data) > 0:
            return result.data[0]
        return {}
    
    def get_all_users(self) -> List[Dict]:
        """
        Get all users from the database
        
        Returns:
            List of user data dictionaries
        """
        result = self.supabase.table(SUPABASE_USER_TABLE).select("*").execute()
        return result.data if result.data else []
    
    def get_all_users_with_watches(self) -> List[Dict]:
        """
        Get all users with active watches
        
        Returns:
            List of user data dicts
        """
        # Get users with watch_expiration field
        result = self.supabase.table(SUPABASE_USER_TABLE).select("*").not_.is_("watch_expiration", "null").execute()
        return result.data if result.data else []
        
    def get_user_by_token(self, token: str) -> Optional[Dict]:
        """
        Find a user based on their auth token
        
        Args:
            token: The authentication token (e.g., access_token or refresh_token)
            
        Returns:
            User data dict or None if not found
        """
        try:
            # Query all users
            all_users = self.get_all_users()
            
            # Iterate through users to find a matching token
            for user in all_users:
                if not user.get('token'):
                    continue
                    
                token_data = user.get('token', {})
                
                # Check for token match - could be in access_token, refresh_token, or token
                if (token_data.get('access_token') == token or 
                    token_data.get('refresh_token') == token or 
                    token_data.get('token') == token):
                    return user
            
            # No match found
            return None
        except Exception as e:
            print(f"Error in get_user_by_token: {e}")
            return None
            
    def update_user_by_token(self, token: str, updates: Dict) -> Dict:
        """
        Update user data directly using token matching
        
        Args:
            token: The authentication token 
            updates: Fields to update
            
        Returns:
            Updated user data or empty dict if user not found
        """
        try:
            # Find the user by token
            user = self.get_user_by_token(token)
            if not user:
                print(f"No user found with the provided token")
                return {}
            
            # Get the user_id
            user_id = user.get('user_id')
            if not user_id:
                print("User found but missing user_id field")
                return {}
                
            # Use the existing update method
            return self.update_user_data(user_id, updates)
        except Exception as e:
            print(f"Error in update_user_by_token: {e}")

    def create_confirmation(self, user_id, message_id, message_content):
        confirmation_data = {}
        confirmation_data["user_id"] = user_id
        confirmation_data["respond_to_message_id"] = message_id
        confirmation_data["message_content"] = message_content
        self.supabase.table(SUPABASE_CONFIRMATIONS_TABLE).upsert(
            confirmation_data
        ).execute()
    
    def delete_confirmation(self, user_id):
        self.supabase.table(SUPABASE_CONFIRMATIONS_TABLE).delete().eq("user_id", user_id).execute()
    
    def get_confirmation(self, user_id):
        result = self.supabase.table(SUPABASE_CONFIRMATIONS_TABLE).select("*").eq("user_id", user_id).execute()
        if result.data and len(result.data) > 0:
            return result.data[0]

    def create_action(self, user_id, action):
        action_data = {}
        action_data["user_id"] = user_id
        action_data["action"] = action
        self.supabase.table(SUPABASE_ACTIONS_TABLE).upsert(
            action_data
        ).execute()
    
    def get_actions(self, user_id):
        result = self.supabase.table(SUPABASE_ACTIONS_TABLE).select("*").eq("user_id", user_id).order("id", desc=False).execute()
        if result.data:
            return result.data
        else:
            return []