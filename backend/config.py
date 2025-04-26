import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
env_loaded = load_dotenv()
if not env_loaded:
    print("ERROR: .env file not found or couldn't be loaded.")
    print("Please create a .env file based on the env_example template.")
    sys.exit(1)

# Check required environment variables
required_vars = [
    "GOOGLE_CLOUD_PROJECT_ID",
    "SUPABASE_URL",
    "SUPABASE_KEY"
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"ERROR: Missing required environment variables: {', '.join(missing_vars)}")
    print("Please update your .env file with the required variables.")
    sys.exit(1)

# Google Cloud Project details
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
PUBSUB_TOPIC = f"projects/{PROJECT_ID}/topics/gmail-notifications"
PUBSUB_SUBSCRIPTION = f"projects/{PROJECT_ID}/subscriptions/gmail-notifications-sub"

# Gmail API configuration
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.metadata"
]

# OAuth2 credentials
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = "token.json"

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_USER_TABLE = "gmail_users"
SUPABASE_HISTORY_TABLE = "gmail_history"

# Database settings for storing user tokens and history IDs
DB_COLLECTION = "gmail_users" 