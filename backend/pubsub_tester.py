#!/usr/bin/env python
"""
PubSub Tester Script

This script provides utilities to test and diagnose Google Cloud PubSub functionality.
"""

import os
import json
import base64
import argparse
from datetime import datetime
from google.cloud import pubsub_v1
from google.oauth2 import service_account
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("pubsub_tester")

def check_environment():
    """Check and print environment variables relevant to PubSub"""
    print("\n=== Environment Variables ===")
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    print(f"GOOGLE_CLOUD_PROJECT_ID: {project_id or 'Not set'}")
    print(f"GOOGLE_APPLICATION_CREDENTIALS: {credentials_path or 'Not set'}")
    
    if credentials_path and os.path.exists(credentials_path):
        print(f"Credentials file exists: Yes")
        # Get file size
        size = os.path.getsize(credentials_path)
        print(f"Credentials file size: {size} bytes")
        
        # Try to parse the file
        try:
            with open(credentials_path, 'r') as f:
                creds_json = json.load(f)
                print(f"Credentials type: {creds_json.get('type', 'Unknown')}")
                print(f"Project ID in credentials: {creds_json.get('project_id', 'Not found')}")
                print(f"Client email: {creds_json.get('client_email', 'Not found')}")
        except Exception as e:
            print(f"Error parsing credentials file: {e}")
    elif credentials_path:
        print(f"Credentials file exists: No (path is set but file not found)")
    else:
        print(f"Credentials file exists: No (path not set)")
    
    # Check for application default credentials
    try:
        import google.auth
        credentials, project = google.auth.default()
        print(f"Application default credentials available: Yes")
        print(f"Application default project: {project}")
    except Exception as e:
        print(f"Application default credentials available: No ({e})")
    
    return project_id, credentials_path

def initialize_clients(project_id, credentials_path=None):
    """Initialize PubSub publisher and subscriber clients"""
    print("\n=== Initializing PubSub Clients ===")
    try:
        if credentials_path and os.path.exists(credentials_path):
            print(f"Using service account credentials from: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            publisher = pubsub_v1.PublisherClient(credentials=credentials)
            subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        else:
            print("Using application default credentials")
            publisher = pubsub_v1.PublisherClient()
            subscriber = pubsub_v1.SubscriberClient()
            
        # Verify we can access the clients
        project_path = f"projects/{project_id}"
        topics = list(publisher.list_topics(request={"project": project_path}))
        print(f"Successfully listed {len(topics)} topics")
        
        subscriptions = list(subscriber.list_subscriptions(request={"project": project_path}))
        print(f"Successfully listed {len(subscriptions)} subscriptions")
        
        return publisher, subscriber
    except Exception as e:
        print(f"Failed to initialize clients: {e}")
        return None, None

def list_topics_and_subscriptions(publisher, subscriber, project_id):
    """List all topics and subscriptions in the project"""
    print("\n=== Topics and Subscriptions ===")
    project_path = f"projects/{project_id}"
    
    print("\nTopics:")
    try:
        topics = list(publisher.list_topics(request={"project": project_path}))
        for topic in topics:
            print(f"- {topic.name}")
    except Exception as e:
        print(f"Error listing topics: {e}")
    
    print("\nSubscriptions:")
    try:
        subscriptions = list(subscriber.list_subscriptions(request={"project": project_path}))
        for subscription in subscriptions:
            print(f"- {subscription.name} (Topic: {subscription.topic})")
    except Exception as e:
        print(f"Error listing subscriptions: {e}")

def publish_test_message(publisher, topic_name, project_id):
    """Publish a test message to a topic"""
    print(f"\n=== Publishing Test Message to {topic_name} ===")
    topic_path = publisher.topic_path(project_id, topic_name)
    
    # Create a test message
    test_data = {
        "test": "message",
        "timestamp": datetime.now().isoformat(),
        "historyId": "12345",
        "emailAddress": "test@example.com"
    }
    
    data = json.dumps(test_data).encode("utf-8")
    
    try:
        future = publisher.publish(topic_path, data)
        message_id = future.result()
        print(f"Published message with ID: {message_id}")
        print(f"Message data: {json.dumps(test_data, indent=2)}")
        return message_id
    except Exception as e:
        print(f"Failed to publish message: {e}")
        return None

def pull_messages(subscriber, subscription_name, project_id, max_messages=10):
    """Pull messages from a subscription"""
    print(f"\n=== Pulling Messages from {subscription_name} ===")
    subscription_path = subscriber.subscription_path(project_id, subscription_name)
    
    try:
        response = subscriber.pull(
            request={
                "subscription": subscription_path,
                "max_messages": max_messages,
            }
        )
        
        print(f"Received {len(response.received_messages)} messages")
        
        ack_ids = []
        for i, received_message in enumerate(response.received_messages):
            print(f"\nMessage {i+1}:")
            ack_ids.append(received_message.ack_id)
            
            # Extract message data
            message = received_message.message
            message_data = message.data
            attributes = {k: v for k, v in message.attributes.items()}
            
            print(f"  Message ID: {message.message_id}")
            print(f"  Attributes: {json.dumps(attributes, indent=2)}")
            
            # Try to decode the message
            try:
                decoded_data = message_data.decode("utf-8")
                print(f"  Data (raw): {decoded_data[:200]}...")
                
                try:
                    json_data = json.loads(decoded_data)
                    print(f"  Data (JSON): {json.dumps(json_data, indent=2)}")
                except:
                    print("  Data is not valid JSON")
            except:
                print(f"  Data (binary): {message_data[:20]}... (binary)")
        
        # Acknowledge the messages
        if ack_ids:
            subscriber.acknowledge(
                request={
                    "subscription": subscription_path,
                    "ack_ids": ack_ids,
                }
            )
            print(f"\nAcknowledged {len(ack_ids)} messages")
        
        return response.received_messages
    except Exception as e:
        print(f"Failed to pull messages: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Test Google Cloud PubSub functionality")
    parser.add_argument("--project", help="Google Cloud Project ID")
    parser.add_argument("--credentials", help="Path to service account credentials file")
    parser.add_argument("--topic", default="gmail-notifications", help="Topic name to use for testing")
    parser.add_argument("--subscription", default="gmail-notifications-sub", help="Subscription name to use for testing")
    parser.add_argument("--publish", action="store_true", help="Publish a test message")
    parser.add_argument("--pull", action="store_true", help="Pull messages from the subscription")
    parser.add_argument("--list", action="store_true", help="List topics and subscriptions")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Check environment first
    env_project_id, env_creds_path = check_environment()
    
    # Use command line args if provided, otherwise use environment
    project_id = args.project or env_project_id
    credentials_path = args.credentials or env_creds_path
    
    if not project_id:
        print("Error: Project ID not provided. Use --project or set GOOGLE_CLOUD_PROJECT_ID")
        return
    
    # Initialize clients
    publisher, subscriber = initialize_clients(project_id, credentials_path)
    if not publisher or not subscriber:
        print("Failed to initialize PubSub clients. Exiting.")
        return
    
    # Run requested tests
    if args.list or args.all:
        list_topics_and_subscriptions(publisher, subscriber, project_id)
    
    if args.publish or args.all:
        publish_test_message(publisher, args.topic, project_id)
    
    if args.pull or args.all:
        pull_messages(subscriber, args.subscription, project_id)
    
    # If no specific tests were requested, show help
    if not (args.list or args.publish or args.pull or args.all):
        parser.print_help()

if __name__ == "__main__":
    main() 