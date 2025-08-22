"""
OAuth service for Google Gmail integration
Handles OAuth flow, token management, and Gmail API client creation
"""

import os
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from models import UserInfo, OAuthTokens, AuthStatus, LoginResponse, AuthStatusResponse


class OAuthService:
    """
    Handles Google OAuth 2.0 flow for Gmail access
    """
    
    # Gmail API scopes required for email management
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'openid'  # Add openid scope to match what Google returns
    ]
    
    def __init__(self, credentials_file: str = "credentials.json"):
        """
        Initialize OAuth service with Google credentials
        
        Args:
            credentials_file: Path to Google OAuth credentials JSON file
        """
        self.credentials_file = credentials_file
        self._load_client_config()
        
    def _load_client_config(self):
        """Load OAuth client configuration from credentials file"""
        try:
            with open(self.credentials_file, 'r') as f:
                client_config = json.load(f)
                
            # Extract client info from the credentials file
            if 'web' in client_config:
                self.client_config = client_config['web']
            elif 'installed' in client_config:
                self.client_config = client_config['installed']
            else:
                raise ValueError("Invalid credentials file format")
                
            self.client_id = self.client_config['client_id']
            self.client_secret = self.client_config['client_secret']
            
            print(f"✅ Loaded OAuth client configuration")
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")
        except Exception as e:
            raise ValueError(f"Failed to load OAuth credentials: {e}")
    
    def generate_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> LoginResponse:
        """
        Generate OAuth authorization URL for user consent
        
        Args:
            redirect_uri: Where to redirect after OAuth consent
            state: Optional state parameter for CSRF protection
            
        Returns:
            LoginResponse with authorization URL and state
        """
        if not state:
            state = secrets.token_urlsafe(32)
            
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                client_config={'web': self.client_config},
                scopes=self.SCOPES
            )
            flow.redirect_uri = redirect_uri
            
            # Generate authorization URL
            authorization_url, _ = flow.authorization_url(
                access_type='offline',  # Request refresh token
                include_granted_scopes='true',
                state=state,
                prompt='consent'  # Force consent screen to get refresh token
            )
            
            return LoginResponse(
                authorization_url=authorization_url,
                state=state
            )
            
        except Exception as e:
            raise ValueError(f"Failed to generate authorization URL: {e}")
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str, state: Optional[str] = None) -> Tuple[OAuthTokens, UserInfo]:
        """
        Exchange authorization code for access tokens and user info
        
        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Redirect URI used in authorization request
            state: State parameter for verification
            
        Returns:
            Tuple of (OAuthTokens, UserInfo)
        """
        try:
            # Create OAuth flow
            flow = Flow.from_client_config(
                client_config={'web': self.client_config},
                scopes=self.SCOPES
            )
            flow.redirect_uri = redirect_uri
            
            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Create token object
            expires_at = None
            if credentials.expiry:
                expires_at = credentials.expiry
            
            # Handle scope variations - Google may return scopes in different order
            actual_scopes = list(credentials.scopes) if credentials.scopes else self.SCOPES
            
            tokens = OAuthTokens(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token,
                token_type="Bearer",
                expires_at=expires_at,
                scopes=actual_scopes
            )
            
            # Get user info
            user_info = self._get_user_info(credentials)
            
            print(f"✅ Successfully exchanged OAuth code for tokens for user: {user_info.email}")
            
            return tokens, user_info
            
        except Exception as e:
            raise ValueError(f"Failed to exchange authorization code: {e}")
    
    def refresh_tokens(self, refresh_token: str) -> OAuthTokens:
        """
        Refresh access token using refresh token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New OAuthTokens with refreshed access token
        """
        try:
            # Create credentials object with refresh token
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri=self.client_config['token_uri'],
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            # Create new token object
            expires_at = None
            if credentials.expiry:
                expires_at = credentials.expiry
            
            # Handle scope variations - use actual scopes returned by Google
            actual_scopes = list(credentials.scopes) if credentials.scopes else self.SCOPES
            
            tokens = OAuthTokens(
                access_token=credentials.token,
                refresh_token=credentials.refresh_token or refresh_token,
                token_type="Bearer",
                expires_at=expires_at,
                scopes=actual_scopes
            )
            
            print(f"✅ Successfully refreshed OAuth tokens")
            
            return tokens
            
        except Exception as e:
            raise ValueError(f"Failed to refresh tokens: {e}")
    
    def validate_tokens(self, tokens: OAuthTokens) -> AuthStatus:
        """
        Validate if tokens are still valid
        
        Args:
            tokens: OAuth tokens to validate
            
        Returns:
            AuthStatus indicating token validity
        """
        try:
            # Check if token is expired
            if tokens.expires_at and tokens.expires_at <= datetime.now():
                return AuthStatus.EXPIRED
            
            # Try to use the token to make a simple API call
            credentials = Credentials(
                token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_uri=self.client_config['token_uri'],
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=tokens.scopes
            )
            
            # Test with a simple Gmail API call
            service = build('gmail', 'v1', credentials=credentials)
            service.users().getProfile(userId='me').execute()
            
            return AuthStatus.AUTHENTICATED
            
        except HttpError as e:
            if e.resp.status in [401, 403]:
                return AuthStatus.EXPIRED
            return AuthStatus.ERROR
        except Exception:
            return AuthStatus.ERROR
    
    def create_gmail_service(self, tokens: OAuthTokens):
        """
        Create authenticated Gmail API service
        
        Args:
            tokens: Valid OAuth tokens
            
        Returns:
            Authenticated Gmail API service object
        """
        try:
            credentials = Credentials(
                token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_uri=self.client_config['token_uri'],
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=tokens.scopes
            )
            
            service = build('gmail', 'v1', credentials=credentials)
            return service
            
        except Exception as e:
            raise ValueError(f"Failed to create Gmail service: {e}")
    
    def _get_user_info(self, credentials: Credentials) -> UserInfo:
        """
        Get user information from Google API
        
        Args:
            credentials: Valid OAuth credentials
            
        Returns:
            UserInfo object with user details
        """
        try:
            # Get user info from Google API
            service = build('oauth2', 'v2', credentials=credentials)
            user_data = service.userinfo().get().execute()
            
            return UserInfo(
                id=user_data['id'],
                email=user_data['email'],
                name=user_data.get('name'),
                picture=user_data.get('picture'),
                verified_email=user_data.get('verified_email', False)
            )
            
        except Exception as e:
            raise ValueError(f"Failed to get user info: {e}")
    
    def revoke_tokens(self, tokens: OAuthTokens) -> bool:
        """
        Revoke OAuth tokens (logout)
        
        Args:
            tokens: Tokens to revoke
            
        Returns:
            True if successful, False otherwise
        """
        try:
            credentials = Credentials(
                token=tokens.access_token,
                refresh_token=tokens.refresh_token,
                token_uri=self.client_config['token_uri'],
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=tokens.scopes
            )
            
            # Revoke the tokens
            credentials.revoke(Request())
            
            print(f"✅ Successfully revoked OAuth tokens")
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to revoke tokens: {e}")
            return False


# Global OAuth service instance
_oauth_service: Optional[OAuthService] = None


def get_oauth_service() -> OAuthService:
    """
    Get global OAuth service instance
    
    Returns:
        OAuthService singleton instance
    """
    global _oauth_service
    if _oauth_service is None:
        _oauth_service = OAuthService()
    return _oauth_service


def create_gmail_client_from_tokens(tokens: OAuthTokens):
    """
    Helper function to create Gmail API client from tokens
    
    Args:
        tokens: Valid OAuth tokens
        
    Returns:
        Authenticated Gmail API service
    """
    oauth_service = get_oauth_service()
    return oauth_service.create_gmail_service(tokens)
