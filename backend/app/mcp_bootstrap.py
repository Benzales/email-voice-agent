import asyncio
import os
from typing import Optional

from mcp_agent.app import MCPApp
from mcp_agent.agents.agent import Agent


# Module-level singletons
_mcp_app: Optional[MCPApp] = None
_gmail_agent: Optional[Agent] = None
_init_lock = asyncio.Lock()


async def initialize_mcp() -> None:
    global _mcp_app, _gmail_agent
    async with _init_lock:
        if _gmail_agent is not None:
            return

        # Initialize MCP app (uses mcp_agent.config.yaml by default)
        _mcp_app = MCPApp(name="voice_gmail_agent_backend")
        await _mcp_app.initialize()

        # Create Gmail agent and keep connection persistent
        _gmail_agent = Agent(
            name="gmail",
            instruction="Execute Gmail operations efficiently",
            server_names=["gmail"],
            connection_persistence=True,
        )
        await _gmail_agent.initialize()

        # Warm up: list tools once so downstream calls are faster
        try:
            await _gmail_agent.list_tools()
        except Exception:
            # Do not fail startup if warmup fails; operational calls will retry
            pass


def get_gmail_agent() -> Agent:
    if _gmail_agent is None:
        raise RuntimeError("Gmail MCP agent not initialized")
    return _gmail_agent


async def cleanup_mcp() -> None:
    global _mcp_app, _gmail_agent
    # Cleanup Gmail agent
    if _gmail_agent is not None:
        try:
            await _gmail_agent.__aexit__(None, None, None)
        except Exception:
            pass
        finally:
            _gmail_agent = None

    # Cleanup MCP app
    if _mcp_app is not None:
        try:
            if hasattr(_mcp_app, 'cleanup'):
                await _mcp_app.cleanup()
            elif hasattr(_mcp_app, '__aexit__'):
                await _mcp_app.__aexit__(None, None, None)
        except Exception:
            pass
        finally:
            _mcp_app = None


