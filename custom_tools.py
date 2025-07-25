#!/usr/bin/env python3
"""
Custom tools for the voice-driven email agent
"""

from typing import Dict, Any, Optional
from google.genai import types

class EmailNavigationTools:
    """Custom tools for email navigation"""
    
    def __init__(self, email_manager):
        self.email_manager = email_manager
        self.session_should_end = False
    
    def get_end_session_tool(self) -> types.Tool:
        """Create a Gemini tool for ending the current session"""
        return types.Tool(
            function_declarations=[{
                "name": "end_session",
                "description": "End the current email session. Call this when the user says 'next', 'skip', or similar navigation commands, or after completing any action on an email (archive, delete, reply, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }]
        )
    
    async def execute_end_session(self) -> Dict[str, Any]:
        """Execute the end session command"""
        try:
            self.session_should_end = True
            
            if self.email_manager.has_more_emails():
                return {
                    "success": True,
                    "message": "Moving to next email...",
                    "action": "end_session_continue"
                }
            else:
                return {
                    "success": True,
                    "message": "You've reached the end of your inbox. All emails have been reviewed.",
                    "action": "end_session_complete"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error ending session: {str(e)}",
                "action": "end_session_error"
            }
    
    def should_end_session(self) -> bool:
        """Check if the session should end"""
        return self.session_should_end
    
    def reset_session_state(self):
        """Reset the session state for a new session"""
        self.session_should_end = False 