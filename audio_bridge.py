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
                    # Audio flowing silently (removed spam logs)
                    await gemini_session.send_realtime_input(
                        audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                    )
                elif "text" in message:
                    # JSON message - handle control signals
                    try:
                        data = json.loads(message["text"])
                        # Control message received (removed spam logs)
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
                print("\n🔄 Gemini interrupted")
                await self.websocket.send_text(json.dumps({"type": "audio_interrupted"}))
            
            # Handle audio data - send to WebSocket
            elif response.data is not None:
                await self.websocket.send_bytes(response.data)  # Send raw bytes
            
            # Handle tool calls - this is where user commands should trigger
            elif response.tool_call:
                print(f"🤖 Gemini wants to call tools: {[fc.name for fc in response.tool_call.function_calls]}")
                return response.tool_call
            
            # Handle other response types
            elif response.server_content:
                print(f"🤖 Gemini server content: {response.server_content}")
            elif hasattr(response, 'text') and response.text:
                print(f"🤖 Gemini text response: {response.text}")
            else:
                print(f"🤖 Gemini response type: {type(response)}")
                # Debug all response attributes
                attrs = [attr for attr in dir(response) if not attr.startswith('_')]
                print(f"🤖 Response attributes: {attrs}")
                for attr in ['tool_call', 'data', 'server_content', 'text']:
                    if hasattr(response, attr):
                        value = getattr(response, attr)
                        print(f"🤖   {attr}: {value} (type: {type(value)})")
                
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
                    
                    # Test command removed - voice commands should work now
                    
                    # Start audio streaming
                    await audio_bridge.start_streaming(session, nav_tools)
                    
                    # Create tasks for handling WebSocket messages and Gemini responses
                    async def handle_websocket_messages():
                        """Handle incoming WebSocket messages"""
                        print("🎤 Starting WebSocket message handler - waiting for voice input...")
                        while not nav_tools.should_end_session():
                            try:
                                message = await asyncio.wait_for(websocket.receive(), timeout=0.5)
                                result = await audio_bridge.handle_websocket_message(message, session)
                                if result == "stop_session":
                                    print("🛑 Stop session requested via WebSocket")
                                    nav_tools.end_session()
                                    break
                            except asyncio.TimeoutError:
                                # Normal timeout, continue listening for voice input
                                continue
                            except asyncio.CancelledError:
                                print("🎤 WebSocket message handler cancelled")
                                break
                            except Exception as e:
                                # Don't spam logs with WebSocket errors
                                if "disconnect" not in str(e).lower():
                                    print(f"⚠️ WebSocket error: {e}")
                                break
                        
                        print("🎤 WebSocket message handler ended")
                    
                    async def handle_gemini_responses():
                        """Continuous Gemini Live response handler - runs for entire session"""
                        print("🤖 Starting CONTINUOUS Gemini response handler...")
                        response_count = 0
                        
                        try:
                            # Continuous listening loop - don't exit when Gemini finishes speaking
                            while not nav_tools.should_end_session():
                                try:
                                    # Use timeout to periodically check session status
                                    async for response in session.receive():
                                        response_count += 1
                                        print(f"🤖 Response #{response_count}")
                                        
                                        if nav_tools.should_end_session():
                                            print("🤖 Session ending, breaking from response loop")
                                            break
                                        
                                        # Let audio bridge handle audio responses
                                        tool_call = await audio_bridge.handle_gemini_response(response)
                                        
                                        # Handle tool calls (this is where user commands get processed)
                                        if tool_call:
                                            print(f"🔧 Processing tool calls: {[fc.name for fc in tool_call.function_calls]}")
                                            function_responses = []
                                            
                                            for fc in tool_call.function_calls:
                                                print(f"🔧 Executing tool: {fc.name}")
                                                function_response = await handle_tool_execution(
                                                    email_info.get('gmail_agent'), fc, nav_tools
                                                )
                                                function_responses.append(function_response)
                                            
                                            # Send tool responses back to Gemini
                                            await session.send_tool_response(function_responses=function_responses)
                                            
                                            # Check if session should end after tool execution
                                            if nav_tools.should_end_session():
                                                print("🎯 Tool execution completed - session should end")
                                                break
                                        
                                        # If Gemini indicates turn is complete, continue listening for new input
                                        if (hasattr(response, 'server_content') and 
                                            response.server_content and 
                                            response.server_content.turn_complete):
                                            print("🤖 Gemini turn complete - continuing to listen for user input...")
                                            # Don't break - keep listening for more responses triggered by user input
                                            
                                except StopAsyncIteration:
                                    # session.receive() ended, but session should continue
                                    print("🤖 Gemini receive ended, but session continues...")
                                    await asyncio.sleep(0.1)
                                    continue
                                except Exception as response_error:
                                    print(f"⚠️ Gemini response error: {response_error}")
                                    await asyncio.sleep(0.1)
                                    continue
                                
                        except asyncio.CancelledError:
                            print("🤖 Continuous Gemini response handler cancelled")
                        except Exception as e:
                            print(f"⚠️ Continuous Gemini handler error: {e}")
                        
                        print("🤖 Continuous Gemini response handler ended")
                    
                    # Run both tasks concurrently
                    websocket_task = asyncio.create_task(handle_websocket_messages())
                    gemini_task = asyncio.create_task(handle_gemini_responses())
                    
                    # Wait specifically for the session to end (when user gives a command)
                    # Don't exit just because a task completes - wait for nav_tools signal
                    try:
                        while not nav_tools.should_end_session():
                            # Check if either task has failed
                            if websocket_task.done() and websocket_task.exception():
                                print(f"❌ WebSocket task failed: {websocket_task.exception()}")
                                break
                            if gemini_task.done() and gemini_task.exception():
                                print(f"❌ Gemini task failed: {gemini_task.exception()}")
                                break
                            
                            # Small delay to prevent busy waiting
                            await asyncio.sleep(0.1)
                        
                        print("🎯 Session ending - nav_tools.should_end_session() is True")
                        
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
