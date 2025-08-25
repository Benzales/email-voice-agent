"""
OpenAI Realtime API integration service
Completely replaces gemini_service.py with OpenAI Realtime API
"""

import asyncio
import os
import json
import base64
import websockets
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from custom_tools import EmailNavigationTools

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")

# OpenAI Realtime API configuration
REALTIME_API_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2025-06-03"

# System instruction adapted for OpenAI (same logic as Gemini version)
system_instruction = """You are a voice-driven Gmail assistant with full access to Gmail API through function calling.

## PRIMARY BEHAVIOR - Single Email Focus:
- You will be provided with information for ONE email at a time
- For the email, announce ONLY: sender and subject
- After reading the email, ask what the user would like to do
- Wait for the user's command before any action
- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next
- **CRITICAL WORKFLOW**: After you execute ANY action on an email (using functions like gmail_modify_email, gmail_delete_email, gmail_send_email, etc.), you MUST immediately call the complete_current_email function. This is mandatory.
- **CRITICAL WORKFLOW**: If the user says "skip", "next", "continue", etc., immediately call the complete_current_email function
- Do NOT ask "what would you like to do next" after completing an email action - just call complete_current_email immediately
- This creates an efficient workflow where each email is processed and the system moves forward automatically
- When performing actions on "this email" or "it", use the email ID that was provided with the email information

## Key Behaviors:
- Be concise but helpful in your responses
- Confirm actions concisely
- When the user says "next", "skip", or "continue", simply acknowledge and call complete_current_email
- Focus only on the current email - there is no history of previous emails in this session

## Voice Interaction:
- Speak clearly and at a moderate pace
- Use natural language to describe what you're doing
- Announce results concisely

## Email Reading Format:
When provided with email info, read it as:
"From [sender] - [subject]. What would you like to do with this email?"

## Important Action Instructions:
- **CRITICAL**: When archiving an email, you MUST use gmail_modify_email with removeLabelIds: ["INBOX"]. Do NOT add labels like "ARCHIVED". Archiving means removing from the inbox.

You can execute any Gmail action the user requests on the current email."""


class OpenAIRealtimeClient:
    """Manages OpenAI Realtime API connection and conversation"""
    
    def __init__(self):
        self.websocket = None
        self.session_config = None
        self.tools = []
        self.conversation_id = None
    
    async def connect(self, tools: List[Dict], gmail_agent, nav_tools):
        """Connect to OpenAI Realtime API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "OpenAI-Beta": "realtime=v1"
        }
        
        try:
            self.websocket = await websockets.connect(
                REALTIME_API_URL, 
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            self.tools = tools
            
            print("✅ Connected to OpenAI Realtime API")
            
            # Send session configuration
            await self._send_session_config(tools)
            
            return self
            
        except Exception as e:
            print(f"❌ Failed to connect to OpenAI Realtime API: {e}")
            raise
    
    async def _send_session_config(self, tools: List[Dict]):
        """Send initial session configuration to OpenAI"""
        config = {
            "type": "session.update",
            "session": {
                "modalities": ["text", "audio"],
                "instructions": system_instruction,
                "voice": "alloy",
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 500
                },
                "tools": tools,
                "tool_choice": "auto",
                "temperature": 0.8,
                "max_response_output_tokens": 4096
            }
        }
        
        await self.websocket.send(json.dumps(config))
        print(f"✅ Sent session config with {len(tools)} tools")
    
    async def send_audio(self, audio_data: bytes):
        """Send audio data to OpenAI"""
        try:
            # Convert to base64 for OpenAI
            audio_base64 = base64.b64encode(audio_data).decode()
            
            message = {
                "type": "input_audio_buffer.append",
                "audio": audio_base64
            }
            await self.websocket.send(json.dumps(message))
            
        except Exception as e:
            print(f"⚠️ Error sending audio to OpenAI: {e}")
    
    async def send_text(self, text: str):
        """Send text message to start conversation"""
        try:
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": text
                        }
                    ]
                }
            }
            await self.websocket.send(json.dumps(message))
            
            # Trigger response generation
            await self.websocket.send(json.dumps({"type": "response.create"}))
            
        except Exception as e:
            print(f"⚠️ Error sending text to OpenAI: {e}")
    
    async def send_function_result(self, call_id: str, output: str):
        """Send function execution result back to OpenAI"""
        try:
            message = {
                "type": "conversation.item.create",
                "item": {
                    "type": "function_call_output",
                    "call_id": call_id,
                    "output": output
                }
            }
            await self.websocket.send(json.dumps(message))
            
            # Trigger response generation after function result
            await self.websocket.send(json.dumps({"type": "response.create"}))
            
        except Exception as e:
            print(f"⚠️ Error sending function result to OpenAI: {e}")
    
    async def receive_events(self):
        """Receive events from OpenAI Realtime API"""
        try:
            async for message in self.websocket:
                try:
                    event = json.loads(message)
                    yield event
                except json.JSONDecodeError:
                    print(f"Failed to decode OpenAI message: {message}")
                    continue
        except websockets.exceptions.ConnectionClosed:
            print("🔌 OpenAI WebSocket connection closed")
        except Exception as e:
            print(f"⚠️ Error receiving from OpenAI: {e}")
    
    async def close(self):
        """Close the WebSocket connection"""
        if self.websocket:
            await self.websocket.close()
            print("🔌 OpenAI Realtime connection closed")


# Core functions to completely replace gemini_service.py functions

async def setup_mcp_connection() -> Tuple[MCPApp, Agent]:
    """
    Initialize MCP app and Gmail agent (same as original, no Gemini dependency)
    
    Returns:
        Tuple of (MCPApp, Agent) instances
        
    Raises:
        Exception: If MCP setup fails
    """
    try:
        # Initialize MCP app
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
        
        print("✅ MCP connection and Gmail agent initialized")
        return mcp_app, gmail_agent
        
    except Exception as e:
        print(f"❌ Failed to setup MCP connection: {e}")
        raise


async def discover_gmail_tools(gmail_agent) -> List[Any]:
    """
    Discover available Gmail tools from MCP agent (same as original)
    
    Args:
        gmail_agent: Initialized Gmail MCP agent
        
    Returns:
        List of available MCP tools
        
    Raises:
        Exception: If tool discovery fails
    """
    try:
        mcp_tools_result = await gmail_agent.list_tools()
        print(f"✅ Discovered {len(mcp_tools_result.tools)} Gmail MCP tools")
        return mcp_tools_result.tools
        
    except Exception as e:
        print(f"❌ Failed to discover Gmail tools: {e}")
        raise


def convert_mcp_to_openai_tools(mcp_tools: List[Any]) -> List[Dict]:
    """
    Convert MCP tools to OpenAI function format (replaces convert_mcp_to_gemini_tools)
    
    Args:
        mcp_tools: List of MCP tools from discover_gmail_tools()
        
    Returns:
        List of OpenAI-compatible function definitions
    """
    openai_tools = []
    
    for tool in mcp_tools:
        # Extract parameters, filtering out schema metadata
        parameters = {}
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            parameters = {
                k: v
                for k, v in tool.inputSchema.items()
                if k not in ["additionalProperties", "$schema"]
            }
            
            # Ensure required field exists
            if "required" not in parameters:
                parameters["required"] = []
        
        # Create OpenAI Realtime API tool definition
        openai_tool = {
            "type": "function",
            "name": tool.name,
            "description": tool.description,
            "parameters": parameters
        }
        
        openai_tools.append(openai_tool)
        
        # Debug first few tools to see their structure
        if len(openai_tools) <= 3:
            print(f"🔧 Tool {len(openai_tools)}: {tool.name}")
            print(f"🔧   Description: {tool.description[:100]}...")
            print(f"🔧   Parameters: {parameters}")
    
    print(f"✅ Converted {len(openai_tools)} MCP tools to OpenAI format")
    return openai_tools


def create_navigation_tools(email_manager) -> EmailNavigationTools:
    """
    Create custom navigation tools for email processing (same as original)
    
    Args:
        email_manager: EmailManager instance
        
    Returns:
        EmailNavigationTools instance
    """
    nav_tools = EmailNavigationTools(email_manager)
    print("✅ Created email navigation tools")
    return nav_tools


def create_openai_session_config(openai_tools: List[Dict]) -> Dict[str, Any]:
    """
    Create configuration for OpenAI session (replaces create_gemini_session_config)
    
    Args:
        openai_tools: List of OpenAI-compatible function definitions
        
    Returns:
        Configuration dictionary for OpenAI session
    """
    config = {
        "tools": openai_tools,
        "instructions": system_instruction,
        "modalities": ["text", "audio"],
        "voice": "alloy",
        "temperature": 0.8
    }
    
    print(f"🔧 OpenAI session config: {len(openai_tools)} tools, system instruction length: {len(system_instruction)} chars")
    print(f"🔧 System instruction preview: {system_instruction[:200]}...")
    
    return config


async def handle_openai_tool_execution(tool_call, gmail_agent, call_id: str, nav_tools: Optional[EmailNavigationTools] = None):
    """
    Handle OpenAI function call execution (replaces handle_tool_execution)
    
    Args:
        tool_call: OpenAI function call object
        gmail_agent: Gmail MCP agent
        call_id: The call ID from the OpenAI event
        nav_tools: Optional navigation tools for custom functions
        
    Returns:
        Function execution result for OpenAI
    """
    try:
        function_name = tool_call.get("name") or tool_call.get("function", {}).get("name")
        function_args_str = tool_call.get("arguments") or tool_call.get("function", {}).get("arguments", "{}")
        function_args = json.loads(function_args_str)
        
        # Handle custom complete_current_email tool
        if function_name == "complete_current_email" and nav_tools:
            result = await nav_tools.execute_complete_current_email()
            return {
                "call_id": call_id,
                "output": json.dumps(result),
                "success": True
            }
        
        # Handle MCP tools
        else:
            print(f"🎯 Executing {function_name} with args: {function_args}")
            
            result = await gmail_agent.call_tool(function_name, arguments=function_args)
            
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
            
            return {
                "call_id": call_id,
                "output": json.dumps(response_content),
                "success": True
            }
    
    except Exception as e:
        print(f"⚠️ Tool call error for {function_name or 'unknown'}: {e}")
        return {
            "call_id": call_id,
            "output": json.dumps({"error": str(e)}),
            "success": False
        }


async def process_openai_responses(openai_client: OpenAIRealtimeClient, gmail_agent, nav_tools: EmailNavigationTools, websocket=None):
    """
    Process responses from OpenAI Realtime API (replaces process_gemini_responses)
    
    Args:
        openai_client: OpenAI Realtime client
        gmail_agent: Gmail MCP agent
        nav_tools: Email navigation tools
        websocket: Optional WebSocket for audio streaming
        
    Returns:
        Generator yielding processed responses
    """
    async for event in openai_client.receive_events():
        try:
            event_type = event.get("type")
            
            # Handle audio responses
            if event_type == "response.audio.delta":
                audio_delta = event.get("delta", "")
                if audio_delta and websocket:
                    try:
                        audio_bytes = base64.b64decode(audio_delta)
                        await websocket.send_bytes(audio_bytes)
                        yield {"type": "audio", "data": audio_bytes}
                    except Exception as e:
                        print(f"⚠️ Error processing audio delta: {e}")
            
            # Handle function calls
            elif event_type == "response.function_call_arguments.done":
                function_call = event.get("item", {}).get("call")
                if function_call:
                    # Execute the function
                    result = await handle_openai_tool_execution(function_call, gmail_agent, nav_tools)
                    
                    # Send result back to OpenAI
                    await openai_client.send_function_result(
                        result["call_id"], 
                        result["output"]
                    )
                    
                    # Check if session should end after tool execution
                    if nav_tools.should_end_session():
                        yield {"type": "session_end"}
                        break
                    
                    yield {"type": "tool_executed", "function": function_call.get("function", {}).get("name")}
            
            # Handle transcriptions
            elif event_type == "conversation.item.input_audio_transcription.completed":
                transcript = event.get("transcript", "")
                if transcript:
                    print(f"🎤 User said: {transcript}")
                    yield {"type": "transcript", "text": transcript}
            
            # Handle errors
            elif event_type == "error":
                error = event.get("error", {})
                error_message = error.get("message", "Unknown OpenAI error")
                print(f"❌ OpenAI Error: {error_message}")
                if websocket:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"OpenAI Error: {error_message}",
                        "recoverable": True
                    })
                yield {"type": "error", "message": error_message}
            
            # Handle session updates
            elif event_type == "session.updated":
                print("✅ OpenAI session updated successfully")
                yield {"type": "session_updated"}
                
        except Exception as response_error:
            print(f"⚠️ Error processing OpenAI response: {response_error}")
            yield {"type": "error", "message": str(response_error)}


async def cleanup_mcp_resources(mcp_app, gmail_agent):
    """
    Clean up MCP resources safely (same as original)
    
    Args:
        mcp_app: MCPApp instance
        gmail_agent: Gmail Agent instance
    """
    cleanup_errors = []
    
    # Cleanup Gmail agent
    if gmail_agent:
        try:
            await gmail_agent.__aexit__(None, None, None)
        except Exception as e:
            cleanup_errors.append(f"Gmail agent cleanup: {e}")
    
    # Cleanup MCP app
    if mcp_app:
        try:
            # Force cleanup of MCP app connections
            if hasattr(mcp_app, 'cleanup'):
                await mcp_app.cleanup()
            elif hasattr(mcp_app, '__aexit__'):
                await mcp_app.__aexit__(None, None, None)
        except Exception as e:
            cleanup_errors.append(f"MCP app cleanup: {e}")
    
    # Report any cleanup errors
    if cleanup_errors:
        print(f"⚠️ Cleanup errors: {'; '.join(cleanup_errors)}")
    
    # Force garbage collection to help with resource cleanup
    import gc
    gc.collect()
    
    print("✅ MCP resources cleaned up")
