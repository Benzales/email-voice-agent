# Voice-driven Email Agent with Google Gemini Audio Integration
# Test file: https://storage.googleapis.com/generativeai-downloads/data/16000.wav
# Install helpers for converting files: pip install librosa soundfile

import asyncio
import io
from pathlib import Path
import wave
from google import genai
from google.genai import types
import soundfile as sf
import librosa

client = genai.Client()

# Native audio output model for voice interaction:
model = "gemini-2.5-flash-preview-native-audio-dialog"

# System instruction for email agent context
config = {
    "response_modalities": ["AUDIO"],
    "system_instruction": """You are a helpful voice-driven email assistant designed for hands-free email processing during commutes. 

Always respond in a clear, friendly tone suitable for voice interaction. Keep responses concise and actionable. When processing email commands, confirm the action before proceeding.""",
}

async def process_voice_command(audio_file_path: str = "sample.wav"):
    """
    Process a voice command using Gemini's audio capabilities.
    
    Args:
        audio_file_path: Path to the audio file containing the voice command
    """
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
        wf = wave.open("response.wav", "wb")
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)  # Output is 24kHz

        # Process the response
        async for response in session.receive():
            if response.data is not None:
                wf.writeframes(response.data)

            # Un-comment this code to print audio data info
            # if response.server_content.model_turn is not None:
            #      print(response.server_content.model_turn.parts[0].inline_data.mime_type)

        wf.close()
        print("Voice response saved to 'response.wav'")

async def main():
    """
    Main function for the voice-driven email agent.
    """
    print("🎤 Voice-driven Email Agent Starting...")
    print("📧 Ready to process email commands by voice")
    print("🔊 Place your voice command in 'sample.wav' and run this script")
    
    try:
        await process_voice_command()
        print("✅ Voice command processed successfully!")
    except FileNotFoundError:
        print("❌ Error: 'sample.wav' file not found")
        print("📝 Please provide an audio file named 'sample.wav' with your voice command")
    except Exception as e:
        print(f"❌ Error processing voice command: {e}")

if __name__ == "__main__":
    asyncio.run(main())
