import os
import json
from typing import Dict, Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from fastapi import HTTPException
import logging

from config import GMAIL_SCOPES, CLIENT_SECRET_FILE, TOKEN_FILE

logger = logging.getLogger(__name__)

def get_credentials(user_id: str, token_data: Optional[Dict] = None) -> Credentials:
    """
    Get or refresh user credentials for Gmail API
    
    Args:
        user_id: The unique identifier for the user (typically email)
        token_data: Optional cached token data
        
    Returns:
        Valid credentials object for API calls
    """
    creds = None
    
    # Ensure user_id is clean (no special characters in filename)
    clean_user_id = user_id.replace('/', '_').replace('\\', '_')
    token_filename = f"{clean_user_id}_{TOKEN_FILE}"
    
    # If we have token data in memory or database, use it
    if token_data:
        try:
            logger.info(f"Creating credentials from provided token data for {user_id}")
            creds = Credentials.from_authorized_user_info(token_data, GMAIL_SCOPES)
        except Exception as e:
            logger.error(f"Error creating credentials from token data: {e}")
            # If there's an issue with the token data, we'll treat it as missing
            creds = None
            
    # Check if we have a local token file for this user
    elif os.path.exists(token_filename):
        try:
            logger.info(f"Loading credentials from token file for {user_id}")
            with open(token_filename, 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), GMAIL_SCOPES)
        except Exception as e:
            logger.error(f"Error loading credentials from token file: {e}")
            # If there's an issue with the token file, delete it
            try:
                os.remove(token_filename)
                logger.info(f"Removed invalid token file for {user_id}")
            except:
                pass
            creds = None
    
    # If no credentials found with user_id, try to list all tokens and find by email
    if not creds:
        try:
            # List all token files
            token_files = [f for f in os.listdir('.') if f.endswith(TOKEN_FILE)]
            for tf in token_files:
                try:
                    with open(tf, 'r') as f:
                        token_content = json.load(f)
                        # Check if this token belongs to our user
                        if token_content.get('email') == user_id:
                            logger.info(f"Found token file by email: {tf}")
                            creds = Credentials.from_authorized_user_info(token_content, GMAIL_SCOPES)
                            if creds:
                                break
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error searching for token files: {e}")
    
    # If credentials don't exist or are invalid
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh the token
            try:
                logger.info(f"Refreshing token for {user_id}")
                creds.refresh(Request())
                
                # Save the refreshed credentials
                logger.info(f"Saving refreshed token for {user_id}")
                token_data = json.loads(creds.to_json())
                
                # Ensure email is stored in token data
                if 'email' not in token_data:
                    token_data['email'] = user_id
                
                with open(token_filename, 'w') as token:
                    json.dump(token_data, token)
                return creds
            except Exception as e:
                logger.error(f"Error refreshing token for {user_id}: {e}")
                
                # If it's an invalid_scope error, we need to clear the token and request re-auth
                if "invalid_scope" in str(e):
                    logger.warning(f"Invalid scope error for {user_id}. This is likely due to scope changes.")
                    logger.warning("Clearing token and requesting re-authentication.")
                    
                    # Delete the token file if it exists
                    if os.path.exists(token_filename):
                        try:
                            os.remove(token_filename)
                            logger.info(f"Removed token file for {user_id} due to scope mismatch")
                        except Exception as del_error:
                            logger.error(f"Error deleting token file: {del_error}")
                
                # Need to get new credentials
                raise HTTPException(
                    status_code=401, 
                    detail=f"Authentication required due to token error: {str(e)}",
                    headers={"WWW-Authenticate": "OAuth2"}
                )
        else:
            # Need to get new credentials via OAuth flow
            logger.info(f"No valid credentials for {user_id}, authentication required")
            raise HTTPException(
                status_code=401, 
                detail="Authentication required",
                headers={"WWW-Authenticate": "OAuth2"}
            )
    
    logger.info(f"Successfully obtained valid credentials for {user_id}")
    return creds

def start_oauth_flow(redirect_uri: str, state: str = None, force_consent: bool = True) -> str:
    """
    Start the OAuth flow by generating an authorization URL
    
    Args:
        redirect_uri: The callback URL after authorization
        state: Optional state parameter to track the user through the flow
        force_consent: Whether to force consent screen, even if the user has already granted access
        
    Returns:
        Authorization URL to redirect the user to
    """
    try:
        logger.info(f"Starting OAuth flow with redirect_uri: {redirect_uri}")
        
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE, 
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Include state if provided
        extra_params = {}
        if state:
            extra_params['state'] = state
            logger.info(f"Including state parameter: {state}")
            
        # Set prompt parameter based on force_consent
        prompt = 'consent' if force_consent else 'select_account'
        logger.info(f"Using prompt='{prompt}' for authorization")
            
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt=prompt,
            **extra_params
        )
        
        logger.info(f"Generated auth URL: {auth_url[:100]}...")
        return auth_url
    except Exception as e:
        logger.error(f"OAuth flow error: {str(e)}")
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
        logger.info(f"Completing OAuth flow for user: {user_id} with redirect_uri: {redirect_uri}")
        
        # Handle case where redirect_uri might have been modified (e.g., additional parameters)
        # Strip any query parameters to ensure it matches what Google expects
        if "?" in redirect_uri:
            base_redirect_uri = redirect_uri.split("?")[0]
            logger.info(f"Stripping query parameters from redirect_uri: {base_redirect_uri}")
            redirect_uri = base_redirect_uri
            
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=GMAIL_SCOPES,
            redirect_uri=redirect_uri
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        
        # Save credentials to file - use email address as token identifier
        token_data = json.loads(creds.to_json())
        
        # Always try to extract the email from the ID token
        email = None
        if hasattr(creds, 'id_token') and creds.id_token:
            try:
                from google.oauth2 import id_token
                from google.auth.transport import requests as google_requests
                info = id_token.verify_oauth2_token(
                    creds.id_token, google_requests.Request(), None)
                if 'email' in info:
                    email = info['email']
                    logger.info(f"Using email from token: {email}")
            except Exception as e:
                logger.warning(f"Could not extract email from id_token: {e}")
        
        # If we couldn't extract email from token, fall back to user_id
        if not email:
            email = user_id
            logger.info(f"Using provided user_id as identifier: {email}")
        
        # Store the email in the token data for reference
        token_data['email'] = email
        
        # Use a standardized filename format with the email
        token_file = f"{email}_{TOKEN_FILE}"
        
        # Remove any existing token files for this user
        if os.path.exists(token_file):
            try:
                os.remove(token_file)
                logger.info(f"Removed existing token file for {email}")
            except Exception as e:
                logger.warning(f"Could not remove existing token file: {e}")
        
        # Save the new token
        with open(token_file, 'w') as token:
            json.dump(token_data, token)
            logger.info(f"Saved new token file for {email}")
            
        return token_data
    except Exception as e:
        logger.error(f"OAuth completion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OAuth completion error: {str(e)}")

def revoke_token(token: str) -> bool:
    """
    Revoke an OAuth token to force re-authentication
    
    Args:
        token: The access token to revoke
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Attempting to revoke token")
        import httpx
        response = httpx.post(
            "https://oauth2.googleapis.com/revoke",
            params={"token": token},
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            logger.info("Token successfully revoked")
            return True
        else:
            logger.error(f"Error revoking token: {response.status_code} {response.text}")
            return False
    except Exception as e:
        logger.error(f"Exception revoking token: {e}")
        return False 