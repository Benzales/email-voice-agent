"""
Audio bridge service for WebSocket ↔ Gemini Live audio streaming
Replaces direct PyAudio components with WebSocket-based audio handling
"""

import asyncio
import json
from typing import Optional, Dict, Any
from google.genai import types
import websockets


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
        
        # Start audio streaming tasks
        input_task = asyncio.create_task(
            self._stream_audio_to_gemini(gemini_session, nav_tools)
        )
        output_task = asyncio.create_task(
            self._stream_audio_from_gemini(gemini_session, nav_tools)
        )
        
        self.audio_tasks = [input_task, output_task]
        
        print("🎵 Started WebSocket ↔ Gemini audio streaming")
    
    async def _stream_audio_to_gemini(self, gemini_session, nav_tools):
        """
        Stream audio from WebSocket to Gemini Live
        Replaces the audio streaming logic from main.py lines 153-166
        """
        try:
            while self.is_streaming and not nav_tools.should_end_session():
                try:
                    # Wait for audio data from WebSocket
                    message = await asyncio.wait_for(self.websocket.recv(), timeout=0.005)
                    
                    # Handle different message types
                    if isinstance(message, bytes):
                        # Raw audio data - send directly to Gemini
                        await gemini_session.send_realtime_input(
                            audio=types.Blob(data=message, mime_type="audio/pcm;rate=16000")
                        )
                    elif isinstance(message, str):
                        # JSON message - handle control signals
                        try:
                            data = json.loads(message)
                            if data.get("type") == "audio_chunk":
                                # Audio data in JSON format
                                audio_data = data.get("data")
                                if audio_data:
                                    await gemini_session.send_realtime_input(
                                        audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                                    )
                            elif data.get("type") == "stop_session":
                                print("🛑 Received stop signal from frontend")
                                nav_tools.end_session()
                                break
                        except json.JSONDecodeError:
                            # Not JSON, ignore
                            pass
                
                except asyncio.TimeoutError:
                    # No audio data received, continue
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed during audio input")
                    break
                except Exception as e:
                    print(f"⚠️ Audio input streaming error: {e}")
                    await self._send_error_to_frontend(f"Audio input error: {str(e)}")
                
                await asyncio.sleep(0.005)  # Match main.py timing
        
        except Exception as e:
            print(f"❌ Fatal error in audio input stream: {e}")
    
    async def _stream_audio_from_gemini(self, gemini_session, nav_tools):
        """
        Stream audio from Gemini Live to WebSocket
        Replaces the audio output logic from main.py lines 186-188
        """
        try:
            async for response in gemini_session.receive():
                if not self.is_streaming or nav_tools.should_end_session():
                    break
                
                try:
                    # Handle interruptions
                    if response.server_content and response.server_content.interrupted is True:
                        print("\n🔄 Interrupted")
                        await self.websocket.send(json.dumps({"type": "audio_interrupted"}))
                    
                    # Handle audio data - send to WebSocket
                    elif response.data is not None:
                        await self.websocket.send(response.data)  # Send raw bytes
                    
                    # Handle other response types (handled elsewhere)
                    elif response.tool_call:
                        # Tool calls are handled by the main session processor
                        pass
                        
                except websockets.exceptions.ConnectionClosed:
                    print("🔌 WebSocket connection closed during audio output")
                    break
                except Exception as e:
                    print(f"⚠️ Audio output streaming error: {e}")
                    await self._send_error_to_frontend(f"Audio output error: {str(e)}")
        
        except Exception as e:
            print(f"❌ Fatal error in audio output stream: {e}")
    
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
            await self.websocket.send(json.dumps({
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
                    
                    # Start audio streaming and response processing
                    await audio_bridge.start_streaming(session, nav_tools)
                    
                    # Main response processing loop (similar to main.py lines 176-258)
                    while not nav_tools.should_end_session():
                        try:
                            async for response in session.receive():
                                try:
                                    # Handle interruptions
                                    if response.server_content and response.server_content.interrupted is True:
                                        print("\n🔄 Interrupted")
                                        await websocket.send_text(json.dumps({"type": "audio_interrupted"}))
                                    
                                    # Handle audio data - handled by audio bridge
                                    elif response.data is not None:
                                        # Audio streaming is handled by the audio bridge
                                        pass
                                    
                                    # Handle tool calls
                                    elif response.tool_call:
                                        function_responses = []
                                        
                                        for fc in response.tool_call.function_calls:
                                            function_response = await handle_tool_execution(
                                                email_info.get('gmail_agent'), fc, nav_tools
                                            )
                                            function_responses.append(function_response)
                                        
                                        # Send tool responses back to Gemini
                                        await session.send_tool_response(function_responses=function_responses)
                                        
                                        # Check if session should end after tool execution
                                        if nav_tools.should_end_session():
                                            break
                                            
                                except Exception as response_error:
                                    print(f"⚠️ Error processing response: {response_error}")
                                    await websocket.send_text(json.dumps({
                                        "type": "error",
                                        "message": f"Response processing error: {str(response_error)}",
                                        "recoverable": True
                                    }))
                                
                                # Break if session should end
                                if nav_tools.should_end_session():
                                    break
                            
                            await asyncio.sleep(0.005)
                            
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            print(f"⚠️ Error in processing loop: {e}")
                            await websocket.send_text(json.dumps({
                                "type": "error",
                                "message": f"Processing error: {str(e)}",
                                "recoverable": True
                            }))
                            await asyncio.sleep(0.005)
                    
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
