"""
Audio bridge service for WebSocket ↔ Gemini Live audio streaming
Replaces direct PyAudio components with WebSocket-based audio handling
"""

import asyncio
import json
from typing import Optional, Dict, Any
from google.genai import types


class WebSocketAudioBridge:
    """
    Manages bidirectional audio streaming between WebSocket and Gemini Live
    Replaces AudioRecorder and AudioPlayer from main.py
    """
    
    def __init__(self, websocket):
        self.websocket = websocket
        self.is_streaming = False
        self.audio_tasks = []
    
    async def start_streaming(self, gemini_session, nav_tools):
        """
        Start bidirectional audio streaming
        
        Args:
            gemini_session: Gemini Live session
            nav_tools: Navigation tools for session control
        """
        if self.is_streaming:
            return
        
        self.is_streaming = True
        print("🎵 Started WebSocket ↔ Gemini audio streaming")
        
        # Note: Audio streaming will be handled in the main session loop
        # This method just sets the flag and prepares the bridge
    
    async def handle_websocket_message(self, message, gemini_session):
        """
        Handle incoming WebSocket message and forward audio to Gemini
        """
        try:
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Raw audio data - send directly to Gemini
                    audio_data = message["bytes"]
                    await gemini_session.send_realtime_input(
                        audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                    )
                elif "text" in message:
                    # JSON message - handle control signals
                    try:
                        data = json.loads(message["text"])
                        if data.get("type") == "stop_session":
                            print("🛑 Received stop signal from frontend")
                            return "stop_session"
                    except json.JSONDecodeError:
                        # Not JSON, ignore
                        pass
        except Exception as e:
            print(f"⚠️ Error handling WebSocket message: {e}")
        
        return None
    
    async def handle_gemini_response(self, response):
        """
        Handle Gemini response and forward audio to WebSocket
        """
        try:
            # Handle interruptions
            if response.server_content and response.server_content.interrupted is True:
                print("\n🔄 Interrupted")
                await self.websocket.send_text(json.dumps({"type": "audio_interrupted"}))
            
            # Handle audio data - send to WebSocket
            elif response.data is not None:
                await self.websocket.send_bytes(response.data)  # Send raw bytes
            
            # Tool calls are handled elsewhere
            elif response.tool_call:
                return response.tool_call
                
        except Exception as e:
            print(f"⚠️ Error handling Gemini response: {e}")
            await self._send_error_to_frontend(f"Audio output error: {str(e)}")
        
        return None
    
    async def stop_streaming(self):
        """Stop all audio streaming tasks"""
        if not self.is_streaming:
            return
        
        self.is_streaming = False
        
        # Cancel all audio tasks
        for task in self.audio_tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete cancellation
        if self.audio_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self.audio_tasks, return_exceptions=True),
                    timeout=2.0
                )
            except asyncio.TimeoutError:
                print("⚠️ Audio tasks did not cancel within timeout")
        
        self.audio_tasks = []
        print("🔇 Stopped WebSocket ↔ Gemini audio streaming")
    
    async def _send_error_to_frontend(self, error_message: str):
        """Send error message to frontend via WebSocket"""
        try:
            await self.websocket.send_text(json.dumps({
                "type": "error",
                "message": error_message,
                "recoverable": True
            }))
        except Exception as e:
            print(f"Failed to send error to frontend: {e}")


async def create_gemini_session_with_websocket(gemini_session_config: Dict[str, Any], websocket, email_info: Dict[str, str]):
    """
    Create and manage a Gemini Live session with WebSocket audio bridge
    Replaces process_single_email_session from main.py but with WebSocket integration
    
    Args:
        gemini_session_config: Configuration for Gemini session
        websocket: WebSocket connection to frontend
        email_info: Current email information
        
    Returns:
        Boolean indicating session success
    """
    from gemini_service import client, model, handle_tool_execution
    
    session_completed = False
    audio_bridge = None
    
    try:
        # Create session timeout (2 minutes like main.py)
        session_timeout = 120.0
        async with asyncio.timeout(session_timeout):
            async with client.aio.live.connect(model=model, config=gemini_session_config) as session:
                
                print(f"📧 Processing Email via WebSocket: {email_info['display_text']}")
                
                try:
                    # Create audio bridge
                    audio_bridge = WebSocketAudioBridge(websocket)
                    nav_tools = email_info.get('nav_tools')  # Passed in from caller
                    
                    # Send initial email information to Gemini
                    await session.send_realtime_input(
                        text=f"Please read me this email and ask what I'd like to do with it. The email is: {email_info['display_text']} [Current email ID: {email_info['id']}]."
                    )
                    
                    # Start audio streaming
                    await audio_bridge.start_streaming(session, nav_tools)
                    
                    # Create tasks for handling WebSocket messages and Gemini responses
                    async def handle_websocket_messages():
                        """Handle incoming WebSocket messages"""
                        while not nav_tools.should_end_session():
                            try:
                                message = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                                result = await audio_bridge.handle_websocket_message(message, session)
                                if result == "stop_session":
                                    nav_tools.end_session()
                                    break
                            except asyncio.TimeoutError:
                                continue
                            except Exception as e:
                                print(f"⚠️ WebSocket message error: {e}")
                                break
                    
                    async def handle_gemini_responses():
                        """Handle Gemini Live responses"""
                        try:
                            async for response in session.receive():
                                if nav_tools.should_end_session():
                                    break
                                
                                # Let audio bridge handle audio responses
                                tool_call = await audio_bridge.handle_gemini_response(response)
                                
                                # Handle tool calls
                                if tool_call:
                                    function_responses = []
                                    
                                    for fc in tool_call.function_calls:
                                        function_response = await handle_tool_execution(
                                            email_info.get('gmail_agent'), fc, nav_tools
                                        )
                                        function_responses.append(function_response)
                                    
                                    # Send tool responses back to Gemini
                                    await session.send_tool_response(function_responses=function_responses)
                                    
                                    # Check if session should end after tool execution
                                    if nav_tools.should_end_session():
                                        break
                        except Exception as e:
                            print(f"⚠️ Gemini response error: {e}")
                    
                    # Run both tasks concurrently
                    websocket_task = asyncio.create_task(handle_websocket_messages())
                    gemini_task = asyncio.create_task(handle_gemini_responses())
                    
                    # Wait for either task to complete or session to end
                    try:
                        await asyncio.wait(
                            [websocket_task, gemini_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                    finally:
                        # Cancel remaining tasks
                        websocket_task.cancel()
                        gemini_task.cancel()
                        try:
                            await asyncio.gather(websocket_task, gemini_task, return_exceptions=True)
                        except:
                            pass
                    
                    session_completed = True
                    
                except Exception as session_error:
                    print(f"⚠️ Session error: {session_error}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": f"Session error: {str(session_error)}",
                        "recoverable": False
                    }))
                
                finally:
                    # Stop audio streaming
                    if audio_bridge:
                        await audio_bridge.stop_streaming()
    
    except asyncio.TimeoutError:
        print("⏰ Session timed out after 2 minutes")
        await websocket.send_text(json.dumps({
            "type": "error", 
            "message": "Session timed out",
            "recoverable": False
        }))
    except Exception as connection_error:
        print(f"❌ Failed to connect to Gemini: {connection_error}")
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Connection error: {str(connection_error)}",
            "recoverable": False
        }))
    
    return session_completed


def validate_audio_format(audio_data: bytes) -> bool:
    """
    Validate that audio data is in the expected format
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Boolean indicating if format is valid
    """
    # Basic validation - check if we have data and it's reasonable size
    if not audio_data:
        return False
    
    # Audio chunks should be reasonably sized (not too small or too large)
    # For 16kHz PCM at 5ms intervals, expect roughly 160 bytes per chunk
    if len(audio_data) < 10 or len(audio_data) > 10000:
        return False
    
    return True


async def send_audio_status(websocket, status: str, message: str = ""):
    """
    Send audio status updates to frontend
    
    Args:
        websocket: WebSocket connection
        status: Status type ("started", "stopped", "error")
        message: Optional status message
    """
    try:
        await websocket.send(json.dumps({
            "type": "audio_status",
            "status": status,
            "message": message
        }))
    except Exception as e:
        print(f"Failed to send audio status: {e}")
