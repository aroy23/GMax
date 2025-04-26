import os
import json
from typing import Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from fastapi import HTTPException

from config import GMAIL_SCOPES, CLIENT_SECRET_FILE, TOKEN_FILE

def get_credentials(user_id: str, token_data: Optional[Dict] = None) -> Credentials:
    """
    Get or refresh user credentials for Gmail API
    
    Args:
        user_id: The unique identifier for the user
        token_data: Optional cached token data
        
    Returns:
        Valid credentials object for API calls
    """
    creds = None
    
    # If we have token data in memory or database, use it
    if token_data:
        creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
    # Check if we have a local token file for this user
    elif os.path.exists(f"{user_id}_{TOKEN_FILE}"):
        with open(f"{user_id}_{TOKEN_FILE}", 'r') as token:
            creds = Credentials.from_authorized_user_info(json.load(token), GMAIL_SCOPES)
    
    # If credentials don't exist or are invalid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh the token
            creds.refresh(Request())
            # Save the refreshed credentials
            with open(f"{user_id}_{TOKEN_FILE}", 'w') as token:
                token.write(creds.to_json())
            return creds
        else:
            # Need to get new credentials via OAuth flow
            raise HTTPException(
                status_code=401, 
                detail="Authentication required",
                headers={"WWW-Authenticate": "OAuth2"}
            )
    
    return creds

def start_oauth_flow(redirect_uri: str) -> str:
    """
    Start the OAuth flow by generating an authorization URL
    
    Args:
        redirect_uri: The callback URL after authorization
        
    Returns:
        Authorization URL to redirect the user to
    """
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE, 
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri
        )
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth flow error: {str(e)}")

def complete_oauth_flow(code: str, redirect_uri: str, user_id: str) -> Dict:
    """
    Complete the OAuth flow with the received authorization code
    
    Args:
        code: The authorization code from Google
        redirect_uri: The callback URL after authorization
        user_id: The unique identifier for the user
        
    Returns:
        User token data for the authenticated user
    """
    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save credentials to file
        token_data = json.loads(creds.to_json())
        with open(f"{user_id}_{TOKEN_FILE}", 'w') as token:
            json.dump(token_data, token)
            
        return token_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth completion error: {str(e)}") 