import requests
import json
import webbrowser
import time
import http.server
import socketserver
import threading
from urllib.parse import parse_qs, urlparse

# Configuration
BASE_URL = "http://localhost:8000"  # Your FastAPI server running locally
REDIRECT_URI = "http://localhost:3001/callback"  # Local redirect for OAuth
USER_ID = "raynishant1@gmail.com"  # User email for testing

# Global variables to store state
auth_code = None
auth_code_received = threading.Event()
user_token = None
history_id = None

# Simple HTTP server to handle OAuth callback
class CallbackHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        
        # Parse the query parameters from the URL
        query = urlparse(self.path).query
        params = parse_qs(query)
        
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
    # Start a simple HTTP server to catch the OAuth redirect
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

def print_response(name, response):
    """Pretty print a response"""
    print(f"\n{'=' * 60}")
    print(f"🔍 {name} - Status Code: {response.status_code}")
    print(f"{'=' * 60}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2))
        return data
    except ValueError:
        print(response.text)
        return None

def test_root_endpoint():
    """Test the root endpoint"""
    print("\n🧪 Testing ROOT endpoint")
    response = requests.get(f"{BASE_URL}/")
    return print_response("Root Response", response)

def test_auth_flow():
    """Test the complete OAuth flow"""
    global user_token
    
    print("\n🧪 Testing AUTH flow")
    
    # 1. Get the auth URL
    response = requests.get(f"{BASE_URL}/auth/url?redirect_uri={REDIRECT_URI}")
    data = print_response("Auth URL Response", response)
    
    if not data or 'auth_url' not in data:
        print("❌ Failed to get auth URL")
        return False
    
    auth_url = data['auth_url']
    
    # 2. Start a server to catch the callback
    server_thread = threading.Thread(target=start_callback_server)
    server_thread.daemon = True
    server_thread.start()
    
    # 3. Open browser for user to authenticate
    print(f"\n🌐 Opening browser for authentication. Please complete the OAuth flow...")
    webbrowser.open(auth_url)
    
    # 4. Wait for the auth code (with timeout)
    auth_received = auth_code_received.wait(timeout=120)
    
    if not auth_received:
        print("❌ Timed out waiting for auth code")
        return False
    
    # 5. Exchange code for token
    print("\n🔄 Exchanging code for token...")
    token_response = requests.post(f"{BASE_URL}/auth/callback", json={
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "user_id": USER_ID
    })
    
    token_data = print_response("Token Response", token_response)
    
    if token_data and token_data.get('authenticated'):
        user_token = token_data
        print("✅ Authentication successful!")
        return True
    
    print("❌ Authentication failed")
    return False

def test_gmail_watch():
    """Test watching a Gmail inbox"""
    global history_id
    
    print("\n🧪 Testing GMAIL WATCH endpoint")
    
    response = requests.post(f"{BASE_URL}/gmail/watch", json={
        "user_id": USER_ID,
        "label_ids": ["INBOX"]
    })
    
    data = print_response("Watch Response", response)
    
    if data and 'historyId' in data:
        history_id = data['historyId']
        print(f"✅ Watch set up successfully with historyId: {history_id}")
        return True
    
    return False

def test_process_history():
    """Test processing history for a user"""
    if not history_id:
        print("⚠️ No history ID available, skipping process history test")
        return False
    
    print("\n🧪 Testing PROCESS HISTORY endpoint")
    
    response = requests.post(f"{BASE_URL}/gmail/process-history", json={
        "user_id": USER_ID,
        "history_id": history_id
    })
    
    data = print_response("Process History Response", response)
    return data is not None

def test_stop_watch():
    """Test stopping a Gmail watch"""
    print("\n🧪 Testing STOP WATCH endpoint")
    
    response = requests.post(f"{BASE_URL}/gmail/stop-watch?user_id={USER_ID}")
    data = print_response("Stop Watch Response", response)
    return data is not None

def test_renew_watches():
    """Test renewing all watches"""
    print("\n🧪 Testing RENEW WATCHES endpoint")
    
    response = requests.post(f"{BASE_URL}/admin/renew-watches")
    data = print_response("Renew Watches Response", response)
    return data is not None

def test_webhook():
    """Test the webhook endpoint with a mock message"""
    print("\n🧪 Testing WEBHOOK endpoint")
    
    # Create a mock Pub/Sub message
    mock_data = {
        "historyId": history_id or "123456",
        "emailAddress": USER_ID
    }
    
    # Encode to base64 to simulate Pub/Sub
    import base64
    encoded_data = base64.b64encode(json.dumps(mock_data).encode()).decode()
    
    response = requests.post(f"{BASE_URL}/webhook/gmail", json={
        "message": {
            "data": encoded_data
        },
        "subscription": "projects/test/subscriptions/test-sub"
    })
    
    data = print_response("Webhook Response", response)
    return data is not None

def run_all_tests():
    """Run all tests in sequence"""
    print("\n🚀 Starting API Test Suite\n")
    print("=" * 80)
    
    # Test basic endpoint
    root_result = test_root_endpoint()
    
    # Authentication flow only if user wants to
    auth_result = False
    proceed = input("\n🔐 Do you want to test the complete OAuth flow? (y/n): ").lower()
    if proceed == 'y':
        auth_result = test_auth_flow()
    else:
        print("Skipping OAuth test")
    
    # Gmail API tests - only if auth succeeded
    if auth_result:
        watch_result = test_gmail_watch()
        process_result = test_process_history()
        
        # Only test stop if watch succeeded
        if watch_result:
            stop_result = test_stop_watch()
        else:
            stop_result = False
            print("⚠️ Skipping stop watch test as watch setup failed")
        
        renew_result = test_renew_watches()
        webhook_result = test_webhook()
    else:
        watch_result = process_result = stop_result = renew_result = webhook_result = False
        print("⚠️ Skipping Gmail API tests as authentication failed or was skipped")
    
    # Print summary
    print("\n" + "=" * 80)
    print("📊 Test Results Summary")
    print("=" * 80)
    print(f"✓ Root Endpoint:        {'✅ Pass' if root_result else '❌ Fail'}")
    print(f"✓ Authentication:       {'✅ Pass' if auth_result else '⚠️ Skipped' if proceed != 'y' else '❌ Fail'}")
    
    if auth_result:
        print(f"✓ Gmail Watch:          {'✅ Pass' if watch_result else '❌ Fail'}")
        print(f"✓ Process History:      {'✅ Pass' if process_result else '❌ Fail'}")
        print(f"✓ Stop Watch:           {'✅ Pass' if stop_result else '❌ Fail'}")
        print(f"✓ Renew Watches:        {'✅ Pass' if renew_result else '❌ Fail'}")
        print(f"✓ Webhook:              {'✅ Pass' if webhook_result else '❌ Fail'}")
    
    print("=" * 80)

if __name__ == "__main__":
    print("""
╭─────────────────────────────────────────────────╮
│         EmailBot API Test Suite                 │
│                                                 │
│  Make sure your FastAPI server is running at:   │
│  http://localhost:8000                          │
╰─────────────────────────────────────────────────╯
    """)
    
    start_server = input("Is your FastAPI server running? (y/n): ").lower()
    if start_server != 'y':
        print("Please start your FastAPI server first with:")
        print("cd backend && uvicorn main:app --reload")
    else:
        run_all_tests() 