#!/usr/bin/env python
"""
PubSub Environment Verification Script

This script checks that your environment is properly configured for Google Cloud PubSub.
"""

import os
import sys
import json
from google.cloud import pubsub_v1
from google.oauth2 import service_account
import google.auth
from google.auth.exceptions import DefaultCredentialsError

def main():
    print("=== Google Cloud PubSub Environment Verification ===\n")
    
    # Step 1: Check environment variables
    print("Checking environment variables...")
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT_ID is not set")
        print("   Set this environment variable to your Google Cloud project ID")
    else:
        print(f"✅ GOOGLE_CLOUD_PROJECT_ID = {project_id}")
    
    if not creds_path:
        print("❌ GOOGLE_APPLICATION_CREDENTIALS is not set")
        print("   Set this environment variable to the path of your service account key file")
    else:
        print(f"✅ GOOGLE_APPLICATION_CREDENTIALS = {creds_path}")
        
        if not os.path.exists(creds_path):
            print(f"❌ Credentials file does not exist at {creds_path}")
        else:
            print(f"✅ Credentials file exists at {creds_path}")
            
            # Check if the credentials file is valid JSON
            try:
                with open(creds_path, 'r') as f:
                    creds = json.load(f)
                if 'type' in creds and creds['type'] == 'service_account':
                    print(f"✅ Credentials file is a valid service account key")
                    print(f"   Project ID in credentials: {creds.get('project_id')}")
                    print(f"   Client email: {creds.get('client_email')}")
                else:
                    print(f"❌ Credentials file is not a valid service account key")
            except json.JSONDecodeError:
                print(f"❌ Credentials file is not valid JSON")
            except Exception as e:
                print(f"❌ Error reading credentials file: {e}")
    
    print("\nChecking authentication...")
    # Step 2: Check if google.auth can get default credentials
    try:
        credentials, default_project = google.auth.default()
        print(f"✅ Default credentials available. Project ID: {default_project}")
    except DefaultCredentialsError:
        print("❌ Default credentials not available")
        print("   Run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS")
    except Exception as e:
        print(f"❌ Error getting default credentials: {e}")
    
    # Step 3: Try to initialize PubSub clients
    print("\nTrying to initialize PubSub clients...")
    pubsub_initialized = False
    
    try:
        if creds_path and os.path.exists(creds_path):
            print("   Using service account credentials")
            credentials = service_account.Credentials.from_service_account_file(creds_path)
            publisher = pubsub_v1.PublisherClient(credentials=credentials)
            subscriber = pubsub_v1.SubscriberClient(credentials=credentials)
        else:
            print("   Using application default credentials")
            publisher = pubsub_v1.PublisherClient()
            subscriber = pubsub_v1.SubscriberClient()
        
        print("✅ Successfully initialized PubSub clients")
        pubsub_initialized = True
    except Exception as e:
        print(f"❌ Failed to initialize PubSub clients: {e}")
    
    # Step 4: Check if we can list topics (this requires permissions)
    if pubsub_initialized and project_id:
        print("\nTrying to list topics and subscriptions...")
        try:
            topics = list(publisher.list_topics(request={"project": f"projects/{project_id}"}))
            print(f"✅ Successfully listed {len(topics)} topics")
            
            # Print the topics
            for topic in topics:
                print(f"   - {topic.name}")
            
            # Try to list subscriptions
            subscriptions = list(subscriber.list_subscriptions(
                request={"project": f"projects/{project_id}"}
            ))
            print(f"✅ Successfully listed {len(subscriptions)} subscriptions")
            
            # Print the subscriptions
            for subscription in subscriptions:
                print(f"   - {subscription.name} -> {subscription.topic}")
                
        except Exception as e:
            print(f"❌ Failed to list topics/subscriptions: {e}")
            print("   This could indicate a permissions issue with your credentials")
    
    # Step 5: Summary
    print("\n=== Summary ===")
    if not project_id:
        print("❌ GOOGLE_CLOUD_PROJECT_ID is missing")
    if not creds_path or not os.path.exists(creds_path):
        print("❌ Valid GOOGLE_APPLICATION_CREDENTIALS is missing")
    if not pubsub_initialized:
        print("❌ Failed to initialize PubSub clients")
    
    if project_id and creds_path and os.path.exists(creds_path) and pubsub_initialized:
        print("✅ Environment appears to be correctly configured for PubSub!")
        print("\nWhen you publish a message using the PubSub console:")
        print("1. Make sure the message format matches what your code expects")
        print("2. If using Cloud Storage notifications, ensure the message format follows")
        print("   the documentation at https://cloud.google.com/storage/docs/pubsub-notifications")
        print("3. Check that your service account has the correct permissions")
        print("   - roles/pubsub.publisher")
        print("   - roles/pubsub.subscriber")
        print("   - roles/pubsub.viewer")
    else:
        print("❌ Environment is not correctly configured for PubSub")
        print("   Please fix the issues above and run this script again")

if __name__ == "__main__":
    main() 