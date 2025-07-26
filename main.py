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
from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from custom_tools import EmailNavigationTools
from gmail_helpers import parse_gmail_search_results
from audio_handlers import AudioRecorder, AudioPlayer

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
- CRITICAL WORKFLOW: After you execute ANY action on an email (using tools like gmail_modify_email, gmail_delete_email, gmail_send_email, etc.), briefly confirm the action with minimal words (e.g., "Archived", "Deleted", "Marked unread"), then immediately call the end_session tool
- CRITICAL WORKFLOW: If the user says "skip", "next", "continue", etc., immediately call the end_session tool
- Do NOT ask "what would you like to do next" after completing an email action - just confirm and call end_session
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

You can execute any Gmail action the user requests on the current email."""

async def send_error_message(session, error_message):
    """Send an error message to the session so the AI can respond to the user"""
    try:
        await session.send_realtime_input(
            text=f"An error occurred: {error_message}. Please acknowledge this error and continue helping the user."
        )
    except Exception as e:
        print(f"Failed to send error message to session: {e}")

async def process_single_email_session(email_manager, nav_tools, gmail_agent, gemini_tools):
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
    
    recorder = AudioRecorder()
    player = AudioPlayer()
    
    # Configuration for Gemini with all discovered MCP tools
    config = {
        "response_modalities": ["AUDIO"],
        "tools": gemini_tools,
        "system_instruction": [system_instruction]
    }
    
    session_completed = False
    
    try:
        async with client.aio.live.connect(model=model, config=config) as session:
            
            print(f"\n📧 Processing Email {email_manager.current_index + 1}/{len(email_manager.emails)}")
            print(f"   From: {sender}")
            print(f"   Subject: {subject}")
            print("   🎤 Listening...")
            
            try:
                # Start recording
                recorder.start_recording()
                player.start_output_stream()
                
                # Audio streaming task
                async def stream_audio():
                    """Continuously stream audio data to Gemini without interruption"""
                    while not nav_tools.should_end_session():
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
                
                # Send initial email information to agent
                await session.send_realtime_input(
                    text=f"Please read me this email and ask what I'd like to do with it. The email is: From {sender} - {subject} [Current email ID: {email_id}]."
                )
                
                # Main response processing loop
                while not nav_tools.should_end_session():
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
                                            # Handle custom end_session tool
                                            if fc.name == "end_session":
                                                print(f"🎯 Executing end_session tool")
                                                
                                                result = await nav_tools.execute_end_session()
                                                
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
                print("✅ Session completed")
                        
            except KeyboardInterrupt:
                print("\n\n👋 User interrupted...")
                return False  # Stop processing emails
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
    
    except Exception as connection_error:
        print(f"❌ Failed to connect to Gemini: {connection_error}")
        return False
    
    return session_completed

async def process_realtime_voice():
    """Process real-time voice input with direct MCP Gmail integration - one session per email"""
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
        print("Exiting...")
        return
    
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
    
    # Add custom end_session tool
    end_session_tool = nav_tools.get_end_session_tool()
    gemini_tools.append(end_session_tool)
    print(f"  - end_session: End the current email session and move to next email")
    
    print("\n🎤 Voice-driven Gmail Assistant Started!")
    print("📧 Processing emails one at a time with fresh sessions")
    print("💬 For each email:")
    print("   - The assistant will read the sender and subject")
    print("   - You can take action: Reply, Archive, Delete, Mark as read/unread")
    print("   - Say 'Next' or 'Skip' to move to the next email")
    print("   - Each email gets a fresh conversation context")
    print("Press Ctrl+C to exit")
    print("\n" + "="*50)
    
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
                print("\n⏭️  Moving to next email...")
                await asyncio.sleep(1)  # Brief pause between sessions
            else:
                print("\n🎉 All emails processed!")
                break
    
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"❌ Unexpected error in main loop: {e}")
    finally:
        # Cleanup MCP connection
        if gmail_agent:
            await gmail_agent.__aexit__(None, None, None)

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