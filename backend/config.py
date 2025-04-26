import os
from dotenv import load_dotenv
load_dotenv()

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.labels",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly"
]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_USER_TABLE = "gmail_users"
SUPABASE_HISTORY_TABLE = "gmail_history"