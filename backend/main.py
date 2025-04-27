import json
import base64
import os
import asyncio
from typing import Dict, Optional, List, Any
from fastapi import FastAPI, HTTPException, Depends, Request, Body, Header, BackgroundTasks
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv
import logging
import threading
import httpx
from google.cloud import pubsub_v1

from gmail_auth import start_oauth_flow, complete_oauth_flow
from gmail_service import GmailService
from supabase_db import SupabaseDB
from email_processor import EmailProcessor
from watch_scheduler import WatchScheduler
from pubsub_service import PubSubService
from config import TOKEN_FILE

from confirmation import send_text
from pydantic import BaseModel

# Load environment variables
load_dotenv()

# Get base URL from environment variable or use localhost default
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
# Get notification webhook URL from environment variable or use None
NOTIFICATION_WEBHOOK_URL = os.getenv("NOTIFICATION_WEBHOOK_URL")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("email_bot")

# Create the FastAPI app
app = FastAPI(
    title="Email Bot API",
    description="API for Email Bot that utilizes Gmail's push notification API and Google Cloud Pub/Sub",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
try:
    db = SupabaseDB()
    print("Supabase database connection established successfully.")
except Exception as e:
    print(f"ERROR: Failed to initialize Supabase database: {e}")
    print("Application may not function correctly without database access.")
    raise

# Initialize watch scheduler
scheduler = WatchScheduler(db)

# Initialize PubSub service
pubsub_service = PubSubService()

# --- Refactored Streaming Pull Logic ---

def pubsub_streaming_pull():
    """Background thread that uses PubSub streaming pull to continuously receive messages"""
    try:
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
        subscription_id = "gmail-notifications-sub" # Ensure this matches your subscription ID

        if not project_id:
            logger.error("Cannot start streaming pull: Missing GOOGLE_CLOUD_PROJECT_ID")
            return

        logger.info(f"Starting PubSub streaming pull from {project_id}/{subscription_id}")

        subscriber = pubsub_v1.SubscriberClient()
        subscription_path = subscriber.subscription_path(project_id, subscription_id)

        def callback(message):
            """Process each incoming PubSub message"""
            try:
                logger.info(f"Received message from streaming pull: {message.message_id}")
                data = message.data.decode("utf-8")
                logger.info(f"Message data: {data[:200]}...") # Log truncated data

                # Process the message similar to how we handle webhook requests
                try:
                    json_data = json.loads(data)
                    # Extract historyId and emailAddress
                    history_id = None
                    email_address = None

                    # Helper function to recursively search for fields
                    def find_fields(obj, depth=0):
                        nonlocal history_id, email_address
                        if depth > 5:  # Prevent infinite recursion
                            return

                        if isinstance(obj, dict):
                            for key, value in obj.items():
                                if key == "historyId" and not history_id:
                                    history_id = str(value)
                                elif key in ["emailAddress", "email"] and not email_address:
                                    # Basic validation
                                    if isinstance(value, str) and '@' in value:
                                        email_address = value
                                    else:
                                        logger.debug(f"Ignoring potential email field with invalid value: {value}")
                                # Recursively search nested objects
                                elif isinstance(value, (dict, list)):
                                    find_fields(value, depth + 1)
                        elif isinstance(obj, list):
                            for item in obj:
                                if isinstance(item, (dict, list)):
                                    find_fields(item, depth + 1)

                    # Search for fields in the message data
                    find_fields(json_data)

                    if email_address and history_id:
                        logger.info(f"Processing notification from streaming pull: {email_address}, history_id: {history_id}")
                        # Process the notification
                        # Using BackgroundTasks to avoid blocking the callback thread?
                        # NOTE: This callback runs in the subscriber's thread pool.
                        # For longer tasks, consider offloading (e.g., to a task queue or separate thread pool).
                        # For now, call directly, assuming process_gmail_notification is reasonably fast.
                        process_gmail_notification(email_address, history_id)
                    else:
                        logger.warning(f"Couldn't extract valid emailAddress and historyId from message: {data[:200]}...")
                except json.JSONDecodeError:
                    logger.error(f"Error decoding JSON in streaming pull: {data[:200]}...")
                except Exception as inner_e:
                    logger.error(f"Error processing message content in callback: {str(inner_e)}")

                # Acknowledge the message regardless of processing outcome to avoid redelivery loops
                message.ack()
                logger.debug(f"Acknowledged message: {message.message_id}")

            except Exception as e:
                logger.error(f"Error in streaming pull callback: {str(e)}")
                # Attempt to ack even on error to prevent potential poison pills
                try:
                    message.ack()
                    logger.warning(f"Acknowledged message {message.message_id} after error in callback.")
                except Exception as ack_error:
                    logger.error(f"Failed to acknowledge message {message.message_id} after error: {ack_error}")

        # Subscribe with streaming pull
        streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
        logger.info(f"Streaming pull listener started for {subscription_path}")

        # Keep the thread running and handle errors
        try:
            # result() blocks until the future is cancelled or raises an exception
            streaming_pull_future.result()
        except asyncio.CancelledError:
             logger.info("Streaming pull cancelled.")
        except Exception as e:
            # Log the error which caused the future to complete
            logger.error(f"Streaming pull listener stopped due to error: {str(e)}")
            streaming_pull_future.cancel() # Ensure cancellation
            # Consider adding a restart mechanism with backoff here if needed
            # For simplicity, we'll let the thread exit. It might need manual restart.
            # Example: time.sleep(60); pubsub_streaming_pull() # Be careful with recursion depth

    except Exception as e:
        logger.error(f"Fatal error starting streaming pull thread: {str(e)}")

# --- End Refactored Streaming Pull Logic ---

# Start the scheduler and potentially streaming pull on app startup
@app.on_event("startup")
async def startup_event():
    # Removed PubSub setup block as PubSubHandler is removed
    # Streaming pull manages its own subscription

    # Start the watch scheduler
    try:
        scheduler.start()
        print("Watch scheduler started successfully.")
    except Exception as e:
        print(f"ERROR starting watch scheduler: {e}")
        print("Automatic watch renewal will not be available.")

    # Removed background polling logic and thread

    # Start the streaming pull if enabled
    use_streaming_pull = os.environ.get("USE_STREAMING_PULL", "true").lower() == "true"

    if use_streaming_pull:
        # Check if PubSubService thinks it's operational (has credentials)
        # This is an indirect check, streaming pull does its own credential check
        if pubsub_service.is_operational:
            streaming_thread = threading.Thread(target=pubsub_streaming_pull, daemon=True)
            streaming_thread.start()
            logger.info("PubSub streaming pull thread started")
        else:
             logger.warning("Skipping start of PubSub streaming pull: PubSubService is not operational (check credentials).")

    # Log the server URL
    print(f"Server running at: {BASE_URL}")
    if BASE_URL != "http://localhost:8000":
        print(f"External URL detected. Using {BASE_URL} for callbacks.")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    # Stop the watch scheduler
    try:
        scheduler.stop()
        print("Watch scheduler stopped successfully.")
    except Exception as e:
        print(f"ERROR stopping watch scheduler: {e}")

# Models for request validation
class AuthCodeRequest(BaseModel):
    code: str
    redirect_uri: str
    user_id: str

class WatchRequest(BaseModel):
    user_id: str
    label_ids: Optional[List[str]] = None

class NotificationRequest(BaseModel):
    message: Dict
    subscription: str

class SubscriptionRequest(BaseModel):
    email: EmailStr
    topic_name: Optional[str] = "email-notifications"
    label_id: Optional[str] = "INBOX"

class UnsubscriptionRequest(BaseModel):
    email: EmailStr

class PubSubMessage(BaseModel):
    message: Dict[str, Any]
    subscription: str

@app.get("/")
def root():
    # Return status including PubSub operational status
    # Note: pubsub_handler removed, using pubsub_service status instead
    return {
        "status": "online",
        "service": "EmailBot Backend",
        "pubsub_operational": pubsub_service.is_operational, # Based on PubSubService init
        "database_connected": db is not None
    }

@app.get("/auth/url")
def get_auth_url(redirect_uri: str, user_id: Optional[str] = None, force_consent: bool = True):
    """Get Gmail OAuth URL for authentication"""
    try:
        logger.info(f"Generating auth URL with redirect_uri: {redirect_uri}, user_id: {user_id}, force_consent: {force_consent}")
        
        # Use user_id as state parameter to track through OAuth flow
        auth_url = start_oauth_flow(
            redirect_uri, 
            state=user_id,
            force_consent=force_consent
        )
        return {"auth_url": auth_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/callback")
@app.get("/auth/callback")
async def auth_callback(request: Request):
    """Handle OAuth callback with authorization code"""
    try:
        # For GET requests, extract params from query string
        if request.method == "GET":
            params = dict(request.query_params)
            code = params.get("code")
            # Use the exact same redirect_uri that was used in the initial request
            redirect_uri = "http://localhost:8000/auth/callback"
            # Get user_id from state parameter
            state = params.get("state")
            user_id = state
            
            logger.info(f"Received OAuth callback GET with state: {state}")
            
            if not code:
                logger.error("Missing authorization code in callback")
                raise HTTPException(status_code=400, detail="Missing authorization code")
            if not user_id:
                logger.error("Missing user_id (state parameter) in callback")
                raise HTTPException(status_code=400, detail="Missing user_id (state parameter)")
        # For POST requests, use the existing structure
        else:
            data = await request.json()
            code = data.get("code")
            redirect_uri = data.get("redirect_uri")
            user_id = data.get("user_id")
            
            logger.info(f"Received OAuth callback POST for user_id: {user_id}")
            
        logger.info(f"Processing OAuth callback with code: {code[:10] if code else 'None'}... and redirect_uri: {redirect_uri}")
        
        try:
            # First, remove any existing token files for this user
            token_file = f"{user_id}_token.json"
            if os.path.exists(token_file):
                try:
                    os.remove(token_file)
                    logger.info(f"Removed existing token file for {user_id}")
                except Exception as e:
                    logger.warning(f"Could not remove existing token file: {e}")
            
            # Complete the OAuth flow to get a new token
            token_data = complete_oauth_flow(
                code, 
                redirect_uri, 
                user_id
            )
            
            # Extract the email from the token data (which is now added by the complete_oauth_flow function)
            email = token_data.get('email', user_id)
            
            # Verify the token has the full access scope
            scopes = token_data.get('scopes', [])
            has_full_access = "https://mail.google.com/" in scopes
            
            if not has_full_access:
                logger.warning(f"Token does not have full Gmail access. Scopes: {scopes}")
                # We'll still proceed, but log a warning
            
            # Store the token in the database using the email as the user identifier
            db.store_token(email, token_data)
            logger.info(f"Successfully stored token for {email} in database")
            
            # For GET requests, redirect to a confirmation page
            if request.method == "GET":
                success_url = f"{BASE_URL}/?auth_success=true&user_id={email}"
                logger.info(f"Auth successful, redirecting to: {success_url}")
                return RedirectResponse(url=success_url)
            
            # For POST requests, return JSON
            return {"authenticated": True, "user_id": email, "has_full_access": has_full_access}
        except Exception as oauth_error:
            logger.error(f"OAuth completion error: {str(oauth_error)}")
            error_message = str(oauth_error)
            
            # Handle scope mismatch errors specially
            if "Scope has changed" in error_message:
                logger.warning("Scope mismatch detected. This may be due to inconsistent GMAIL_SCOPES configuration.")
                logger.warning("Check config.py to ensure GMAIL_SCOPES match what's being used in the OAuth flow.")
            
            if request.method == "GET":
                error_url = f"{BASE_URL}/?auth_error=true&error={error_message}"
                return RedirectResponse(url=error_url)
            raise HTTPException(status_code=500, detail=f"OAuth error: {error_message}")
    except Exception as e:
        logger.error(f"Error in auth callback: {str(e)}")
        if request.method == "GET":
            return RedirectResponse(url=f"{BASE_URL}/?auth_error=true&error={str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# @app.post("/auth/reset")
# @app.get("/auth/reset")
# def reset_auth(user_id: str):
#     """Reset a user's authentication and force re-authentication with new scopes"""
#     try:
#         logger.info(f"Resetting authentication for user: {user_id}")
        
#         # 1. Get current token from database
#         user_data = db.get_user_data(user_id)
#         if not user_data or 'token' not in user_data:
#             return {
#                 "status": "warning", 
#                 "message": f"No token found for {user_id}"
#             }
            
#         token_data = user_data.get('token')
        
#         # 2. Try to revoke token if we have an access token
#         if token_data and 'token' in token_data:
#             try:
#                 revoke_result = revoke_token(token_data['token'])
#                 logger.info(f"Token revocation result: {revoke_result}")
#             except Exception as e:
#                 logger.error(f"Error revoking token: {e}")
        
#         # 3. Delete token file if it exists
#         token_filename = f"{user_id}_{TOKEN_FILE}"
#         if os.path.exists(token_filename):
#             try:
#                 os.remove(token_filename)
#                 logger.info(f"Removed token file for {user_id}")
#             except Exception as e:
#                 logger.error(f"Error removing token file: {e}")
                
#         # 4. Clear token in database
#         try:
#             db.update_user_data(user_id, {'token': None})
#             logger.info(f"Cleared token in database for {user_id}")
#         except Exception as e:
#             logger.error(f"Error clearing token in database: {e}")
        
#         # 5. Generate a new auth URL for the user
#         auth_url = start_oauth_flow("http://localhost:8000/auth/callback", state=user_id)
        
#         return {
#             "status": "success",
#             "message": "Authentication reset successfully. Please re-authenticate with the new URL.",
#             "auth_url": auth_url
#         }
#     except Exception as e:
#         logger.error(f"Error resetting authentication: {e}")
#         raise HTTPException(status_code=500, detail=str(e))

@app.post("/gmail/watch")
def start_watch(request: WatchRequest):
    """Start watching a user's Gmail inbox"""
    # Removed check for pubsub_handler.is_operational
    # Dependency check is implicit in whether GmailService can start watch

    try:
        # Get user data from database
        user_data = db.get_user_data(request.user_id)
        if not user_data or 'token' not in user_data:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated"
            )

        # Create Gmail service
        gmail_service_sync = GmailService()

        # Start the watch - Requires Pub/Sub Topic Name
        # Assuming the topic name is configured correctly elsewhere (e.g., env var or default)
        # The gmail_service_sync.start_watch method likely needs the topic name now, not a webhook URL.
        # This needs verification based on the implementation of GmailService.start_watch.
        # For now, assuming it uses a pre-configured topic or default.
        # If it *still* requires webhook_url, the logic needs adjustment.
        # Let's assume it uses the topic linked to 'gmail-notifications-sub' implicitly or via config.
        # *** TODO: Verify how `gmail_service_sync.start_watch` gets the Pub/Sub topic name ***
        
        # Determine the Pub/Sub topic name to use
        # Option 1: Use default from PubSubService (if available)
        topic_name = pubsub_service.topic_name # Assuming PubSubService holds this
        # Option 2: Get from env var directly
        # topic_name = os.getenv("PUB SUB_TOPIC_NAME", "gmail-notifications") 
        # Option 3: Hardcode (less flexible)
        #topic_name = "gmail-notifications"
        
        if not topic_name:
            raise HTTPException(status_code=500, detail="Pub/Sub topic name not configured.")
             
        logger.info(f"Starting Gmail watch for {request.user_id} targeting Pub/Sub topic: {topic_name}")
        watch_response = gmail_service_sync.start_watch(
            label_ids=request.label_ids
        )

        # Store the watch data
        db.store_watch_data(
            request.user_id,
            watch_response.get("historyId"),
            watch_response.get("expiration")
        )

        # Log the watch event
        db.log_history_event(
            request.user_id,
            watch_response.get("historyId"),
            "watch_started",
            {
                "expiration": watch_response.get("expiration"),
                "historyId": watch_response.get("historyId"),
                "topic_name": topic_name
            }
        )

        return watch_response
    except Exception as e:
        logger.error(f"Failed to start watch: {str(e)}")
        # Provide more context if it's a known configuration issue
        if "topic" in str(e).lower():
             logger.error("Ensure the Pub/Sub topic exists and the service account has permissions.")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/gmail/stop-watch")
def stop_watch(user_id: str):
    """Stop watching a user's Gmail inbox"""
    # Removed check for pubsub_handler.is_operational

    try:
        # Get user data from database
        user_data = db.get_user_data(user_id)
        if not user_data or 'token' not in user_data:
            raise HTTPException(
                status_code=401,
                detail="User not authenticated"
            )

        # Create Gmail service
        gmail_service_sync = GmailService()

        # Stop the watch
        logger.info(f"Stopping Gmail watch for user {user_id}")
        result = gmail_service_sync.stop_watch()
        logger.info(f"Stop watch result for {user_id}: {result}") # Log result, often empty on success

        # Update user data in DB (clear expiration)
        db.update_user_data(user_id, {
            "watch_expiration": None
            # Consider clearing historyId too if watch is stopped? Depends on logic.
        })

        # Log the watch stop event
        db.log_history_event(
            user_id,
            user_data.get("last_history_id", "unknown"),
            "watch_stopped",
            {} # Include any relevant info from 'result' if available
        )

        return result # Often returns empty 204 No Content on success
    except Exception as e:
        logger.error(f"Failed to stop watch for {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/admin/renew-watches")
def renew_watches():
    """Manually trigger renewal of all Gmail watches"""
    # Removed check for pubsub_handler.is_operational

    try:
        results = scheduler.renew_all_watches()
        return results
    except Exception as e:
        logger.error(f"Error during manual watch renewal: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Background task to process Gmail notifications
def process_gmail_notification(email_address: str, history_id: str):
    """Process Gmail notification in the background"""
    logger.info("===============================================")
    logger.info(f"PROCESSING GMAIL NOTIFICATION: {email_address}, history_id: {history_id}")
    logger.info("===============================================")

    try:
        # Extract user ID from email
        user_id = email_address
        logger.info(f"Looking up user data for {user_id}")

        # Get user data
        user_data = db.get_user_data(user_id)
        if not user_data:
            logger.error(f"User {user_id} not found in database")
            return # Cannot process without user data

        if 'token' not in user_data or not user_data['token']:
            logger.error(f"User {user_id} found but has no valid authentication token")
            return # Cannot process without token

        # Get the last history ID
        last_history_id = user_data.get('last_history_id')
        logger.info(f"Last history ID from database for {user_id}: {last_history_id}")

        # Check if this is an already processed notification or out of order
        # Convert to integers for reliable comparison
        try:
            current_hist_id_int = int(history_id)
            last_hist_id_int = int(last_history_id) if last_history_id else 0

            if last_history_id and current_hist_id_int <= last_hist_id_int:
                logger.warning(f"Ignoring notification for {user_id}: history_id {history_id} <= last_history_id {last_history_id}. Likely already processed or out of order.")
                # Note: Pub/Sub doesn't guarantee order, but duplicates are possible.
                # This check prevents reprocessing known history.
                return
        except ValueError:
             logger.error(f"Invalid history ID format for user {user_id}: current='{history_id}', last='{last_history_id}'. Skipping processing.")
             return


        # Process the notification
        logger.info(f"Creating EmailProcessor for {user_id}")
        # Ensure token is passed correctly
        token_info = user_data.get('token')
        processor = EmailProcessor()

        logger.info(f"Processing notification for {user_id} with history_id {history_id}, last_history_id {last_history_id}")
        result = processor.process_notification(db, history_id, last_history_id)
        # Use default=str for non-serializable items like datetime
        logger.info(f"Notification processing result for {user_id}: {json.dumps(result, default=str)}")

        # Update the last history ID if processing was successful and returned a new history ID
        new_history_id = result.get('historyId')
        if result.get('status') in ['processed', 'initialized'] and new_history_id:
             # Ensure the new history ID is greater than the last one before updating
            try:
                new_hist_id_int = int(new_history_id)
                if new_hist_id_int > last_hist_id_int:
                    logger.info(f"Updating last_history_id for {user_id} from {last_history_id} to {new_history_id}")
                    db.update_history_id(user_id, new_history_id)

                    # Log the processing event
                    logger.info(f"Logging history event for successful processing for {user_id}")
                    db.log_history_event(
                        user_id,
                        new_history_id,
                        f"notification_processed_{result.get('status')}",
                        {
                            "processedCount": result.get('processedCount', 0),
                            "results": result.get('results', []) # Ensure results are serializable
                        }
                    )

                    # Send notifications for any new messages if webhook configured
                    if NOTIFICATION_WEBHOOK_URL and result.get('status') == 'processed' and result.get('processedCount', 0) > 0:
                        logger.info(f"Sending notifications for {result.get('processedCount', 0)} processed messages for {user_id}")
                        for msg_result in result.get('results', []):
                            # Check if message was successfully processed and not spam
                            if msg_result.get('processed') and msg_result.get('action') != 'spam_detected':
                                # Send notification with full content
                                send_email_notification(user_id, msg_result)
                    elif not NOTIFICATION_WEBHOOK_URL:
                         logger.debug("Skipping external notification sending (NOTIFICATION_WEBHOOK_URL not set).")

                else:
                    logger.warning(f"Not updating last_history_id for {user_id}: new history ID {new_history_id} is not greater than last {last_history_id}.")

            except ValueError:
                 logger.error(f"Invalid new history ID format received from processor for user {user_id}: '{new_history_id}'. Not updating.")
        else:
            logger.warning(f"Not updating last_history_id for {user_id} due to status: {result.get('status')} or missing historyId in result.")

        logger.info(f"Completed processing notification for {user_id}: {result.get('status')}")
    except Exception as e:
        import traceback
        logger.error(f"Error processing Gmail notification for {email_address}, history_id {history_id}: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Consider adding logic here to handle specific errors, e.g., requeueing or alerting.

def send_email_notification(user_id: str, message_data: Dict):
    """
    Send a notification about a new email with its full content
    
    Args:
        user_id: The user ID (email address)
        message_data: The processed message data
    """
    if not NOTIFICATION_WEBHOOK_URL:
        logger.info("No notification webhook URL configured. Skipping notification.")
        return
        
    try:
        # Prepare notification data with full message content
        notification_data = {
            "type": "new_email",
            "user_id": user_id,
            "timestamp": message_data.get("timestamp"),
            "message": {
                "id": message_data.get("messageId"),
                "thread_id": message_data.get("threadId"),
                "from": message_data.get("from"),
                "to": message_data.get("to", ""),
                "subject": message_data.get("subject"),
                "content": message_data.get("full_content", ""),  # Use full content
                "preview": message_data.get("content_preview", "")
            }
        }
        
        # Use a synchronous request with a standard timeout
        logger.info(f"Sending notification to webhook: {NOTIFICATION_WEBHOOK_URL}")
        response = httpx.post(
            NOTIFICATION_WEBHOOK_URL,
            json=notification_data,
            timeout=10.0
        )
        
        if response.status_code < 200 or response.status_code >= 300:
            logger.error(f"Failed to send notification: {response.status_code} {response.text}")
        else:
            logger.info(f"Notification sent successfully: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending email notification: {e}")

@app.post("/gmail-push-webhook")
async def gmail_push_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Specialized webhook endpoint for handling Gmail's push notifications directly
    
    Gmail's notification format is different from regular PubSub messages.
    This endpoint is designed to handle Gmail's specific format.
    """
    logger.info("=== Received request on /gmail-push-webhook ===")
    
    try:
        # Get the raw request body for logging
        raw_body = await request.body()
        raw_body_str = raw_body.decode('utf-8', errors='replace')
        logger.info(f"Raw webhook request body: {raw_body_str}")
        
        try:
            # Parse the JSON request body
            body = json.loads(raw_body_str)
            logger.info(f"Parsed JSON: {json.dumps(body, indent=2)}")
            
            # Gmail notifications have a specific format
            # Try to extract historyId and emailAddress directly
            
            # First, check if it's a Gmail notification with data field
            if "message" in body and "data" in body["message"]:
                data_base64 = body["message"]["data"]
                try:
                    # Decode the base64 data
                    decoded_bytes = base64.b64decode(data_base64)
                    decoded_data = decoded_bytes.decode('utf-8')
                    logger.info(f"Decoded data: {decoded_data}")
                    
                    # Parse the JSON data
                    data = json.loads(decoded_data)
                    logger.info(f"Parsed data: {json.dumps(data, indent=2)}")
                    
                    # Extract historyId and emailAddress
                    history_id = None
                    email_address = None
                    
                    # Try different paths where these values might be found
                    if "historyId" in data:
                        history_id = data["historyId"]
                    if "emailAddress" in data:
                        email_address = data["emailAddress"]
                        
                    # If we couldn't find them directly, try using our search algorithm
                    if not history_id or not email_address:
                        # Helper function to recursively search for fields
                        def find_fields(obj, depth=0):
                            nonlocal history_id, email_address
                            if depth > 5:  # Prevent infinite recursion
                                return
                                
                            if isinstance(obj, dict):
                                for key, value in obj.items():
                                    if key == "historyId" and not history_id:
                                        history_id = str(value)
                                    elif key in ["emailAddress", "email"] and not email_address:
                                        email_address = value
                                    # Recursively search nested objects
                                    elif isinstance(value, (dict, list)):
                                        find_fields(value, depth + 1)
                            elif isinstance(obj, list):
                                for item in obj:
                                    if isinstance(item, (dict, list)):
                                        find_fields(item, depth + 1)
                        
                        # Search for fields in the decoded data
                        find_fields(data)
                    
                    # Log what we found
                    logger.info(f"Extracted email_address: {email_address}, history_id: {history_id}")
                    
                    # If we have both values, process the notification
                    if email_address and history_id:
                        # Process the notification in the background
                        logger.info(f"Adding background task to process notification")
                        background_tasks.add_task(
                            process_gmail_notification,
                            email_address,
                            history_id
                        )
                        
                        return {"status": "processing"}
                    else:
                        logger.error("Could not extract required fields from notification")
                        return {"status": "error", "detail": "Missing required fields in notification"}
                except Exception as decode_error:
                    logger.error(f"Error decoding data: {str(decode_error)}")
                    return {"status": "error", "detail": f"Error decoding data: {str(decode_error)}"}
            else:
                logger.error("Request does not match expected Gmail notification format")
                return {"status": "error", "detail": "Invalid notification format"}
        except json.JSONDecodeError:
            logger.error("Request body is not valid JSON")
            return {"status": "error", "detail": "Invalid JSON in request body"}
    except Exception as e:
        logger.error(f"Unhandled error processing Gmail push webhook: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {"status": "error", "detail": str(e)}

@app.get("/index")
def index():
    gmail_service = GmailService()
    return gmail_service.indexer(db)

class SmsReply(BaseModel):
    textId: str
    fromNumber: str
    text: str
    data: str | None = None

@app.post("/handle-confirmation")
async def handle_confirmation(
    request: Request,
    reply: SmsReply = Body(...),
    x_textbelt_timestamp: str = Header(..., alias="X-textbelt-timestamp"),
    x_textbelt_signature: str = Header(..., alias="X-textbelt-signature"),
):
    print("handle confirmation")
    gmail_service = GmailService()
    profile = gmail_service.service.users().getProfile(userId="me").execute()  
    user_email = profile["emailAddress"]
    phone_number = db.get_user_data(user_email).get("phone_number")

    reply_text = reply.text.strip().lower()
    if reply_text == "yes":
        confirmation = db.get_confirmation(user_email)
        print(confirmation)
        gmail_service.reply(db, confirmation["respond_to_message_id"], confirmation["message_content"])
        res = send_text(phone_number, "Perfect! The reply has been sent.")
        print(res)
        db.delete_confirmation(user_email)
    elif reply_text == "no":
        res = send_text(phone_number, "Got it! This reply won't be sent.")
        print(res)
        db.delete_confirmation(user_email)

    return {"status": "received"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)