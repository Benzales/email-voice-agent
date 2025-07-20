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
                    if fc.name == "printMarkUnread":
                        result = "Email marked as unread successfully"
                        print("📧 Marking email as unread...")
                    elif fc.name == "printArchive":
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
    print("📁 Processing all WAV files in 'input' folder...")
    
    try:
        await process_all_input_files()
        print("\n🎉 All files processed successfully!")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
