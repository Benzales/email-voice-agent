# Voice Email Agent - Web Architecture

## Overview

A voice-driven Gmail assistant that helps users clear their inbox through natural voice commands. The application uses a modern web-based architecture with FastAPI backend and Next.js frontend, connected via WebSocket for real-time audio streaming.

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
│  │  │ • Single Button │  │  • 48kHz Native Audio       │   │    │
│  │  │ • Auto-connect  │  │  • No Resampling            │   │    │
│  │  │ • Status Display│  │  • Real-time Streaming      │   │    │
│  │  └─────────────────┘  └─────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                              WebSocket Connection
                            (Bidirectional Audio)
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
│  │               Core Services                             │    │
│  │  • Email Service (EmailManager)                        │    │
│  │  • Gemini Service (MCP Integration)                    │    │
│  │  • Custom Tools (Navigation)                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                                    │
                              API Connections
                                    │
┌─────────────────────────────────────────────────────────────────┐
│                    External Services                            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐   │
│  │   Gmail API      │  │  Gemini Live API │  │  MCP Server │   │
│  │  (via MCP)       │  │  (Voice AI)     │  │  (Tools)    │   │
│  └──────────────────┘  └──────────────────┘  └─────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🎨 User Interface Design

### Single-Button Experience
The UI follows a streamlined, voice-first design philosophy:

#### **Initial State**
- **Auto-connects** to backend on page load
- **Fetches email count** without starting processing
- **Displays**: "Ready! X emails in your inbox"
- **Single button**: "🎤 Clear My Inbox (X emails)"

#### **Active Session State**
- **Recording indicator**: Shows microphone is active
- **Progress bar**: Current email / total emails
- **Voice command hints**: "archive", "delete", "skip", "reply"
- **Stop button**: Allows user to end session early

#### **Completion State**
- **Success message**: "All emails processed! 🎉"
- **Reset button**: Return to initial state for new session

## 🔄 Application Flow

### 1. Initialization Phase
```
Page Load → Auto-connect WebSocket → Fetch Email Count → Show Ready State
```

**Technical Details:**
- Next.js component auto-triggers WebSocket connection
- FastAPI backend connects to Gmail MCP server
- Email count fetched and displayed to user
- System waits for explicit user action

### 2. Session Start Phase
```
User Clicks Button → Start Voice Session → Initialize Gemini Live → Begin Email Processing
```

**Technical Details:**
- Frontend sends `start_session` message via WebSocket
- Backend creates Gemini Live session with 15 Gmail tools
- Audio bridge establishes bidirectional streaming
- First email announced to user

### 3. Email Processing Loop
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

### 4. Session Management
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
fastapi_server.py (Orchestration)
├── email_service.py (Email Management)
├── gemini_service.py (AI Integration)  
├── audio_bridge.py (Audio Streaming)
├── models.py (Type Safety)
└── custom_tools.py (Navigation)
```

#### **Email Service** (`email_service.py`)
- **EmailManager**: Sequential email processing with deterministic state
- **Email Fetching**: Gmail MCP integration for inbox search
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

// Session control
{ type: "start_session", email_query: "in:inbox", max_results: 50 }
{ type: "stop_session", reason: "user_requested" }
{ type: "ping" } // Keepalive
```

#### **Backend → Frontend Messages**
```typescript
// Audio responses (base64-encoded from Gemini)
WebSocket.send(audioBytes)

// Session status updates
{ type: "session_status", status: "ready", message: "Ready! 7 emails in inbox", progress: {...} }
{ type: "error", message: "...", recoverable: true }
{ type: "audio_interrupted" } // Clear audio queue
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
- ✅ **Clean UX**: Single-button interface with auto-connect

### Technical Excellence
- ✅ **Modern stack**: FastAPI + Next.js + TypeScript
- ✅ **Real-time audio**: WebSocket streaming with perfect quality
- ✅ **Type safety**: Pydantic models throughout
- ✅ **Error handling**: Comprehensive error recovery
- ✅ **Production ready**: Deployable to Vercel + Railway/Render

### Performance Optimizations
- ✅ **Audio quality**: Native 48kHz without interpolation artifacts
- ✅ **Session isolation**: Clean state per email
- ✅ **Efficient streaming**: Batched audio processing
- ✅ **Resource management**: Proper cleanup and monitoring

The web-based voice email agent successfully replaces the terminal-only version with improved reliability, better user experience, and production-ready deployment capabilities.
