import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import base64
import google.generativeai as genai

from gmail_service import GmailService
from config import GEMINI_API_KEY


genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

class EmailProcessor:
    """Email processor for handling new messages"""
    
    def __init__(self):
        """
        Initialize the email processor
        
        Args:
            user_id: The unique identifier for the user
            token_data: Optional cached token data
        """
        self.gmail_service = GmailService()
        
    def process_notification(self, db, history_id: str, last_history_id: Optional[str] = None) -> Dict:
        """
        Process a Gmail notification with a history ID
        
        Args:
            history_id: The history ID from the notification
            last_history_id: The last processed history ID (if available)
            
        Returns:
            Processing result with new messages
        """
        # If we don't have a last history ID, use the current one
        if not last_history_id:
            return {
                "status": "initialized",
                "historyId": history_id,
                "message": "No previous history ID. Initialized tracking."
            }
        
        # Get history changes since last processed history ID
        history_result = self.gmail_service.get_history(last_history_id)
        
        # Check if history ID is too old
        if history_result.get("error") == "historyExpired":
            # In a real implementation, we would do full sync here
            return {
                "status": "sync_required",
                "historyId": history_id,
                "message": "History ID too old, full sync required"
            }
        
        # Process new or modified messages
        changes = history_result.get("changes", [])
        processed_results = []
        
        for change in changes:
            if change.get("change") == "added":
                # Process new message
                result = self._process_new_message(db, change.get("messageId"))
                processed_results.append(result)
            elif change.get("change") == "modified":
                # Process modified message
                result = self._process_modified_message(
                    change.get("messageId"),
                    change.get("labelsAdded", []), 
                    change.get("labelsRemoved", [])
                )
                processed_results.append(result)
        
        return {
            "status": "processed",
            "historyId": history_result.get("latestHistoryId", history_id),
            "processedCount": len(processed_results),
            "results": processed_results
        }
    
    def _process_new_message(self, db, message_id: str) -> Dict:
        """
        Process a new message
        
        Args:
            message_id: The ID of the new message
            
        Returns:
            Processing result
        """
        try:
            # Try to get full message format first
            try:
                message = self.gmail_service.get_message(message_id, format="full")
                message_format = "full"
            except Exception as e:
                    # Re-raise if it's not a permission issue
                    raise
            
            # Extract headers
            headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
            
            # Extract the email content (if available with our permissions)
            if message_format == "full":
                email_content = self._extract_email_content(message)
            else:
                # For metadata format, use snippet
                email_content = message.get('snippet', '[Email content not available with current permissions]')

            profile = self.gmail_service.service.users().getProfile(userId="me").execute()  
            user_email = profile["emailAddress"]
            payload = message.get("payload", {})
            sent_from = ""
            for header in payload["headers"]:
                if header["name"] == 'From':
                    sent_from = header["value"]
            if sent_from == user_email:
                print("SKIPPING")
                return

            # Print email details to console
            self._print_email_details(headers, email_content)

            # Use Gemini to classify if the email is spam
            is_spam = False
            spam_classification = "none"
            try:
                # Extract sender domain from email
                sender = headers.get("From", "")
                domain = sender.split('@')[-1].split('>')[0] if '@' in sender else ""
                subject = headers.get("Subject", "")
                
                # Classify using Gemini
                spam_classification = self._classify_spam_with_gemini(domain, subject, email_content)
                
                if spam_classification == "spam":
                    is_spam = True
                    self.gmail_service.modify_message(message_id, add_labels=['SPAM'])
                elif spam_classification == "not spam":
                    print("NOT SPAM")
            except Exception as e:
                print(f"Error classifying with Gemini: {e}")

            reply_classification = "none"
            try:
                # Extract sender domain from email
                sender = headers.get("From", "")
                domain = sender.split('@')[-1].split('>')[0] if '@' in sender else ""
                subject = headers.get("Subject", "")
                reply_classification = self._classify_reply_with_gemini(domain, subject, email_content)
                
                if reply_classification == "reply":
                    self.gmail_service.reply(db, message_id)
                elif reply_classification == "no reply":
                    print("NO REPLY")
            except Exception as e:
                print(f"Error classifying with Gemini: {e}")
            
            return {
                "messageId": message_id,
                "threadId": message.get("threadId"),
                "processed": True,
                "timestamp": datetime.now().isoformat(),
                "action": spam_classification,
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "content_preview": email_content[:200] + "..." if len(email_content) > 200 else email_content,
                "full_content": email_content,
                "format_used": message_format
            }
        except Exception as e:
            print(f"Error processing message {message_id}: {e}")
            return {
                "messageId": message_id,
                "processed": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
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
                print(f"Error decoding message body: {e}")
        
        # Case 2: Multipart message
        elif 'parts' in payload:
            # First look for text/plain parts
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                    try:
                        text_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                        content += text_content + "\n"
                    except Exception as e:
                        print(f"Error decoding text part: {e}")
            
            # If no text/plain, try HTML
            if not content:
                for part in payload['parts']:
                    if part.get('mimeType') == 'text/html' and part.get('body', {}).get('data'):
                        try:
                            html_content = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='replace')
                            content += f"[HTML Content] {html_content[:500]}...\n"
                        except Exception as e:
                            print(f"Error decoding HTML part: {e}")
            
            # Try to find nested multipart content
            if not content:
                for part in payload['parts']:
                    if 'parts' in part:
                        for subpart in part['parts']:
                            if subpart.get('mimeType') == 'text/plain' and subpart.get('body', {}).get('data'):
                                try:
                                    text_content = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8', errors='replace')
                                    content += text_content + "\n"
                                except Exception as e:
                                    print(f"Error decoding nested text part: {e}")
        
        # Case 3: Check for snippet as a fallback
        if not content and 'snippet' in message:
            content = message['snippet']
        
        # If we still don't have content, return a placeholder
        if not content:
            return "[No email content could be extracted]"
            
        return content.strip()
    
    def _print_email_details(self, headers: Dict, content: str) -> None:
        """
        Print email details to console
        
        Args:
            headers: Email headers
            content: Email content
        """
        separator = "="*60
        print(f"\n{separator}")
        print("NEW EMAIL RECEIVED")
        print(f"From: {headers.get('From', 'Unknown')}")
        print(f"To: {headers.get('To', 'Unknown')}")
        print(f"Subject: {headers.get('Subject', 'No Subject')}")
        print(f"Date: {headers.get('Date', 'Unknown')}")
        print("-"*60)
        print("Content:")
        
        # Print content (limited to 1000 chars for readability)
        if len(content) > 1000:
            print(content[:1000] + "...")
        else:
            print(content)
        
        print(f"{separator}\n")
    
    def _process_modified_message(self, message_id: str, 
                                 labels_added: List[str], 
                                 labels_removed: List[str]) -> Dict:
        """
        Process a modified message
        
        Args:
            message_id: The ID of the modified message
            labels_added: Labels added to the message
            labels_removed: Labels removed from the message
            
        Returns:
            Processing result
        """
        try:
            # Get the message to extract content and details
            try:
                message = self.gmail_service.get_message(message_id, format="full")
                message_format = "full"
                # Extract headers
                headers = {h['name']: h['value'] for h in message.get('payload', {}).get('headers', [])}
                # Extract content
                email_content = self._extract_email_content(message)
            except Exception as e:
                    # Re-raise if it's not a permission issue
                    raise
                    
            return {
                "messageId": message_id,
                "threadId": message.get("threadId"),
                "processed": True,
                "timestamp": datetime.now().isoformat(),
                "action": "labels_updated",
                "from": headers.get("From", ""),
                "to": headers.get("To", ""),
                "subject": headers.get("Subject", ""),
                "labelsAdded": labels_added,
                "labelsRemoved": labels_removed,
                "content_preview": email_content[:200] + "..." if len(email_content) > 200 else email_content,
                "full_content": email_content,
                "format_used": message_format
            }
        except Exception as e:
            print(f"Error processing modified message {message_id}: {e}")
            return {
                "messageId": message_id,
                "processed": True,
                "timestamp": datetime.now().isoformat(),
                "action": "labels_updated",
                "labelsAdded": labels_added,
                "labelsRemoved": labels_removed,
                "error": str(e)
            }
    
    def _classify_spam_with_gemini(self, domain: str, subject: str, content: str) -> str:
        """
        Use Gemini to classify an email as spam, reply, or don't reply
        
        Args:
            domain: The sender's domain
            subject: The email subject
            content: The email content
            
        Returns:
            Classification: "spam", "not spam"
        """
        try:
            
            # Create prompt with email details
            prompt = f"""
            Please classify this email as either "spam", or "not spam" based on the following information:
            
            From domain: {domain}
            Subject: {subject}
            
            Email content:
            {content}
            
            Return only ONLY '1' if it is spam, or '0' if it is not spam. Do not return anything else.
            """
            
            # Get response from Gemini
            response = model.generate_content(prompt)
            
            # Extract classification
            result = response.text.strip()
            
            # Validate result
            if result == "1":
                return "spam"
            elif result == "0":
                return "not spam"
            else:
                # Default to not replying if classification is unclear
                print(f"Invalid classification from Gemini: {result}")
                return "not spam"
                
        except Exception as e:
            print(f"Error with Gemini classification: {e}")
            # Default to not replying if there's an error
            return "not spam" 
    
    def _classify_reply_with_gemini(self, domain: str, subject: str, content: str) -> str:
        """
        Use Gemini to classify an email as spam, reply, or don't reply
        
        Args:
            domain: The sender's domain
            subject: The email subject
            content: The email content
            
        Returns:
            Classification: "reply", or "dont_reply"
        """
        try:
            # Create prompt with email details
            prompt = f"""
            Please classify this email as either "reply", or "dont_reply" based on the following information:
            
            From domain: {domain}
            Subject: {subject}
            
            Email content:
            {content}
            
            Return only ONLY '1' if it is an email that you should reply to, or '0' if it is not an email you should reply to. Do not return anything else.
            """
            
            # Get response from Gemini
            response = model.generate_content(prompt)
            
            # Extract classification
            result = response.text.strip()
            
            # Validate result
            if result == "1":
                return "reply"
            elif result == "0":
                return "no reply"
            else:
                # Default to not replying if classification is unclear
                print(f"Invalid classification from Gemini: {result}")
                return "no reply" 
                    
        except Exception as e:
            print(f"Error with Gemini classification: {e}")
            # Default to not replying if there's an error
            return "no reply" 