import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
env_loaded = load_dotenv()
if not env_loaded:
    print("ERROR: .env file not found or couldn't be loaded.")
    print("Please create a .env file based on the env_example template.")
    sys.exit(1)

# Google Cloud Project details
PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT_ID")
PUBSUB_TOPIC = f"projects/{PROJECT_ID}/topics/gmail-notifications"
PUBSUB_SUBSCRIPTION = f"projects/{PROJECT_ID}/subscriptions/gmail-notifications-sub"

# Gmail API configuration
GMAIL_SCOPES = [
    "https://mail.google.com/"  # Full access to Gmail - this is the most permissive scope and includes all others
]

# OAuth2 credentials
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CLIENT_SECRET_FILE", "client_secret.json")
TOKEN_FILE = "token.json"

# Supabase settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_USER_TABLE = "gmail_users"
SUPABASE_HISTORY_TABLE = "gmail_history"
SUPABASE_CONFIRMATIONS_TABLE = "confirmations"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]