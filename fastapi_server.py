"""
FastAPI server for voice-driven email agent
Orchestrates extracted components and provides WebSocket interface for frontend
"""

import asyncio
import json
import os
import time
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Import our extracted services
from email_service import EmailManager, initialize_email_manager, extract_email_details
from gemini_service import (
    setup_mcp_connection, discover_gmail_tools, convert_mcp_to_gemini_tools,
    create_navigation_tools, create_gemini_session_config, cleanup_mcp_resources
)
from audio_bridge import WebSocketAudioBridge, create_gemini_session_with_websocket
from oauth_gmail_tools import create_oauth_gmail_tools, create_oauth_gmail_tool_executor
from models import (
    HealthCheckResponse, SessionInfoResponse, SessionConfig, SessionStatus,
    create_error_message, create_session_status_message, parse_websocket_message,
    MessageType, LoginRequest, LoginResponse, CallbackRequest, AuthStatusResponse, 
    LogoutResponse, UserInfo, OAuthTokens, AuthStatus
)
from oauth_service import get_oauth_service
from user_session import get_session_manager, shutdown_session_manager

# Global state for the application
class AppState:
    def __init__(self):
        self.mcp_app = None
        self.gmail_agent = None
        self.gemini_tools = []
        self.oauth_tool_executor = None  # OAuth Gmail tool executor
        self.current_session: Optional[Dict[str, Any]] = None
        self.is_initialized = False
        
    def reset_session(self):
        """Reset current session state"""
        self.current_session = None

# Global app state
app_state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan manager - handles startup and shutdown
    Initializes MCP connections on startup and cleans up on shutdown
    """
    print("🚀 Starting Email Voice Agent FastAPI Server...")
    
    try:
        # Initialize MCP and Gmail agent
        print("📡 Initializing MCP connection...")
        app_state.mcp_app, app_state.gmail_agent = await setup_mcp_connection()
        
        # Discover and convert tools
        print("🔧 Discovering Gmail tools...")
        mcp_tools = await discover_gmail_tools(app_state.gmail_agent)
        app_state.gemini_tools = convert_mcp_to_gemini_tools(mcp_tools)
        
        app_state.is_initialized = True
        print(f"✅ Server initialized with {len(app_state.gemini_tools)} Gmail tools")
        
        yield  # Server is running
        
    except Exception as e:
        print(f"❌ Failed to initialize server: {e}")
        raise
    
    finally:
        # Cleanup on shutdown
        print("🧹 Cleaning up resources...")
        if app_state.mcp_app or app_state.gmail_agent:
            await cleanup_mcp_resources(app_state.mcp_app, app_state.gmail_agent)
        await shutdown_session_manager()
        print("👋 Server shutdown complete")


# Create FastAPI app with lifespan manager
app = FastAPI(
    title="Email Voice Agent API",
    description="Voice-driven Gmail assistant with WebSocket audio streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware for Next.js frontend
# Note: Starlette's CORSMiddleware does not support wildcard patterns in allow_origins
# so we use allow_origin_regex to allow any Vercel deployment subdomain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js development
        "https://localhost:3000", # HTTPS local development
            "https://courieragent.ai",  # Production custom domain
        "https://www.courieragent.ai",  # WWW subdomain
        "https://courier-black.vercel.app",  # Legacy production alias
    ],
    allow_origin_regex=r"^https://.*\.vercel\.app$",  # Allow all Vercel deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "Email Voice Agent API",
        "status": "running",
        "initialized": app_state.is_initialized,
        "docs": "/docs",
        "websocket": "/ws/voice-session"
    }


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint for monitoring"""
    services = {
        "mcp": app_state.mcp_app is not None,
        "gmail_agent": app_state.gmail_agent is not None,
        "gemini_tools": len(app_state.gemini_tools) > 0
    }
    
    return HealthCheckResponse(
        status="healthy" if app_state.is_initialized else "initializing",
        timestamp=time.time(),
        services=services
    )


# OAuth Authentication Helper
security = HTTPBearer(auto_error=False)

async def get_current_session(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    """
    Extract session ID from Authorization header
    Returns session ID if valid, None otherwise
    """
    if not credentials:
        return None
    
    # Session ID is passed as Bearer token
    return credentials.credentials


@app.get("/session/status", response_model=SessionInfoResponse)
async def get_session_status(session_id: Optional[str] = Depends(get_current_session)):
    """Get current session status - requires authentication"""
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
        
    # Validate session
    try:
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        
        if auth_status.status != AuthStatus.AUTHENTICATED:
            raise HTTPException(status_code=401, detail="Invalid session")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")
    
    if not app_state.current_session:
        return SessionInfoResponse(
            active=False,
            status=SessionStatus.COMPLETED
        )
    
    return SessionInfoResponse(
        active=True,
        status=app_state.current_session.get("status", SessionStatus.ACTIVE),
        current_email=app_state.current_session.get("current_email"),
        progress=app_state.current_session.get("progress"),
        started_at=app_state.current_session.get("started_at")
    )


# OAuth Authentication Endpoints
@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest, http_request: Request):
    """
    Initiate OAuth login flow
    Returns authorization URL for user to visit
    """
    try:
        oauth_service = get_oauth_service()
        
        # Use backend callback URL instead of frontend
        # Use environment variable or fallback to localhost for development
        default_redirect_uri = oauth_service.redirect_uri or "http://localhost:8000/auth/callback"
        redirect_uri = request.redirect_uri or default_redirect_uri
        
        # Encode the frontend origin in the state parameter so we can redirect back to the correct domain
        import base64
        import json
        
        # Get the origin from the request headers
        origin = http_request.headers.get("origin")
        if not origin:
            # Fallback to environment variable or localhost
            origin = os.getenv("FRONTEND_URL", "https://courieragent.ai")
        
        # Create state with both user state and frontend origin
        state_data = {
            "user_state": request.state,
            "frontend_origin": origin
        }
        encoded_state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        login_response = oauth_service.generate_authorization_url(
            redirect_uri=redirect_uri,
            state=encoded_state
        )
        
        return login_response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate login: {str(e)}")


@app.get("/auth/callback")
async def oauth_callback(
    code: str = None,
    state: str = None,
    error: str = None
):
    """
    Handle OAuth callback from Google
    Exchange authorization code for tokens and create user session
    """
    try:
        if error:
            raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
        
        if not code:
            raise HTTPException(status_code=400, detail="Authorization code required")
        
        oauth_service = get_oauth_service()
        session_manager = get_session_manager()
        
        # Exchange code for tokens - use the same redirect URI that was used in authorization
        # The frontend always sends https://courier.fly.dev/auth/callback, so use that consistently
        default_redirect_uri = oauth_service.redirect_uri or "http://localhost:8000/auth/callback"
        redirect_uri = default_redirect_uri
        tokens, user_info = oauth_service.exchange_code_for_tokens(
            code=code,
            redirect_uri=redirect_uri,
            state=state
        )
        
        # Create user session with tracking info
        session_id = await session_manager.create_session(tokens, user_info)
        print(f"🔑 Created new session ID: {session_id[:8]}... for user: {user_info.email}")
        
        # Decode the state to get the frontend origin
        import base64
        import json
        
        frontend_url = os.getenv("FRONTEND_URL", "https://courieragent.ai")  # Default fallback
        
        if state:
            try:
                # Decode the state parameter to extract frontend origin
                state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
                frontend_url = state_data.get("frontend_origin", frontend_url)
            except Exception as e:
                print(f"⚠️ Failed to decode state parameter: {e}, using default frontend URL")
        
        # Redirect to the correct frontend origin with session info
        redirect_url = f"{frontend_url}/auth/callback?session_id={session_id}&success=true"
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")


@app.get("/auth/status", response_model=AuthStatusResponse)
async def get_auth_status(session_id: Optional[str] = Depends(get_current_session)):
    """
    Check authentication status for current session
    """
    print(f"🔍 Auth status check - session_id: {session_id[:8] + '...' if session_id else 'None'}")
    
    if not session_id:
        print("❌ No session ID provided, returning unauthenticated")
        return AuthStatusResponse(
            status="unauthenticated",
            user=None,
            expires_at=None,
            scopes=[]
        )
    
    try:
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        print(f"✅ Auth validation result: {auth_status.status} for user: {auth_status.user.email if auth_status.user else 'None'}")
        return auth_status
        
    except Exception as e:
        print(f"❌ Auth status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check auth status: {str(e)}")


@app.post("/auth/logout", response_model=LogoutResponse)
async def logout(session_id: Optional[str] = Depends(get_current_session)):
    """
    Logout user and revoke tokens
    """
    if not session_id:
        return LogoutResponse(success=True, message="No active session")
    
    try:
        session_manager = get_session_manager()
        success = await session_manager.logout_session(session_id, revoke_tokens=True)
        
        return LogoutResponse(
            success=success,
            message="Successfully logged out" if success else "Logout failed"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Logout failed: {str(e)}")


@app.get("/auth/user")
async def get_user_info(session_id: Optional[str] = Depends(get_current_session)):
    """
    Get current authenticated user information
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        session_manager = get_session_manager()
        session = await session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        return {
            "user": session.user_info.dict(),
            "session_id": session_id,
            "expires_at": session.tokens.expires_at.isoformat() if session.tokens.expires_at else None,
            "scopes": session.tokens.scopes
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")


# Admin endpoints for user tracking
@app.get("/admin/users")
async def get_all_users(
    limit: Optional[int] = Query(50, description="Maximum number of users to return"),
    offset: int = Query(0, description="Number of users to skip"),
    session_id: Optional[str] = Depends(get_current_session)
):
    """
    Get all users with pagination (Admin endpoint)
    Requires authentication
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate session
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        
        if auth_status.status != AuthStatus.AUTHENTICATED:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get user database
        from user_database import get_user_database
        user_db = await get_user_database()
        
        # Get users
        users = await user_db.get_all_users(limit=limit, offset=offset)
        
        return {
            "users": [user.to_dict() for user in users],
            "total_returned": len(users),
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get users: {str(e)}")


@app.get("/admin/users/{user_id}")
async def get_user_details(
    user_id: str,
    session_id: Optional[str] = Depends(get_current_session)
):
    """
    Get detailed user information including login history
    Requires authentication
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate session
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        
        if auth_status.status != AuthStatus.AUTHENTICATED:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get user database
        from user_database import get_user_database
        user_db = await get_user_database()
        
        # Get user and login history
        user = await user_db.get_user(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        login_history = await user_db.get_user_login_history(user_id, limit=100)
        
        return {
            "user": user.to_dict(),
            "login_history": [login.to_dict() for login in login_history],
            "total_login_records": len(login_history)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user details: {str(e)}")


@app.get("/admin/statistics")
async def get_user_statistics(session_id: Optional[str] = Depends(get_current_session)):
    """
    Get overall user statistics
    Requires authentication
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate session
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        
        if auth_status.status != AuthStatus.AUTHENTICATED:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get user database
        from user_database import get_user_database
        user_db = await get_user_database()
        
        # Get statistics
        stats = await user_db.get_user_statistics()
        
        # Add current session info
        stats["current_active_sessions"] = session_manager.get_active_sessions_count()
        stats["current_active_users"] = list(session_manager.get_active_users())
        
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@app.post("/admin/cleanup")
async def cleanup_old_data(
    days: int = Query(90, description="Number of days to keep login history"),
    session_id: Optional[str] = Depends(get_current_session)
):
    """
    Clean up old login history records
    Requires authentication
    """
    if not session_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        # Validate session
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        
        if auth_status.status != AuthStatus.AUTHENTICATED:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Get user database
        from user_database import get_user_database
        user_db = await get_user_database()
        
        # Cleanup old data
        await user_db.cleanup_old_sessions(days=days)
        
        return {
            "success": True,
            "message": f"Cleaned up login history older than {days} days"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cleanup data: {str(e)}")


@app.websocket("/ws/voice-session")
async def websocket_voice_session(
    websocket: WebSocket,
    session_id: str = Query(..., description="OAuth session ID required for authentication")
):
    """
    Main WebSocket endpoint for voice-driven email processing
    Handles the complete email processing workflow with audio streaming
    Requires valid OAuth session for authentication
    """
    # Validate session before accepting WebSocket connection
    try:
        session_manager = get_session_manager()
        auth_status = await session_manager.validate_session(session_id)
        
        if auth_status.status != AuthStatus.AUTHENTICATED:
            print(f"🚫 WebSocket authentication failed: {auth_status.status}")
            await websocket.close(code=4001, reason="Authentication required")
            return
            
        print(f"🔐 WebSocket authenticated for user: {auth_status.user.email if auth_status.user else 'Unknown'}")
        
    except Exception as e:
        print(f"🚫 WebSocket authentication error: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    await websocket.accept()
    print(f"🔌 WebSocket connected (authenticated: {auth_status.user.email if auth_status.user else 'Unknown'})")
    
    if not app_state.is_initialized:
        await websocket.send_text(json.dumps(
            create_error_message("Server not initialized", recoverable=False).dict()
        ))
        await websocket.close()
        return
    
    email_manager = None
    nav_tools = None
    session_config = SessionConfig()
    
    try:
        # Send initial status - connected but not processing yet
        await websocket.send_text(json.dumps(
            create_session_status_message(SessionStatus.INITIALIZING, "Connected! Loading email count...").dict()
        ))
        
        # Fetch email count without starting processing
        print("📧 Fetching inbox email count...")
        
        # Get session and Gmail service for the authenticated session
        session = await session_manager.get_session(session_id)
        if not session:
            raise Exception("Invalid session")
            
        gmail_service = await session_manager.get_gmail_service(session_id)
        if not gmail_service:
            raise Exception("Failed to get Gmail service for session")
        
        # Use OAuth email manager instead of MCP
        from email_service_oauth import initialize_oauth_email_manager
        email_manager = await initialize_oauth_email_manager(
            gmail_service,
            user_id=session.user_info.id,
            query=session_config.email_query,
            max_results=session_config.max_results,
            auth_mode="oauth"
        )
        
        if email_manager.is_exhausted():
            await websocket.send_text(json.dumps(
                create_session_status_message(SessionStatus.COMPLETED, "No emails found in inbox").dict()
            ))
            return
        
        # Send ready status with email count - wait for user to start
        email_count = len(email_manager.emails)
        await websocket.send_text(json.dumps(
            create_session_status_message(
                SessionStatus.READY, 
                f"Ready! Found {email_count} emails in your inbox",
                progress={"current": 0, "total": email_count, "remaining": email_count}
            ).dict()
        ))
        
        print(f"✅ Ready to process {email_count} emails - waiting for user to start...")
        
        # Wait for start command from frontend
        while True:
            try:
                message = await websocket.receive_text()
                data = json.loads(message)
                if data.get("type") == "start_session":
                    print("🚀 User started voice session - beginning email processing...")
                    break
                elif data.get("type") == "stop_session":
                    print("🛑 User cancelled session")
                    return
            except Exception as e:
                print(f"⚠️ Error waiting for start command: {e}")
                break
        
        # Create navigation tools
        nav_tools = create_navigation_tools(email_manager)
        
        # Create Gmail tools based on authentication mode
        if gmail_service:
            # OAuth mode - create OAuth Gmail tools
            print("🔧 Using OAuth Gmail tools for authenticated session")
            oauth_gmail_tools = create_oauth_gmail_tools(gmail_service)
            complete_current_email_tool = nav_tools.get_complete_current_email_tool()
            gemini_tools_with_nav = oauth_gmail_tools + [complete_current_email_tool]
            
            # Store OAuth tool executor for handling tool calls
            app_state.oauth_tool_executor = create_oauth_gmail_tool_executor(gmail_service)
        else:
            # MCP mode - use existing MCP tools
            print("🔧 Using MCP Gmail tools (fallback mode)")
            complete_current_email_tool = nav_tools.get_complete_current_email_tool()
            gemini_tools_with_nav = app_state.gemini_tools + [complete_current_email_tool]
            app_state.oauth_tool_executor = None
        
        # Create Gemini session configuration
        gemini_session_config = create_gemini_session_config(gemini_tools_with_nav)
        print(f"🔧 Gemini session config has {len(gemini_session_config['tools'])} tools:")
        for i, tool in enumerate(gemini_session_config['tools']):
            try:
                # Handle different tool object types
                if hasattr(tool, 'function_declarations'):
                    if isinstance(tool.function_declarations, list):
                        tool_names = [fd.name if hasattr(fd, 'name') else fd.get('name', 'unknown') for fd in tool.function_declarations]
                    else:
                        tool_names = [tool.function_declarations.name if hasattr(tool.function_declarations, 'name') else 'unknown']
                else:
                    tool_names = ['unknown_tool']
                print(f"🔧   Tool {i+1}: {tool_names}")
            except Exception as e:
                print(f"🔧   Tool {i+1}: Error getting name - {e}")
        
        # Initialize session state
        app_state.current_session = {
            "status": SessionStatus.ACTIVE,
            "started_at": time.time(),
            "email_manager": email_manager,
            "nav_tools": nav_tools
        }
        
        # Send session ready status
        await websocket.send_text(json.dumps(
            create_session_status_message(
                SessionStatus.ACTIVE, 
                f"Ready to process {len(email_manager.emails)} emails",
                progress=email_manager.get_progress()
            ).dict()
        ))
        
        # Main email processing loop
        while not email_manager.is_exhausted():
            current_email = email_manager.get_current_email()
            if not current_email:
                break
            
            # Extract email details
            email_info = extract_email_details(current_email)
            email_info['nav_tools'] = nav_tools  # Pass nav_tools to session
            email_info['gmail_agent'] = app_state.gmail_agent  # Pass gmail_agent to session
            
            # Update session state
            app_state.current_session.update({
                "current_email": email_info,
                "progress": email_manager.get_progress()
            })
            
            print(f"📧 Processing email {email_manager.current_index + 1}/{len(email_manager.emails)}: {email_info['display_text']}")
            
            # Send progress update
            await websocket.send_text(json.dumps(
                create_session_status_message(
                    SessionStatus.PROCESSING,
                    f"Processing: {email_info['display_text']}",
                    progress=email_manager.get_progress()
                ).dict()
            ))
            
            # Process single email with Gemini Live + WebSocket audio
            session_success = await process_single_email_websocket(
                websocket, gemini_session_config, email_info, nav_tools
            )
            
            if not session_success:
                print("❌ Email session failed or was interrupted")
                break
            
            # Move to next email
            email_manager.next_email()
            
            # Brief pause between emails
            if not email_manager.is_exhausted():
                await asyncio.sleep(1)
        
        # All emails processed successfully
        await websocket.send_text(json.dumps(
            create_session_status_message(
                SessionStatus.COMPLETED,
                "All emails processed! 🎉",
                progress=email_manager.get_progress()
            ).dict()
        ))
        
        print("🎉 All emails processed successfully!")
        
    except Exception as e:
        print(f"❌ WebSocket session error: {e}")
        await websocket.send_text(json.dumps(
            create_error_message(f"Session error: {str(e)}", recoverable=False).dict()
        ))
    
    finally:
        # Reset session state
        app_state.reset_session()
        print("🔌 WebSocket session ended")


async def process_single_email_websocket(
    websocket: WebSocket, 
    gemini_session_config: Dict[str, Any], 
    email_info: Dict[str, Any],
    nav_tools
) -> bool:
    """
    Process a single email using WebSocket audio streaming
    Replaces process_single_email_session from main.py
    
    Args:
        websocket: WebSocket connection
        gemini_session_config: Gemini session configuration
        email_info: Current email information
        nav_tools: Navigation tools for session control
        
    Returns:
        Boolean indicating success
    """
    try:
        # Reset navigation tools for new email session
        nav_tools.reset_session_state()
        
        # Create and run Gemini session with WebSocket audio bridge
        session_success = await create_gemini_session_with_websocket(
            gemini_session_config, websocket, email_info
        )
        
        return session_success
        
    except Exception as e:
        print(f"❌ Single email processing error: {e}")
        await websocket.send_text(json.dumps(
            create_error_message(f"Email processing error: {str(e)}", recoverable=True).dict()
        ))
        return False


# Removed /ws/test-audio endpoint - not needed in production


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    print("🚀 Starting Email Voice Agent FastAPI Server...")
    uvicorn.run(
        "fastapi_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
