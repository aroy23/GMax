from fastapi import FastAPI

import os.path
import random
import base64

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.message import EmailMessage
from email.mime.text import MIMEText
import google.auth
import google.generativeai as genai

from supabase_db import SupabaseDB

from config import GEMINI_API_KEY, SCOPES

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

app = FastAPI()
db = SupabaseDB()


@app.get("/")
def root():
    return {"Test": "Hello World!"}

def auth():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return creds

@app.get("/labels")
def print_labels():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        creds = auth()
    try:
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            return {"Status": "No labels found"}
        result = []
        for label in labels:
            result.append(label["name"])
        return {"Labels": result}

    except HttpError as error:
        print(f"An error occurred: {error}")
    return {"Hello": "World"}

@app.get("/send")
def send():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        creds = auth()

    try:
        service = build("gmail", "v1", credentials=creds)

        profile = service.users().getProfile(userId="me").execute()  
        user_email = profile["emailAddress"]

        message = EmailMessage()

        user_data = db.get_user_data(user_email)
        persona = user_data.get("persona") if user_data else None

        if persona:
            original_content = "Hello!\n\nMy name is Bob Dylan."
            message_content = model.generate_content(
                "Give me a plain string response to this email below:\n\n" + original_content + '\n\nUse this as the persona of the responder and act as them fully:\n\n' + persona
            )
        
            message.set_content(message_content.text)
            message["To"] = "fermatjw@gmail.com"
            message["From"] = user_email
            message["Subject"] = "Automated draft"

            # encoded message
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )

            return {"Message id": send_message["id"]}

    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None
        return {"Status": "Failed!"}

def fetch_one_message(service, message_id: str) -> dict:
    msg = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()
    return msg

def gmail_body_to_text(data: str) -> str:
    b64 = data.replace("-", "+").replace("_", "/")
    b64 += "=" * ((4 - len(b64) % 4) % 4)
    return base64.b64decode(b64).decode("utf-8", errors="replace")

@app.get("/reply") # /reply?original_email_id=some_id
def reply(original_email_id: str):
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        creds = auth()

    try:
        service = build("gmail", "v1", credentials=creds)

        profile = service.users().getProfile(userId="me").execute()  
        user_email = profile["emailAddress"]

        user_data = db.get_user_data(user_email)
        persona = user_data.get("persona") if user_data else None

        if persona:
            # original_content = "Hello!\n\nMy name is Bob Dylan."
            original_email = fetch_one_message(service, original_email_id)
            payload = original_email["payload"]
            if payload.get("body", {}).get("data"):
                original_body = gmail_body_to_text(payload["body"]["data"])
            else:
                original_body = ""
                for part in payload.get("parts", []):
                    if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                        original_body = gmail_body_to_text(part["body"]["data"])
            
            sent_from = 'Unknown'
            subject = 'No Subject'
            message_id_header = ''
            thread_id = original_email["threadId"]
            
            for header in payload["headers"]:
                if header["name"] == 'From':
                    sent_from = header["value"]
                elif header["name"] == 'Subject':
                    subject = header["value"]
                elif header["name"] == 'Message-ID':
                    message_id_header = header["value"]

            email = f'\nSTART OF EMAIL\nFrom: {sent_from}\nSubject: {subject}\nBody:\n{original_body}\n'

            message_content = model.generate_content(
                "Taking into account the sender (and their email address) and subject and body, give me a plain string response to this email below:\n\n" + email + '\n\nUse this as the persona of the responder and act as them fully:\n\n' + persona
            )

            if not subject.lower().startswith("re:"):
                subject = "Re: " + subject
            
            mime = MIMEText(message_content.text)
            mime["To"] = sent_from
            mime["Subject"] = subject
            mime["In-Reply-To"] = message_id_header
            mime["References"] = message_id_header

            encoded_message = base64.urlsafe_b64encode(mime.as_bytes()).decode()

            create_message = {"raw": encoded_message, "threadId": thread_id}
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )

            return {"Message id": send_message["id"]}

    except HttpError as error:
        print(f"An error occurred: {error}")
        send_message = None
        return {"Status": "Failed!"}

@app.get("/index")
def index():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        creds = auth()

    try:
        service = build("gmail", "v1", credentials=creds)

        profile = service.users().getProfile(userId="me").execute()  
        user_email = profile["emailAddress"]

        request = service.users().messages().list(
            userId="me",
            q='in:sent after:2024/04/01 before:2025/04/30'
        )

        messages = []
        while request is not None:
            response = request.execute()
            ids = response.get("messages", [])
            for msg_meta in ids:
                msg = service.users().messages().get(
                    userId="me",
                    id=msg_meta["id"],
                    format="full"
                ).execute()
                messages.append(msg)

            # if there’s another page, prepare the next request
            request = service.users().messages().list_next(request, response)

        selected_messages = messages if len(messages) <= 5 else random.sample(messages, 5)
        emails = []
        for m in selected_messages:
            payload = m["payload"]
            if payload.get("body", {}).get("data"):
                body = gmail_body_to_text(payload["body"]["data"])
            else:
                body = ""
                for part in payload.get("parts", []):
                    if part["mimeType"] == "text/plain" and part.get("body", {}).get("data"):
                        body = gmail_body_to_text(part["body"]["data"])
            
            sent_to = 'Unknown'
            subject = 'No Subject'
            
            for header in payload["headers"]:
                if header["name"] == 'To':
                    sent_to = header["value"]
                elif header["name"] == 'Subject':
                    subject = header["value"]

            email = f'\nSTART OF EMAIL\nTo: {sent_to}\nSubject: {subject}\nBody:\n{body}\n'
            emails.append(email)

        persona_response = model.generate_content(
            "Take these 5 emails below and give me a plain string prompt that you can take in as a plain string later that acts as a persona that captures the email writing style of the sender, recognizing tone and levels of professionalism by also taking into account the address the email is sent to:\n\n" + str([m.get("snippet") + "\n\n" for m in selected_messages])
        )
        
        persona = persona_response.text
        db.update_user_data(user_email, { "persona": persona })

        return {"Status": "Success!"}
    

    except HttpError as error:
        print(f"An error occurred: {error}")
        return {"Status:", "Failed!"}