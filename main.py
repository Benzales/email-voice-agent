# Voice-driven Email Agent with Google Gemini Audio Integration
# Test file: https://storage.googleapis.com/generativeai-downloads/data/16000.wav
# Install helpers for converting files: pip install librosa soundfile

import asyncio
import io
from pathlib import Path
import wave
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
import soundfile as sf
import librosa
import pyaudio
import threading
import queue
import tempfile
from gmail_service import GmailService
from tool_handlers import ToolHandlers

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

client = genai.Client(api_key=api_key)

# Initialize Gmail service
gmail_service = GmailService()

# Half cascade model:
model = "gemini-live-2.5-flash-preview"

# Native audio output model:
# model = "gemini-2.5-flash-preview-native-audio-dialog"

# Tool definitions for email actions
mark_unread_tool = {
    "name": "markUnread",
    "description": "Marks the current email as unread."
}

mark_read_tool = {
    "name": "markRead",
    "description": "Marks the current email as read."
}

archive_tool = {
    "name": "archive", 
    "description": "Archives the current email."
}

delete_tool = {
    "name": "deleteEmail",
    "description": "Moves the current email to trash."
}

get_next_email_tool = {
    "name": "getNextEmail",
    "description": "Get the next email in the inbox clearing sequence. This is called automatically after each action."
}

get_inbox_stats_tool = {
    "name": "getInboxStats",
    "description": "Get statistics about the inbox (total emails, unread count, etc.)"
}

tools = [{"function_declarations": [
    get_next_email_tool,
    mark_unread_tool, 
    mark_read_tool,
    archive_tool, 
    delete_tool,
    get_inbox_stats_tool
]}]

# System instruction for email agent context
system_instruction = """You are a voice-driven email assistant dedicated to helping users efficiently clear their Gmail inbox.

## Your Primary Function: Inbox Clearing

You operate in a continuous inbox clearing mode:
1. Announce each email's sender and subject clearly and concisely
2. Wait for the user's action command (archive, delete, mark as read/unread)
3. Execute the action and automatically move to the next email
4. Continue until all emails are processed

## Key behaviors:
- Keep responses extremely concise - just sender and subject
- ALWAYS automatically call getNextEmail after completing an action
- When inbox is cleared, announce completion with stats
- Be efficient and focused on helping users process emails quickly

## Available actions for each email:
- Archive - removes from inbox
- Delete - moves to trash
- Mark as read/unread - changes read status
- If the user says 'skip', treat it as 'mark as unread'

## Voice interactions:
- Speak clearly and at a moderate pace
- Use natural pauses between emails
- Confirm actions briefly (e.g., "Archived", "Deleted")

Focus on speed and efficiency to help users achieve inbox zero."""

config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,
    "system_instruction": [system_instruction]
}

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000

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
        self.current_playback_task = None
        
    def start_output_stream(self):
        """Start the output audio stream"""
        self.output_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=CHUNK
        )
        
    async def play_audio_data(self, audio_data):
        """Play audio data asynchronously"""
        try:
            if self.output_stream is None:
                self.start_output_stream()
            
            # Cancel any existing playback
            if self.current_playback_task and not self.current_playback_task.done():
                self.current_playback_task.cancel()
            
            # Create new playback task
            self.current_playback_task = asyncio.create_task(self._play_audio_async(audio_data))
            
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    async def _play_audio_async(self, audio_data):
        """Async method to play audio data"""
        try:
            # Play the audio data in a single write to maintain proper timing
            self.output_stream.write(audio_data)
        except asyncio.CancelledError:
            # Audio playback was cancelled (interrupted)
            pass
        except Exception as e:
            print(f"Error in async audio playback: {e}")
    
    def stop_current_playback(self):
        """Stop current audio playback"""
        if self.current_playback_task and not self.current_playback_task.done():
            self.current_playback_task.cancel()
    
    def close(self):
        """Close the audio stream"""
        self.stop_current_playback()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.audio.terminate()

async def process_realtime_voice():
    """
    Process real-time voice input with VAD and stream audio responses.
    """
    recorder = AudioRecorder()
    player = AudioPlayer()
    
    # Authenticate Gmail service
    print("🔐 Authenticating with Gmail...")
    try:
        gmail_service.authenticate()
        print("✅ Gmail authentication successful!")
    except Exception as e:
        print(f"❌ Gmail authentication failed: {e}")
        print("\nPlease make sure you have:")
        print("1. Created OAuth2 credentials in Google Cloud Console")
        print("2. Downloaded credentials.json to this directory")
        print("3. Enabled Gmail API in your Google Cloud project")
        return
    
    # Initialize inbox session automatically
    print("\n📧 Loading inbox emails...")
    email_count = gmail_service.initialize_inbox_session('in:inbox', 50)
    print(f"✅ Found {email_count} emails to process")
    
    # Initialize tool handlers
    tool_handlers = ToolHandlers(gmail_service)
    
    async with client.aio.live.connect(model=model, config=config) as session:
        
        print("\n🎤 Voice-driven Inbox Clearing Started!")
        print("💬 Available commands: archive, delete, skip, mark as read/unread")
        print("🔊 I'll announce each email - just say what to do with it")
        print("Press Ctrl+C to exit")
        print("\n" + "="*50)
        
        try:
            # Start recording
            recorder.start_recording()
            
            # Start audio output stream
            player.start_output_stream()
            
            # Flag to track if we should auto-get next email
            should_get_next_email = True  # Start with first email
            
            # Create a separate task for audio streaming
            async def stream_audio():
                """Continuously stream audio data to Gemini without interruption"""
                while True:
                    audio_data = recorder.get_audio_data()
                    if audio_data:
                        await session.send_realtime_input(
                            audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                        )
                    await asyncio.sleep(0.005)  # Very short sleep to prevent CPU overuse
            
            # Start the audio streaming task
            audio_task = asyncio.create_task(stream_audio())
            
            # Main response processing loop
            while True:
                # Auto-trigger next email if needed
                if should_get_next_email:
                    should_get_next_email = False
                    # Send a tool call for the next email
                    await session.send_tool_response(function_responses=[
                        types.FunctionResponse(
                            id="auto_next",
                            name="getNextEmail",
                            response={"trigger": "auto"}
                        )
                    ])
                
                # Process responses without blocking audio streaming
                try:
                    # Slightly longer timeout since audio streaming is separate
                    response = await asyncio.wait_for(session.receive().__anext__(), timeout=0.05)
                    
                    # Handle interruptions first (immediate priority)
                    if response.server_content and response.server_content.interrupted is True:
                        print("\n🔄 Interrupted - listening for new input...")
                        # Stop current audio playback when interrupted
                        player.stop_current_playback()
                    
                    elif response.data is not None:
                        # Play audio response asynchronously
                        await player.play_audio_data(response.data)
                    
                    # Handle tool calls
                    elif response.tool_call:
                        function_responses = []
                        
                        for fc in response.tool_call.function_calls:
                            # Process the tool call using our handler
                            result, should_exit = tool_handlers.process_tool_call(fc)
                            
                            # Check if we should get the next email
                            should_get_next_email = tool_handlers.should_get_next_email
                            
                            # Create function response
                            function_response = types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"result": result}
                            )
                            function_responses.append(function_response)
                            
                            # Exit if all emails processed
                            if should_exit:
                                print("\n👋 All emails processed. Exiting...")
                                raise KeyboardInterrupt()

                        await session.send_tool_response(function_responses=function_responses)
                        
                except asyncio.TimeoutError:
                    # No response yet, continue without delay
                    pass
                
                # Minimal delay to prevent CPU overuse
                await asyncio.sleep(0.005)
                    
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
        finally:
            # Cancel audio streaming task
            if 'audio_task' in locals():
                audio_task.cancel()
            recorder.stop_recording()
            recorder.audio.terminate()
            player.close()

async def main():
    """
    Main function for the voice-driven email agent.
    """
    print("🎤 Voice-driven Inbox Clearing Agent")
    print("📧 Starting automatic inbox processing...")
    print("🎙️  Initializing voice input...")
    
    try:
        await process_realtime_voice()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
