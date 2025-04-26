#!/usr/bin/env python
"""
Cloud Storage Notification Simulator

This script simulates sending a Cloud Storage notification to a PubSub topic.
The notification format follows the documentation at:
https://cloud.google.com/storage/docs/pubsub-notifications
"""

import os
import json
import base64
import argparse
from datetime import datetime
from google.cloud import pubsub_v1
from google.oauth2 import service_account

def get_storage_notification_payload(event_type="OBJECT_FINALIZE", bucket_id="example-bucket", 
                                    object_id="example-object.txt", generation="123456", 
                                    payload_format="JSON_API_V1"):
    """
    Generate a Cloud Storage notification payload.
    
    Args:
        event_type: Type of event (e.g. OBJECT_FINALIZE, OBJECT_DELETE)
        bucket_id: Name of the bucket
        object_id: Name of the object
        generation: Generation number of the object
        payload_format: Format of the payload
        
    Returns:
        A tuple of (attributes, payload) as they would be sent to PubSub
    """
    # Create the attributes
    attributes = {
        "notificationConfig": f"projects/_/buckets/{bucket_id}/notificationConfigs/1",
        "eventType": event_type,
        "payloadFormat": payload_format,
        "bucketId": bucket_id,
        "objectId": object_id,
        "objectGeneration": str(generation),
        "eventTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    }
    
    # If this is an overwrite, add the appropriate attributes
    if event_type == "OBJECT_FINALIZE" and "overwroteGeneration" in locals():
        attributes["overwroteGeneration"] = locals()["overwroteGeneration"]
    elif event_type in ["OBJECT_ARCHIVE", "OBJECT_DELETE"] and "overwrittenByGeneration" in locals():
        attributes["overwrittenByGeneration"] = locals()["overwrittenByGeneration"]
        
    # Create the payload
    if payload_format == "JSON_API_V1":
        payload = {
            "kind": "storage#object",
            "id": f"{bucket_id}/{object_id}/{generation}",
            "selfLink": f"https://www.googleapis.com/storage/v1/b/{bucket_id}/o/{object_id}",
            "name": object_id,
            "bucket": bucket_id,
            "generation": str(generation),
            "metageneration": "1",
            "contentType": "text/plain",
            "timeCreated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "updated": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "storageClass": "STANDARD",
            "size": "100",
            "md5Hash": "CY9rzUYh03PK3k6DJie09g==",
            "contentEncoding": "identity",
            "contentDisposition": "inline",
            "crc32c": "4frTKA==",
            "etag": "CJiPp9fVz90CEAE="
        }
        
        # For delete events, add timeDeleted
        if event_type == "OBJECT_DELETE":
            payload["timeDeleted"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    else:
        # If using NONE format, no payload
        payload = None
        
    return attributes, payload

def send_storage_notification(publisher, project_id, topic_name, attributes, payload):
    """
    Send a simulated Cloud Storage notification to a PubSub topic.
    
    Args:
        publisher: PubSub publisher client
        project_id: Google Cloud project ID
        topic_name: Name of the PubSub topic
        attributes: Dictionary of message attributes
        payload: Message payload (or None if no payload)
        
    Returns:
        Message ID if successful, None otherwise
    """
    topic_path = publisher.topic_path(project_id, topic_name)
    
    # Encode payload as JSON string if it exists
    data = b''
    if payload:
        data = json.dumps(payload).encode("utf-8")
    
    try:
        future = publisher.publish(
            topic_path,
            data=data,
            **attributes
        )
        message_id = future.result()
        print(f"Published Cloud Storage notification message with ID: {message_id}")
        return message_id
    except Exception as e:
        print(f"Failed to publish message: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Simulate a Cloud Storage notification to PubSub")
    parser.add_argument("--project", help="Google Cloud Project ID")
    parser.add_argument("--credentials", help="Path to service account credentials file")
    parser.add_argument("--topic", default="gmail-notifications", help="Topic name to publish to")
    parser.add_argument("--event-type", default="OBJECT_FINALIZE", 
                        choices=["OBJECT_FINALIZE", "OBJECT_METADATA_UPDATE", "OBJECT_DELETE", "OBJECT_ARCHIVE"],
                        help="Event type to simulate")
    parser.add_argument("--bucket", default="test-bucket", help="Bucket name")
    parser.add_argument("--object", default="test-object.txt", help="Object name")
    parser.add_argument("--payload-format", default="JSON_API_V1", 
                        choices=["JSON_API_V1", "NONE"],
                        help="Payload format")
    
    args = parser.parse_args()
    
    # Check environment variables if not provided as arguments
    project_id = args.project or os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
    credentials_path = args.credentials or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if not project_id:
        print("Error: Project ID not provided. Use --project or set GOOGLE_CLOUD_PROJECT_ID")
        return
    
    # Initialize the publisher client
    try:
        if credentials_path and os.path.exists(credentials_path):
            print(f"Using service account credentials from: {credentials_path}")
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            publisher = pubsub_v1.PublisherClient(credentials=credentials)
        else:
            print("Using application default credentials")
            publisher = pubsub_v1.PublisherClient()
            
        print(f"Successfully initialized PubSub publisher client")
    except Exception as e:
        print(f"Failed to initialize PubSub publisher client: {e}")
        return
    
    # Generate the notification payload
    attributes, payload = get_storage_notification_payload(
        event_type=args.event_type,
        bucket_id=args.bucket,
        object_id=args.object,
        generation=str(int(datetime.now().timestamp())),  # Use current timestamp as generation
        payload_format=args.payload_format
    )
    
    print(f"\nSimulating a Cloud Storage {args.event_type} notification")
    print(f"Bucket: {args.bucket}")
    print(f"Object: {args.object}")
    print(f"Payload format: {args.payload_format}")
    
    # Print the message attributes
    print("\nMessage Attributes:")
    for key, value in attributes.items():
        print(f"  {key}: {value}")
    
    # Print the payload if it exists
    if payload:
        print("\nPayload (first 200 chars):")
        payload_str = json.dumps(payload, indent=2)
        print(f"{payload_str[:200]}..." if len(payload_str) > 200 else payload_str)
    else:
        print("\nPayload: None (as requested)")
    
    # Send the notification
    print("\nSending notification...")
    send_storage_notification(publisher, project_id, args.topic, attributes, payload)
    
    # Also show what the message would look like in the PubSub webhook
    print("\nEquivalent PubSub webhook message (as received by your application):")
    webhook_message = {
        "message": {
            "attributes": attributes,
            "data": base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8") if payload else "",
            "messageId": "123456789",
            "publishTime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        },
        "subscription": f"projects/{project_id}/subscriptions/{args.topic}-sub"
    }
    print(json.dumps(webhook_message, indent=2))
    
    print("\nVerify this matches what your application expects to receive.")

if __name__ == "__main__":
    main() 