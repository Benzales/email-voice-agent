# OpenAI Realtime API Migration Plan

## Overview

This document outlines the comprehensive plan to replace Google Gemini Live API with OpenAI's Realtime API in the Voice Email Agent. The migration maintains the existing web architecture, OAuth authentication, and Gmail integration while switching the AI voice processing backend.

## 🎯 Migration Objectives

1. **Replace Gemini Live** with OpenAI Realtime API for voice processing
2. **Maintain existing functionality** - all voice commands and email operations
3. **Preserve web architecture** - FastAPI backend + Next.js frontend
4. **Keep OAuth authentication** and multi-user support intact
5. **Maintain Gmail MCP integration** for email operations
6. **Ensure audio quality** and real-time streaming performance

## 📋 Current Architecture Analysis

### Components That Need Modification

#### 🔴 **Major Changes Required**
1. **`gemini_service.py`** → **`openai_service.py`**
   - Replace Gemini Live client with OpenAI Realtime client
   - Convert tool schemas from Gemini format to OpenAI format
   - Update system instructions and session configuration

2. **`audio_bridge.py`** → **`openai_audio_bridge.py`**
   - Replace Gemini Live session handling with OpenAI WebSocket connection
   - Update audio format handling (OpenAI uses different audio specs)
   - Modify response processing for OpenAI's event-based protocol

3. **`fastapi_server.py`**
   - Update imports and service initialization
   - Replace Gemini session management with OpenAI session management
   - Update lifespan management for OpenAI connections

#### 🟡 **Minor Changes Required**
4. **`models.py`**
   - Update type definitions for OpenAI-specific message formats
   - Add OpenAI event models and response types

5. **Frontend Components**
   - Audio format adjustments (if needed)
   - Update any Gemini-specific references in UI

6. **Configuration Files**
   - Update environment variable names
   - Modify dependency requirements

#### 🟢 **No Changes Required**
- **OAuth system** (`oauth_service.py`, `user_session.py`) - Remains unchanged
- **Gmail integration** (`email_service.py`, `email_service_oauth.py`) - Remains unchanged
- **MCP system** (`custom_tools.py`) - Remains unchanged
- **Frontend authentication** - Remains unchanged
- **WebSocket protocol** - Core protocol remains the same

## 🔧 Technical Implementation Plan

### Phase 1: Environment Setup

#### 1.1 Update Dependencies
**File: `requirements-fastapi.txt`**
```bash
# OpenAI Realtime API dependencies (replacing Gemini completely)
openai>=1.12.0
scipy>=1.11.0  # For audio resampling
websockets>=12.0  # Already present
```

**File: `pyproject.toml`**
```toml
dependencies = [
    # OpenAI Realtime API (replacing Gemini completely)
    "openai>=1.12.0",
    "scipy>=1.11.0",  # For high-quality audio resampling
    "python-dotenv",
    # ... keep all other dependencies (NO google-genai)
]
```

#### 1.2 Environment Variables
**Instructions for user:**
Add to your `.env` file:
```bash
# OpenAI API key (replacing Gemini completely)
OPENAI_API_KEY=your_openai_api_key_here

# Remove GEMINI_API_KEY - no longer needed
# GEMINI_API_KEY=your_old_gemini_key  # DELETE THIS LINE
```

### Phase 2: Core Service Migration

#### 2.1 Create OpenAI Service (`openai_service.py`)

**Key Changes:**
- Replace `google.genai.Client` with `openai.OpenAI`
- Convert MCP tools to OpenAI function format
- Implement OpenAI Realtime WebSocket connection
- Adapt system instructions for OpenAI's format

**Core Functions to Implement:**
```python
# Replace gemini_service.py functions
async def setup_openai_connection() -> OpenAIRealtimeClient
def convert_mcp_to_openai_tools(mcp_tools: List) -> List[Dict]
def create_openai_session_config(tools: List) -> Dict
async def handle_openai_tool_execution(tool_call, gmail_agent, nav_tools)
async def process_openai_responses(session, gmail_agent, nav_tools, websocket)
```

**OpenAI Realtime API Specifications:**
- **WebSocket URL**: `wss://api.openai.com/v1/realtime`
- **Audio Format**: 24kHz PCM16 (different from Gemini's 48kHz)
- **Protocol**: Event-based (not request-response like Gemini)
- **Authentication**: Bearer token in WebSocket headers

#### 2.2 Create OpenAI Audio Bridge (`openai_audio_bridge.py`)

**Key Changes:**
- Replace Gemini Live session with OpenAI Realtime WebSocket
- Handle OpenAI's event-based protocol (`conversation.item.created`, `response.audio.delta`, etc.)
- Convert audio formats (48kHz browser → 24kHz OpenAI)
- Implement OpenAI's conversation state management

**Audio Pipeline Changes:**
```
Current: Browser 48kHz → Gemini Live 48kHz
New:     Browser 48kHz → Resample to 24kHz → OpenAI Realtime 24kHz
```

### Phase 3: Protocol Adaptation

#### 3.1 OpenAI Realtime Protocol vs Gemini Live

**Gemini Live (Current):**
```python
# Session-based with direct method calls
await session.send_realtime_input(audio=audio_blob)
async for response in session.receive():
    if response.data:  # Audio response
        await websocket.send_bytes(response.data)
```

**OpenAI Realtime (Target):**
```python
# Event-based WebSocket protocol
await ws.send(json.dumps({
    "type": "input_audio_buffer.append",
    "audio": base64_audio
}))

# Handle events
if event["type"] == "response.audio.delta":
    audio_data = base64.b64decode(event["delta"])
    await websocket.send_bytes(audio_data)
```

#### 3.2 Tool Calling Format Conversion

**Gemini Format (Current):**
```python
{
    "name": "gmail_modify_email",
    "description": "Archive email by removing INBOX label",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "removeLabelIds": {"type": "array"}
        }
    }
}
```

**OpenAI Format (Target):**
```python
{
    "name": "gmail_modify_email",
    "description": "Archive email by removing INBOX label",
    "parameters": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "removeLabelIds": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["id"]
    }
}
```

### Phase 4: Audio Processing Updates

#### 4.1 Frontend Audio Changes
**File: `web/src/hooks/useVoiceSession.ts`**

Current audio processing sends 48kHz directly:
```typescript
// May need audio resampling for OpenAI's 24kHz requirement
// Or handle resampling on backend
```

#### 4.2 Backend Audio Processing
**New audio conversion pipeline:**
```python
# Convert browser 48kHz to OpenAI 24kHz
def resample_audio(audio_data: bytes, from_rate: int = 48000, to_rate: int = 24000) -> bytes:
    # Implement audio resampling
    pass
```

### Phase 5: Session Management Updates

#### 5.1 Replace Session Lifecycle
**Current Gemini Flow:**
```python
async with client.aio.live.connect(model=model, config=config) as session:
    # Process emails in isolated sessions
```

**New OpenAI Flow:**
```python
async with websockets.connect(
    "wss://api.openai.com/v1/realtime",
    extra_headers={"Authorization": f"Bearer {api_key}"}
) as websocket:
    # Manage conversation state manually
```

### Phase 6: Error Handling & Recovery

#### 6.1 OpenAI-Specific Error Handling
- **Rate limiting**: OpenAI has different rate limits
- **Connection errors**: Different reconnection strategies
- **Audio buffer management**: OpenAI requires explicit buffer management

## 🚀 Step-by-Step Implementation Guide

### Step 1: Backup and Preparation
```bash
# Create backup branch
git checkout -b backup-gemini-implementation

# Create migration branch
git checkout -b migrate-to-openai-realtime
```

### Step 2: Install OpenAI Dependencies
```bash
# Update requirements
pip install openai>=1.12.0

# Test OpenAI connection
python -c "import openai; print('OpenAI library installed successfully')"
```

### Step 3: Environment Configuration
Add to your `.env` file:
```bash
OPENAI_API_KEY=your_openai_api_key_here
```

### Step 4: Create OpenAI Service Module

Create `openai_service.py`:
```python
"""
OpenAI Realtime API integration service
Replaces gemini_service.py with OpenAI Realtime API
"""

import asyncio
import os
import json
import base64
import websockets
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")

# OpenAI Realtime API configuration
REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-10-01"

# System instruction adapted for OpenAI
system_instruction = """You are a voice-driven Gmail assistant with full access to Gmail API through function calling.

## PRIMARY BEHAVIOR - Single Email Focus:
- You will be provided with information for ONE email at a time
- For the email, announce ONLY: sender and subject
- After reading the email, ask what the user would like to do
- Wait for the user's command before any action
- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next
- **CRITICAL WORKFLOW**: After you execute ANY action on an email, you MUST immediately call the complete_current_email function. This is mandatory.
- **CRITICAL WORKFLOW**: If the user says "skip", "next", "continue", etc., immediately call the complete_current_email function

## Voice Interaction:
- Speak clearly and at a moderate pace
- Use natural language to describe what you're doing
- Announce results concisely

## Email Reading Format:
When provided with email info, read it as:
"From [sender] - [subject]. What would you like to do with this email?"

## Important Action Instructions:
- **CRITICAL**: When archiving an email, you MUST use gmail_modify_email with removeLabelIds: ["INBOX"]. Do NOT add labels like "ARCHIVED". Archiving means removing from the inbox.
"""

class OpenAIRealtimeClient:
    """Manages OpenAI Realtime API connection and conversation"""
    
    def __init__(self):
        self.websocket = None
        self.session_config = None
        self.tools = []
    
    async def connect(self, tools: List[Dict], gmail_agent, nav_tools):
        """Connect to OpenAI Realtime API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        self.websocket = await websockets.connect(REALTIME_API_URL, extra_headers=headers)
        self.tools = tools
        
        # Send session configuration
        await self._send_session_config(tools)
        
        return self
    
    async def _send_session_config(self, tools: List[Dict]):
        """Send initial session configuration to OpenAI"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_instruction,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 200
                },
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            }
        }
        await self.websocket.send(json.dumps(config))
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to OpenAI"""
        # Convert to base64 for OpenAI
        audio_base64 = base64.b64encode(audio_data).decode()
        
        message = {
            "type": "input_audio_buffer.append",
            "audio": audio_base64
        }
        await self.websocket.send(json.dumps(message))
    
    async def send_text(self, text: str):
        """Send text message to start conversation"""
        message = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": text
                    }
                ]
            }
        }
        await self.websocket.send(json.dumps(message))
        
        # Trigger response generation
        await self.websocket.send(json.dumps({"type": "response.create"}))
    
    async def receive_events(self):
        """Receive events from OpenAI Realtime API"""
        async for message in self.websocket:
            try:
                event = json.loads(message)
                yield event
            except json.JSONDecodeError:
                print(f"Failed to decode message: {message}")
                continue
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()

# Core functions to replace gemini_service.py functions
async def setup_openai_connection() -> Tuple[Any, Any, OpenAIRealtimeClient]:
    """Setup OpenAI Realtime connection (completely replaces setup_mcp_connection)"""
    # Import MCP setup directly (no Gemini dependency)
    from mcp_agent.app import MCPApp
    from mcp_agent.agents.agent import Agent
    
    # Setup MCP connection for Gmail tools (independent of Gemini)
    mcp_app = MCPApp()
    await mcp_app.start()
    gmail_agent = mcp_app.get_agent("gmail")
    
    # Create OpenAI client
    client = OpenAIRealtimeClient()
    return mcp_app, gmail_agent, client

def convert_mcp_to_openai_tools(mcp_tools: List) -> List[Dict]:
    """Convert MCP tools to OpenAI function format"""
    openai_tools = []
    
    for tool in mcp_tools:
        openai_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["inputSchema"]
            }
        }
        
        # Ensure required fields are present
        if "required" not in openai_tool["function"]["parameters"]:
            openai_tool["function"]["parameters"]["required"] = []
        
        openai_tools.append(openai_tool)
    
    return openai_tools

def create_openai_session_config(openai_tools: List[Dict]) -> Dict[str, Any]:
    """Create OpenAI session configuration (replaces create_gemini_session_config)"""
    return {
        "tools": openai_tools,
        "instructions": system_instruction,
        "modalities": ["text", "audio"],
        "voice": "alloy"
    }

async def handle_openai_tool_execution(tool_call, gmail_agent, nav_tools=None):
    """Handle OpenAI function call execution"""
    try:
        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])
        
        # Handle custom complete_current_email tool
        if function_name == "complete_current_email" and nav_tools:
            result = await nav_tools.execute_complete_current_email()
            return {
                "type": "function_call_output",
                "call_id": tool_call["id"],
                "output": json.dumps(result)
            }
        
        # Handle MCP tools
        else:
            print(f"🎯 Executing {function_name} with args: {function_args}")
            
            result = await gmail_agent.call_tool(function_name, arguments=function_args)
            
            # Extract text content from MCP result
            response_content = {}
            if hasattr(result, 'content') and result.content:
                text_parts = []
                for content_item in result.content:
                    if hasattr(content_item, 'text'):
                        text_parts.append(content_item.text)
                response_content["result"] = "\n".join(text_parts)
            else:
                response_content["result"] = "Tool executed successfully"
            
            return {
                "type": "function_call_output",
                "call_id": tool_call["id"],
                "output": json.dumps(response_content)
            }
    
    except Exception as e:
        print(f"❌ Tool execution failed: {e}")
        return {
            "type": "function_call_output",
            "call_id": tool_call["id"],
            "output": json.dumps({"error": str(e)})
        }

# Keep existing cleanup function
async def cleanup_openai_resources(mcp_app, gmail_agent, openai_client):
    """Cleanup OpenAI and MCP resources"""
    if openai_client:
        await openai_client.close()
    
    # Cleanup MCP resources
    from gemini_service import cleanup_mcp_resources
    await cleanup_mcp_resources(mcp_app, gmail_agent)
```

### Step 5: Create OpenAI Audio Bridge

Create `openai_audio_bridge.py`:
```python
"""
OpenAI Realtime API audio bridge for WebSocket ↔ OpenAI audio streaming
Replaces audio_bridge.py with OpenAI Realtime API integration
"""

import asyncio
import json
import base64
from typing import Optional, Dict, Any

class OpenAIAudioBridge:
    """
    Manages bidirectional audio streaming between WebSocket and OpenAI Realtime API
    Replaces WebSocketAudioBridge for OpenAI integration
    """
    
    def __init__(self, websocket):
        self.websocket = websocket
        self.is_streaming = False
        self.openai_client = None
    
    async def start_streaming(self, openai_client, nav_tools):
        """Start bidirectional audio streaming with OpenAI"""
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.openai_client = openai_client
        print("🎵 Started WebSocket ↔ OpenAI Realtime audio streaming")
    
    async def handle_websocket_message(self, message, openai_client):
        """Handle incoming WebSocket message and forward audio to OpenAI"""
        try:
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Raw audio data - send to OpenAI
                    audio_data = message["bytes"]
                    
                    # Debug audio format
                    if len(audio_data) > 0 and hash(audio_data) % 200 == 0:
                        print(f"🔍 Sending to OpenAI: {len(audio_data)} bytes as PCM16 24kHz")
                    
                    # Resample from 48kHz to 24kHz if needed
                    resampled_audio = self._resample_audio(audio_data, 48000, 24000)
                    await openai_client.send_audio(resampled_audio)
                    
                elif "text" in message:
                    # JSON control messages
                    try:
                        data = json.loads(message["text"])
                        if data.get("type") == "stop_session":
                            print("🛑 Received stop signal from frontend")
                            return "stop_session"
                    except json.JSONDecodeError:
                        pass
        except Exception as e:
            print(f"⚠️ Error handling WebSocket message: {e}")
        
        return None
    
    def _resample_audio(self, audio_data: bytes, from_rate: int, to_rate: int) -> bytes:
        """Resample audio from one rate to another"""
        # Simple downsampling by taking every nth sample
        # For production, use librosa or scipy for better quality
        if from_rate == to_rate:
            return audio_data
        
        # Convert bytes to 16-bit samples
        import struct
        samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
        
        # Downsample by taking every nth sample
        ratio = from_rate // to_rate
        downsampled = samples[::ratio]
        
        # Convert back to bytes
        return struct.pack(f'<{len(downsampled)}h', *downsampled)
    
    async def handle_openai_response(self, event):
        """Handle response from OpenAI and forward to WebSocket"""
        try:
            event_type = event.get("type")
            
            if event_type == "response.audio.delta":
                # Audio response from OpenAI
                audio_delta = event.get("delta", "")
                if audio_delta:
                    audio_bytes = base64.b64decode(audio_delta)
                    await self.websocket.send_bytes(audio_bytes)
                    return {"type": "audio", "data": audio_bytes}
            
            elif event_type == "response.audio.done":
                # Audio response completed
                print("🎵 Audio response completed")
                return {"type": "audio_complete"}
            
            elif event_type == "conversation.item.input_audio_transcription.completed":
                # User speech transcription
                transcript = event.get("transcript", "")
                if transcript:
                    print(f"🎤 User said: {transcript}")
                return {"type": "transcript", "text": transcript}
            
            elif event_type == "response.function_call_arguments.done":
                # Function call completed
                function_call = event.get("function_call")
                if function_call:
                    return {"type": "function_call", "call": function_call}
            
            elif event_type == "error":
                # Error from OpenAI
                error = event.get("error", {})
                error_message = error.get("message", "Unknown OpenAI error")
                print(f"❌ OpenAI Error: {error_message}")
                await self.websocket.send_json({
                    "type": "error",
                    "message": f"OpenAI Error: {error_message}",
                    "recoverable": True
                })
                return {"type": "error", "message": error_message}
            
        except Exception as e:
            print(f"⚠️ Error handling OpenAI response: {e}")
            await self._send_error_to_frontend(f"Response handling error: {str(e)}")
        
        return None
    
    async def _send_error_to_frontend(self, error_message: str):
        """Send error message to frontend"""
        try:
            await self.websocket.send_json({
                "type": "error",
                "message": error_message,
                "recoverable": True
            })
        except Exception as e:
            print(f"Failed to send error to frontend: {e}")

async def create_openai_session_with_websocket(openai_session_config: Dict[str, Any], websocket, email_info: Dict[str, str]):
    """
    Create and manage an OpenAI Realtime session with WebSocket audio bridge
    Replaces create_gemini_session_with_websocket
    """
    from openai_service import OpenAIRealtimeClient, handle_openai_tool_execution
    
    session_completed = False
    audio_bridge = None
    openai_client = None
    
    try:
        session_timeout = 120  # 2 minutes like Gemini version
        
        async with asyncio.timeout(session_timeout):
            # Create OpenAI Realtime client
            openai_client = OpenAIRealtimeClient()
            
            # Get tools and MCP agent from session config
            tools = openai_session_config.get("tools", [])
            gmail_agent = openai_session_config.get("gmail_agent")
            nav_tools = email_info.get('nav_tools')
            
            # Connect to OpenAI
            await openai_client.connect(tools, gmail_agent, nav_tools)
            
            print(f"📧 Processing Email via OpenAI: {email_info['display_text']}")
            
            # Create audio bridge
            audio_bridge = OpenAIAudioBridge(websocket)
            
            # Send initial email information to OpenAI
            await openai_client.send_text(
                f"Please read me this email and ask what I'd like to do with it. The email is: {email_info['display_text']} [Current email ID: {email_info['id']}]."
            )
            
            # Start audio streaming
            await audio_bridge.start_streaming(openai_client, nav_tools)
            
            # Main event processing loop
            async for event in openai_client.receive_events():
                # Handle audio and other responses
                result = await audio_bridge.handle_openai_response(event)
                
                if result and result.get("type") == "function_call":
                    # Execute function call
                    function_call = result["call"]
                    response = await handle_openai_tool_execution(function_call, gmail_agent, nav_tools)
                    
                    # Send function result back to OpenAI
                    await openai_client.websocket.send(json.dumps(response))
                    
                    # Check if this was the complete_current_email call
                    if function_call["function"]["name"] == "complete_current_email":
                        print("✅ Email session completed")
                        session_completed = True
                        break
                
                # Handle WebSocket messages from frontend
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=0.01)
                    control_result = await audio_bridge.handle_websocket_message(message, openai_client)
                    if control_result == "stop_session":
                        break
                except asyncio.TimeoutError:
                    # No message from frontend, continue
                    continue
                except Exception as e:
                    print(f"WebSocket receive error: {e}")
                    break
    
    except asyncio.TimeoutError:
        print("⏰ OpenAI session timed out")
        await websocket.send_json({
            "type": "error",
            "message": "Session timed out - moving to next email",
            "recoverable": True
        })
        session_completed = True
    
    except Exception as e:
        print(f"❌ OpenAI session error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": f"Session error: {str(e)}",
            "recoverable": True
        })
    
    finally:
        # Cleanup
        if openai_client:
            await openai_client.close()
    
    return session_completed
```

### Step 6: Update FastAPI Server

Modify `fastapi_server.py`:
```python
# Replace imports
from openai_service import (
    setup_openai_connection, discover_gmail_tools, convert_mcp_to_openai_tools,
    create_navigation_tools, create_openai_session_config, cleanup_openai_resources
)
from openai_audio_bridge import OpenAIAudioBridge, create_openai_session_with_websocket

# Update AppState class
class AppState:
    def __init__(self):
        self.mcp_app = None
        self.gmail_agent = None
        self.openai_client = None  # Add OpenAI client
        self.openai_tools = []     # Change from gemini_tools
        self.current_session: Optional[Dict[str, Any]] = None
        self.is_initialized = False

# Update lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting Email Voice Agent FastAPI Server with OpenAI...")
    
    try:
        # Initialize MCP and OpenAI
        print("📡 Initializing OpenAI and MCP connections...")
        app_state.mcp_app, app_state.gmail_agent, app_state.openai_client = await setup_openai_connection()
        
        # Discover and convert tools
        print("🔧 Discovering Gmail tools...")
        mcp_tools = await discover_gmail_tools(app_state.gmail_agent)
        app_state.openai_tools = convert_mcp_to_openai_tools(mcp_tools)  # Change to openai_tools
        
        app_state.is_initialized = True
        print(f"✅ Server initialized with {len(app_state.openai_tools)} Gmail tools for OpenAI")
        
        yield
        
    except Exception as e:
        print(f"❌ Failed to initialize server: {e}")
        raise
    
    finally:
        print("🧹 Cleaning up resources...")
        if app_state.mcp_app or app_state.gmail_agent or app_state.openai_client:
            await cleanup_openai_resources(app_state.mcp_app, app_state.gmail_agent, app_state.openai_client)
        await shutdown_session_manager()
        print("👋 Server shutdown complete")

# Update WebSocket handler
async def websocket_voice_session(websocket: WebSocket, session_id: str = Query(...)):
    # ... authentication code remains the same ...
    
    try:
        # Create session configuration for OpenAI
        nav_tools = create_navigation_tools()
        session_config = create_openai_session_config(app_state.openai_tools)  # Use openai_tools
        session_config["gmail_agent"] = app_state.gmail_agent  # Add gmail_agent to config
        
        # ... rest of session handling with OpenAI ...
        
        # Process emails with OpenAI
        session_completed = await create_openai_session_with_websocket(
            session_config, websocket, email_info
        )
        
    except Exception as e:
        # ... error handling remains the same ...
```

### Step 7: Update Models (if needed)

Modify `models.py` to add OpenAI-specific types:
```python
# Add OpenAI-specific models
class OpenAIEvent(BaseModel):
    type: str
    event_id: Optional[str] = None
    # Add other OpenAI event fields as needed

class OpenAIFunctionCall(BaseModel):
    id: str
    function: Dict[str, Any]
    type: str = "function"
```

### Step 8: Test the Migration

1. **Test OpenAI Connection:**
```bash
python -c "
import asyncio
from openai_service import OpenAIRealtimeClient
async def test():
    client = OpenAIRealtimeClient()
    print('OpenAI service created successfully')
asyncio.run(test())
"
```

2. **Test Backend Integration:**
```bash
python test_backend.py
```

3. **Test Full Application:**
```bash
python start_server.py
# In another terminal:
cd web && npm run dev
```

## 🔍 Key Differences: Gemini Live vs OpenAI Realtime

### Audio Format
- **Gemini Live**: 48kHz PCM16 (matches browser native)
- **OpenAI Realtime**: 24kHz PCM16 (requires resampling)

### Protocol
- **Gemini Live**: Session-based with async generators
- **OpenAI Realtime**: Event-based WebSocket protocol

### Tool Calling
- **Gemini Live**: Direct function response objects
- **OpenAI Realtime**: JSON-based function calling with call IDs

### Authentication
- **Gemini Live**: API key in client initialization
- **OpenAI Realtime**: Bearer token in WebSocket headers

## 🚨 Potential Issues & Solutions

### Issue 1: Audio Quality Degradation
**Problem**: Resampling 48kHz → 24kHz may reduce quality
**Solution**: Use high-quality resampling (librosa/scipy) or handle on frontend

### Issue 2: Different Event Timing
**Problem**: OpenAI events may have different timing than Gemini
**Solution**: Adjust timeout values and add appropriate buffering

### Issue 3: Tool Call Format Differences
**Problem**: OpenAI function calling has different response format
**Solution**: Implement proper conversion layer in `handle_openai_tool_execution`

### Issue 4: Connection Management
**Problem**: OpenAI WebSocket connection handling differs from Gemini sessions
**Solution**: Implement proper connection pooling and reconnection logic

## 🧪 Testing Strategy

### Unit Tests
1. Test `convert_mcp_to_openai_tools` function
2. Test audio resampling functions
3. Test OpenAI event handling

### Integration Tests
1. Test full email processing workflow
2. Test audio streaming pipeline
3. Test OAuth authentication with OpenAI backend

### Performance Tests
1. Compare audio latency: Gemini Live vs OpenAI Realtime
2. Test concurrent user sessions
3. Measure memory usage with OpenAI connections

## 📝 Post-Migration Checklist

- [ ] All voice commands work correctly
- [ ] Audio quality is acceptable
- [ ] OAuth authentication still works
- [ ] Gmail operations function properly
- [ ] Error handling is robust
- [ ] Performance is comparable to Gemini version
- [ ] Frontend UI updates reflect OpenAI integration
- [ ] Documentation is updated
- [ ] Environment variables are documented
- [ ] Dependencies are properly updated

## 🔄 Rollback Plan

If migration fails:
1. Switch back to `backup-gemini-implementation` branch
2. Restore original environment variables
3. Reinstall Gemini dependencies
4. Verify original functionality

## 📚 Additional Resources

- [OpenAI Realtime API Documentation](https://platform.openai.com/docs/guides/realtime)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)
- [WebSocket Audio Streaming Best Practices](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API)

---

This migration plan provides a comprehensive roadmap for replacing Gemini Live with OpenAI's Realtime API while maintaining all existing functionality and architecture. The modular approach allows for incremental testing and rollback if needed.
