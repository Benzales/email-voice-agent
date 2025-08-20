# FastAPI Backend Integration

This directory contains the FastAPI backend that wraps your existing `main.py` logic for web-based voice interaction.

## 🏗️ Architecture

The backend preserves your original `main.py` logic by extracting core components into reusable modules:

```
main.py (unchanged) ← Your original terminal app
├── email_service.py ← EmailManager + email fetching
├── gemini_service.py ← MCP setup + Gemini sessions  
├── audio_bridge.py ← WebSocket ↔ Gemini audio streaming
├── models.py ← Type-safe WebSocket messages
└── fastapi_server.py ← Web server orchestration
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install fastapi uvicorn websockets pydantic
# Your existing dependencies (google-genai, mcp-agent, etc.) are already installed
```

### 2. Test Backend Integration
```bash
python test_backend.py
```

### 3. Start the Server
```bash
python start_server.py
# Or directly: python fastapi_server.py
```

### 4. Verify Server
- **Health Check**: http://localhost:8000/health
- **API Docs**: http://localhost:8000/docs  
- **WebSocket**: ws://localhost:8000/ws/voice-session

## 📡 API Endpoints

### REST Endpoints
- `GET /` - Basic server info
- `GET /health` - Health check with service status
- `GET /session/status` - Current session information

### WebSocket Endpoints
- `ws://localhost:8000/ws/voice-session` - Main voice session
- `ws://localhost:8000/ws/test-audio` - Audio pipeline testing

## 🎵 WebSocket Protocol

### Voice Session Messages

**Frontend → Backend:**
```typescript
// Raw audio data (PCM 16kHz)
WebSocket.send(audioBytes)

// Control messages
{ type: "start_session" }
{ type: "stop_session" }
```

**Backend → Frontend:**
```typescript
// Audio responses from Gemini
WebSocket.send(audioBytes)

// Status updates
{ type: "session_status", status: "active", progress: {...} }
{ type: "error", message: "...", recoverable: true }
```

## 🧪 Testing

### Backend Integration Test
```bash
python test_backend.py
```
Tests all components work together:
- ✅ MCP connection setup
- ✅ Gmail tool discovery  
- ✅ Email fetching
- ✅ Navigation tools
- ✅ Session configuration
- ✅ Pydantic models

### Audio Pipeline Test
Connect to `ws://localhost:8000/ws/test-audio` to test audio streaming without full email processing.

## 🔧 Configuration

The server uses the same environment variables as your `main.py`:
- `GEMINI_API_KEY` - Required for Gemini Live API

## 🎯 Voice-Only Design

The FastAPI backend maintains your voice-first approach:
- **No complex UI** - Just audio streaming
- **Gemini handles all interaction** - Tool execution results go to Gemini, not frontend
- **Minimal WebSocket protocol** - Only audio + basic control messages
- **Session isolation** - Each email gets its own clean Gemini session

## 🔄 How It Works

1. **Initialization**: Server starts, connects to MCP, discovers Gmail tools
2. **Session Start**: Frontend connects via WebSocket
3. **Email Fetching**: Server fetches inbox emails using your existing logic
4. **Per-Email Processing**: 
   - Create isolated Gemini Live session
   - Stream audio bidirectionally via WebSocket
   - Execute Gmail tools (archive, delete, reply, etc.)
   - Move to next email automatically
5. **Session End**: All emails processed or user disconnects

## 🚀 Next Steps

With the backend running, you can:

1. **Test with curl/wscat**:
   ```bash
   wscat -c ws://localhost:8000/ws/voice-session
   ```

2. **Build Next.js frontend** (Phase 2 of implementation plan)

3. **Deploy backend** to Railway/Render for production

## 🔍 Debugging

- Check logs in terminal where server is running
- Visit `/health` endpoint to verify all services are connected
- Use `/ws/test-audio` to test audio pipeline separately
- Run `test_backend.py` to verify component integration

Your original `main.py` remains completely unchanged and functional - this FastAPI backend is a parallel implementation that reuses your core logic!
