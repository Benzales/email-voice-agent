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
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent

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

# Removed MCPGmailToolHandler class - using direct MCP tool exposure instead

# System instruction for direct Gmail MCP access
system_instruction = """You are a voice-driven Gmail assistant with full access to the Gmail API through MCP tools.

## Key Behaviors:
- Be concise but helpful in your responses
- When searching emails, use Gmail's powerful search syntax
- Confirm actions concisely
- For batch operations, always confirm the count before proceeding
- When reading emails, summarize key information unless asked for full content

## Voice Interaction:
- Speak clearly and at a moderate pace
- Use natural language to describe what you're doing
- Announce results concisely
- For long lists, offer to read more details if needed

You can handle any Gmail-related request the user has. Be proactive in suggesting the best tool for their needs."""

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
    
    # Configuration for Gemini with all discovered MCP tools
    config = {
        "response_modalities": ["AUDIO"],
        "tools": gemini_tools,  # All MCP tools directly exposed
        "system_instruction": [system_instruction]
    }
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            
            print("\n🎤 Voice-driven Gmail Assistant Started!")
            print("💬 You now have full Gmail API access via voice commands")
            print("🔊 Examples: 'Search for unread emails', 'Archive all promotional emails', 'Create a draft reply'")
            print("📧 All Gmail operations are available - just ask!")
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
                
                # Send artificial introductory message
                await session.send_realtime_input(
                    text="Hello! Please introduce yourself as my voice-driven Gmail assistant with full access to the Gmail API. Explain that I can search emails, read content, modify messages, create drafts, and more. Ask me what I'd like to do with my emails today."
                )
                
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
                                            # Execute MCP tool directly
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