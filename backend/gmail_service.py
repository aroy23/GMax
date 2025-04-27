import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
import time

from gmail_auth import get_credentials
from config import PUBSUB_TOPIC

import random
import base64
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage
from email.mime.text import MIMEText
import google.auth
import google.generativeai as genai

from config import GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

class GmailService:
    def __init__(self):
        """
        Initialize Gmail API service for a user
        
        Args:
            user_id: The unique identifier for the user
            token_data: Optional cached token data
        """
        self.credentials = get_credentials()
        self.service = build('gmail', 'v1', credentials=self.credentials)
        
    def start_watch(self, label_ids: Optional[List[str]] = None, webhook_url: Optional[str] = None) -> Dict:
        """
        Set up Gmail API watch on a user's mailbox
        
        Args:
            label_ids: Optional list of label IDs to filter notifications
            webhook_url: Optional URL for the push notifications
            
        Returns:
            Watch response with historyId and expiration
        """
        try:
            request_body = {
                "topicName": PUBSUB_TOPIC,
                "labelFilterBehavior": "include",
                "labelIds": label_ids or ["INBOX", "UNREAD"]
            }
            
            # Add webhook URL if provided
            if webhook_url:
                print(f"Using webhook URL: {webhook_url}")
                # Using a custom label to track the webhook URL - Google won't use this
                # but it helps for debugging
                request_body["labelFilterAction"] = "include"
                request_body["webhookUrl"] = webhook_url
            
            watch_response = self.service.users().watch(
                userId='me', 
                body=request_body
            ).execute()
            
            # Return both the historyId and expiration timestamp
            return {
                "historyId": watch_response.get("historyId"),
                "expiration": watch_response.get("expiration"),
                "expirationTime": datetime.fromtimestamp(
                    int(watch_response.get("expiration")) / 1000
                ).isoformat()
            }
        except HttpError as error:
            print(f"Gmail watch error: {error}")
            raise
    
    def stop_watch(self) -> Dict:
        """
        Stop watching a user's mailbox
        
        Returns:
            Success response
        """
        try:
            response = self.service.users().stop(userId='me').execute()
            return {"success": True, "response": response}
        except HttpError as error:
            print(f"Gmail stop watch error: {error}")
            raise
    
    def get_watch_status(self) -> Dict:
        """
        Get the current watch status for the user's mailbox
        
        Returns:
            Dictionary with watch status information or error
        """
        try:
            # Gmail API doesn't have a direct method to check watch status
            # We use the profile endpoint which returns historyId
            profile = self.service.users().getProfile(userId='me').execute()
            history_id = profile.get('historyId')
            
            # Check if we have a watch expiration stored in our database
            # This would normally come from database, but we'll need to implement
            # a dummy check here
            try:
                # Try to get labels as a simple way to test API connectivity
                labels = self.service.users().labels().list(userId='me').execute()
                label_count = len(labels.get('labels', []))
                
                return {
                    "active": True,  # We don't know for sure, but API works
                    "historyId": history_id,
                    "labels": label_count,
                    "note": "Gmail API doesn't provide direct watch status. This is a best guess."
                }
            except HttpError as label_error:
                # If we can't get labels, there might be an issue with the API
                return {
                    "active": False,
                    "historyId": history_id,
                    "error": str(label_error)
                }
        except HttpError as error:
            print(f"Gmail get watch status error: {error}")
            return {
                "active": False,
                "error": str(error)
            }
    
    def get_history(self, start_history_id: str) -> List[Dict]:
        """
        Get mailbox change history since a specific history ID
        
        Args:
            start_history_id: The history ID to start from
            
        Returns:
            List of history records with message changes
        """
        try:
            results = []
            page_token = None
            
            while True:
                history_list = self.service.users().history().list(
                    userId='me',
                    startHistoryId=start_history_id,
                    pageToken=page_token,
                    historyTypes=['messageAdded', 'labelAdded', 'labelRemoved']
                ).execute()
                
                if 'history' in history_list:
                    results.extend(history_list['history'])
                
                page_token = history_list.get('nextPageToken')
                if not page_token:
                    break
            
            # Extract the latest historyId
            latest_history_id = history_list.get('historyId', start_history_id)
            
            # Process and return the history records
            return {
                "latestHistoryId": latest_history_id,
                "changes": self._process_history_records(results)
            }
        except HttpError as error:
            if error.resp.status == 404:
                # History ID is too old, need to resync
                print("History ID is too old, need to resync")
                return {"error": "historyExpired", "latestHistoryId": None}
            print(f"Gmail history error: {error}")
            raise
    
    def _process_history_records(self, history_records: List[Dict]) -> List[Dict]:
        """
        Process history records to extract message changes
        
        Args:
            history_records: Raw history records from Gmail API
            
        Returns:
            Processed list of message changes
        """
        changes = []
        
        for record in history_records:
            # Handle new messages
            if 'messagesAdded' in record:
                for msg_added in record['messagesAdded']:
                    message = msg_added.get('message', {})
                    if not self._is_message_in_changes(changes, message.get('id')):
                        changes.append({
                            'messageId': message.get('id'),
                            'threadId': message.get('threadId'),
                            'labelIds': message.get('labelIds', []),
                            'change': 'added'
                        })
            
            # Handle label changes
            if 'labelsAdded' in record:
                for label_added in record['labelsAdded']:
                    message = label_added.get('message', {})
                    message_id = message.get('id')
                    change_item = self._get_or_create_change_item(changes, message_id, message)
                    
                    # Add new labels to the change item
                    if 'labelsAdded' not in change_item:
                        change_item['labelsAdded'] = []
                    change_item['labelsAdded'].extend(label_added.get('labelIds', []))
                    change_item['change'] = 'modified'
            
            # Handle label removals
            if 'labelsRemoved' in record:
                for label_removed in record['labelsRemoved']:
                    message = label_removed.get('message', {})
                    message_id = message.get('id')
                    change_item = self._get_or_create_change_item(changes, message_id, message)
                    
                    # Add removed labels to the change item
                    if 'labelsRemoved' not in change_item:
                        change_item['labelsRemoved'] = []
                    change_item['labelsRemoved'].extend(label_removed.get('labelIds', []))
                    change_item['change'] = 'modified'
        
        return changes
    
    def _is_message_in_changes(self, changes: List[Dict], message_id: str) -> bool:
        """Check if a message is already in the changes list"""
        for change in changes:
            if change.get('messageId') == message_id:
                return True
        return False
    
    def _get_or_create_change_item(self, changes: List[Dict], message_id: str, message: Dict) -> Dict:
        """Get existing change item or create a new one"""
        for change in changes:
            if change.get('messageId') == message_id:
                return change
        
        # Create new change item
        new_change = {
            'messageId': message_id,
            'threadId': message.get('threadId'),
            'labelIds': message.get('labelIds', []),
            'change': 'modified'
        }
        changes.append(new_change)
        return new_change
    
    def get_message(self, message_id: str, format: str = 'full') -> Dict:
        """
        Get a specific message by ID
        
        Args:
            message_id: The ID of the message to retrieve
            format: The format of the message (minimal, full, raw, metadata)
            
        Returns:
            The message data
        """
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id, 
                format=format
            ).execute()
            
            return message
        except HttpError as error:
            print(f"Get message error: {error}")
            raise
    
    def modify_message(self, message_id: str, add_labels: List[str] = None, 
                       remove_labels: List[str] = None) -> Dict:
        """
        Modify the labels on a message
        
        Args:
            message_id: The ID of the message to modify
            add_labels: Labels to add to the message
            remove_labels: Labels to remove from the message
            
        Returns:
            The updated message
        """
        try:
            body = {
                'addLabelIds': add_labels or [],
                'removeLabelIds': remove_labels or []
            }
            
            result = self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            
            return result
        except HttpError as error:
            print(f"Modify message error: {error}")
            raise
    
    def trash_message(self, message_id: str) -> Dict:
        """
        Move a message to trash
        
        Args:
            message_id: The ID of the message to trash
            
        Returns:
            The trashed message
        """
        try:
            result = self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            
            return result
        except HttpError as error:
            print(f"Trash message error: {error}")
            raise
    
    def list_messages(self, max_results: int = 10, label_ids: Optional[List[str]] = None) -> List[Dict]:
        """
        List messages in the user's mailbox
        
        Args:
            max_results: Maximum number of messages to return
            label_ids: List of label IDs to filter by (e.g., ["INBOX"])
            
        Returns:
            List of message metadata
        """
        try:
            # Prepare the query parameters
            query_params = {
                'userId': 'me',
                'maxResults': max_results
            }
            
            # Add label filter if provided
            if label_ids:
                query_params['labelIds'] = label_ids
                
            # Get the messages list
            response = self.service.users().messages().list(**query_params).execute()
            
            # Return the messages
            return response.get('messages', [])
        except HttpError as error:
            print(f"List messages error: {error}")
            raise

# def auth():
#     creds = None
#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             creds.refresh(Request())
#         else:
#             flow = InstalledAppFlow.from_client_secrets_file(
#                 "credentials.json", SCOPES
#             )
#             creds = flow.run_local_server(port=0)
#         with open("token.json", "w") as token:
#             token.write(creds.to_json())
    
#     return creds

# @app.get("/labels")
# def print_labels():
#     creds = None
#     if os.path.exists("token.json"):
#         creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#     if not creds or not creds.valid:
#         creds = auth()
#     try:
#         # Call the Gmail API
#         service = build("gmail", "v1", credentials=creds)
#         results = service.users().labels().list(userId="me").execute()
#         labels = results.get("labels", [])

#         if not labels:
#             return {"Status": "No labels found"}
#         result = []
#         for label in labels:
#             result.append(label["name"])
#         return {"Labels": result}

#     except HttpError as error:
#         print(f"An error occurred: {error}")
#     return {"Hello": "World"}

    # @app.get("/send")
    def send(self):
        try:
            profile = self.service.users().getProfile(userId="me").execute()  
            user_email = profile["emailAddress"]

            message = EmailMessage()

            user_data = db.get_user_data(user_email)
            persona = user_data.get("persona") if user_data else None

            if persona:
                original_content = "Hello!\n\nMy name is Bob Dylan."
                message_content = model.generate_content(
                    "Give me a plain string response to this email below:\n\n" + original_content + '\n\nUse this as the persona of the responder and act as them fully:\n\n' + persona
                )
            
                message.set_content(message_content.text)
                message["To"] = "fermatjw@gmail.com"
                message["From"] = user_email
                message["Subject"] = "Automated draft"

                # encoded message
                encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

                create_message = {"raw": encoded_message}
                send_message = (
                    self.service.users()
                    .messages()
                    .send(userId="me", body=create_message)
                    .execute()
                )

                return {"Message id": send_message["id"]}

        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None
            return {"Status": "Failed!"}

    def gmail_body_to_text(self,data: str) -> str:
        b64 = data.replace("-", "+").replace("_", "/")
        b64 += "=" * ((4 - len(b64) % 4) % 4)
        return base64.b64decode(b64).decode("utf-8", errors="replace")

    def reply(self, db, original_email_id: str, body: str):
        try:
            profile = self.service.users().getProfile(userId="me").execute()  
            user_email = profile["emailAddress"]

            user_data = db.get_user_data(user_email)
            persona = user_data.get("persona") if user_data else None
            if persona:
                original_email = self.get_message(original_email_id)
                payload = original_email["payload"]
                
                sent_from = 'Unknown'
                subject = 'No Subject'
                message_id_header = ''
                thread_id = original_email["threadId"]
                
                for header in payload["headers"]:
                    if header["name"] == 'From':
                        sent_from = header["value"]
                    elif header["name"] == 'Subject':
                        subject = header["value"]
                    elif header["name"] == 'Message-ID':
                        message_id_header = header["value"]

                if not subject.lower().startswith("re:"):
                    subject = "Re: " + subject
                
                mime = MIMEText(body)
                mime["To"] = sent_from
                mime["Subject"] = subject
                mime["In-Reply-To"] = message_id_header
                mime["References"] = message_id_header

                encoded_message = base64.urlsafe_b64encode(mime.as_bytes()).decode()

                create_message = {"raw": encoded_message, "threadId": thread_id}
                send_message = (
                    self.service.users()
                    .messages()
                    .send(userId="me", body=create_message)
                    .execute()
                )

                print("Replied!", send_message["id"])

        except HttpError as error:
            print(f"An error occurred: {error}")
            send_message = None
            print("Failed!")
    
    def draft(self, db, original_email_id: str):
        try:
            profile = self.service.users().getProfile(userId="me").execute()  
            user_email = profile["emailAddress"]

            user_data = db.get_user_data(user_email)
            persona = user_data.get("persona") if user_data else None
            if persona:
                original_email = self.get_message(original_email_id)
                payload = original_email["payload"]
                if payload.get("body", {}).get("data"):
                    original_body = self.gmail_body_to_text(payload["body"]["data"])
                else:
                    original_body = ""
                    for part in payload.get("parts", []):
                        if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                            original_body = self.gmail_body_to_text(part["body"]["data"])
                
                for header in payload["headers"]:
                    if header["name"] == 'From':
                        sent_from = header["value"]
                    elif header["name"] == 'Subject':
                        subject = header["value"]

                email = f'\nSTART OF EMAIL\nFrom: {sent_from}\nSubject: {subject}\nBody:\n{original_body}\n'

                message_content = model.generate_content(
                    "Taking into account the sender (and their email address) and subject and body, give me a plain string response to this email below:\n\n" + email + '\n\nUse this as the persona of the responder and act as them fully:\n\n' + persona
                )
                
                draft = {}
                draft["content"] = message_content.text
                
                return draft

        except HttpError as error:
            print(f"An error occurred: {error}")
            print("Failed!")

    def indexer(self, db):
        try:
            profile = self.service.users().getProfile(userId="me").execute()  
            user_email = profile["emailAddress"]

            request = self.service.users().messages().list(
                userId="me",
                q='in:sent after:2024/04/01 before:2025/04/30'
            )

            messages = []
            while request is not None:
                response = request.execute()
                ids = response.get("messages", [])
                for msg_meta in ids:
                    msg = self.service.users().messages().get(
                        userId="me",
                        id=msg_meta["id"],
                        format="full"
                    ).execute()
                    messages.append(msg)

                # if there’s another page, prepare the next request
                request = self.service.users().messages().list_next(request, response)

            selected_messages = messages if len(messages) <= 5 else random.sample(messages, 5)
            emails = []
            for m in selected_messages:
                payload = m["payload"]
                if payload.get("body", {}).get("data"):
                    body = self.gmail_body_to_text(payload["body"]["data"])
                else:
                    body = ""
                    for part in payload.get("parts", []):
                        if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                            body = self.gmail_body_to_text(part["body"]["data"])
                
                sent_to = 'Unknown'
                subject = 'No Subject'
                
                for header in payload["headers"]:
                    if header["name"] == 'To':
                        sent_to = header["value"]
                    elif header["name"] == 'Subject':
                        subject = header["value"]

                email = f'\nSTART OF EMAIL\nTo: {sent_to}\nSubject: {subject}\nBody:\n{body}\n'
                emails.append(email)

            persona_response = model.generate_content(
                "Take these 5 emails below and give me a plain string prompt that you can take in as a plain string later that acts as a persona that captures the email writing style of the sender, recognizing tone and levels of professionalism by also taking into account the address the email is sent to:\n\n" + str([m.get("snippet") + "\n\n" for m in selected_messages])
            )
            
            persona = persona_response.text
            db.update_user_data(user_email, { "persona": persona })

            return {"Status": "Success!"}
        

        except HttpError as error:
            print(f"An error occurred: {error}")
            return {"Status:", "Failed!"}