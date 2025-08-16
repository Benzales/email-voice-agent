"""
App helper functions to initialize MCP/Gmail agent and fetch inbox emails.
These are used by the Streamlit UI to avoid duplicating core logic.
"""

from __future__ import annotations

from typing import Tuple, List, Dict, Any

from google.genai import types
from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent

from gmail_helpers import parse_gmail_search_results


async def initialize_mcp_and_gmail_agent() -> Tuple[MCPApp, Agent]:
    """Create and initialize MCP app and Gmail agent."""
    mcp_app = MCPApp(name="voice_gmail_agent")
    await mcp_app.initialize()

    gmail_agent = Agent(
        name="gmail",
        instruction="Execute Gmail operations efficiently",
        server_names=["gmail"],
        connection_persistence=True,
    )
    await gmail_agent.initialize()
    return mcp_app, gmail_agent


async def fetch_inbox_emails(gmail_agent: Agent, query: str = "in:inbox", max_results: int = 50) -> List[Dict[str, Any]]:
    """Fetch emails from Gmail inbox using the MCP Gmail tool and parse them.

    Returns a list of dicts with at least keys: 'id', 'from', 'subject'.
    """
    search_result = await gmail_agent.call_tool(
        "gmail_search_emails",
        arguments={"query": query, "maxResults": max_results},
    )
    emails = parse_gmail_search_results(search_result)
    return emails or []


async def build_gemini_tools(gmail_agent: Agent, nav_tools) -> List[types.Tool]:
    """Build Gemini tool declarations from MCP tools and navigation tools."""
    mcp_tools_result = await gmail_agent.list_tools()
    
    gemini_tools = []
    for tool in mcp_tools_result.tools:
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
    
    # Add custom complete_current_email tool
    complete_current_email_tool = nav_tools.get_complete_current_email_tool()
    gemini_tools.append(complete_current_email_tool)
    
    return gemini_tools


async def cleanup_mcp_and_gmail(mcp_app: MCPApp | None, gmail_agent: Agent | None) -> None:
    """Cleanup resources for MCP app and Gmail agent safely."""
    if gmail_agent is not None:
        try:
            await gmail_agent.__aexit__(None, None, None)
        except Exception:
            pass

    if mcp_app is not None:
        try:
            if hasattr(mcp_app, "cleanup"):
                await mcp_app.cleanup()  # type: ignore[arg-type]
            elif hasattr(mcp_app, "__aexit__"):
                await mcp_app.__aexit__(None, None, None)  # type: ignore[misc]
        except Exception:
            pass


