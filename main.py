#!/usr/bin/env python3
"""
Voice-driven Email Agent with Direct MCP Integration
This uses the article's approach - dynamically discovering and exposing all Gmail MCP tools directly to Gemini
"""

import asyncio
import json
import traceback
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
import base64
import io
from typing import Tuple
import numpy as np
import soundfile as sf
import librosa
from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from custom_tools import EmailNavigationTools
from gmail_helpers import parse_gmail_search_results
from audio_local_bridge import LocalAudioBridge

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

client = genai.Client(api_key=api_key)

# Model selection
model = "gemini-live-2.5-flash-preview"

# Removed EmailSession dataclass - no longer needed for direct MCP approach

class EmailManager:
    """Manages sequential email reading with deterministic state"""
    def __init__(self):
        self.emails = []
        self.current_index = 0
        
    def set_emails(self, emails):
        """Store emails from search results"""
        self.emails = emails
        self.current_index = 0
        
    def get_current_email(self):
        """Get the current email or None if exhausted"""
        if self.current_index < len(self.emails):
            return self.emails[self.current_index]
        return None
        
    def next_email(self):
        """Move to next email"""
        self.current_index += 1
        
    def has_more_emails(self):
        """Check if there are more emails to read"""
        return self.current_index < len(self.emails) - 1
        
    def is_exhausted(self):
        """Check if all emails have been read"""
        return self.current_index >= len(self.emails)

# Removed MCPGmailToolHandler class - using direct MCP tool exposure instead

# System instruction for direct Gmail MCP access
system_instruction = """You are a voice-driven Gmail assistant with full access to the Gmail API through MCP tools.

## PRIMARY BEHAVIOR - Single Email Focus:
- You will be provided with information for ONE email at a time
- For the email, announce ONLY: sender and subject
- After reading the email, ask what the user would like to do
- Wait for the user's command before any action
- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next
- **CRITICAL WORKFLOW**: After you execute ANY action on an email (using tools like gmail_modify_email, gmail_delete_email, gmail_send_email, etc.), you MUST immediately call the complete_current_email tool. This is mandatory.
- **CRITICAL WORKFLOW**: If the user says "skip", "next", "continue", etc., immediately call the complete_current_email tool
- Do NOT ask "what would you like to do next" after completing an email action - just call complete_current_email immediately
- This creates an efficient workflow where each email is processed and the system moves forward automatically
- When performing actions on "this email" or "it", use the email ID that was provided with the email information

## Key Behaviors:
- Be concise but helpful in your responses
- Confirm actions concisely
- When the user says "next", "skip", or "continue", simply acknowledge and call end_session
- Focus only on the current email - there is no history of previous emails in this session

## Voice Interaction:
- Speak clearly and at a moderate pace
- Use natural language to describe what you're doing
- Announce results concisely

## Email Reading Format:
When provided with email info, read it as:
"From [sender] - [subject]
What would you like to do with this email?"

## Important Action Instructions:
- **CRITICAL**: When archiving an email, you MUST use gmail_modify_email with removeLabelIds: ["INBOX"]. Do NOT add labels like "ARCHIVED". Archiving means removing from the inbox.

You can execute any Gmail action the user requests on the current email."""

async def send_error_message(session, error_message):
    """Send an error message to the session so the AI can respond to the user"""
    try:
        await session.send_realtime_input(
            text=f"An error occurred: {error_message}. Please acknowledge this error and continue helping the user."
        )
    except Exception as e:
        print(f"Failed to send error message to session: {e}")

async def process_single_email_session(email_manager, nav_tools, gmail_agent, gemini_tools, audio_bridge=None):
    """Process a single email in its own session"""
    current_email = email_manager.get_current_email()
    if not current_email:
        return False  # No more emails
    
    # Reset navigation tools state for new session
    nav_tools.reset_session_state()
    
    # Extract email details
    email_id = current_email.get('id', '')
    sender = current_email.get('from', 'Unknown')
    subject = current_email.get('subject', 'No subject')
    
    # Use provided bridge or default to LocalAudioBridge
    if audio_bridge is None:
        from audio_local_bridge import LocalAudioBridge
        bridge = LocalAudioBridge()
    else:
        bridge = audio_bridge
    def _is_base64_ascii(b: bytes, probe: int = 128) -> bool:
        try:
            sample = b[:probe].decode('ascii')
        except UnicodeDecodeError:
            return False
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=\n\r")
        return all(ch in allowed for ch in sample)

    def _resample_pcm16(pcm16: bytes, src_rate: int, dst_rate: int) -> bytes:
        if src_rate == dst_rate:
            return pcm16
        x = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32767.0
        y = librosa.resample(x, orig_sr=src_rate, target_sr=dst_rate, res_type="kaiser_best")
        y = np.clip(y, -1.0, 1.0)
        return (y * 32767.0).astype(np.int16).tobytes()

    def _decode_ai_audio_to_pcm16(data: bytes, target_rate: int = 24000) -> Tuple[bytes, int]:
        """Decode Gemini AI audio to PCM16 mono and standardize to target_rate.

        Returns (pcm_bytes, target_rate).
        """
        raw = data
        # 1) Base64 detection/decoding
        if _is_base64_ascii(raw):
            try:
                raw = base64.b64decode(raw, validate=True)
            except Exception:
                # If strict decode fails, try non-strict
                try:
                    raw = base64.b64decode(raw)
                except Exception:
                    pass
        # 2) Try to decode via soundfile (handles WAV/OGG/FLAC/etc.)
        try:
            with io.BytesIO(raw) as bio:
                audio, sr = sf.read(bio, dtype='float32', always_2d=False)
            # Convert to mono if needed
            if audio.ndim == 2:
                audio = audio.mean(axis=1)
            if sr != target_rate:
                audio = librosa.resample(audio, orig_sr=sr, target_sr=target_rate, res_type="kaiser_best")
            audio = np.clip(audio, -1.0, 1.0)
            pcm = (audio * 32767.0).astype(np.int16).tobytes()
            return pcm, target_rate
        except Exception:
            pass
        # 3) Try raw float32 PCM (little-endian)
        try:
            if len(raw) % 4 == 0:
                f = np.frombuffer(raw, dtype='<f4')
                if f.size > 0 and np.isfinite(f).all():
                    f = np.clip(f, -1.0, 1.0)
                    # Assume source ~48k if unknown, resample to target_rate
                    src_rate = 48000
                    if src_rate != target_rate:
                        f = librosa.resample(f, orig_sr=src_rate, target_sr=target_rate, res_type="kaiser_best")
                    pcm = (f * 32767.0).astype(np.int16).tobytes()
                    return pcm, target_rate
        except Exception:
            pass
        # 4) Fallback: assume raw is PCM16 mono; if we cannot infer src sr,
        # treat it as already at target_rate to avoid pitch/time distortion
        if len(raw) % 2 == 0:
            return raw, target_rate
        return raw, target_rate
    
    # Configuration for Gemini with all discovered MCP tools
    config = {
        "response_modalities": ["AUDIO"],
        "tools": gemini_tools,
        "system_instruction": [system_instruction]
    }
    
    session_completed = False
    
    try:
        # Ensure clean session with timeout
        session_timeout = 120.0  # 2 minute timeout per email session
        async with asyncio.timeout(session_timeout):
            async with client.aio.live.connect(model=model, config=config) as session:
                
                print(f"📧 Processing Email {email_manager.current_index + 1}/{len(email_manager.emails)}")
                
                try:
                    # Start local audio bridge (mic + speaker)
                    bridge.start()
                    
                    # Audio streaming task
                    async def stream_audio():
                        """Continuously stream audio data to Gemini without interruption"""
                        audio_sent_count = 0
                        while not nav_tools.should_end_session():
                            try:
                                audio_data = bridge.get_user_audio()
                                if audio_data:
                                    await session.send_realtime_input(
                                        audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                                    )
                                    audio_sent_count += 1
                                    # Log every 20th chunk to confirm audio is flowing
                                    if audio_sent_count % 20 == 0:
                                        print(f"🎙️ Mic audio flowing: sent {audio_sent_count} chunks to Gemini")
                            except Exception as e:
                                print(f"⚠️ Audio streaming error: {e}")
                                await send_error_message(session, f"Audio streaming issue: {str(e)}")
                            await asyncio.sleep(0.005)
                    
                    # Start audio streaming
                    audio_task = asyncio.create_task(stream_audio())
                    
                    # Send initial email information to agent
                    await session.send_realtime_input(
                        text=f"Please read me this email and ask what I'd like to do with it. The email is: From {sender} - {subject} [Current email ID: {email_id}]."  #TODO: can remove email id and ensure every tool call has access to the email id. 
                    )
                    
                    # Main response processing loop
                    while not nav_tools.should_end_session():
                        try:
                            async for response in session.receive():
                                try:
                                    # Handle interruptions
                                    if response.server_content and response.server_content.interrupted is True:
                                        print("\n🔄 Interrupted")
                                        # Clear any queued AI audio to avoid stale playback
                                        try:
                                            bridge.clear_ai_audio()
                                        except Exception:
                                            pass
                                    
                                    # Handle audio data
                                    elif response.data is not None:
                                        # Decode Gemini audio to PCM16 (handles base64/container/raw) and play
                                        pcm16, sr = _decode_ai_audio_to_pcm16(response.data, target_rate=24000)
                                        bridge.put_ai_audio(pcm16, sample_rate_hz=sr, num_channels=1)
                                    
                                    # Handle tool calls
                                    elif response.tool_call:
                                        function_responses = []
                                        
                                        for fc in response.tool_call.function_calls:
                                            try:
                                                # Handle custom complete_current_email tool
                                                if fc.name == "complete_current_email":
                                                    result = await nav_tools.execute_complete_current_email()
                                                    
                                                    function_response = types.FunctionResponse(
                                                        id=fc.id,
                                                        name=fc.name,
                                                        response=result
                                                    )
                                                    function_responses.append(function_response)
                                                
                                                # Handle MCP tools
                                                else:
                                                    print(f"🎯 Executing {fc.name} with args: {dict(fc.args)}")
                                                    
                                                    result = await gmail_agent.call_tool(
                                                        fc.name,
                                                        arguments=dict(fc.args)
                                                    )
                                                    
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
                                                    
                                                    # Create function response
                                                    function_response = types.FunctionResponse(
                                                        id=fc.id,
                                                        name=fc.name,
                                                        response=response_content
                                                    )
                                                    function_responses.append(function_response)
                                            
                                            except Exception as tool_error:
                                                print(f"⚠️ Tool call error for {fc.name}: {tool_error}")
                                                error_response = types.FunctionResponse(
                                                    id=fc.id,
                                                    name=fc.name,
                                                    response={"result": f"Error: {str(tool_error)}"}
                                                )
                                                function_responses.append(error_response)
                                        
                                        # Send tool responses
                                        await session.send_tool_response(function_responses=function_responses)
                                        
                                        # Check if session should end after tool execution
                                        if nav_tools.should_end_session():
                                            break
                                            
                                except Exception as response_error:
                                    print(f"⚠️ Error processing response: {response_error}")
                                    await send_error_message(session, f"Response processing error: {str(response_error)}")
                                
                                # Break if session should end
                                if nav_tools.should_end_session():
                                    break
                            
                            await asyncio.sleep(0.005)
                            
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            print(f"⚠️ Error in processing loop: {e}")
                            await send_error_message(session, f"Processing error: {str(e)}")
                            await asyncio.sleep(0.005)
                    
                    session_completed = True
                            
                except KeyboardInterrupt:
                    print("\n\n👋 User interrupted...")
                    return False  # Stop processing emails
                except Exception as session_error:
                    print(f"⚠️ Session error: {session_error}")
                finally:
                    # Cancel audio streaming task with timeout
                    if 'audio_task' in locals():
                        try:
                            audio_task.cancel()
                            # Wait for cancellation to complete with timeout
                            try:
                                await asyncio.wait_for(audio_task, timeout=2.0)
                            except (asyncio.CancelledError, asyncio.TimeoutError):
                                pass  # Expected when cancelling
                            except Exception as e:
                                print(f"⚠️ Error during task cancellation: {e}")
                        except Exception as e:
                            print(f"⚠️ Error canceling audio task: {e}")
                    
                    # Enhanced audio resource cleanup
                    try:
                        if 'bridge' in locals() and bridge and not bridge.closed():
                            bridge.stop()
                    except Exception as e:
                        print(f"⚠️ Error cleaning up audio bridge: {e}")
    
    except Exception as connection_error:
        print(f"❌ Failed to connect to Gemini: {connection_error}")
        return False
    
    return session_completed

async def process_realtime_voice():
    """Process real-time voice input with direct MCP Gmail integration - one session per email"""
    email_manager = EmailManager()
    
    # Initialize MCP app and Gmail agent
    mcp_app = MCPApp(name="voice_gmail_agent")
    await mcp_app.initialize()
    
    # Create Gmail agent
    gmail_agent = Agent(
        name="gmail",
        instruction="Execute Gmail operations efficiently",
        server_names=["gmail"],
        connection_persistence=True
    )
    
    # Initialize the agent
    await gmail_agent.initialize()
    
    # Get available tools from MCP and convert to Gemini format
    mcp_tools_result = await gmail_agent.list_tools()
    
    # Fetch emails from inbox before starting voice session
    try:
        # Search for inbox emails using the correct Gmail MCP tool
        search_result = await gmail_agent.call_tool(
            "gmail_search_emails",
            arguments={"query": "in:inbox", "maxResults": 50}
        )
        
        # Extract emails from result using helper function
        emails = parse_gmail_search_results(search_result)
        
        if emails:
            email_manager.set_emails(emails)
            print(f"✅ Found {len(emails)} emails in inbox")
        else:
            print("⚠️ No emails found in inbox")
            return
            
    except Exception as e:
        print(f"⚠️ Error fetching emails: {e}")
        return
    
    # Dynamically convert MCP tools to Gemini format
    gemini_tools = []
    for tool in mcp_tools_result.tools:        
        # Extract parameters, filtering out schema metadata
        parameters = {}
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            parameters = {
                k: v
                for k, v in tool.inputSchema.items()
                if k not in ["additionalProperties", "$schema"]
            }
        
        # Create Gemini-compatible tool definition
        gemini_tool = types.Tool(
            function_declarations=[{
                "name": tool.name,
                "description": tool.description,
                "parameters": parameters,
            }]
        )
        gemini_tools.append(gemini_tool)
    
    # Create custom navigation tools
    nav_tools = EmailNavigationTools(email_manager)
    
    # Add custom complete_current_email tool
    complete_current_email_tool = nav_tools.get_complete_current_email_tool()
    gemini_tools.append(complete_current_email_tool)
    
    try:
        # Process emails one by one
        while not email_manager.is_exhausted():
            session_success = await process_single_email_session(
                email_manager, nav_tools, gmail_agent, gemini_tools
            )
            
            if not session_success:
                print("❌ Session failed or was interrupted")
                break
            
            # Move to next email for next session
            email_manager.next_email()
            
            if not email_manager.is_exhausted():
                await asyncio.sleep(1)  # Brief pause between sessions
            else:
                print("\n🎉 All emails processed!")
                break
    
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"❌ Unexpected error in main loop: {e}")
    finally:
        # Enhanced MCP connection cleanup
        cleanup_errors = []
        
        # Cleanup Gmail agent
        if 'gmail_agent' in locals() and gmail_agent:
            try:
                await gmail_agent.__aexit__(None, None, None)
            except Exception as e:
                cleanup_errors.append(f"Gmail agent cleanup: {e}")
        
        # Cleanup MCP app
        if 'mcp_app' in locals() and mcp_app:
            try:
                # Force cleanup of MCP app connections
                if hasattr(mcp_app, 'cleanup'):
                    await mcp_app.cleanup()
                elif hasattr(mcp_app, '__aexit__'):
                    await mcp_app.__aexit__(None, None, None)
            except Exception as e:
                cleanup_errors.append(f"MCP app cleanup: {e}")
        
        # Report any cleanup errors
        if cleanup_errors:
            print(f"⚠️ Cleanup errors: {'; '.join(cleanup_errors)}")
        
        # Force garbage collection to help with resource cleanup
        import gc
        gc.collect()

async def cleanup_resources(*resources):
    """Helper function to cleanup multiple resources safely"""
    cleanup_errors = []
    
    for resource in resources:
        if resource is None:
            continue
            
        try:
            # Try different cleanup methods based on resource type
            if hasattr(resource, '__aexit__'):
                await resource.__aexit__(None, None, None)
            elif hasattr(resource, 'cleanup'):
                if asyncio.iscoroutinefunction(resource.cleanup):
                    await resource.cleanup()
                else:
                    resource.cleanup()
            elif hasattr(resource, 'close'):
                if asyncio.iscoroutinefunction(resource.close):
                    await resource.close()
                else:
                    resource.close()
            elif hasattr(resource, 'terminate'):
                resource.terminate()
        except Exception as e:
            cleanup_errors.append(f"{type(resource).__name__}: {e}")
    
    if cleanup_errors:
        print(f"⚠️ Resource cleanup errors: {'; '.join(cleanup_errors)}")

async def main():
    """Main function for the voice-driven email agent with direct MCP access"""
    try:
        # Add timeout to prevent hanging in test environments
        await asyncio.wait_for(process_realtime_voice(), timeout=300.0)  # 5 minute timeout
    except asyncio.TimeoutError:
        print("⏰ Main process timed out after 5 minutes")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}") 