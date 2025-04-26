import os
import json
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse
import requests
from pathlib import Path

# Configuration
CLIENT_ID = ""  # Fill in your client ID
CLIENT_SECRET = ""  # Fill in your client secret
REDIRECT_URI = "http://localhost:3001/callback"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/gmail.readonly"

# Global variables
auth_code = None
auth_code_received = threading.Event()

class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        
        # Parse the query parameters from the URL
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        
        if 'code' in params:
            auth_code = params['code'][0]
            print(f"✅ OAuth code received: {auth_code[:10]}...")
            
            # Send a simple response to the browser
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"""
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; margin-top: 50px;">
                <h1>Authentication Successful!</h1>
                <p>You can close this window and return to the test script.</p>
                <script>window.close();</script>
            </body>
            </html>
            """)
            
            # Signal that we received the auth code
            auth_code_received.set()
        else:
            self.send_response(400)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b"Missing authorization code")

def start_callback_server():
    PORT = 3001
    handler = CallbackHandler
    
    try:
        with socketserver.TCPServer(("", PORT), handler) as httpd:
            print(f"🔌 Callback server started at port {PORT}")
            
            # Serve until auth_code_received is set
            while not auth_code_received.is_set():
                httpd.handle_request()
                
    except OSError as e:
        print(f"⚠️ Error starting callback server: {e}")
        print("Make sure port 3001 is available or change the PORT variable")

def get_auth_url():
    """Generate the authorization URL"""
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE,
        'response_type': 'code',
        'access_type': 'offline',
        'prompt': 'consent'
    }
    
    auth_url = f"{AUTH_URI}?{urllib.parse.urlencode(params)}"
    return auth_url

def exchange_code_for_token(code):
    """Exchange authorization code for tokens"""
    data = {
        'code': code,
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }
    
    response = requests.post(TOKEN_URI, data=data)
    return response.json()

def save_token_to_file(token_data, filename="token.json"):
    """Save token data to a file"""
    with open(filename, 'w') as f:
        json.dump(token_data, f, indent=2)
    print(f"✅ Token saved to {filename}")

def manual_oauth_flow():
    """Run the complete OAuth flow manually"""
    # Step 1: Generate auth URL and open browser
    auth_url = get_auth_url()
    print(f"🌐 Opening browser for authentication at:\n{auth_url}")
    
    # Step 2: Start server to catch the callback
    server_thread = threading.Thread(target=start_callback_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Step 3: Open browser for user to authenticate
    webbrowser.open(auth_url)
    
    # Step 4: Wait for the auth code
    auth_received = auth_code_received.wait(timeout=120)
    
    if not auth_received:
        print("❌ Timed out waiting for auth code")
        return False
    
    # Step 5: Exchange code for token
    print("\n🔄 Exchanging code for token...")
    token_data = exchange_code_for_token(auth_code)
    
    if 'access_token' in token_data:
        print("✅ Successfully obtained access token!")
        print(f"Access token: {token_data['access_token'][:10]}...")
        
        if 'refresh_token' in token_data:
            print(f"Refresh token: {token_data['refresh_token'][:10]}...")
        
        # Save token to file
        save_token_to_file(token_data)
        return True
    else:
        print("❌ Failed to obtain tokens:")
        print(token_data)
        return False

if __name__ == "__main__":
    print("""
╭─────────────────────────────────────────────────╮
│         Manual OAuth 2.0 Flow Testing           │
│                                                 │
│  You will need to provide your own credentials  │
│  from the Google API Console                    │
╰─────────────────────────────────────────────────╯
    """)
    
    # Check if credentials are provided
    if not CLIENT_ID or not CLIENT_SECRET:
        print("❌ Please fill in your CLIENT_ID and CLIENT_SECRET in the script.")
        
        client_id = input("Enter your Client ID: ")
        client_secret = input("Enter your Client Secret: ")
        
        if client_id and client_secret:
            CLIENT_ID = client_id
            CLIENT_SECRET = client_secret
        else:
            print("❌ Client ID and Client Secret are required.")
            exit(1)
    
    # Run the flow
    manual_oauth_flow() 