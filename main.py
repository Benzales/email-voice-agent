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
        self.audio_buffer = b''
        self.is_playing = False
        
    def add_audio_data(self, audio_data):
        """Add audio data to buffer"""
        self.audio_buffer += audio_data
        
    def play_buffered_audio(self, sample_rate=24000):
        """Play all buffered audio data smoothly"""
        if not self.audio_buffer or self.is_playing:
            return
            
        self.is_playing = True
        try:
            stream = self.audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
                frames_per_buffer=CHUNK
            )
            
            # Play the buffered audio data
            stream.write(self.audio_buffer)
            stream.stop_stream()
            stream.close()
            
            # Clear buffer after playing
            self.audio_buffer = b''
            
        except Exception as e:
            print(f"Error playing audio: {e}")
        finally:
            self.is_playing = False

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
            
            # Send audio data continuously
            while True:
                audio_data = recorder.get_audio_data()
                if audio_data:
                    await session.send_realtime_input(
                        audio=types.Blob(data=audio_data, mime_type="audio/pcm;rate=16000")
                    )
                
                # Check for responses
                try:
                    response = await asyncio.wait_for(session.receive().__anext__(), timeout=0.1)
                    
                    if response.data is not None:
                        # Add audio data to buffer
                        player.add_audio_data(response.data)
                    
                    # Handle tool calls
                    elif response.tool_call:
                        # Play any buffered audio before tool response
                        player.play_buffered_audio()
                        
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
                    # No response yet, try to play buffered audio
                    if player.audio_buffer and not player.is_playing:
                        player.play_buffered_audio()
                    pass
                
                await asyncio.sleep(0.1)  # Small delay to prevent blocking
                    
        except KeyboardInterrupt:
            print("\n\n👋 Exiting...")
        finally:
            recorder.stop_recording()
            recorder.audio.terminate()
            player.audio.terminate()

async def process_voice_command(audio_file_path: str, output_file_path: str = None):
    """
    Process a voice command using Gemini's audio capabilities with tool support.
    
    Args:
        audio_file_path: Path to the audio file containing the voice command
        output_file_path: Path for the output response file (optional)
    """
    if output_file_path is None:
        # Create output filename based on input filename
        input_path = Path(audio_file_path)
        output_file_path = f"response_{input_path.stem}.wav"
    
    async with client.aio.live.connect(model=model, config=config) as session:
        
        # Load and convert audio to the required format
        buffer = io.BytesIO()
        y, sr = librosa.load(audio_file_path, sr=16000)
        sf.write(buffer, y, sr, format='RAW', subtype='PCM_16')
        buffer.seek(0)
        audio_bytes = buffer.read()

        # Send the audio input to Gemini
        await session.send_realtime_input(
            audio=types.Blob(data=audio_bytes, mime_type="audio/pcm;rate=16000")
        )

        # Set up output audio file
        wf = wave.open(output_file_path, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)  # Output is 24kHz

        # Process the response
        async for response in session.receive():
            if response.data is not None:
                wf.writeframes(response.data)
            
            # Handle tool calls
            elif response.tool_call:
                function_responses = []
                for fc in response.tool_call.function_calls:
                    print(f"🔧 Tool called: {fc.name}")
                    
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

            # Un-comment this code to print audio data info
            # if response.server_content.model_turn is not None:
            #      print(response.server_content.model_turn.parts[0].inline_data.mime_type)

        wf.close()
        print(f"Voice response saved to '{output_file_path}'")

async def process_all_input_files():
    """
    Process all WAV files in the input folder and create response files.
    """
    input_folder = Path("input")
    
    if not input_folder.exists():
        print("❌ Error: 'input' folder not found")
        return
    
    wav_files = list(input_folder.glob("*.wav"))
    
    if not wav_files:
        print("❌ No WAV files found in 'input' folder")
        return
    
    print(f"🎵 Found {len(wav_files)} WAV files to process")
    
    for wav_file in wav_files:
        print(f"\n🎤 Processing: {wav_file.name}")
        try:
            output_file = f"response_{wav_file.stem}.wav"
            await process_voice_command(str(wav_file), output_file)
            print(f"✅ Successfully processed {wav_file.name}")
        except Exception as e:
            print(f"❌ Error processing {wav_file.name}: {e}")

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
