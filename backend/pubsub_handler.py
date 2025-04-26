import json
import base64
import sys
from typing import Dict, Any, Optional, Callable
from google.cloud import pubsub_v1
from google.oauth2 import service_account
from google.auth.exceptions import DefaultCredentialsError
import os

from config import PROJECT_ID, PUBSUB_TOPIC, PUBSUB_SUBSCRIPTION

class PubSubHandler:
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize PubSub handler for Gmail notifications
        
        Args:
            credentials_path: Optional path to service account credentials file
        """
        self.is_operational = True
        
        try:
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
                self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
            else:
                # Use application default credentials
                try:
                    self.publisher = pubsub_v1.PublisherClient()
                    self.subscriber = pubsub_v1.SubscriberClient()
                except DefaultCredentialsError as e:
                    print(f"ERROR: Google Cloud credentials not found: {e}")
                    print("Please either:")
                    print("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable to point to a service account key")
                    print("2. Run 'gcloud auth application-default login' if using gcloud")
                    self.is_operational = False
                    raise
                
            self.topic_path = self.publisher.topic_path(PROJECT_ID, PUBSUB_TOPIC.split('/')[-1])
            self.subscription_path = self.subscriber.subscription_path(
                PROJECT_ID, 
                PUBSUB_SUBSCRIPTION.split('/')[-1]
            )
        except Exception as e:
            print(f"WARNING: PubSub initialization failed: {e}")
            print("Email notifications will not be processed until this is fixed.")
            self.is_operational = False
            self.publisher = None
            self.subscriber = None
            self.topic_path = f"projects/{PROJECT_ID}/topics/gmail-notifications"
            self.subscription_path = f"projects/{PROJECT_ID}/subscriptions/gmail-notifications-sub"
    
    def create_topic_if_not_exists(self) -> None:
        """Create the Gmail notifications topic if it doesn't exist"""
        if not self.is_operational:
            print("Skipping topic creation, PubSub is not operational")
            return
            
        try:
            self.publisher.get_topic(request={"topic": self.topic_path})
            print(f"Topic {self.topic_path} already exists")
        except Exception:
            # Topic doesn't exist, create it
            self.publisher.create_topic(request={"name": self.topic_path})
            print(f"Created topic {self.topic_path}")
            
            # Grant Gmail API service account publish access
            policy = self.publisher.get_iam_policy(request={"resource": self.topic_path})
            policy.bindings.add(
                role="roles/pubsub.publisher",
                members=["serviceAccount:gmail-api-push@system.gserviceaccount.com"]
            )
            self.publisher.set_iam_policy(
                request={"resource": self.topic_path, "policy": policy}
            )
            print("Granted publish access to Gmail API")
    
    def create_subscription_if_not_exists(self) -> None:
        """Create the subscription if it doesn't exist"""
        if not self.is_operational:
            print("Skipping subscription creation, PubSub is not operational")
            return
            
        try:
            self.subscriber.get_subscription(
                request={"subscription": self.subscription_path}
            )
            print(f"Subscription {self.subscription_path} already exists")
        except Exception:
            # Subscription doesn't exist, create it
            self.subscriber.create_subscription(
                request={
                    "name": self.subscription_path, 
                    "topic": self.topic_path,
                    "ack_deadline_seconds": 60
                }
            )
            print(f"Created subscription {self.subscription_path}")
    
    def process_pubsub_message(self, message: Dict) -> Dict:
        """
        Process a Pub/Sub message from a push notification
        
        Args:
            message: The Pub/Sub message
            
        Returns:
            Decoded data with historyId
        """
        if not self.is_operational:
            return {"error": "PubSub is not operational due to missing credentials"}
            
        if 'data' not in message:
            return {"error": "No data in message"}
        
        try:
            # Decode base64 data
            encoded_data = message['data']
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')
            data = json.loads(decoded_data)
            
            print(f"Decoded PubSub data: {json.dumps(data, indent=2)}")
            
            # Extract the necessary fields
            # Gmail push notifications might have different formats
            # Try different known formats
            
            # Format 1: Direct format
            if "historyId" in data and "emailAddress" in data:
                return {
                    "historyId": data.get("historyId"),
                    "emailAddress": data.get("emailAddress")
                }
                
            # Format 2: Gmail API Watch notification structure
            if "message" in data and "data" in data.get("message", {}):
                message_data = data.get("message", {}).get("data", {})
                if isinstance(message_data, str):
                    try:
                        # It might be base64 encoded again
                        inner_data = json.loads(base64.b64decode(message_data).decode('utf-8'))
                        if "historyId" in inner_data and "emailAddress" in inner_data:
                            return {
                                "historyId": inner_data.get("historyId"),
                                "emailAddress": inner_data.get("emailAddress")
                            }
                    except:
                        pass
            
            # Format 3: Search in arbitrary fields - last resort
            # Look through all fields to find anything that looks like historyId and emailAddress
            history_id = None
            email_address = None
            
            def extract_fields(obj, depth=0):
                nonlocal history_id, email_address
                if depth > 5:  # Prevent infinite recursion
                    return
                    
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        # Look for historyId
                        if key == "historyId" and history_id is None:
                            history_id = str(value)
                        # Look for email-related fields
                        elif key in ["emailAddress", "email"] and email_address is None:
                            email_address = value
                        # Search nested objects
                        elif isinstance(value, (dict, list)):
                            extract_fields(value, depth + 1)
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)):
                            extract_fields(item, depth + 1)
            
            extract_fields(data)
            
            # If we found both fields
            if history_id and email_address:
                return {
                    "historyId": history_id,
                    "emailAddress": email_address
                }
            
            # If we couldn't find the expected fields, try to find a Gmail object
            # Some Gmail notifications might include the email in their structure
            # This is a fallback attempt
            
            # If we got here, we couldn't extract the required fields
            print(f"WARNING: Failed to extract historyId or emailAddress from message: {json.dumps(data, indent=2)}")
            
            return {
                "error": "Could not extract historyId and emailAddress from message",
                "decoded_data": data
            }
        except Exception as e:
            print(f"ERROR: Failed to process Pub/Sub message: {str(e)}")
            return {"error": f"Failed to process Pub/Sub message: {str(e)}"}
    
    def listen_for_messages(self, callback: Callable[[str, str], None]) -> None:
        """
        Start listening for Pub/Sub messages (blocking)
        
        Args:
            callback: Function to call with (user_email, history_id) when message received
        """
        if not self.is_operational:
            print("Cannot listen for messages, PubSub is not operational")
            return
            
        def _callback(message):
            try:
                data = json.loads(message.data.decode('utf-8'))
                history_id = data.get('historyId')
                email_address = data.get('emailAddress')
                
                if history_id and email_address:
                    # Call the provided callback with the history ID and email
                    callback(email_address, history_id)
                    
                # Acknowledge the message
                message.ack()
            except Exception as e:
                print(f"Error processing message: {e}")
                # Still ack to prevent redelivery of problematic messages
                message.ack()
        
        # Start the subscriber
        streaming_pull_future = self.subscriber.subscribe(
            self.subscription_path, callback=_callback
        )
        print(f"Listening for messages on {self.subscription_path}")
        
        try:
            streaming_pull_future.result()
        except Exception as e:
            streaming_pull_future.cancel()
            print(f"Listening for messages failed: {e}")
            
    def setup_pubsub(self) -> None:
        """Set up the Pub/Sub topic and subscription"""
        if not self.is_operational:
            print("Skipping PubSub setup, not operational due to missing credentials")
            return
            
        self.create_topic_if_not_exists()
        self.create_subscription_if_not_exists() 