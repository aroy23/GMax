import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import httpx
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from gmail_auth import get_credentials
from config import PUBSUB_TOPIC

logger = logging.getLogger("email_bot")

class GmailService:
    """Service for interacting with Gmail API"""
    
    def __init__(self):
        """Initialize the Gmail service"""
        self.client = httpx.AsyncClient()
    
    async def watch_mailbox(self, email: str, label_id: str = "INBOX", webhook_url: Optional[str] = None) -> Dict:
        """
        Set up a watch on a user's Gmail mailbox
        
        Args:
            email: User's email address
            label_id: Gmail label ID to watch
            webhook_url: Optional URL for the push notifications
            
        Returns:
            Watch response with historyId and expiration
        """
        try:
            # Get user data from database (would be implemented in a real application)
            user_data = await self._get_user_data(email)
            
            if not user_data or 'token' not in user_data:
                raise ValueError(f"User {email} not authenticated")
            
            # Create Gmail service
            gmail = await self._create_gmail_service(email, user_data.get('token'))
            
            # Set up watch
            request_body = {
                "topicName": PUBSUB_TOPIC,
                "labelIds": [label_id]
            }
            
            # Add webhook URL if provided
            if webhook_url:
                logger.info(f"Using webhook URL: {webhook_url}")
                request_body["labelFilterAction"] = "include"
                request_body["webhookUrl"] = webhook_url
            
            watch_response = gmail.users().watch(
                userId='me',
                body=request_body
            ).execute()
            
            # Format response
            result = {
                "historyId": watch_response.get("historyId"),
                "expiration": watch_response.get("expiration"),
                "expirationTime": datetime.fromtimestamp(
                    int(watch_response.get("expiration")) / 1000
                ).isoformat()
            }
            
            # Store watch data (would be implemented in a real application)
            await self._store_watch_data(email, result)
            
            return result
        except Exception as e:
            logger.error(f"Error watching mailbox for {email}: {e}")
            raise
    
    async def stop_watch(self, email: str) -> Dict:
        """
        Stop watching a user's Gmail mailbox
        
        Args:
            email: User's email address
            
        Returns:
            Success response
        """
        try:
            # Get user data from database (would be implemented in a real application)
            user_data = await self._get_user_data(email)
            
            if not user_data or 'token' not in user_data:
                raise ValueError(f"User {email} not authenticated")
            
            # Create Gmail service
            gmail = await self._create_gmail_service(email, user_data.get('token'))
            
            # Stop the watch
            gmail.users().stop(userId='me').execute()
            
            # Update user data (would be implemented in a real application)
            await self._update_user_data(email, {"watch_expiration": None})
            
            return {"success": True, "message": f"Watch stopped for {email}"}
        except Exception as e:
            logger.error(f"Error stopping watch for {email}: {e}")
            raise
            
    async def process_email_notification(self, notification_data: Dict) -> Dict:
        """
        Process a Gmail notification
        
        Args:
            notification_data: Decoded notification data from Pub/Sub
            
        Returns:
            Processing result
        """
        try:
            email_address = notification_data.get("emailAddress")
            history_id = notification_data.get("historyId")
            
            if not email_address or not history_id:
                raise ValueError("Missing emailAddress or historyId in notification")
                
            # Get user data from database (would be implemented in a real application)
            user_data = await self._get_user_data(email_address)
            
            if not user_data or 'token' not in user_data:
                logger.error(f"User {email_address} not authenticated")
                return {"error": "User not authenticated"}
                
            # Get the last history ID
            last_history_id = user_data.get('last_history_id')
            
            # Create Gmail service
            gmail = await self._create_gmail_service(email_address, user_data.get('token'))
            
            # Get history changes
            history_result = await self._get_history_changes(gmail, last_history_id, history_id)
            
            # Process new messages (get and print content)
            for change in history_result:
                if change.get("change") == "added":
                    message_id = change.get("messageId")
                    try:
                        # Get message content
                        message = await self._get_message(gmail, message_id)
                        
                        # Extract headers
                        headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
                        
                        # Extract content
                        content = self._extract_email_content(message)
                        
                        # Print email details
                        self._print_email_details(headers, content)
                    except Exception as e:
                        logger.error(f"Error processing message {message_id}: {e}")
            
            # Update the last history ID
            await self._update_history_id(email_address, history_id)
            
            return {
                "status": "processed",
                "email": email_address,
                "historyId": history_id,
                "changes": history_result
            }
        except Exception as e:
            logger.error(f"Error processing email notification: {e}")
            return {"error": str(e)}
    
    async def check_status(self) -> bool:
        """Check if the Gmail service is operational"""
        try:
            # Simple status check - can be enhanced for more detailed status info
            # For example, checking credential validity for a test account
            return True
        except Exception:
            return False
    
    # Helper methods (placeholders - would be implemented in real application)
    
    async def _get_user_data(self, email: str) -> Optional[Dict]:
        """Get user data from database"""
        # This would be implemented to fetch from a real database
        # For now, return a mock response for testing
        return {
            "token": {"access_token": "mock-token", "refresh_token": "mock-refresh"},
            "last_history_id": "12345678"
        }
    
    async def _create_gmail_service(self, email: str, token_data: Dict) -> Any:
        """Create a Gmail API service instance"""
        # In a real implementation, this would create a proper API client
        # Here we just return a mock object for demonstration
        from unittest.mock import MagicMock
        mock_service = MagicMock()
        return mock_service
        
    async def _store_watch_data(self, email: str, watch_data: Dict) -> None:
        """Store watch data in database"""
        # This would update a real database
        pass
        
    async def _update_user_data(self, email: str, updates: Dict) -> None:
        """Update user data in database"""
        # This would update a real database
        pass
        
    async def _update_history_id(self, email: str, history_id: str) -> None:
        """Update the last processed history ID for a user"""
        # This would update a real database
        pass
        
    async def _get_history_changes(self, gmail_service: Any, start_history_id: str, end_history_id: str) -> List[Dict]:
        """Get history changes between two history IDs"""
        # This would call the Gmail API to get history changes
        # Return mock data for now
        return [
            {"messageId": "mock1", "change": "added"},
            {"messageId": "mock2", "change": "modified"}
        ]
    
    async def _get_message(self, gmail_service: Any, message_id: str) -> Dict:
        """Get a Gmail message by ID"""
        # In a real implementation, this would call the Gmail API
        # Since we're using a mock, just return a dummy message
        # In a real app, you'd do something like:
        # message = gmail_service.users().messages().get(userId='me', id=message_id, format='full').execute()
        
        # Return dummy data for demonstration
        return {
            "id": message_id,
            "threadId": f"thread-{message_id}",
            "payload": {
                "headers": [
                    {"name": "From", "value": "example@example.com"},
                    {"name": "To", "value": "user@example.com"},
                    {"name": "Subject", "value": "Test Email"},
                    {"name": "Date", "value": datetime.now().isoformat()}
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {
                            "data": base64.urlsafe_b64encode(b"This is a test email message.").decode('utf-8')
                        }
                    }
                ]
            }
        }
    
    def _extract_email_content(self, message: Dict) -> str:
        """
        Extract the text content from an email message
        
        Args:
            message: The Gmail message object
            
        Returns:
            The extracted text content
        """
        content = ""
        payload = message.get('payload', {})
        
        # Case 1: Simple message with body data
        if 'body' in payload and payload['body'].get('data'):
            try:
                content = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='replace')
            except Exception as e:
                logger.error(f"Error decoding message body: {e}")
        
        # Case 2: Multipart message
        elif 'parts' in payload:
            # First look for text/plain parts
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                    try:
                        text_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                        content += text_content + "\n"
                    except Exception as e:
                        logger.error(f"Error decoding text part: {e}")
            
            # If no text/plain, try HTML
            if not content:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/html' and part.get('body', {}).get('data'):
                        try:
                            html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                            content += f"[HTML Content] {html_content[:500]}...\n"
                        except Exception as e:
                            logger.error(f"Error decoding HTML part: {e}")
        
        return content.strip()
    
    def _print_email_details(self, headers: Dict, content: str) -> None:
        """
        Print email details to console
        
        Args:
            headers: Email headers
            content: Email content
        """
        separator = "="*60
        logger.info(f"\n{separator}")
        logger.info("NEW EMAIL RECEIVED (ASYNC SERVICE)")
        logger.info(f"From: {headers.get('From', 'Unknown')}")
        logger.info(f"To: {headers.get('To', 'Unknown')}")
        logger.info(f"Subject: {headers.get('Subject', 'No Subject')}")
        logger.info(f"Date: {headers.get('Date', 'Unknown')}")
        logger.info("-"*60)
        logger.info("Content:")
        
        # Print content (limited for readability)
        if len(content) > 1000:
            logger.info(content[:1000] + "...")
        else:
            logger.info(content)
        
        logger.info(f"{separator}\n") 