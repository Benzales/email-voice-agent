"""
Tool handlers for the voice-driven email agent
Handles all tool function calls from the Gemini API
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from gmail_mcp_client import get_gmail_client, EmailMessage

logger = logging.getLogger(__name__)

class ToolHandlers:
    def __init__(self):
        self.pending_actions = []
        self.last_email_id = None
        self.last_email_summary = None
    
    async def handle_tool_call(self, function_name: str, args: Dict[str, Any]) -> str:
        """Handle function calls from the AI assistant"""
        
        handler_map = {
            "read_latest_email": self._handle_read_latest_email,
            "mark_email_unread": self._handle_mark_unread,
            "archive_email": self._handle_archive_email,
            "delete_email": self._handle_delete_email,
            "undo_action": self._handle_undo_action,
            "auto_draft_reply": self._handle_auto_draft_reply,
        }
        
        handler = handler_map.get(function_name)
        if handler:
            return await handler(args)
        else:
            return f"Unknown function: {function_name}"
    
    async def _handle_read_latest_email(self, args: Dict[str, Any]) -> str:
        """Read the latest unread email"""
        try:
            gmail_client = await get_gmail_client()
            emails = await gmail_client.gmail_list(query="is:unread", max_results=1)
            
            if not emails:
                return "No unread emails found."
            
            # Get the full email details
            email = await gmail_client.gmail_get(emails[0].id)
            if not email:
                return "Error retrieving email details."
            
            # Store for potential actions
            self.last_email_id = email.id
            
            # Create summary
            summary = f"From: {email.sender}\n"
            summary += f"Subject: {email.subject}\n"
            summary += f"Content: {email.body[:500]}..."
            
            self.last_email_summary = summary
            
            # Mark as read
            await gmail_client.gmail_mark_as_read(email.id)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error reading email: {e}")
            return f"Error reading email: {str(e)}"
    
    async def _handle_mark_unread(self, args: Dict[str, Any]) -> str:
        """Mark the last read email as unread"""
        if not self.last_email_id:
            return "No email has been read yet."
        
        self.pending_actions.append({
            "action": "mark_unread",
            "email_id": self.last_email_id,
            "description": "Mark email as unread"
        })
        
        return f"Action queued: Mark email as unread. Say 'undo' to cancel or wait for execution."
    
    async def _handle_archive_email(self, args: Dict[str, Any]) -> str:
        """Archive the last read email"""
        if not self.last_email_id:
            return "No email has been read yet."
        
        self.pending_actions.append({
            "action": "archive",
            "email_id": self.last_email_id,
            "description": "Archive email"
        })
        
        return f"Action queued: Archive email. Say 'undo' to cancel or wait for execution."
    
    async def _handle_delete_email(self, args: Dict[str, Any]) -> str:
        """Delete (trash) the last read email"""
        if not self.last_email_id:
            return "No email has been read yet."
        
        self.pending_actions.append({
            "action": "delete",
            "email_id": self.last_email_id,
            "description": "Delete email"
        })
        
        return f"Action queued: Delete email. Say 'undo' to cancel or wait for execution."
    
    async def _handle_undo_action(self, args: Dict[str, Any]) -> str:
        """Undo the last pending action"""
        if not self.pending_actions:
            return "No actions to undo."
        
        action = self.pending_actions.pop()
        return f"Undone: {action['description']}"
    
    async def _handle_auto_draft_reply(self, args: Dict[str, Any]) -> str:
        """Generate an auto-draft reply for the last read email"""
        if not self.last_email_id:
            return "No email has been read yet."
        
        try:
            gmail_client = await get_gmail_client()
            
            # Get response style from args
            style = args.get("style", "neutral")
            
            # Generate response using MCP server
            draft_response = await gmail_client.gmail_generate_response(
                self.last_email_id,
                response_style=style
            )
            
            if draft_response:
                return f"Generated draft reply:\n\n{draft_response}\n\nNote: This is just a draft. You would need to send it manually."
            else:
                return "Error generating draft reply."
            
        except Exception as e:
            logger.error(f"Error generating draft reply: {e}")
            return f"Error generating draft reply: {str(e)}"
    
    async def execute_pending_actions(self):
        """Execute all pending actions after a delay"""
        if not self.pending_actions:
            return
        
        logger.info("Executing pending actions...")
        gmail_client = await get_gmail_client()
        
        for action in self.pending_actions:
            try:
                if action["action"] == "mark_unread":
                    await gmail_client.gmail_mark_as_unread(action["email_id"])
                elif action["action"] == "archive":
                    await gmail_client.gmail_archive(action["email_id"])
                elif action["action"] == "delete":
                    await gmail_client.gmail_trash(action["email_id"])
                
                logger.info(f"Executed: {action['description']}")
            except Exception as e:
                logger.error(f"Error executing action {action['description']}: {e}")
        
        self.pending_actions = [] 