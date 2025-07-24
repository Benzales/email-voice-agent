"""
Gmail MCP Client - Connects to the Gmail MCP Server
"""
import os
import json
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from mcp.client import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.types import Tool, CallToolResult, TextContent

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    """Email message data structure"""
    id: str
    thread_id: str
    sender: str
    subject: str
    body: str
    timestamp: str
    is_unread: bool
    labels: List[str]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmailMessage':
        """Create EmailMessage from dictionary"""
        return cls(
            id=data.get('id', ''),
            thread_id=data.get('threadId', ''),
            sender=data.get('sender', ''),
            subject=data.get('subject', ''),
            body=data.get('body', ''),
            timestamp=data.get('timestamp', ''),
            is_unread=data.get('isUnread', False),
            labels=data.get('labels', [])
        )


class GmailMCPClient:
    """Client for interacting with Gmail MCP Server"""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self._running = False
        self._stdio_context = None
        
    async def connect(self):
        """Connect to the Gmail MCP Server"""
        # Path to the MCP server executable
        server_path = os.path.join(os.path.dirname(__file__), "Gmail-MCP-Server", "dist", "index.js")
        
        # Create server parameters for stdio connection
        server_params = StdioServerParameters(
            command="node",
            args=[server_path],
            env={
                **os.environ,
                "GMAIL_CLIENT_ID": os.getenv("GMAIL_CLIENT_ID", ""),
                "GMAIL_CLIENT_SECRET": os.getenv("GMAIL_CLIENT_SECRET", ""),
                "GMAIL_REDIRECT_URI": os.getenv("GMAIL_REDIRECT_URI", "http://localhost:3000/auth/google/callback"),
            }
        )
        
        # Create stdio client using context manager
        self._stdio_context = stdio_client(server_params)
        self.read_stream, self.write_stream = await self._stdio_context.__aenter__()
        
        # Create session
        self.session = ClientSession(self.read_stream, self.write_stream)
        await self.session.__aenter__()
        
        # Initialize the connection
        await self.session.initialize()
        self._running = True
        
        logger.info("Connected to Gmail MCP Server")
        
        # List available tools
        tools = await self.session.list_tools()
        logger.info(f"Available tools: {[tool.name for tool in tools.tools]}")
        
    async def disconnect(self):
        """Disconnect from the MCP server"""
        self._running = False
        if self.session:
            await self.session.__aexit__(None, None, None)
        if self._stdio_context:
            await self._stdio_context.__aexit__(None, None, None)
        logger.info("Disconnected from Gmail MCP Server")
    
    async def _call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool on the MCP server"""
        if not self.session:
            raise RuntimeError("Not connected to MCP server")
            
        result = await self.session.call_tool(tool_name, arguments or {})
        
        # Extract content from result
        if isinstance(result, CallToolResult):
            if result.content and len(result.content) > 0:
                content = result.content[0]
                if isinstance(content, TextContent):
                    try:
                        # Try to parse as JSON
                        return json.loads(content.text)
                    except json.JSONDecodeError:
                        # Return as plain text if not JSON
                        return content.text
        
        return result
    
    async def gmail_list(self, query: str = "is:unread", max_results: int = 10) -> List[EmailMessage]:
        """List emails matching the query"""
        try:
            result = await self._call_tool("gmail_list", {
                "query": query,
                "maxResults": max_results
            })
            
            # Parse emails from result
            emails = []
            if isinstance(result, list):
                for email_data in result:
                    emails.append(EmailMessage.from_dict(email_data))
            
            return emails
        except Exception as e:
            logger.error(f"Error listing emails: {e}")
            return []
    
    async def gmail_get(self, message_id: str) -> Optional[EmailMessage]:
        """Get a specific email by ID"""
        try:
            result = await self._call_tool("gmail_get", {"messageId": message_id})
            if result:
                return EmailMessage.from_dict(result)
            return None
        except Exception as e:
            logger.error(f"Error getting email: {e}")
            return None
    
    async def gmail_modify(self, message_id: str, add_labels: List[str] = None, remove_labels: List[str] = None) -> bool:
        """Modify email labels"""
        try:
            await self._call_tool("gmail_modify", {
                "messageId": message_id,
                "addLabelIds": add_labels or [],
                "removeLabelIds": remove_labels or []
            })
            return True
        except Exception as e:
            logger.error(f"Error modifying email: {e}")
            return False
    
    async def gmail_send(self, to: str, subject: str, body: str) -> bool:
        """Send an email"""
        try:
            await self._call_tool("gmail_send", {
                "to": to,
                "subject": subject,
                "body": body
            })
            return True
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def gmail_trash(self, message_id: str) -> bool:
        """Move email to trash"""
        try:
            await self._call_tool("gmail_trash", {"messageId": message_id})
            return True
        except Exception as e:
            logger.error(f"Error trashing email: {e}")
            return False
    
    async def gmail_archive(self, message_id: str) -> bool:
        """Archive an email"""
        # Archive is done by removing INBOX label
        return await self.gmail_modify(message_id, remove_labels=["INBOX"])
    
    async def gmail_mark_as_read(self, message_id: str) -> bool:
        """Mark email as read"""
        return await self.gmail_modify(message_id, remove_labels=["UNREAD"])
    
    async def gmail_mark_as_unread(self, message_id: str) -> bool:
        """Mark email as unread"""
        return await self.gmail_modify(message_id, add_labels=["UNREAD"])
    
    async def gmail_generate_response(self, message_id: str, response_style: str = "neutral") -> Optional[str]:
        """Generate a response to an email"""
        try:
            result = await self._call_tool("gmail_generate_response", {
                "messageId": message_id,
                "responseStyle": response_style
            })
            return result if isinstance(result, str) else None
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return None


# Singleton instance
_gmail_client: Optional[GmailMCPClient] = None


async def get_gmail_client() -> GmailMCPClient:
    """Get or create the Gmail MCP client instance"""
    global _gmail_client
    
    if _gmail_client is None:
        _gmail_client = GmailMCPClient()
        await _gmail_client.connect()
    
    return _gmail_client


async def cleanup_gmail_client():
    """Clean up the Gmail MCP client"""
    global _gmail_client
    
    if _gmail_client:
        await _gmail_client.disconnect()
        _gmail_client = None