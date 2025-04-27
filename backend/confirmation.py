import os
from dotenv import load_dotenv
import requests
from typing import Dict, Any

load_dotenv()

API_KEY = os.getenv("TEXTBELT_KEY")
TEXTBELT_NGROK = os.getenv("TEXTBELT_NGROK")

def send_text(phone: str, message: str, reply_webhook_url = False) -> Dict[str, Any]:
    """
    Send an SMS via Textbelt, optionally asking Textbelt to POST replies
    to your `reply_webhook_url`, and including `webhookData` passthrough.
    """
    payload: Dict[str, Any] = {
        "phone": phone,
        "message": message,
        "key": API_KEY,
    }
    if reply_webhook_url:
        payload["replyWebhookUrl"] = f"{TEXTBELT_NGROK}/handle-confirmation"

    resp = requests.post("https://textbelt.com/text", data=payload)
    resp.raise_for_status()
    return resp.json()