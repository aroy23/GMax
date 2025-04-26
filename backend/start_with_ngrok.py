import os
import subprocess
import sys
import json
import time
import signal
import requests
from urllib.parse import urlparse

def is_ngrok_running():
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        return response.status_code == 200
    except requests.RequestException:
        return False

def get_ngrok_public_url():
    try:
        response = requests.get("http://127.0.0.1:4040/api/tunnels")
        data = response.json()
        for tunnel in data["tunnels"]:
            if tunnel["proto"] == "https":
                return tunnel["public_url"]
        return None
    except requests.RequestException:
        return None

def start_ngrok(port):
    """Start ngrok tunnel to the specified port"""
    ngrok_command = ["ngrok", "http", str(port)]
    return subprocess.Popen(
        ngrok_command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def start_fastapi_server(port, base_url):
    """Start the FastAPI server with the specified base URL"""
    env = os.environ.copy()
    env["BASE_URL"] = base_url
    fastapi_command = [sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", str(port)]
    return subprocess.Popen(
        fastapi_command,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        env=env
    )

def handle_shutdown(signum, frame):
    """Handle shutdown gracefully"""
    print("\nShutting down server and ngrok...")
    if "fastapi_process" in globals() and fastapi_process:
        fastapi_process.terminate()
    if "ngrok_process" in globals() and ngrok_process:
        ngrok_process.terminate()
    sys.exit(0)

if __name__ == "__main__":
    port = 8000
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)
    
    # Check if ngrok is already running
    if not is_ngrok_running():
        print("Starting ngrok tunnel...")
        ngrok_process = start_ngrok(port)
    else:
        print("ngrok is already running.")
        ngrok_process = None
    
    # Wait for ngrok to start up
    max_attempts = 10
    attempts = 0
    ngrok_url = None
    
    while attempts < max_attempts:
        attempts += 1
        print(f"Waiting for ngrok to start (attempt {attempts}/{max_attempts})...")
        time.sleep(1)
        ngrok_url = get_ngrok_public_url()
        if ngrok_url:
            break
    
    if not ngrok_url:
        print("Failed to get ngrok public URL. Please check if ngrok is running correctly.")
        if ngrok_process:
            ngrok_process.terminate()
        sys.exit(1)
    
    print(f"ngrok tunnel established at: {ngrok_url}")
    
    # Start FastAPI server with the ngrok URL
    print(f"Starting FastAPI server with BASE_URL={ngrok_url}")
    fastapi_process = start_fastapi_server(port, ngrok_url)
    
    try:
        # Keep the script running
        fastapi_process.wait()
    except KeyboardInterrupt:
        handle_shutdown(None, None) 