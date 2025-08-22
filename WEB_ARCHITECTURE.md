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
│  │  • WebSocket ↔ Gemini Live Streaming                   │    │
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

## 🔐 OAuth Authentication System

### Multi-User Authentication Flow
The application supports secure OAuth 2.0 authentication allowing multiple users to access their personal Gmail accounts through the voice interface.

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

**Backend OAuth Services:**
- **`oauth_service.py`**: Google OAuth 2.0 flow management
- **`user_session.py`**: Multi-user session storage and management
- **OAuth Endpoints**: Complete REST API for authentication operations

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
- **Voice command hints**: "archive", "delete", "skip", "reply"
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
Click Sign In → Generate Auth URL → Google Consent → Backend Callback → Session Creation → Frontend Redirect → Authenticated State
```

**Step-by-step:**
1. **Frontend**: `POST /auth/login` → Backend generates Google OAuth URL
2. **Redirect**: User sent to Google OAuth consent screen
3. **Google Callback**: `GET /auth/callback?code=...` → Backend receives authorization code
4. **Token Exchange**: Backend exchanges code for access/refresh tokens
5. **Session Creation**: Backend creates user session with tokens
6. **Frontend Redirect**: Backend redirects to `http://localhost:3000/auth/callback?session_id=...&success=true`
7. **Session Storage**: Frontend stores session ID in localStorage
8. **Auth State Update**: useAuth hook updates to authenticated state

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
- Backend creates Gemini Live session with 15 Gmail tools
- Audio bridge establishes bidirectional streaming
- First email announced to user

### 4. Email Processing Loop
```
Announce Email → Wait for Voice Command → Execute Tool → Confirm Action → Next Email
```

**Detailed Flow:**
1. **Email Announcement**: Gemini reads "From [sender] - [subject]. What would you like to do?"
2. **Continuous Listening**: System waits indefinitely for user voice input
3. **Voice Recognition**: User speaks command ("archive", "delete", "mark as read", etc.)
4. **Tool Execution**: Gemini calls appropriate Gmail tool (gmail_modify_email, gmail_delete_email, etc.)
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
- **Token Management**: Access token refresh and validation
- **Gmail API Integration**: Direct Gmail service creation with user tokens
- **Security Features**: CSRF protection, token revocation, scope validation

#### **User Session Manager** (`user_session.py`)
- **Multi-User Support**: Concurrent sessions for multiple authenticated users
- **Session Storage**: In-memory storage with automatic cleanup and expiry
- **Token Refresh**: Automatic refresh token handling for expired sessions
- **Session Validation**: Real-time session and token validation
- **Resource Management**: Proper cleanup and memory management

#### **Email Service** (`email_service.py` + `email_service_oauth.py`)
- **Dual Mode Support**: Both OAuth direct API and MCP agent modes
- **EmailManager**: Sequential email processing with deterministic state
- **OAuth Email Operations**: Direct Gmail API calls with user tokens
- **Email Fetching**: Gmail search with user-specific authentication
- **Progress Tracking**: Current/total/remaining email counts
- **State Management**: Clean email iteration and completion detection

#### **Gemini Service** (`gemini_service.py`)
- **MCP Connection**: Integration with Gmail MCP server
- **Tool Discovery**: Dynamic discovery of 14 Gmail tools
- **Tool Conversion**: MCP schema → Gemini Live format
- **Session Configuration**: Gemini Live setup with tools and system instructions
- **Tool Execution**: Gmail action processing and response handling

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

#### **Frontend → Backend Messages**
```typescript
// Raw audio data (48kHz PCM)
WebSocket.send(audioBytes)

// Session control (OAuth-aware)
{ 
  type: "start_session", 
  email_query: "in:inbox", 
  max_results: 50,
  user_id: "google_user_id",      // OAuth user identification
  access_token: "oauth_token"     // User's Gmail access token
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

#### **OAuth REST API Endpoints**
```typescript
// Authentication Flow
POST /auth/login          → Generate OAuth authorization URL
GET  /auth/callback       → Handle Google OAuth callback
GET  /auth/status         → Check current authentication status
POST /auth/logout         → Logout and revoke tokens
GET  /auth/user          → Get authenticated user information


// Example OAuth Flow:
POST /auth/login { redirect_uri?: string }
→ { authorization_url: "https://accounts.google.com/...", state: "..." }

GET /auth/callback?code=...&state=...
→ 302 Redirect to frontend with session_id

GET /auth/status (Authorization: Bearer session_id)
→ { status: "authenticated", user: {...}, expires_at: "...", scopes: [...] }
```

## 🎤 Voice Command Processing

### Supported Voice Commands
- **"archive"** / **"archive this email"** → Removes from INBOX label
- **"delete"** / **"delete this email"** → Permanently deletes email
- **"mark as read"** → Removes UNREAD label
- **"mark as unread"** → Adds UNREAD label  
- **"skip"** / **"next"** / **"continue"** → Moves to next email without action
- **"reply"** → Starts email composition flow

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

#### **Backend (Railway/Render/DigitalOcean)**
- **FastAPI server**: Handles WebSocket connections and Gmail integration
- **Environment variables**: GEMINI_API_KEY required
- **Port**: 8000 (configurable)
- **Health checks**: `/health` endpoint for monitoring

#### **Frontend (Vercel)**
- **Next.js application**: Static site with client-side audio processing
- **Environment variables**: Backend WebSocket URL
- **CDN**: Global distribution via Vercel's edge network
- **HTTPS**: Required for microphone access

#### **Architecture Benefits**
- **Scalable**: Frontend scales via CDN, backend scales horizontally
- **Reliable**: Separate concerns, independent scaling
- **Cost-effective**: Frontend free on Vercel, backend ~$5-10/month
- **Global**: Fast loading worldwide via Vercel edge network

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
User: "archive"
Gemini: "I've archived that email for you."
→ Automatically moves to next email
Gemini: "From Chase - Review new account. What would you like to do with this email?"
User: "delete"
Gemini: "I've deleted that email."
→ Process continues until inbox is clear
```

## 🔧 Development & Testing

### Local Development
- **Backend Tests**: `python test_backend.py` - Validates all components
- **Audio Testing**: WebSocket endpoint `/ws/test-audio` for audio pipeline testing
- **Health Monitoring**: `/health` endpoint shows service status
- **API Documentation**: `/docs` endpoint with interactive API docs

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

## 🎉 Key Achievements

### Functional Completeness
- ✅ **Full voice workflow**: Speak → Action → Next email
- ✅ **All Gmail actions**: Archive, delete, mark read/unread, reply, skip
- ✅ **Perfect audio**: Natural speech quality and recognition
- ✅ **Reliable sessions**: Continuous listening and proper tool execution
- ✅ **OAuth Authentication**: Complete Google OAuth 2.0 integration
- ✅ **Multi-user support**: Multiple users can authenticate simultaneously
- ✅ **Clean UX**: Authentication-aware interface with user profiles

### Technical Excellence
- ✅ **Modern stack**: FastAPI + Next.js + TypeScript + OAuth 2.0
- ✅ **Real-time audio**: WebSocket streaming with perfect quality
- ✅ **Secure authentication**: Google OAuth with proper token management
- ✅ **Type safety**: Pydantic models throughout (including auth models)
- ✅ **Error handling**: Comprehensive error recovery and auth state management
- ✅ **Production ready**: Deployable to Vercel + Railway/Render with OAuth

### OAuth & Security Features
- ✅ **Google OAuth 2.0**: Complete authorization flow with CSRF protection
- ✅ **Token management**: Automatic refresh, validation, and revocation
- ✅ **Session security**: Secure session storage with 24-hour expiry
- ✅ **Multi-user isolation**: Each user's Gmail access completely isolated
- ✅ **Scope management**: Proper Gmail permissions and user consent
- ✅ **Authentication guards**: Protected routes and conditional rendering

### Performance Optimizations
- ✅ **Audio quality**: Native 48kHz without interpolation artifacts
- ✅ **Session isolation**: Clean state per email and per user
- ✅ **Efficient streaming**: Batched audio processing
- ✅ **Resource management**: Proper cleanup and monitoring
- ✅ **Authentication efficiency**: Optimized auth checks and token refresh

The web-based voice email agent now provides enterprise-grade OAuth authentication while maintaining the streamlined voice-first user experience. Multiple users can securely access their personal Gmail accounts through natural voice commands.
