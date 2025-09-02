"""
User session management for OAuth-authenticated users
Handles in-memory storage of user sessions, tokens, and session validation
"""

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Set
from dataclasses import dataclass, field

from models import UserInfo, OAuthTokens, AuthStatus, AuthStatusResponse
from oauth_service import get_oauth_service
from user_database import get_user_database


@dataclass
class UserSession:
    """
    Represents an active user session
    """
    session_id: str
    user_info: UserInfo
    tokens: OAuthTokens
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    gmail_service: Optional[any] = field(default=None, init=False)
    
    def is_expired(self, session_timeout: timedelta = timedelta(hours=24)) -> bool:
        """Check if session is expired based on last access time"""
        return datetime.now() - self.last_accessed > session_timeout
    
    def is_token_expired(self) -> bool:
        """Check if OAuth token is expired"""
        if not self.tokens.expires_at:
            return False
        return datetime.now() >= self.tokens.expires_at
    
    def refresh_access(self):
        """Update last accessed time"""
        self.last_accessed = datetime.now()


class UserSessionManager:
    """
    Manages user sessions and OAuth tokens in memory
    """
    
    def __init__(self, session_timeout_hours: int = 24, cleanup_interval_minutes: int = 60):
        """
        Initialize session manager
        
        Args:
            session_timeout_hours: Hours before session expires
            cleanup_interval_minutes: Minutes between cleanup runs
        """
        self.sessions: Dict[str, UserSession] = {}
        self.user_to_session: Dict[str, str] = {}  # user_id -> session_id mapping
        self.session_timeout = timedelta(hours=session_timeout_hours)
        self.cleanup_interval = timedelta(minutes=cleanup_interval_minutes)
        self.oauth_service = get_oauth_service()
        self.user_database = None  # Will be initialized async
        
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        print(f"✅ User session manager initialized (timeout: {session_timeout_hours}h)")
    
    async def create_session(self, tokens: OAuthTokens, user_info: UserInfo, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
        """
        Create a new user session
        
        Args:
            tokens: OAuth tokens for the user
            user_info: User information from Google
            user_agent: User agent string for tracking
            ip_address: IP address for tracking
            
        Returns:
            Session ID string
        """
        # Initialize database if not already done
        if self.user_database is None:
            self.user_database = await get_user_database()
        
        # Generate unique session ID
        session_id = secrets.token_urlsafe(32)
        
        # Remove any existing session for this user
        await self.remove_user_session(user_info.id)
        
        # Create new session
        session = UserSession(
            session_id=session_id,
            user_info=user_info,
            tokens=tokens
        )
        
        # Store session in memory
        self.sessions[session_id] = session
        self.user_to_session[user_info.id] = session_id
        
        # Store user info and login in database
        try:
            await self.user_database.create_or_update_user(user_info)
            await self.user_database.record_login(user_info.id, session_id, user_agent, ip_address)
            print(f"✅ Created session for user: {user_info.email} (session: {session_id[:8]}...) - recorded in database")
        except Exception as e:
            print(f"⚠️ Failed to record login in database: {e}")
            print(f"✅ Created session for user: {user_info.email} (session: {session_id[:8]}...) - in-memory only")
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[UserSession]:
        """
        Get user session by session ID
        
        Args:
            session_id: Session ID to lookup
            
        Returns:
            UserSession if found and valid, None otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Check if session is expired
        if session.is_expired(self.session_timeout):
            await self.remove_session(session_id)
            return None
        
        # Check if tokens need refresh
        if session.is_token_expired() and session.tokens.refresh_token:
            try:
                # Attempt to refresh tokens
                new_tokens = self.oauth_service.refresh_tokens(session.tokens.refresh_token)
                session.tokens = new_tokens
                print(f"✅ Refreshed tokens for session: {session_id[:8]}...")
            except Exception as e:
                print(f"❌ Failed to refresh tokens for session {session_id[:8]}...: {e}")
                await self.remove_session(session_id)
                return None
        
        # Update last accessed time
        session.refresh_access()
        
        return session
    
    async def get_session_by_user_id(self, user_id: str) -> Optional[UserSession]:
        """
        Get user session by user ID
        
        Args:
            user_id: Google user ID
            
        Returns:
            UserSession if found and valid, None otherwise
        """
        session_id = self.user_to_session.get(user_id)
        if not session_id:
            return None
        
        return await self.get_session(session_id)
    
    async def validate_session(self, session_id: str) -> AuthStatusResponse:
        """
        Validate a session and return auth status
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            AuthStatusResponse with current status
        """
        session = await self.get_session(session_id)
        
        if not session:
            return AuthStatusResponse(
                status=AuthStatus.UNAUTHENTICATED,
                user=None,
                expires_at=None,
                scopes=[]
            )
        
        # Validate tokens with OAuth service
        token_status = self.oauth_service.validate_tokens(session.tokens)
        
        if token_status != AuthStatus.AUTHENTICATED:
            await self.remove_session(session_id)
            return AuthStatusResponse(
                status=token_status,
                user=None,
                expires_at=None,
                scopes=[]
            )
        
        return AuthStatusResponse(
            status=AuthStatus.AUTHENTICATED,
            user=session.user_info,
            expires_at=session.tokens.expires_at,
            scopes=session.tokens.scopes
        )
    
    async def get_gmail_service(self, session_id: str):
        """
        Get Gmail API service for a session
        
        Args:
            session_id: Session ID
            
        Returns:
            Gmail API service object or None if session invalid
        """
        session = await self.get_session(session_id)
        if not session:
            return None
        
        # Create Gmail service if not cached
        if not session.gmail_service:
            try:
                session.gmail_service = self.oauth_service.create_gmail_service(session.tokens)
            except Exception as e:
                print(f"❌ Failed to create Gmail service for session {session_id[:8]}...: {e}")
                return None
        
        return session.gmail_service
    
    async def remove_session(self, session_id: str) -> bool:
        """
        Remove a user session
        
        Args:
            session_id: Session ID to remove
            
        Returns:
            True if session was removed, False if not found
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Remove from both mappings
        self.sessions.pop(session_id, None)
        self.user_to_session.pop(session.user_info.id, None)
        
        print(f"✅ Removed session: {session_id[:8]}... for user: {session.user_info.email}")
        
        return True
    
    async def remove_user_session(self, user_id: str) -> bool:
        """
        Remove session for a specific user
        
        Args:
            user_id: Google user ID
            
        Returns:
            True if session was removed, False if not found
        """
        session_id = self.user_to_session.get(user_id)
        if not session_id:
            return False
        
        return await self.remove_session(session_id)
    
    async def logout_session(self, session_id: str, revoke_tokens: bool = True, emails_processed: int = 0) -> bool:
        """
        Logout a user session
        
        Args:
            session_id: Session ID to logout
            revoke_tokens: Whether to revoke OAuth tokens with Google
            emails_processed: Number of emails processed in this session
            
        Returns:
            True if successful, False otherwise
        """
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        # Record logout in database
        if self.user_database:
            try:
                await self.user_database.record_logout(session_id, emails_processed)
            except Exception as e:
                print(f"⚠️ Failed to record logout in database: {e}")
        
        # Optionally revoke tokens with Google
        if revoke_tokens:
            try:
                self.oauth_service.revoke_tokens(session.tokens)
            except Exception as e:
                print(f"⚠️ Failed to revoke tokens during logout: {e}")
        
        # Remove session
        await self.remove_session(session_id)
        
        return True
    
    def get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        return len(self.sessions)
    
    def get_active_users(self) -> Set[str]:
        """Get set of active user IDs"""
        return set(self.user_to_session.keys())
    
    async def _periodic_cleanup(self):
        """
        Periodic cleanup of expired sessions
        """
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval.total_seconds())
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ Error in session cleanup: {e}")
    
    async def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if session.is_expired(self.session_timeout):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            await self.remove_session(session_id)
        
        if expired_sessions:
            print(f"🧹 Cleaned up {len(expired_sessions)} expired sessions")
    
    async def shutdown(self):
        """Shutdown session manager and cleanup"""
        if hasattr(self, '_cleanup_task'):
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close database connection
        if self.user_database:
            await self.user_database.close()
        
        print("👋 User session manager shutdown")


# Global session manager instance
_session_manager: Optional[UserSessionManager] = None


def get_session_manager() -> UserSessionManager:
    """
    Get global session manager instance
    
    Returns:
        UserSessionManager singleton instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = UserSessionManager()
    return _session_manager


async def shutdown_session_manager():
    """Shutdown global session manager"""
    global _session_manager
    if _session_manager:
        await _session_manager.shutdown()
        _session_manager = None
