# Voice-driven Email Agent with Google Gemini Audio Integration
# Test file: https://storage.googleapis.com/generativeai-downloads/data/16000.wav
# Install helpers for converting files: pip install librosa soundfile

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Google AI SDK
import google.generativeai as genai

# Import our modules
from tool_handlers import ToolHandlers
from gmail_mcp_client import get_gmail_client, cleanup_gmail_client

# Configure Gemini API
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    print("Error: GEMINI_API_KEY environment variable not set")
    print("Please set it with: export GEMINI_API_KEY='your-api-key'")
    sys.exit(1)

genai.configure(api_key=api_key)

# Available tools for the AI
tools = [
    {
        "function_declarations": [
            {
                "name": "read_latest_email",
                "description": "Read the latest unread email from inbox",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "mark_email_unread",
                "description": "Mark the current email as unread",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "archive_email",
                "description": "Archive the current email",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "delete_email",
                "description": "Delete the current email (move to trash)",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "undo_action",
                "description": "Undo the last pending action",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "auto_draft_reply",
                "description": "Generate an automatic draft reply to the current email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "style": {
                            "type": "string",
                            "description": "Style of the response: neutral, friendly, or professional",
                            "enum": ["neutral", "friendly", "professional"]
                        }
                    },
                    "required": []
                }
            }
        ]
    }
]

async def process_audio_file(audio_path: str, model, chat_session, tool_handlers: ToolHandlers):
    """Process a single audio file"""
    print(f"\n📢 Processing: {audio_path}")
    
    # Upload the audio file
    audio_file = genai.upload_file(audio_path, mime_type="audio/wav")
    
    # Send audio to Gemini with function calling enabled
    response = chat_session.send_message([
        "Listen to this audio command and execute the appropriate email action. Use the available tools to perform the requested action.",
        audio_file
    ])
    
    # Process any function calls
    if response.parts:
        for part in response.parts:
            if hasattr(part, 'function_call'):
                function_call = part.function_call
                result = await tool_handlers.handle_tool_call(
                    function_call.name,
                    dict(function_call.args) if hasattr(function_call, 'args') else {}
                )
                
                # Send the result back to continue the conversation
                response = chat_session.send_message([{
                    "function_response": {
                        "name": function_call.name,
                        "response": {"result": result}
                    }
                }])
                
                # Print the final response
                if response.text:
                    print(f"\n🤖 Assistant: {response.text}")
            elif hasattr(part, 'text') and part.text:
                print(f"\n🤖 Assistant: {part.text}")

async def execute_pending_with_delay(tool_handlers: ToolHandlers, delay: int = 5):
    """Execute pending actions after a delay"""
    await asyncio.sleep(delay)
    await tool_handlers.execute_pending_actions()

async def main():
    """Main function to process voice commands"""
    try:
        # Initialize Gmail MCP client
        print("🔌 Connecting to Gmail MCP Server...")
        gmail_client = await get_gmail_client()
        
        # Initialize tool handlers
        tool_handlers = ToolHandlers()
        
        # Create Gemini model with function calling
        model = genai.GenerativeModel(
            model_name='gemini-1.5-flash-002',
            tools=tools
        )
        
        # Start a chat session
        chat_session = model.start_chat(history=[])
        
        # Process each audio file in the input directory
        input_dir = Path("input")
        audio_files = sorted(input_dir.glob("*.wav"))
        
        if not audio_files:
            print("❌ No .wav files found in the input directory")
            return
        
        print(f"\n📁 Found {len(audio_files)} audio files to process")
        
        for audio_file in audio_files:
            await process_audio_file(str(audio_file), model, chat_session, tool_handlers)
            
            # Start a task to execute pending actions after delay
            if tool_handlers.pending_actions:
                print("\n⏳ Pending actions will execute in 5 seconds...")
                asyncio.create_task(execute_pending_with_delay(tool_handlers))
        
        # Wait a bit for any pending tasks
        await asyncio.sleep(6)
        
        print("\n✅ All audio files processed!")
        
    except Exception as e:
        logger.error(f"Error in main: {e}")
        print(f"\n❌ Error: {e}")
    finally:
        # Cleanup
        await cleanup_gmail_client()

if __name__ == "__main__":
    asyncio.run(main())
