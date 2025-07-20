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

# Load environment variables from .env file
load_dotenv()

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

client = genai.Client(api_key=api_key)

# Half cascade model:
model = "gemini-live-2.5-flash-preview"

# Native audio output model:
# model = "gemini-2.5-flash-preview-native-audio-dialog"

# Tool definitions for email actions
print_mark_unread = {
    "name": "markUnread",
    "description": "Marks the email as unread."
}

print_archive = {
    "name": "archive", 
    "description": "Archives the email."
}

tools = [{"function_declarations": [print_mark_unread, print_archive]}]

# System instruction for email agent context
config = {
    "response_modalities": ["AUDIO"],
    "tools": tools,
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
        
    def start_output_stream(self):
        """Start the output audio stream"""
        self.output_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=CHUNK
        )
        
    def play_audio_data(self, audio_data):
        """Play audio data in real-time"""
        try:
            if self.output_stream is None:
                self.start_output_stream()
            
            # Play the audio data immediately
            self.output_stream.write(audio_data)
            
        except Exception as e:
            print(f"Error playing audio: {e}")
    
    def close(self):
        """Close the audio stream"""
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
    
    async with client.aio.live.connect(model=model, config=config) as session:
        
        print("🎤 Voice-driven Email Agent Ready!")
        print("🔧 Available tools: Mark Unread, Archive")
        print("💬 Speak your email command (VAD enabled - will auto-detect speech)")
        print("🔊 Audio responses will play automatically")
        print("Press Ctrl+C to exit")
        print("\n" + "="*50)
        
        try:
            # Start recording
            recorder.start_recording()
            
            # Start audio output stream
            player.start_output_stream()
            
            # Send audio data continuously
            while True:
                audio_data = recorder.get_audio_data()
                if audio_data:
                    await session.send_realtime_input(
                        audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                    )
                
                # Process responses without timeout
                try:
                    # Use a very short timeout just to check for responses
                    response = await asyncio.wait_for(session.receive().__anext__(), timeout=0.01)
                    
                    if response.data is not None:
                        # Play audio response immediately
                        player.play_audio_data(response.data)
                    
                    # Handle tool calls
                    elif response.tool_call:
                        function_responses = []
                        for fc in response.tool_call.function_calls:
                            print(f"\n🔧 Tool called: {fc.name}")
                            
                            # Handle different tool functions
                            if fc.name == "markUnread":
                                result = "Email marked as unread successfully"
                                print("📧 Marking email as unread...")
                            elif fc.name == "archive":
                                result = "Email archived successfully"
                                print("📁 Archiving email...")
                            else:
                                result = "Unknown tool called"
                            
                            function_response = types.FunctionResponse(
                                id=fc.id,
                                name=fc.name,
                                response={"result": result}
                            )
                            function_responses.append(function_response)

                        await session.send_tool_response(function_responses=function_responses)
                        
                except asyncio.TimeoutError:
                    # No response yet, continue recording
                    pass
                
                # Very short delay to prevent blocking
                await asyncio.sleep(0.01)
                    
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
        finally:
            recorder.stop_recording()
            recorder.audio.terminate()
            player.close()

async def main():
    """
    Main function for the voice-driven email agent.
    """
    print("🎤 Voice-driven Email Agent Starting...")
    print("📧 Ready to process email commands by voice")
    print("🔧 Available tools: Mark Unread, Archive")
    print("🎙️  Starting real-time voice input...")
    
    try:
        await process_realtime_voice()
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
