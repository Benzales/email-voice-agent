"""
Gemini Live and MCP integration service extracted from main.py
Handles MCP setup, tool discovery, and Gemini session management
"""

import asyncio
import os
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent
from custom_tools import EmailNavigationTools

# Load environment variables
load_dotenv()

# Get API key from environment
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please set it in your .env file.")

client = genai.Client(api_key=api_key)

# Model selection
model = "gemini-live-2.5-flash-preview"

# System instruction for direct Gmail MCP access
system_instruction = """You are a voice-driven Gmail assistant with full access to the Gmail API through MCP tools.

## PRIMARY BEHAVIOR - Single Email Focus:
- You will be provided with information for ONE email at a time
- For the email, announce ONLY: sender and subject
- After reading the email, ask what the user would like to do
- Wait for the user's command before any action
- Possible actions include: reply, archive, delete, mark as read/unread, or skip to next
- **CRITICAL WORKFLOW**: After you execute ANY action on an email (using tools like gmail_modify_email, gmail_delete_email, gmail_send_email, etc.), you MUST immediately call the complete_current_email tool. This is mandatory.
- **CRITICAL WORKFLOW**: If the user says "skip", "next", "continue", etc., immediately call the complete_current_email tool
- Do NOT ask "what would you like to do next" after completing an email action - just call complete_current_email immediately
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

## Important Action Instructions:
- **CRITICAL**: When archiving an email, you MUST use gmail_modify_email with removeLabelIds: ["INBOX"]. Do NOT add labels like "ARCHIVED". Archiving means removing from the inbox.

You can execute any Gmail action the user requests on the current email."""


async def setup_mcp_connection() -> Tuple[MCPApp, Agent]:
    """
    Initialize MCP app and Gmail agent
    
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
    Discover available Gmail tools from MCP agent
    
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


def convert_mcp_to_gemini_tools(mcp_tools: List[Any]) -> List[types.Tool]:
    """
    Convert MCP tools to Gemini-compatible format
    
    Args:
        mcp_tools: List of MCP tools from discover_gmail_tools()
        
    Returns:
        List of Gemini-compatible tools
    """
    gemini_tools = []
    
    for tool in mcp_tools:        
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
    
    print(f"✅ Converted {len(gemini_tools)} MCP tools to Gemini format")
    return gemini_tools


def create_navigation_tools(email_manager) -> EmailNavigationTools:
    """
    Create custom navigation tools for email processing
    
    Args:
        email_manager: EmailManager instance
        
    Returns:
        EmailNavigationTools instance
    """
    nav_tools = EmailNavigationTools(email_manager)
    print("✅ Created email navigation tools")
    return nav_tools


def create_gemini_session_config(gemini_tools: List[types.Tool]) -> Dict[str, Any]:
    """
    Create configuration for Gemini Live session
    
    Args:
        gemini_tools: List of Gemini-compatible tools
        
    Returns:
        Configuration dictionary for Gemini session
    """
    config = {
        "response_modalities": ["AUDIO"],
        "tools": gemini_tools,
        "system_instruction": [system_instruction]
    }
    return config


async def handle_tool_execution(gmail_agent, function_call, nav_tools: Optional[EmailNavigationTools] = None) -> types.FunctionResponse:
    """
    Handle execution of a single tool call
    
    Args:
        gmail_agent: Gmail MCP agent
        function_call: Gemini function call object
        nav_tools: Optional navigation tools for custom functions
        
    Returns:
        FunctionResponse for Gemini
        
    Raises:
        Exception: If tool execution fails
    """
    try:
        # Handle custom complete_current_email tool
        if function_call.name == "complete_current_email" and nav_tools:
            result = await nav_tools.execute_complete_current_email()
            
            return types.FunctionResponse(
                id=function_call.id,
                name=function_call.name,
                response=result
            )
        
        # Handle MCP tools
        else:
            print(f"🎯 Executing {function_call.name} with args: {dict(function_call.args)}")
            
            result = await gmail_agent.call_tool(
                function_call.name,
                arguments=dict(function_call.args)
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
            
            return types.FunctionResponse(
                id=function_call.id,
                name=function_call.name,
                response=response_content
            )
    
    except Exception as e:
        print(f"⚠️ Tool call error for {function_call.name}: {e}")
        return types.FunctionResponse(
            id=function_call.id,
            name=function_call.name,
            response={"result": f"Error: {str(e)}"}
        )


async def process_gemini_responses(session, gmail_agent, nav_tools: EmailNavigationTools, websocket=None):
    """
    Process responses from Gemini Live session
    
    Args:
        session: Gemini Live session
        gmail_agent: Gmail MCP agent
        nav_tools: Email navigation tools
        websocket: Optional WebSocket for audio streaming (replaces direct audio)
        
    Returns:
        Generator yielding processed responses
    """
    async for response in session.receive():
        try:
            # Handle interruptions
            if response.server_content and response.server_content.interrupted is True:
                print("\n🔄 Interrupted")
                if websocket:
                    # Send interruption signal to frontend
                    await websocket.send_json({"type": "audio_interrupted"})
                yield {"type": "interrupted"}
            
            # Handle audio data
            elif response.data is not None:
                if websocket:
                    # Send audio to WebSocket instead of direct player
                    await websocket.send_bytes(response.data)
                yield {"type": "audio", "data": response.data}
            
            # Handle tool calls
            elif response.tool_call:
                function_responses = []
                
                for fc in response.tool_call.function_calls:
                    function_response = await handle_tool_execution(gmail_agent, fc, nav_tools)
                    function_responses.append(function_response)
                
                # Send tool responses back to Gemini
                await session.send_tool_response(function_responses=function_responses)
                
                # Check if session should end after tool execution
                if nav_tools.should_end_session():
                    yield {"type": "session_end"}
                    break
                    
                yield {"type": "tool_executed", "functions": [fc.name for fc in response.tool_call.function_calls]}
                
        except Exception as response_error:
            print(f"⚠️ Error processing response: {response_error}")
            yield {"type": "error", "message": str(response_error)}


async def cleanup_mcp_resources(mcp_app, gmail_agent):
    """
    Clean up MCP resources safely
    
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
