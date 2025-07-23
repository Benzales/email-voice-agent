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

read_content_tool = {
    "name": "readEmailContent",
    "description": "Read the full content/body of the current email."
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
    read_content_tool,
    get_inbox_stats_tool
]}]

# System instruction for email agent context
system_instruction = """You are a voice-driven email assistant dedicated to helping users efficiently clear their Gmail inbox.

## Your Primary Function: Inbox Clearing

You operate in a continuous inbox clearing mode:
1. Announce each email's sender and subject clearly and concisely
2. Wait for the user's action command (archive, delete, mark as read/unread, read content)
3. Execute the action and automatically move to the next email
4. Continue until all emails are processed

## Key behaviors:
- Keep responses extremely concise - just sender and subject
- ALWAYS automatically call getNextEmail after completing an action (except when reading content)
- When inbox is cleared, announce completion with stats
- Be efficient and focused on helping users process emails quickly

## Available actions for each email:
- Archive - removes from inbox
- Delete - moves to trash
- Mark as read/unread - changes read status
- Read content - reads the full email body aloud
- If the user says 'skip', treat it as 'mark as unread'

## Voice interactions:
- Speak clearly and at a moderate pace
- Use natural pauses between emails
- Confirm actions briefly (e.g., "Archived", "Deleted")
- When reading content, read it clearly and completely

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
                # Get audio data from queue (timeout to check stop flag)
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
        print("💬 Available commands: archive, delete, skip, mark as read/unread, read content")
        print("🔊 I'll announce each email - just say what to do with it")
        print("Press Ctrl+C to exit")
        print("\n" + "="*50)
        
        try:
            # Start recording
            recorder.start_recording()
            
            # Start audio output stream and playback thread
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
            
            # Auto-trigger first email
            if should_get_next_email:
                should_get_next_email = False
                await session.send_tool_response(function_responses=[
                    types.FunctionResponse(
                        id="auto_next",
                        name="getNextEmail",
                        response={"trigger": "auto"}
                    )
                ])
            
            # Keep the session running continuously
            while True:
                try:
                    # Main response processing loop using Google's recommended pattern
                    async for response in session.receive():
                        # Handle interruptions immediately
                        if response.server_content and response.server_content.interrupted is True:
                            print("\n🔄 Interrupted - clearing audio queue")
                            # Clear any queued audio as Google suggests
                            player.clear_queue()
                            print("👂 Processing your command...")
                        
                        # Handle audio data
                        elif response.data is not None:
                            # Queue audio for playback (non-blocking)
                            player.queue_audio(response.data)
                        
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
                            
                            # If we need to get the next email, do it after sending tool responses
                            if should_get_next_email:
                                should_get_next_email = False
                                await session.send_tool_response(function_responses=[
                                    types.FunctionResponse(
                                        id="auto_next",
                                        name="getNextEmail",
                                        response={"trigger": "auto"}
                                    )
                                ])
                    
                    # If we reach here, the async for loop exited (no more messages)
                    # Small delay before retrying to avoid busy loop
                    await asyncio.sleep(0.005)
                    
                except asyncio.CancelledError:
                    # Task was cancelled, re-raise to exit properly
                    raise
                except Exception as e:
                    print(f"Error in response processing: {e}")
                    await asyncio.sleep(0.005)  # Brief pause before retrying
                    
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
