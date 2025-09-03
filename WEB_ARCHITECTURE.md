# Voice Email Agent - Web Architecture

## Overview

A voice-driven Gmail assistant that helps users clear their inbox through natural voice commands. The application uses a modern web-based architecture with FastAPI backend and Next.js frontend, connected via WebSocket for real-time audio streaming. Features complete OAuth 2.0 integration for secure multi-user Gmail access.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Browser                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                Next.js Frontend                         │    │
│  │  ┌─────────────────┐  ┌─────────────────────────────┐   │    │
│  │  │ VoiceEmailAgent │  │     Audio Pipeline          │   │    │
│  │  │    Component    │  │  • WebRTC Microphone        │   │    │
│  │  │                 │  │  • Web Audio API            │   │    │
│  │  │ • OAuth UI      │  │  • 48kHz Native Audio       │   │    │
│  │  │ • User Profile  │  │  • No Resampling            │   │    │
│  │  │ • Status Display│  │  • Real-time Streaming      │   │    │
│  │  └─────────────────┘  └─────────────────────────────┘   │    │
│  │  ┌─────────────────────────────────────────────────┐       │    │
│  │  │           Authentication System                 │       │    │
│  │  │  • useAuth Hook (State Management)             │       │    │
│  │  │  • AuthButton (Login/Logout UI)                │       │    │
│  │  │  • OAuth Callback Handler                      │       │    │
│  │  │  • Protected Routes & Guards                   │       │    │
│  │  └─────────────────────────────────────────────────┘       │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                        WebSocket Connection + OAuth
                         (Bidirectional Audio + Auth)
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                 Audio Bridge                            │    │
│  │  • WebSocket ↔ git Live Streaming                   │    │
│  │  • Continuous Response Listener                        │    │
│  │  • Tool Execution Handler                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               OAuth Services                            │    │
│  │  • OAuth Service (Google OAuth 2.0)                    │    │
│  │  • User Session Manager (Multi-user)                   │    │
│  │  • Token Refresh & Validation                          │    │
│  │  • Secure Session Storage                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │               Core Services                             │    │
│  │  • Email Service (OAuth + MCP Modes)                   │    │
│  │  • Gemini Service (MCP Integration)                    │    │
│  │  • Custom Tools (Navigation)                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                        API Connections + OAuth
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐   │
│  │   Gmail API      │  │  Gemini Live API │  │Google OAuth │   │
│  │ (Direct + MCP)   │  │  (Voice AI)     │  │   Server    │   │
│  └──────────────────┘  └──────────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔐 OAuth Authentication & Security System

### Multi-User Authentication Flow with Security Protection
The application supports secure OAuth 2.0 authentication allowing multiple users to access their personal Gmail accounts through the voice interface. **All expensive operations (WebSocket/Gemini Live API) require proper authentication to prevent unauthorized cost abuse.**

#### **Authentication Architecture**
```
User Authentication Flow:
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │  Google OAuth   │
│  (Next.js)      │    │   (FastAPI)     │    │    Server       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
    1. Click "Sign in"           │                       │
         │ ─────────────────────▶│                       │
         │                  2. Generate Auth URL         │
         │                       │ ─────────────────────▶│
         │                       │                  3. Return URL
         │                       │ ◀─────────────────────│
         │ ◀─────────────────────│                       │
    4. Redirect to Google        │                       │
         │ ─────────────────────────────────────────────▶│
         │                       │                  5. User Consent
         │                       │                       │
         │                  6. Callback with Code        │
         │                       │ ◀─────────────────────│
         │                  7. Exchange Code for Tokens  │
         │                       │ ─────────────────────▶│
         │                       │                  8. Return Tokens
         │                       │ ◀─────────────────────│
         │                  9. Create User Session       │
         │ ◀─────────────────────│                       │
   10. Authenticated State       │                       │
```

#### **OAuth Components**

**Frontend Authentication:**
- **`useAuth` Hook**: Complete authentication state management
- **`AuthButton`**: Google-branded login/logout interface
- **`UserProfile`**: Displays authenticated user information
- **`ProtectedRoute`**: Authentication guards for protected content
- **OAuth Callback Page**: Handles post-authentication redirect
- **Backend Config**: Centralized backend URL management for production/development

**Backend OAuth Services:**
- **`oauth_service.py`**: Google OAuth 2.0 flow management with environment variables
- **`user_session.py`**: Multi-user session storage and management
- **OAuth Endpoints**: Complete REST API for authentication operations
- **Dynamic Redirect System**: Automatically redirects to correct frontend domain

#### **Supported OAuth Scopes**
- `https://www.googleapis.com/auth/gmail.modify` - Full Gmail access for email management
- `https://www.googleapis.com/auth/userinfo.email` - User email address
- `https://www.googleapis.com/auth/userinfo.profile` - User profile information
- `openid` - OpenID Connect authentication

#### **Session Management**
- **In-Memory Storage**: Secure session storage with automatic cleanup
- **Token Refresh**: Automatic refresh token handling
- **Session Timeout**: 24-hour session expiry with periodic cleanup
- **Multi-User Support**: Concurrent sessions for multiple users
- **Security Features**: CSRF protection, token revocation, secure logout

#### **🔄 Dynamic OAuth Redirect System**
**Problem Solved**: Multiple Vercel deployment URLs (project alias vs deployment hash) caused double authentication when OAuth callback redirected to wrong domain.

**Solution**: Dynamic frontend origin detection and state-encoded redirects:
```typescript
// Frontend Origin Detection (Backend)
origin = http_request.headers.get("origin") || fallback_url

// State Parameter Encoding
state_data = {
  "user_state": request.state,
  "frontend_origin": origin  // 🎯 Captures actual frontend domain
}
encoded_state = base64.urlsafe_b64encode(json.dumps(state_data))

// OAuth Callback Dynamic Redirect
state_data = json.loads(base64.urlsafe_b64decode(state))
frontend_url = state_data.get("frontend_origin", default_fallback)
redirect_url = f"{frontend_url}/auth/callback?session_id={session_id}"
```

**Benefits**:
- ✅ **Single Sign-In**: Works with both `courier-black.vercel.app` and deployment URLs
- ✅ **No Cross-Domain Issues**: User stays on same domain throughout OAuth flow
- ✅ **Automatic Detection**: Backend automatically detects correct frontend origin
- ✅ **Fallback Safety**: Falls back to environment variable if origin detection fails

## 🎨 User Interface Design

### Single-Button Experience
The UI follows a streamlined, voice-first design philosophy:

#### **Unauthenticated State**
- **Authentication UI**: "Sign in with Google" button with Google branding
- **User guidance**: Clear messaging about Gmail access requirements
- **Security info**: Explains OAuth permissions and data access

#### **Authentication Flow State**
- **Processing**: Shows loading spinner during OAuth flow
- **Callback handling**: Processes OAuth callback and creates session
- **Success confirmation**: Displays welcome message and redirects

#### **Authenticated Initial State**
- **User profile**: Shows authenticated user's name, email, and profile picture
- **Auto-connects** to backend with user's OAuth tokens
- **Fetches email count** for the authenticated user's inbox
- **Displays**: "Ready! X emails in your inbox"
- **Single button**: "🎤 Clear My Inbox (X emails)"
- **Sign out option**: Red "Sign Out" button in profile section

#### **Active Session State**
- **Recording indicator**: Shows microphone is active
- **Progress bar**: Current email / total emails
- **Voice command hints**: "archive", "read it", "create draft", "skip"
- **Stop button**: Allows user to end session early

#### **Completion State**
- **Success message**: "All emails processed! 🎉"
- **Reset button**: Return to initial state for new session

## 🔄 Application Flow

### 1. Authentication Phase
```
Page Load → Check Auth Status → Show Login/Authenticated UI
```

**Technical Details:**
- Next.js component checks for stored session ID in localStorage
- If session exists, validates with backend `/auth/status` endpoint
- Shows appropriate UI: login form or authenticated user interface
- OAuth flow initiated when user clicks "Sign in with Google"

#### **OAuth Flow Details:**
```
Click Sign In → Generate Auth URL (+ Origin Detection) → Google Consent → Backend Callback → Session Creation → Dynamic Frontend Redirect → Authenticated State
```

**Step-by-step:**
1. **Frontend**: `POST /auth/login` → Backend captures origin header and generates Google OAuth URL
2. **State Encoding**: Backend encodes frontend origin in OAuth state parameter
3. **Redirect**: User sent to Google OAuth consent screen
4. **Google Callback**: `GET /auth/callback?code=...&state=...` → Backend receives authorization code
5. **Token Exchange**: Backend exchanges code for access/refresh tokens
6. **Session Creation**: Backend creates user session with tokens
7. **Dynamic Redirect**: Backend decodes state, redirects to original frontend domain
   - `https://courier-black.vercel.app/auth/callback?session_id=...&success=true` (if from alias)
   - `https://courier-{hash}.vercel.app/auth/callback?session_id=...&success=true` (if from deployment)
8. **Session Storage**: Frontend stores session ID in localStorage
9. **Auth State Update**: useAuth hook updates to authenticated state

### 2. Initialization Phase (Authenticated Users)
```
Authentication Complete → Auto-connect WebSocket → Fetch Email Count → Show Ready State
```

**Technical Details:**
- Next.js component auto-triggers WebSocket connection (only if authenticated)
- FastAPI backend uses user's OAuth tokens for Gmail API access
- Email count fetched from authenticated user's Gmail account
- System waits for explicit user action to start voice processing

### 3. Session Start Phase
```
User Clicks Button → Start Voice Session → Initialize Gemini Live → Begin Email Processing
```

**Technical Details:**
- Frontend sends `start_session` message via WebSocket
- Backend creates Gemini Live session with Gmail tools (5 OAuth Gmail tools + navigation)
- Audio bridge establishes bidirectional streaming
- First email announced to user

### 4. Email Processing Loop
```
Announce Email → Wait for Voice Command → Execute Tool → Confirm Action → Next Email
```

**Detailed Flow:**
1. **Email Announcement**: Gemini reads "From [sender] - [subject]. What would you like to do?"
2. **Continuous Listening**: System waits indefinitely for user voice input
3. **Voice Recognition**: User speaks command ("archive", "read it", "create draft", etc.)
4. **Tool Execution**: Gemini calls appropriate Gmail tool (gmail_modify_email, gmail_read_email_content, gmail_create_draft, etc.)
5. **Action Confirmation**: Gemini confirms "I've archived that email"
6. **Session Completion**: complete_current_email tool called automatically
7. **Next Email**: New isolated session starts for next email

### 5. Session Management
```
Isolated Sessions → One Gemini Session Per Email → Clean State Reset → Resource Cleanup
```

**Key Features:**
- Each email processed in completely isolated Gemini Live session
- Navigation tools reset between emails for clean state
- Proper resource cleanup and connection management
- Graceful error handling and recovery

## 🎵 Audio Pipeline Architecture

### Frontend Audio Processing
```
Microphone → getUserMedia() → Web Audio API → Float32 Audio → 16-bit PCM → WebSocket
```

**Technical Implementation:**
- **WebRTC**: `navigator.mediaDevices.getUserMedia()` for microphone access
- **Web Audio API**: `AudioContext` and `ScriptProcessorNode` for real-time processing
- **Native Quality**: 48kHz browser audio sent directly (no resampling interpolation)
- **Format**: 16-bit PCM audio chunks streamed continuously

### Backend Audio Bridge
```
WebSocket → Audio Bridge → Gemini Live Session → Tool Execution → Response Audio → WebSocket
```

**Key Components:**
- **WebSocketAudioBridge**: Manages bidirectional audio streaming
- **Continuous Listener**: Persistent Gemini response handler that never dies
- **Tool Processor**: Handles voice command → tool call conversion
- **Audio Format**: Sends `audio/pcm;rate=48000` to preserve quality

### Audio Quality Optimizations
- **No Interpolation**: Removed linear interpolation resampling that degraded quality
- **Native Sample Rate**: Uses browser's 48kHz directly instead of downsampling
- **Continuous Streaming**: Audio chunks batched and played sequentially
- **Interruption Handling**: Audio queue cleared when user interrupts Gemini

## 🔧 Backend Services

### Core Services Architecture
```
fastapi_server.py (Orchestration + OAuth Endpoints)
├── oauth_service.py (Google OAuth 2.0 Management)
├── user_session.py (Multi-user Session Management)
├── email_service.py (Email Management - OAuth + MCP)
├── email_service_oauth.py (OAuth-specific Email Operations)
├── gemini_service.py (AI Integration)  
├── audio_bridge.py (Audio Streaming)
├── models.py (Type Safety + OAuth Models)
└── custom_tools.py (Navigation)
```

#### **OAuth Service** (`oauth_service.py`)
- **Google OAuth 2.0 Flow**: Complete authorization URL generation and code exchange
- **Environment Variables**: Loads OAuth credentials from environment (no credentials.json)
- **Token Management**: Access token refresh and validation with optimized validation
- **Gmail API Integration**: Direct Gmail service creation with user tokens
- **Security Features**: CSRF protection, token revocation, scope validation
- **Production Ready**: Secure environment-based configuration for deployment

#### **User Session Manager** (`user_session.py`)
- **Multi-User Support**: Concurrent sessions for multiple authenticated users
- **Session Storage**: In-memory storage with automatic cleanup and expiry
- **Token Refresh**: Automatic refresh token handling for expired sessions
- **Session Validation**: Real-time session and token validation
- **Resource Management**: Proper cleanup and memory management

#### **Email Service** (`email_service.py` + `email_service_oauth.py` + `oauth_gmail_tools.py`)
- **Dual Mode Support**: Both OAuth direct API and MCP agent modes
- **EmailManager**: Sequential email processing with deterministic state
- **OAuth Email Operations**: Direct Gmail API calls with user tokens
- **OAuth Gmail Tools**: Gemini-compatible tools for OAuth mode (gmail_modify_email, gmail_create_draft, gmail_read_email_content, gmail_list_labels, etc.)
- **Dynamic Tool Selection**: Automatically provides OAuth tools to Gemini when user is authenticated
- **Email Fetching**: Gmail search with user-specific authentication
- **Progress Tracking**: Current/total/remaining email counts
- **State Management**: Clean email iteration and completion detection

#### **Gemini Service** (`gemini_service.py`)
- **MCP Connection**: Integration with Gmail MCP server (fallback mode)
- **Tool Discovery**: Dynamic discovery of Gmail tools (MCP fallback mode)
- **Tool Conversion**: MCP schema → Gemini Live format
- **OAuth Tool Integration**: Prioritizes OAuth Gmail tools when user is authenticated
- **Dual Tool Execution**: Handles both OAuth and MCP tool execution modes
- **Session Configuration**: Gemini Live setup with tools and system instructions
- **Tool Execution**: Gmail action processing and response handling with proper authentication

#### **Audio Bridge** (`audio_bridge.py`)
- **WebSocket Integration**: Frontend ↔ Backend audio streaming
- **Gemini Live Connection**: Real-time audio streaming to/from Gemini
- **Continuous Response Listener**: Persistent handler that survives turn completion
- **Tool Call Processing**: Voice command → Gmail tool execution
- **Session Management**: Proper session lifecycle and cleanup

#### **Models** (`models.py`)
- **Type Safety**: Pydantic models for all WebSocket messages
- **Message Types**: Audio, session status, error handling
- **Validation**: Ensure reliable communication between frontend/backend
- **API Contracts**: Well-defined interfaces for all interactions

#### **Custom Tools** (`custom_tools.py`)
- **Navigation Tools**: EmailNavigationTools for session control
- **Complete Email Tool**: Ends current email session and moves to next
- **Session State**: Manages when to end sessions and progress to next email

### WebSocket Communication Protocol

#### **🔐 Authentication Required**
All WebSocket connections now require valid OAuth session authentication:
```typescript
// WebSocket Connection (AUTHENTICATION REQUIRED)
ws://localhost:8000/ws/voice-session?session_id=YOUR_OAUTH_SESSION_ID

// Connection rejected with HTTP 403 if:
// - No session_id provided
// - Invalid/expired session_id
// - Session not authenticated
```

#### **Frontend → Backend Messages**
```typescript
// Raw audio data (48kHz PCM) - Only after authentication
WebSocket.send(audioBytes)

// Session control (Authenticated users only)
{ 
  type: "start_session", 
  email_query: "in:inbox", 
  max_results: 50
  // Note: user_id and access_token now handled via session validation
}
{ type: "stop_session", reason: "user_requested" }
{ type: "ping" } // Keepalive
```

#### **Backend → Frontend Messages**
```typescript
// Audio responses (base64-encoded from Gemini)
WebSocket.send(audioBytes)

// Session status updates (OAuth-aware)
{ 
  type: "session_status", 
  status: "ready", 
  message: "Ready! 7 emails in inbox", 
  progress: {...},
  user_email: "user@gmail.com"    // Authenticated user context
}
{ type: "error", message: "...", recoverable: true }
{ type: "audio_interrupted" } // Clear audio queue
```

#### **🔐 Secured REST API Endpoints**
```typescript
// Authentication Flow (Public endpoints)
POST /auth/login          → Generate OAuth authorization URL
GET  /auth/callback       → Handle Google OAuth callback

// Protected Endpoints (Require Bearer token authentication)
GET  /auth/status         → Check current authentication status (🔐 AUTH REQUIRED)
POST /auth/logout         → Logout and revoke tokens (🔐 AUTH REQUIRED)
GET  /auth/user          → Get authenticated user information (🔐 AUTH REQUIRED)
GET  /session/status     → Get voice session status (🔐 AUTH REQUIRED)

// Removed for Security (404 Not Found)
// GET  /auth/sessions   → REMOVED - Admin endpoint security risk
// GET  /ws/test-audio   → REMOVED - Debug endpoint not needed in production

// Example OAuth Flow:
POST /auth/login { redirect_uri?: string }
→ { authorization_url: "https://accounts.google.com/...", state: "..." }

GET /auth/callback?code=...&state=...
→ 302 Redirect to frontend with session_id

GET /auth/status (Authorization: Bearer session_id)
→ { status: "authenticated", user: {...}, expires_at: "...", scopes: [...] }
```

## 🛡️ Security Implementation

### Production Security Features
The application implements comprehensive security measures to prevent unauthorized access and cost abuse:

#### **🔐 Authentication Requirements**
- **WebSocket Endpoint**: Requires valid `session_id` query parameter
- **Protected HTTP Endpoints**: Require `Authorization: Bearer {session_id}` header
- **Session Validation**: All sessions validated against OAuth tokens before access
- **Cost Protection**: Expensive Gemini Live API operations blocked for unauthorized users

#### **🚫 Removed Vulnerable Endpoints**
- **`/auth/sessions`**: Admin endpoint removed (privacy/security risk)
- **`/ws/test-audio`**: Debug endpoint removed (unnecessary attack surface)

#### **✅ Security Testing Results**
- Unauthorized WebSocket connections → **403 Forbidden**
- Missing authentication headers → **401 Unauthorized** 
- Invalid session IDs → **403 Forbidden**
- Admin endpoints → **404 Not Found**

#### **🎯 Security Architecture**
```typescript
// Frontend Authentication Integration
const [authState] = useAuth();
const [sessionState, sessionControls] = useVoiceSession(
  wsUrl, 
  authState.sessionId  // 🔐 Session ID passed for authentication
);

// WebSocket URL Construction
const authenticatedWsUrl = sessionId 
  ? `${wsUrl}?session_id=${sessionId}`  // 🔐 Authenticated connection
  : wsUrl;  // ❌ Will be rejected

// Backend Authentication Validation
async function websocket_voice_session(
  websocket: WebSocket,
  session_id: str = Query(..., description="OAuth session ID required")
) {
  // 🔐 Validate session before accepting WebSocket
  auth_status = await session_manager.validate_session(session_id);
  if auth_status.status != AuthStatus.AUTHENTICATED:
    await websocket.close(code=4001, reason="Authentication required");
    return;
  
  await websocket.accept();  // ✅ Authenticated connection established
}
```

## 🎤 Voice Command Processing

### Supported Voice Commands
- **"archive"** / **"archive this email"** → Removes from INBOX label
- **"delete"** / **"trash this email"** → Moves email to trash (recoverable)
- **"mark as read"** → Removes UNREAD label
- **"mark as unread"** → Adds UNREAD label  
- **"read it"** / **"what does it say"** → Reads full email content aloud
- **"create draft"** / **"save as draft"** → Creates draft email for later
- **"move to [label]"** → Moves email to specified label/folder
- **"what labels do I have"** → Lists available Gmail labels
- **"skip"** / **"next"** / **"continue"** → Moves to next email without action

### Voice Processing Flow
```
User Voice → Web Audio API → WebSocket → Gemini Live → Voice Recognition → Tool Selection → Gmail API → Confirmation → Next Email
```

**Technical Details:**
1. **Audio Capture**: 48kHz native browser audio (no quality loss)
2. **Streaming**: Continuous audio chunks sent to Gemini Live
3. **Recognition**: Gemini Live processes speech and identifies intent
4. **Tool Mapping**: Voice command mapped to appropriate Gmail tool
5. **Execution**: Tool executed with proper email ID and parameters
6. **Confirmation**: Gemini announces action completion
7. **Navigation**: complete_current_email tool called automatically

## 🔄 Session Management

### Email Session Isolation
Each email is processed in a completely isolated Gemini Live session:

#### **Session Lifecycle**
```
Create Session → Configure Tools → Send Email Info → Wait for Voice → Process Command → Execute Tool → End Session → Next Email
```

#### **State Management**
- **Clean Slate**: Each email starts with fresh Gemini session
- **No History**: No memory of previous emails or actions
- **Tool Reset**: Navigation tools reset between sessions
- **Resource Cleanup**: Proper cleanup of audio and network resources

#### **Session Status States**
- **`initializing`**: Connecting and loading email count
- **`ready`**: Connected, showing email count, waiting for user to start
- **`active`**: Session started, Gemini announcing current email
- **`processing`**: User gave command, executing Gmail tool
- **`completed`**: All emails processed successfully
- **`error`**: Something went wrong, recoverable or fatal

## 🚀 Deployment Architecture

### Development Setup
```bash
# Backend (Terminal 1)
python start_server.py  # or start_uv_server.py

# Frontend (Terminal 2)  
cd web && npm run dev
```

### Production Deployment

#### **Vercel Frontend Deployment Process**

**From `add-ui` Branch (Current Development):**
```bash
# Install Vercel CLI
npm install -g vercel

# Deploy from web directory
cd web
vercel --prod

# Fix any build errors (TypeScript/linting)
npm run build  # Test locally first

# Redeploy after fixes
vercel --prod
```

**Build Requirements:**
- All TypeScript errors must be resolved
- Linting warnings are acceptable, but errors will fail deployment
- Missing library files (audioUtils.ts, websocket/client.ts) must be present

**Deployment URLs:**
- **Production**: `https://courier-{hash}-{project}.vercel.app` (deployment-specific)
- **Alias**: `https://courier-black.vercel.app` (may take time to update)

#### **Backend (Fly.io)**
- **FastAPI server**: Containerized with Docker for WebSocket and Gmail integration
- **Global edge deployment**: Deployed on Fly.io for low-latency WebSocket connections
- **Environment variables**: 
  - `GEMINI_API_KEY` - Google AI API key
  - `GMAIL_CLIENT_ID` - Google OAuth client ID
  - `GMAIL_CLIENT_SECRET` - Google OAuth client secret  
  - `GMAIL_REDIRECT_URI` - OAuth callback URI (`https://courier.fly.dev/auth/callback`)
  - `FRONTEND_URL` - Frontend domain for OAuth redirects (optional, auto-detected)
- **Port**: 8000 (configurable)
- **Health checks**: `/health` endpoint for monitoring
- **Scaling**: Single machine deployment with `max_machines_running = 1` for session persistence
- **Domain**: `https://courier.fly.dev`

#### **Frontend (Vercel)**
- **Next.js application**: Static site with client-side audio processing and OAuth integration
- **Environment variables**: 
  - `NEXT_PUBLIC_API_URL` - Backend API URL (defaults to `https://courier.fly.dev`)
  - `NEXT_PUBLIC_WS_URL` - WebSocket URL (defaults to `wss://courier.fly.dev/ws/voice-session`)
- **CDN**: Global distribution via Vercel's edge network
- **HTTPS**: Required for microphone access and OAuth security
- **Multiple URLs**: 
  - Production deployment: `https://courier-{hash}-{project}.vercel.app`
  - Project alias: `https://courier-black.vercel.app` (cleaner URL)
- **Dynamic OAuth redirects**: Backend automatically redirects to correct domain

#### **Architecture Benefits**
- **Scalable**: Frontend scales via CDN, backend scales globally via Fly.io
- **Reliable**: Separate concerns, independent scaling, health monitoring
- **Cost-effective**: Frontend free on Vercel, backend ~$5-10/month on Fly.io
- **Global**: Fast loading worldwide via Vercel + Fly.io edge networks
- **Secure**: OAuth environment variables isolated in production secrets
- **WebSocket optimized**: Fly.io provides excellent WebSocket performance globally

## 🔍 Key Technical Innovations

### Audio Quality Preservation
- **No Resampling**: Eliminated linear interpolation that degraded voice recognition
- **Native Sample Rates**: Uses browser's 48kHz directly
- **Continuous Streaming**: Batched audio playback prevents overlapping voices
- **Base64 Decoding**: Proper handling of Gemini Live's audio format

### Session Continuity
- **Continuous Response Listener**: Gemini handler runs throughout entire session
- **Turn Completion Handling**: Continues listening after Gemini finishes speaking
- **Tool Call Processing**: Processes voice commands immediately when detected
- **Proper Session Ending**: Only ends when complete_current_email tool is called

### Error Handling & Reliability
- **WebSocket Keepalive**: Prevents connection timeouts
- **Audio Context Monitoring**: Auto-resumes if browser suspends audio
- **Graceful Degradation**: Handles network issues and audio failures
- **Resource Cleanup**: Proper cleanup of all audio and network resources

## 🎯 User Experience Flow

### Streamlined Interaction
1. **Page Load**: Auto-connects, shows "Ready! X emails in inbox"
2. **Single Click**: "🎤 Clear My Inbox (X emails)" starts everything
3. **Voice Commands**: Natural speech recognition for email actions
4. **Automatic Flow**: Moves through emails until inbox is clear
5. **Completion**: "All emails processed! 🎉"

### Voice Interaction Pattern
```
Gemini: "From Tesla - Get $7500 Off. What would you like to do with this email?"
User: "read it"
Gemini: "This email says: Take advantage of our limited-time offer..."
User: "archive"
Gemini: "I've archived that email for you."
→ Automatically moves to next email
Gemini: "From Chase - Review new account. What would you like to do with this email?"
User: "create draft reply"
Gemini: "I've created a draft reply for you to review later."
→ Process continues until inbox is clear
```

## 🔧 Development & Testing

### Local Development
- **Backend Tests**: `python test_backend.py` - Validates all components
- **Audio Testing**: WebSocket endpoint `/ws/test-audio` for audio pipeline testing
- **Health Monitoring**: `/health` endpoint shows service status
- **API Documentation**: `/docs` endpoint with interactive API docs

### Common Production Issues

#### **OAuth Session Persistence Failure**
**Symptom**: Authentication succeeds but immediately reverts to login screen
**Cause**: Multiple Fly.io machines running with in-memory session storage
**Fix**: 
```bash
flyctl machines list  # Check for multiple machines
flyctl machines stop <extra_machine_id>
flyctl machines destroy <extra_machine_id> --force
```
**Prevention**: Ensure `max_machines_running = 1` in fly.toml for stateful apps

### Debugging Features
- **Voice Detection**: Console shows when voice is detected
- **Tool Execution**: Backend logs show all Gmail tool calls
- **Audio Format**: Shows native audio format being sent to Gemini
- **Session Lifecycle**: Detailed logging of session start/end/errors

### Configuration
- **Email Query**: Customizable Gmail search (default: "in:inbox")
- **Max Results**: Configurable email batch size (default: 50)
- **Audio Settings**: Browser manages microphone permissions and settings
- **Session Timeouts**: 2-minute timeout per email session

### User Database Management
The application includes a persistent SQLite database for user tracking with multiple access methods:

#### **Quick Database Status Check**
```bash
# One-liner to check current database status
flyctl ssh console -C "python3 -c 'import sqlite3; c=sqlite3.connect(\"/data/users.db\"); print(f\"Users: {c.execute(\"SELECT COUNT(*) FROM users\").fetchone()[0]}, Sessions: {c.execute(\"SELECT COUNT(*) FROM login_history\").fetchone()[0]}\")'"
```

#### **Detailed Database Inspection**
```bash
# Connect to production server and inspect database contents
flyctl ssh console -C "python3 -c \"
import sqlite3
conn = sqlite3.connect('/data/users.db')
cursor = conn.cursor()

# Get user count and login count
cursor.execute('SELECT COUNT(*) FROM users')
user_count = cursor.fetchone()[0]
cursor.execute('SELECT COUNT(*) FROM login_history')
login_count = cursor.fetchone()[0]

print(f'📊 Database Status: {user_count} users, {login_count} sessions')

# Show recent users
if user_count > 0:
    cursor.execute('SELECT email, name, total_logins, total_emails_processed, last_login FROM users ORDER BY last_login DESC LIMIT 5')
    print('👥 Recent Users:')
    for row in cursor.fetchall():
        email, name, logins, emails, last_login = row
        print(f'   {email} ({name}): {logins} logins, {emails} emails')

conn.close()
\""
```

#### **Admin API Endpoints**
All admin endpoints require authentication via `Authorization: Bearer {session_id}` header:
- **`GET /admin/users`** - List all users with pagination
- **`GET /admin/users/{user_id}`** - Detailed user info + login history
- **`GET /admin/statistics`** - Overall usage statistics
- **`POST /admin/cleanup`** - Clean up old login records

#### **Database Location**
- **Development**: `users.db` (local file, git-ignored)
- **Production**: `/data/users.db` (persistent Fly.io volume)
- **Backup**: Automatic Fly.io volume snapshots (5-day retention)

## 🎉 Key Achievements

### Functional Completeness
- ✅ **Full voice workflow**: Speak → Action → Next email
- ✅ **All Gmail actions**: Archive, trash, mark read/unread, read content, create drafts, label management, skip
- ✅ **Privacy Policy**: Comprehensive privacy policy deployed and accessible
- ✅ **Perfect audio**: Natural speech quality and recognition
- ✅ **Reliable sessions**: Continuous listening and proper tool execution
- ✅ **OAuth Authentication**: Complete Google OAuth 2.0 integration
- ✅ **Multi-user support**: Multiple users can authenticate simultaneously
- ✅ **Clean UX**: Authentication-aware interface with user profiles
- ✅ **User Tracking**: Persistent SQLite database with login history and usage statistics

### Technical Excellence
- ✅ **Modern stack**: FastAPI + Next.js + TypeScript + OAuth 2.0
- ✅ **Real-time audio**: WebSocket streaming with perfect quality
- ✅ **Secure authentication**: Google OAuth with proper token management
- ✅ **Type safety**: Pydantic models throughout (including auth models)
- ✅ **Error handling**: Comprehensive error recovery and auth state management
- ✅ **Production ready**: Deployable to Vercel + Railway/Render with OAuth

### 🛡️ **Production Security Features**
- ✅ **WebSocket Authentication**: All expensive operations require valid OAuth session
- ✅ **Endpoint Protection**: HTTP endpoints secured with Bearer token authentication
- ✅ **Cost Abuse Prevention**: Unauthorized access to Gemini Live API blocked
- ✅ **Vulnerability Removal**: Admin and debug endpoints removed for production
- ✅ **Session Validation**: Real-time OAuth token validation before API access
- ✅ **Security Testing**: Comprehensive testing confirms all attack vectors blocked
- ✅ **Frontend Integration**: Seamless authentication between frontend and backend

### OAuth & Security Architecture
- ✅ **Google OAuth 2.0**: Complete authorization flow with CSRF protection
- ✅ **Token management**: Automatic refresh, validation, and revocation
- ✅ **Session security**: Secure session storage with 24-hour expiry
- ✅ **Multi-user isolation**: Each user's Gmail access completely isolated
- ✅ **Scope management**: Proper Gmail permissions and user consent
- ✅ **Authentication guards**: Protected routes and conditional rendering
- ✅ **Cost protection**: Prevents unauthorized expensive API operations
- ✅ **Environment-based config**: Production-ready OAuth without credentials files
- ✅ **Dynamic OAuth redirects**: Single sign-in across multiple deployment URLs

### Performance Optimizations
- ✅ **Audio quality**: Native 48kHz without interpolation artifacts
- ✅ **Session isolation**: Clean state per email and per user
- ✅ **Efficient streaming**: Batched audio processing
- ✅ **Resource management**: Proper cleanup and monitoring
- ✅ **Authentication efficiency**: Optimized auth checks and token refresh
- ✅ **Security performance**: Fast session validation without blocking UX

### 🚀 **Production Deployment Achievements**
- ✅ **Containerized Backend**: Docker-based FastAPI deployment on Fly.io
- ✅ **Global Edge Network**: Fly.io + Vercel for worldwide low-latency access
- ✅ **Environment Security**: All secrets managed via Fly.io secrets and Vercel env vars
- ✅ **CORS Configuration**: Dynamic CORS handling for multiple frontend domains
- ✅ **Health Monitoring**: Production health checks and deployment validation
- ✅ **WebSocket Optimization**: Fly.io single-machine deployment for session persistence
- ✅ **Multiple Frontend URLs**: Support for both project aliases and deployment hashes
- ✅ **Dynamic Redirects**: OAuth callback automatically redirects to correct domain
- ✅ **Zero Downtime**: Rolling deployments with health checks
- ✅ **Production Hardening**: Removed debug endpoints, secure OAuth configuration
- ✅ **Persistent User Database**: SQLite database with Fly.io volume for user tracking

The web-based voice email agent is now **fully deployed in production** with enterprise-grade security and global accessibility. The application provides OAuth authentication protecting all expensive operations, while maintaining the streamlined voice-first user experience. Multiple users can securely access their personal Gmail accounts through natural voice commands **without risk of unauthorized cost abuse**.

## 🌐 **Live Production URLs**
- **Primary**: https://courier-black.vercel.app (Clean project alias)
- **Current**: https://courier-po0de60ss-benjamingonzales121102-1293s-projects.vercel.app (Latest deployment)
- **Backend**: https://courier.fly.dev (Global Fly.io deployment)
- **Privacy Policy**: Available at `/privacy` on any frontend URL

The application automatically handles authentication across all URLs with dynamic OAuth redirects, ensuring users never need to authenticate twice regardless of which URL they access.
