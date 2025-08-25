"""
OpenAI Realtime API audio bridge for WebSocket ↔ OpenAI audio streaming
Completely replaces audio_bridge.py with OpenAI Realtime API integration
"""

import asyncio
import json
import base64
import struct
from typing import Optional, Dict, Any
from scipy import signal
import numpy as np
from openai_service import OpenAIRealtimeClient, handle_openai_tool_execution


class OpenAIAudioBridge:
    """
    Manages bidirectional audio streaming between WebSocket and OpenAI Realtime API
    Completely replaces WebSocketAudioBridge for OpenAI integration
    """
    
    def __init__(self, websocket):
        self.websocket = websocket
        self.is_streaming = False
        self.openai_client = None
        self.audio_tasks = []
    
    async def start_streaming(self, openai_client: OpenAIRealtimeClient, nav_tools):
        """
        Start bidirectional audio streaming with OpenAI
        
        Args:
            openai_client: OpenAI Realtime client
            nav_tools: Navigation tools for session control
        """
        if self.is_streaming:
            return
        
        self.is_streaming = True
        self.openai_client = openai_client
        print("🎵 Started WebSocket ↔ OpenAI Realtime audio streaming")
    
    def _resample_audio(self, audio_data: bytes, from_rate: int = 48000, to_rate: int = 24000) -> bytes:
        """
        High-quality audio resampling using scipy
        OpenAI Realtime API requires 24kHz, browser typically sends 48kHz
        
        Args:
            audio_data: Raw PCM16 audio bytes
            from_rate: Source sample rate (default 48kHz)
            to_rate: Target sample rate (default 24kHz for OpenAI)
            
        Returns:
            Resampled audio bytes
        """
        if from_rate == to_rate:
            return audio_data
        
        try:
            # Convert bytes to numpy array (16-bit PCM)
            audio_samples = np.frombuffer(audio_data, dtype=np.int16)
            
            # Calculate number of output samples
            num_samples = int(len(audio_samples) * to_rate / from_rate)
            
            # Use scipy's high-quality resampling
            resampled = signal.resample(audio_samples, num_samples)
            
            # Convert back to int16 and bytes
            resampled_int16 = resampled.astype(np.int16)
            return resampled_int16.tobytes()
            
        except Exception as e:
            print(f"⚠️ Audio resampling error: {e}")
            # Fallback: simple decimation (lower quality but works)
            samples = struct.unpack(f'<{len(audio_data)//2}h', audio_data)
            ratio = from_rate // to_rate
            downsampled = samples[::ratio]
            return struct.pack(f'<{len(downsampled)}h', *downsampled)
    
    async def handle_websocket_message(self, message, openai_client: OpenAIRealtimeClient):
        """
        Handle incoming WebSocket message and forward audio to OpenAI
        
        Args:
            message: WebSocket message
            openai_client: OpenAI Realtime client
            
        Returns:
            Control signal or None
        """
        try:
            if message["type"] == "websocket.receive":
                if "bytes" in message:
                    # Raw audio data - resample and send to OpenAI
                    audio_data = message["bytes"]
                    
                    # Debug audio format occasionally
                    if len(audio_data) > 0 and hash(audio_data) % 200 == 0:
                        print(f"🔍 Resampling for OpenAI: {len(audio_data)} bytes (48kHz → 24kHz)")
                    
                    # Resample from browser's 48kHz to OpenAI's 24kHz
                    resampled_audio = self._resample_audio(audio_data, 48000, 24000)
                    
                    # Send to OpenAI
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
    
    async def handle_openai_response(self, event, gmail_agent, nav_tools):
        """
        Handle response from OpenAI and forward to WebSocket
        
        Args:
            event: OpenAI event
            gmail_agent: Gmail MCP agent
            nav_tools: Email navigation tools
            
        Returns:
            Processing result or None
        """
        try:
            event_type = event.get("type")
            
            # Skip debug logging now that function calls are working
            # Handle audio responses
            if event_type == "response.audio.delta":
                audio_delta = event.get("delta", "")
                if audio_delta:
                    try:
                        # Decode base64 audio from OpenAI
                        audio_bytes = base64.b64decode(audio_delta)
                        # Send directly to frontend (OpenAI already provides proper format)
                        await self.websocket.send_bytes(audio_bytes)
                        return {"type": "audio", "data": audio_bytes}
                    except Exception as e:
                        print(f"⚠️ Error processing audio delta: {e}")
            
            # Handle audio completion
            elif event_type == "response.audio.done":
                print("🎵 OpenAI audio response completed")
                return {"type": "audio_complete"}
            
            # Handle user speech transcription
            elif event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                if transcript:
                    print(f"🎤 User said: {transcript}")
                    return {"type": "transcript", "text": transcript}
            
            # Handle function calls
            elif event_type == "response.function_call_arguments.done":
                # Extract function call data directly from the event
                function_name = event.get("name")
                function_arguments = event.get("arguments", "{}")
                call_id = event.get("call_id")
                
                if function_name:
                    # Create function call in the format expected by handle_openai_tool_execution
                    function_call = {
                        "name": function_name,
                        "arguments": function_arguments
                    }
                    
                    print(f"🔧 OpenAI function call: {function_name}")
                    
                    # Execute the function
                    result = await handle_openai_tool_execution(function_call, gmail_agent, call_id, nav_tools)
                    
                    # Send result back to OpenAI
                    await self.openai_client.send_function_result(
                        call_id, 
                        result["output"]
                    )
                    
                    # Check if session should end
                    if nav_tools.should_end_session():
                        return {"type": "session_end"}
                    
                    return {"type": "tool_executed", "function": function_name}
            
            # Handle interruptions
            elif event_type == "response.cancelled":
                print("🔄 OpenAI response cancelled (interruption)")
                await self.websocket.send_json({"type": "audio_interrupted"})
                return {"type": "interrupted"}
            
            # Handle errors
            elif event_type == "error":
                error = event.get("error", {})
                error_message = error.get("message", "Unknown OpenAI error")
                error_code = error.get("code", "unknown")
                print(f"❌ OpenAI Error [{error_code}]: {error_message}")
                
                await self.websocket.send_json({
                    "type": "error",
                    "message": f"OpenAI Error: {error_message}",
                    "recoverable": error_code not in ["invalid_api_key", "insufficient_quota"]
                })
                return {"type": "error", "message": error_message, "code": error_code}
            
            # Handle session updates
            elif event_type == "session.updated":
                print("✅ OpenAI session updated successfully")
                return {"type": "session_updated"}
            
            # Handle response creation
            elif event_type == "response.created":
                print("🤖 OpenAI response created")
                return {"type": "response_created"}
            
            # Handle response completion
            elif event_type == "response.done":
                print("🤖 OpenAI response completed")
                return {"type": "response_done"}
                
        except Exception as e:
            print(f"⚠️ Error handling OpenAI response: {e}")
            await self._send_error_to_frontend(f"Response handling error: {str(e)}")
        
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
        print("🔇 Stopped WebSocket ↔ OpenAI audio streaming")
    
    async def _send_error_to_frontend(self, error_message: str):
        """Send error message to frontend via WebSocket"""
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
    Completely replaces create_gemini_session_with_websocket
    
    Args:
        openai_session_config: Configuration for OpenAI session
        websocket: WebSocket connection to frontend
        email_info: Current email information
        
    Returns:
        Boolean indicating session success
    """
    from openai_service import OpenAIRealtimeClient
    
    session_completed = False
    audio_bridge = None
    openai_client = None
    
    try:
        session_timeout = 120.0  # 2 minutes like Gemini version
        
        async with asyncio.timeout(session_timeout):
            # Create OpenAI Realtime client
            openai_client = OpenAIRealtimeClient()
            
            # Get configuration components
            tools = openai_session_config.get("tools", [])
            gmail_agent = email_info.get('gmail_agent')
            nav_tools = email_info.get('nav_tools')
            
            if not gmail_agent or not nav_tools:
                raise ValueError("gmail_agent and nav_tools must be provided in email_info")
            
            # Connect to OpenAI
            await openai_client.connect(tools, gmail_agent, nav_tools)
            
            print(f"📧 Processing Email via OpenAI: {email_info['display_text']}")
            
            try:
                # Create audio bridge
                audio_bridge = OpenAIAudioBridge(websocket)
                
                # Send initial email information to OpenAI
                await openai_client.send_text(
                    f"Please read me this email and ask what I'd like to do with it. The email is: {email_info['display_text']} [Current email ID: {email_info['id']}]."
                )
                
                # Start audio streaming
                await audio_bridge.start_streaming(openai_client, nav_tools)
                
                # Create tasks for handling WebSocket messages and OpenAI responses
                async def handle_websocket_messages():
                    """Handle incoming WebSocket messages"""
                    print("🎤 Starting WebSocket message handler - waiting for voice input...")
                    while not nav_tools.should_end_session():
                        try:
                            message = await asyncio.wait_for(websocket.receive(), timeout=0.5)
                            result = await audio_bridge.handle_websocket_message(message, openai_client)
                            if result == "stop_session":
                                print("🛑 Stop session requested via WebSocket")
                                nav_tools.end_session()
                                break
                        except asyncio.TimeoutError:
                            # Normal timeout, continue listening
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
                
                async def handle_openai_responses():
                    """Continuous OpenAI response handler - runs for entire session"""
                    print("🤖 Starting CONTINUOUS OpenAI response handler...")
                    response_count = 0
                    
                    try:
                        # Continuous listening loop for OpenAI events
                        while not nav_tools.should_end_session():
                            try:
                                async for event in openai_client.receive_events():
                                    response_count += 1
                                    
                                    if nav_tools.should_end_session():
                                        print("🤖 Session ending, breaking from response loop")
                                        break
                                    
                                    # Handle the event
                                    result = await audio_bridge.handle_openai_response(event, gmail_agent, nav_tools)
                                    
                                    # Check for session end
                                    if result and result.get("type") == "session_end":
                                        print("🎯 OpenAI session completed - session should end")
                                        break
                                    
                                    # Handle errors that should break the session
                                    if result and result.get("type") == "error":
                                        error_code = result.get("code", "")
                                        if error_code in ["invalid_api_key", "insufficient_quota"]:
                                            print(f"💸 Critical OpenAI error: {error_code}")
                                            nav_tools.end_session()
                                            break
                                
                                # If we exit the event loop but session shouldn't end, reconnect
                                if not nav_tools.should_end_session():
                                    print("🔄 OpenAI event stream ended, but session continues...")
                                    await asyncio.sleep(0.1)
                                    continue
                                else:
                                    break
                                    
                            except asyncio.CancelledError:
                                print("🤖 OpenAI response handler cancelled")
                                break
                            except Exception as e:
                                print(f"⚠️ OpenAI response error: {e}")
                                await asyncio.sleep(0.1)
                                continue
                                
                    except Exception as e:
                        print(f"⚠️ Continuous OpenAI handler error: {e}")
                    
                    print("🤖 Continuous OpenAI response handler ended")
                
                # Run both tasks concurrently
                websocket_task = asyncio.create_task(handle_websocket_messages())
                openai_task = asyncio.create_task(handle_openai_responses())
                
                # Wait for the session to end
                try:
                    while not nav_tools.should_end_session():
                        # Check if either task has failed
                        if websocket_task.done() and websocket_task.exception():
                            print(f"❌ WebSocket task failed: {websocket_task.exception()}")
                            break
                        if openai_task.done() and openai_task.exception():
                            print(f"❌ OpenAI task failed: {openai_task.exception()}")
                            break
                        
                        # Small delay to prevent busy waiting
                        await asyncio.sleep(0.1)
                    
                    print("🎯 Session ending - nav_tools.should_end_session() is True")
                    
                finally:
                    # Cancel remaining tasks
                    websocket_task.cancel()
                    openai_task.cancel()
                    try:
                        await asyncio.gather(websocket_task, openai_task, return_exceptions=True)
                    except:
                        pass
                
                session_completed = True
                
            except Exception as session_error:
                print(f"⚠️ OpenAI session error: {session_error}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"OpenAI session error: {str(session_error)}",
                    "recoverable": False
                })
            
            finally:
                # Stop audio streaming
                if audio_bridge:
                    await audio_bridge.stop_streaming()
    
    except asyncio.TimeoutError:
        print("⏰ OpenAI session timed out after 2 minutes")
        await websocket.send_json({
            "type": "error", 
            "message": "OpenAI session timed out",
            "recoverable": False
        })
    except Exception as connection_error:
        print(f"❌ Failed to connect to OpenAI: {connection_error}")
        await websocket.send_json({
            "type": "error",
            "message": f"OpenAI connection error: {str(connection_error)}",
            "recoverable": False
        })
    finally:
        # Cleanup OpenAI client
        if openai_client:
            await openai_client.close()
    
    return session_completed


def validate_audio_format(audio_data: bytes) -> bool:
    """
    Validate that audio data is in the expected format
    Same validation logic as original but adapted for OpenAI requirements
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Boolean indicating if format is valid
    """
    # Basic validation - check if we have data and it's reasonable size
    if not audio_data:
        return False
    
    # Audio chunks should be reasonably sized
    # For 24kHz PCM (OpenAI format) at 5ms intervals, expect roughly 240 bytes per chunk
    if len(audio_data) < 10 or len(audio_data) > 20000:
        return False
    
    # Check if data length is even (16-bit samples)
    if len(audio_data) % 2 != 0:
        return False
    
    return True


async def send_audio_status(websocket, status: str, message: str = ""):
    """
    Send audio status updates to frontend
    Same interface as original for compatibility
    
    Args:
        websocket: WebSocket connection
        status: Status type ("started", "stopped", "error")
        message: Optional status message
    """
    try:
        await websocket.send_json({
            "type": "audio_status",
            "status": status,
            "message": message
        })
    except Exception as e:
        print(f"Failed to send audio status: {e}")
