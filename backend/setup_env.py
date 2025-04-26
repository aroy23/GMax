#!/usr/bin/env python
"""
Setup script to create a proper .env file for the EmailBot backend
"""
import os
import sys
import shutil

def main():
    """Main function to set up .env file"""
    print("EmailBot Environment Setup")
    print("==========================\n")
    
    # Check if .env file already exists
    if os.path.exists(".env"):
        overwrite = input(".env file already exists. Overwrite? (y/n): ").lower()
        if overwrite != 'y':
            print("Setup canceled.")
            return
    
    # Check if env_example exists
    if not os.path.exists("env_example"):
        print("Error: env_example file not found. Please make sure you're in the backend directory.")
        return
        
    # Create a copy of env_example as .env
    shutil.copy("env_example", ".env")
    print("Created .env file from template.\n")
    
    # Now prompt for values
    print("Please provide the following values:")
    
    # Google Cloud Project ID
    project_id = input("Google Cloud Project ID: ").strip()
    if project_id:
        update_env_var("GOOGLE_CLOUD_PROJECT_ID", project_id)
    
    # Google Client Secret File
    client_secret = input("Path to client_secret.json file (press Enter for default 'client_secret.json'): ").strip()
    if client_secret:
        update_env_var("GOOGLE_CLIENT_SECRET_FILE", client_secret)
    
    # OAuth Redirect URI
    redirect_uri = input("OAuth Redirect URI (press Enter for default 'http://localhost:3000/auth/callback'): ").strip()
    if redirect_uri:
        update_env_var("OAUTH_REDIRECT_URI", redirect_uri)
    
    # Supabase URL
    supabase_url = input("Supabase URL: ").strip()
    if supabase_url:
        update_env_var("SUPABASE_URL", supabase_url)
    
    # Supabase Key
    supabase_key = input("Supabase Anon Key: ").strip()
    if supabase_key:
        update_env_var("SUPABASE_KEY", supabase_key)
    
    print("\nEnvironment setup complete!")
    print("You can edit the .env file directly to change these values later.")
    
    # Google Cloud credentials
    print("\nFor Google Cloud credentials, you'll need to either:")
    print("1. Set GOOGLE_APPLICATION_CREDENTIALS environment variable to a service account key file")
    print("2. Run 'gcloud auth application-default login' if using gcloud")
    print("\nYou can now run the application with: uvicorn main:app --reload")

def update_env_var(var_name, value):
    """Update a variable in the .env file"""
    with open(".env", "r") as f:
        lines = f.readlines()
    
    with open(".env", "w") as f:
        for line in lines:
            if line.startswith(f"{var_name}="):
                f.write(f"{var_name}={value}\n")
            else:
                f.write(line)

if __name__ == "__main__":
    # Check if we're in the backend directory
    if not os.path.exists("main.py"):
        print("Error: This script should be run from the backend directory.")
        sys.exit(1)
    
    main() 