import json
import base64
from typing import Dict, Any, Optional, List
from google.cloud import pubsub_v1
from google.oauth2 import service_account
import os
import logging

from config import PROJECT_ID, PUBSUB_TOPIC, PUBSUB_SUBSCRIPTION

logger = logging.getLogger("email_bot")

class PubSubService:
    """Service for working with Google Cloud Pub/Sub"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize the PubSub service
        
        Args:
            credentials_path: Optional path to service account credentials file
        """

        print("HELLO NISHAAAAAANT!!!!!!!!!!!!!!!")
        self.is_operational = True
        self.project_id = PROJECT_ID
        self.topic_name = PUBSUB_TOPIC.split('/')[-1]
        self.subscription_name = PUBSUB_SUBSCRIPTION.split('/')[-1]
        
        try:
            if credentials_path and os.path.exists(credentials_path):
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path
                )
                self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
                self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
            else:
                # Use application default credentials
                self.publisher = pubsub_v1.PublisherClient()
                self.subscriber = pubsub_v1.SubscriberClient()
                
            self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            
        except Exception as e:
            logger.error(f"PubSub service initialization failed: {e}")
            self.is_operational = False
            self.publisher = None
            self.subscriber = None
            self.topic_path = f"projects/{self.project_id}/topics/{self.topic_name}"
    
    async def create_subscription(self, email: str, topic_name: Optional[str] = None) -> str:
        """
        Create a Pub/Sub subscription for an email address
        
        Args:
            email: Email address to create subscription for
            topic_name: Optional topic name, defaults to the main topic
            
        Returns:
            Subscription ID
        """
        if not self.is_operational:
            logger.error("Cannot create subscription, PubSub service not operational")
            raise RuntimeError("PubSub service not operational")
            
        # Generate a subscription ID based on the email
        subscription_id = f"gmail-{email.replace('@', '-').replace('.', '-')}"
        
        # Get the topic path
        topic_path = self.topic_path
        if topic_name:
            topic_path = self.publisher.topic_path(self.project_id, topic_name)
            
        # Get the subscription path
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_id
        )
        
        try:
            # Try to get the subscription to see if it exists
            self.subscriber.get_subscription(
                request={"subscription": subscription_path}
            )
            logger.info(f"Subscription {subscription_id} already exists")
        except Exception:
            # Subscription doesn't exist, create it
            self.subscriber.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": 60
                }
            )
            logger.info(f"Created subscription {subscription_id}")
            
        return subscription_id
    
    async def delete_subscription(self, email: str) -> bool:
        """
        Delete a Pub/Sub subscription for an email address
        
        Args:
            email: Email address to delete subscription for
            
        Returns:
            Success status
        """
        if not self.is_operational:
            logger.error("Cannot delete subscription, PubSub service not operational")
            raise RuntimeError("PubSub service not operational")
            
        # Generate the subscription ID based on the email
        subscription_id = f"gmail-{email.replace('@', '-').replace('.', '-')}"
        
        # Get the subscription path
        subscription_path = self.subscriber.subscription_path(
            self.project_id, subscription_id
        )
        
        try:
            # Delete the subscription
            self.subscriber.delete_subscription(
                request={"subscription": subscription_path}
            )
            logger.info(f"Deleted subscription {subscription_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting subscription {subscription_id}: {e}")
            return False
    
    def decode_message(self, encoded_data: str) -> Dict:
        """
        Decode a base64-encoded Pub/Sub message
        
        Args:
            encoded_data: Base64-encoded message data
            
        Returns:
            Decoded message as dict
        """
        try:
            # First, ensure we have a valid string
            if not isinstance(encoded_data, str):
                logger.error(f"Expected string for encoded_data, got {type(encoded_data)}")
                raise TypeError(f"Expected string for encoded_data, got {type(encoded_data)}")
                
            # Try to decode the base64 data
            try:
                decoded_bytes = base64.b64decode(encoded_data)
                logger.debug(f"Successfully decoded base64 data to bytes of length {len(decoded_bytes)}")
            except Exception as e:
                logger.error(f"Failed to decode base64 data: {str(e)}")
                logger.error(f"First 100 chars of encoded data: {encoded_data[:100]}...")
                raise ValueError(f"Invalid base64 data: {str(e)}")
                
            # Try to decode to UTF-8
            try:
                decoded_string = decoded_bytes.decode('utf-8')
                logger.debug(f"Successfully decoded bytes to UTF-8 string of length {len(decoded_string)}")
            except UnicodeDecodeError as e:
                logger.error(f"Failed to decode bytes as UTF-8: {str(e)}")
                raise ValueError(f"Data is not valid UTF-8: {str(e)}")
                
            # Try to parse as JSON
            try:
                result = json.loads(decoded_string)
                logger.debug(f"Successfully parsed JSON data")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON data: {str(e)}")
                logger.error(f"Decoded string: {decoded_string[:200]}...")
                raise ValueError(f"Invalid JSON data: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error decoding message: {e}")
            raise
    
    async def check_status(self) -> bool:
        """
        Check if the PubSub service is operational
        
        Returns:
            Operational status
        """
        if not self.is_operational:
            return False
            
        try:
            # Try to get the topic to see if it exists
            self.publisher.get_topic(request={"topic": self.topic_path})
            return True
        except Exception:
            return False 