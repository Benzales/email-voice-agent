# Implementation Plan: Voice-Only FastAPI Integration

## Phase 1: Backend Preparation (Minimal main.py Changes)

### Step 1.1: Extract Core Components
**Goal**: Create reusable modules without breaking main.py

**Files to Create**:
- `email_service.py` - Extract EmailManager and email fetching logic
- `gemini_service.py` - Extract Gemini session and MCP setup logic  
- `audio_bridge.py` - Create WebSocket ↔ Gemini audio bridge
- `models.py` - Pydantic models for WebSocket messages

**Extraction Strategy**:
- **Copy** functions from main.py (don't modify original)
- Add WebSocket parameters to copied functions
- Keep main.py as working reference implementation

### Step 1.2: Create FastAPI Server
**File**: `fastapi_server.py`

**Components**:
- WebSocket endpoint `/ws/voice-session`
- CORS middleware for Next.js frontend
- Basic health check endpoint
- Error handling and logging

### Step 1.3: Audio Bridge Implementation
**File**: `audio_bridge.py`

**Core Function**: Replace PyAudio streams with WebSocket streams
- Input: WebSocket audio chunks → Gemini Live session
- Output: Gemini Live audio → WebSocket
- Maintain same 16kHz PCM format and 5ms intervals

## Phase 2: Frontend Development (Next.js)

### Step 2.1: Audio Infrastructure
**Components**:
- WebRTC for microphone access
- Web Audio API for real-time processing
- WebSocket client for backend communication
- Audio format conversion (browser → 16kHz PCM)

### Step 2.2: Minimal UI
**Pages**:
- `pages/index.tsx` - Single page with start/stop button
- Simple, clean interface focused on voice interaction
- No email display, no status indicators

### Step 2.3: WebSocket Integration
**Features**:
- Auto-connect to FastAPI WebSocket
- Bidirectional audio streaming
- Connection error handling
- Automatic reconnection

## Phase 3: Integration Testing

### Step 3.1: Local Development Setup
**Backend**:
- Run FastAPI server on `localhost:8000`
- Test WebSocket audio streaming
- Verify MCP/Gemini integration works

**Frontend**:
- Run Next.js on `localhost:3000`
- Test microphone access and audio output
- Verify WebSocket communication

### Step 3.2: End-to-End Testing
**Test Cases**:
- Complete email processing workflow
- Audio quality and latency
- Error handling and recovery
- Session cleanup and resource management

## Phase 4: Deployment Preparation

### Step 4.1: Backend Deployment (Railway/Render)
**Configuration**:
- Environment variables (.env handling)
- Production WebSocket settings
- Health checks and monitoring
- CORS configuration for production domain

### Step 4.2: Frontend Deployment (Vercel)
**Configuration**:
- Environment variables for backend URL
- Production build optimization
- WebSocket connection to production backend
- HTTPS/WSS configuration

## Detailed Implementation Steps

### Backend Architecture
```
fastapi_server.py
├── WebSocket endpoint
├── Audio bridge orchestration
├── Import and use extracted services
└── Error handling

email_service.py (extracted from main.py lines 37-64, 332-352)
├── EmailManager class
├── fetch_inbox_emails()
├── parse_gmail_search_results()
└── Email state management

gemini_service.py (extracted from main.py lines 314-381, 113-308)
├── setup_mcp_connection()
├── discover_and_convert_tools()
├── create_gemini_session()
├── process_gemini_responses()
└── handle_tool_execution()

audio_bridge.py (new - replaces lines 148-166, 186-188)
├── websocket_to_gemini_audio()
├── gemini_to_websocket_audio()
├── audio_format_conversion()
└── stream_management()
```

### Frontend Architecture
```
pages/index.tsx
├── WebSocket connection
├── Microphone access
├── Audio streaming
└── Simple start/stop UI

hooks/useWebSocketAudio.ts
├── WebSocket management
├── Audio streaming logic
├── Error handling
└── Connection state

utils/audioUtils.ts
├── Format conversion
├── Audio processing
└── Browser compatibility
```

### WebSocket Message Flow
```
1. Frontend connects to WebSocket
2. User clicks "Start" → begin audio streaming
3. Continuous audio chunks: Frontend → Backend → Gemini
4. Continuous audio responses: Gemini → Backend → Frontend
5. User voice commands processed by Gemini
6. Tool executions happen backend-only
7. Gemini audio responses reach user
8. Process continues until all emails done
```

### Key Integration Points

**Replace PyAudio with WebSocket** (main.py lines 148-166):
```python
# Current: recorder.get_audio_data()
# New: await websocket.receive_bytes()

# Current: player.queue_audio(response.data)  
# New: await websocket.send_bytes(response.data)
```

**Maintain Existing Logic**:
- EmailManager workflow unchanged
- Tool execution flow unchanged
- Gemini session management unchanged
- Error handling patterns unchanged

## Minimal WebSocket Requirements for Voice-Only

The frontend only needs:

1. **Audio Input**: User voice → Backend → Gemini
2. **Audio Output**: Gemini → Backend → Frontend → User
3. **Session Control**: Start/Stop buttons (optional - could auto-start)

### What the Frontend WON'T Need

- ❌ Email display (Gemini reads it aloud)
- ❌ Progress indicators (Gemini announces "Email 3 of 10")  
- ❌ Tool execution status (Gemini says "I've archived that email")
- ❌ Action buttons (voice commands only)
- ❌ Error messages (Gemini handles/announces errors)

### Simplified WebSocket Protocol

**Frontend → Backend:**
```typescript
{ type: "audio_chunk", data: ArrayBuffer }
{ type: "start_session" }  // Optional
{ type: "stop_session" }   // Optional
```

**Backend → Frontend:**
```typescript
{ type: "audio_response", data: ArrayBuffer }
```

## Risk Mitigation

### Potential Issues
1. **Audio Latency**: WebSocket + network vs direct PyAudio
2. **Browser Compatibility**: WebRTC/WebSocket support
3. **Connection Stability**: WebSocket disconnections
4. **Audio Quality**: Compression/format conversion

### Mitigation Strategies
1. **Optimize Audio Pipeline**: Minimal buffering, efficient encoding
2. **Progressive Enhancement**: Fallback for unsupported browsers
3. **Reconnection Logic**: Automatic session recovery
4. **Quality Testing**: Extensive audio format testing

## Success Criteria

### Phase 1 Success
- FastAPI server runs and accepts WebSocket connections
- Audio bridge successfully streams to/from Gemini Live
- Core email processing logic works via WebSocket

### Phase 2 Success  
- Next.js frontend captures microphone audio
- WebSocket communication established
- Audio playback works in browser

### Phase 3 Success
- Complete email workflow works end-to-end
- Audio quality acceptable for voice interaction
- Error handling prevents crashes

### Phase 4 Success
- Deployed application accessible via web browser
- Performance acceptable for real-world usage
- Stable operation under normal load

## Implementation Order

1. **Start with Step 1.1**: Extract core components from main.py
2. **Then Step 1.3**: Create audio bridge (most critical component)
3. **Then Step 1.2**: FastAPI server to tie everything together
4. **Test backend thoroughly** before moving to frontend
5. **Phase 2**: Frontend development
6. **Phase 3**: Integration testing
7. **Phase 4**: Deployment

This approach prioritizes **preserving your main.py logic** while creating the minimal infrastructure needed for web-based voice interaction. The approach is incremental - each phase builds on the previous one and can be tested independently.
