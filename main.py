#!/usr/bin/env python3
"""
Voice-driven Email Agent with Direct MCP Integration
This uses the article's approach - dynamically discovering and exposing all Gmail MCP tools directly to Gemini
"""

import asyncio
import json
import pyaudio
import queue
import threading
import traceback
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from custom_tools import EmailNavigationTools

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

client = genai.Client(api_key=api_key)

# Model selection
model = "gemini-live-2.5-flash-preview"

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

# Removed EmailSession dataclass - no longer needed for direct MCP approach

class AudioRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.audio_queue = queue.Queue()
        
    def start_recording(self):
        self.is_recording = True
        self.frames = []
        
        def callback(in_data, frame_count, time_info, status):
            if self.is_recording:
                self.audio_queue.put(in_data)
            return (in_data, pyaudio.paContinue)
        
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=callback
        )
        self.stream.start_stream()
        print("🎤 Recording started... (speak now)")
        
    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        print("⏹️  Recording stopped")
        
    def get_audio_data(self):
        """Get all recorded audio data as PCM bytes"""
        audio_data = b''
        while not self.audio_queue.empty():
            audio_data += self.audio_queue.get()
        return audio_data

class AudioPlayer:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.output_stream = None
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.stop_playback = False
        
    def start_output_stream(self):
        """Start the output audio stream"""
        self.output_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=CHUNK
        )
        
        # Start playback thread
        self.stop_playback = False
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
    
    def _playback_worker(self):
        """Worker thread that continuously plays audio from the queue"""
        while not self.stop_playback:
            try:
                audio_data = self.audio_queue.get(timeout=0.005)
                if audio_data and self.output_stream:
                    self.output_stream.write(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in playback worker: {e}")
    
    def queue_audio(self, audio_data):
        """Queue audio data for playback"""
        self.audio_queue.put(audio_data)
    
    def clear_queue(self):
        """Clear all queued audio"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def close(self):
        """Close the audio stream"""
        self.stop_playback = True
        if self.playback_thread:
            self.playback_thread.join(timeout=1)
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.audio.terminate()

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

## PRIMARY BEHAVIOR - Sequential Email Reading:
- You will be provided with email information one at a time
- For each email, announce ONLY: sender and subject
- After reading each email, ask what the user would like to do
- Wait for the user's command before any action
- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next
- CRITICAL WORKFLOW: After you execute ANY action on an email (using tools like gmail_modify_email, gmail_delete_email, gmail_send_email, etc.), briefly confirm the action with minimal words (e.g., "Archived", "Deleted", "Marked unread"), then immediately call the next_email tool
- CRITICAL WORKFLOW: If the user says "skip", "next", "continue", etc., immediately call the next_email tool
- Do NOT ask "what would you like to do next" after completing an email action - just confirm and move to the next email automatically
- This creates an efficient inbox clearing workflow where each email is processed and the system moves forward automatically
- DO NOT search for emails yourself - they will be provided to you
- When performing actions on "this email" or "it", use the email ID that was provided with the email information

## Key Behaviors:
- Be concise but helpful in your responses
- Confirm actions concisely
- When the user says "next", "skip", or "continue", simply acknowledge and wait for the next email
- If the user wants to stop reading emails, acknowledge this

## Voice Interaction:
- Speak clearly and at a moderate pace
- Use natural language to describe what you're doing
- Announce results concisely

## Email Reading Format:
When provided with email info, read it as:
"From [sender] - [subject]
What would you like to do with this email?"

You can execute any Gmail action the user requests on the current email."""

async def send_error_message(session, error_message):
    """Send an error message to the session so the AI can respond to the user"""
    try:
        await session.send_realtime_input(
            text=f"An error occurred: {error_message}. Please acknowledge this error and continue helping the user."
        )
    except Exception as e:
        print(f"Failed to send error message to session: {e}")

async def process_realtime_voice():
    """Process real-time voice input with direct MCP Gmail integration"""
    recorder = AudioRecorder()
    player = AudioPlayer()
    email_manager = EmailManager()
    
    # Initialize MCP app and Gmail agent
    print("🔧 Initializing MCP-Agent framework...")
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
    print(f"✅ Connected to Gmail MCP server with {len(mcp_tools_result.tools)} tools")
    
    # Fetch emails from inbox before starting voice session
    print("\n📧 Fetching emails from inbox...")
    try:
        # Search for inbox emails using the correct Gmail MCP tool
        search_result = await gmail_agent.call_tool(
            "gmail_search_emails",
            arguments={"query": "in:inbox", "maxResults": 50}
        )
        
        # Extract emails from result
        emails = []
        if hasattr(search_result, 'content') and search_result.content:
            for content_item in search_result.content:
                if hasattr(content_item, 'text'):
                    text_content = content_item.text
                    
                    # Parse the Gmail MCP response format
                    # Format is: ID: [id]\nSubject: [subject]\nFrom: [from]\nDate: [date]\n\n
                    lines = text_content.split('\n')
                    current_email = {}
                    
                    for line in lines:
                        line = line.strip()
                        
                        if line.startswith('ID: '):
                            # Save previous email if it exists
                            if current_email and 'id' in current_email:
                                emails.append(current_email)
                            # Start new email
                            current_email = {'id': line.replace('ID: ', '').strip()}
                            
                        elif line.startswith('Subject: ') and 'id' in current_email:
                            current_email['subject'] = line.replace('Subject: ', '').strip()
                            
                        elif line.startswith('From: ') and 'id' in current_email:
                            current_email['from'] = line.replace('From: ', '').strip()
                            
                        elif line.startswith('Date: ') and 'id' in current_email:
                            current_email['date'] = line.replace('Date: ', '').strip()
                    
                    # Don't forget the last email
                    if current_email and 'id' in current_email:
                        emails.append(current_email)
        
        if emails:
            email_manager.set_emails(emails)
            print(f"✅ Found emails in inbox")
        else:
            print("⚠️ No emails found in inbox")
            
    except Exception as e:
        print(f"⚠️ Error fetching emails: {e}")
        print("Continuing without pre-loaded emails...")
    
    # Dynamically convert MCP tools to Gemini format
    gemini_tools = []
    print("\n📋 Available Gmail operations:")
    for tool in mcp_tools_result.tools:
        print(f"  - {tool.name}: {tool.description}")
        
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
    
    # Add custom next_email tool
    next_email_tool = nav_tools.get_next_email_tool()
    gemini_tools.append(next_email_tool)
    print(f"  - next_email: Move to the next email in the inbox sequence")
    
    # Configuration for Gemini with all discovered MCP tools
    config = {
        "response_modalities": ["AUDIO"],
        "tools": gemini_tools,  # All MCP tools directly exposed
        "system_instruction": [system_instruction]
    }
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            
            print("\n🎤 Voice-driven Gmail Assistant Started!")
            print("📧 Pre-loading your inbox emails...")
            print("💬 The assistant will read each email sequentially")
            print("🎯 After each email, you can:")
            print("   - Take action: Reply, Archive, Delete, Mark as read/unread")
            print("   - Say 'Next' or 'Skip' to move to the next email")
            print("   - Say 'Stop' to exit email reading mode")
            print("Press Ctrl+C to exit")
            print("\n" + "="*50)
            
            try:
                # Start recording
                recorder.start_recording()
                player.start_output_stream()
                
                # Audio streaming task
                async def stream_audio():
                    """Continuously stream audio data to Gemini without interruption"""
                    while True:
                        try:
                            audio_data = recorder.get_audio_data()
                            if audio_data:
                                await session.send_realtime_input(
                                    audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                                )
                        except Exception as e:
                            print(f"⚠️ Audio streaming error: {e}")
                            await send_error_message(session, f"Audio streaming issue: {str(e)}")
                        await asyncio.sleep(0.005)
                
                # Start audio streaming
                audio_task = asyncio.create_task(stream_audio())
                
                # Send initial instruction to agent
                if len(email_manager.emails) > 0:
                    current_email = email_manager.get_current_email()
                    
                    # Extract email details
                    email_id = current_email.get('id', '')
                    sender = current_email.get('from', 'Unknown')
                    subject = current_email.get('subject', 'No subject')
                    
                    await session.send_realtime_input(
                        text=f"Please introduce yourself as my voice-driven Gmail assistant, then read me the first email. The first email is: From {sender} - {subject} [Current email ID: {email_id}]. After reading it, ask what I'd like to do with this email."
                    )
                else:
                    await session.send_realtime_input(
                        text="Please introduce yourself as my voice-driven Gmail assistant and let me know that you couldn't find any emails in my inbox. Ask how you can help me today."
                    )
                
                # Store last processed email ID for tracking
                last_email_id = None
                
                # Main response processing loop
                while True:
                    try:
                        async for response in session.receive():
                            try:
                                # Handle interruptions
                                if response.server_content and response.server_content.interrupted is True:
                                    print("\n🔄 Interrupted - clearing audio queue")
                                    player.clear_queue()
                                    print("👂 Processing your command...")
                                
                                # Handle audio data
                                elif response.data is not None:
                                    player.queue_audio(response.data)
                                
                                # Handle tool calls
                                elif response.tool_call:
                                    function_responses = []
                                    
                                    for fc in response.tool_call.function_calls:
                                        try:
                                            # Handle custom next_email tool
                                            if fc.name == "next_email":
                                                print(f"🎯 Executing custom next_email tool")
                                                
                                                result = await nav_tools.execute_next_email()
                                                
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
                                        
                            except Exception as response_error:
                                print(f"⚠️ Error processing response: {response_error}")
                                await send_error_message(session, f"Response processing error: {str(response_error)}")
                        
                        await asyncio.sleep(0.005)
                        
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        print(f"⚠️ Error in main processing loop: {e}")
                        await send_error_message(session, f"Processing error: {str(e)}")
                        await asyncio.sleep(0.005)
                        
            except KeyboardInterrupt:
                print("\n\n👋 Exiting...")
            except Exception as session_error:
                print(f"⚠️ Session error: {session_error}")
            finally:
                
                # Cancel audio streaming task
                if 'audio_task' in locals():
                    try:
                        audio_task.cancel()
                    except Exception as e:
                        print(f"⚠️ Error canceling audio task: {e}")
                
                try:
                    recorder.stop_recording()
                    recorder.audio.terminate()
                    player.close()
                except Exception as e:
                    print(f"⚠️ Error cleaning up audio resources: {e}")
                
                # Cleanup MCP connection
                if gmail_agent:
                    await gmail_agent.__aexit__(None, None, None)
    
    except Exception as connection_error:
        print(f"❌ Failed to connect to Gemini: {connection_error}")

async def main():
    """Main function for the voice-driven email agent with direct MCP access"""
    print("🎤 Voice-driven Gmail Agent with Direct MCP Integration")
    print("📧 Full Gmail API access through natural language")
    print("🎙️  Initializing voice input...")
    
    try:
        await process_realtime_voice()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        print("Please check your configuration and try again.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"❌ Fatal error: {e}") 