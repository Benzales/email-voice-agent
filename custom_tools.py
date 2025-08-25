#!/usr/bin/env python3
"""
Custom tools for the voice-driven email agent
"""

from typing import Dict, Any, Optional

class EmailNavigationTools:
    """Custom tools for email navigation"""
    
    def __init__(self, email_manager):
        self.email_manager = email_manager
        self.session_should_end = False
    
    def get_complete_current_email_tool(self) -> Dict[str, Any]:
        """Create an OpenAI Realtime API compatible tool for completing the current email's processing"""
        return {
            "type": "function",
            "name": "complete_current_email",
            "description": "Complete processing of the current email and move to the next one. Call this when the user says 'next', 'skip', or similar navigation commands, or after completing any action on an email (archive, delete, reply, etc.).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    
    async def execute_complete_current_email(self) -> Dict[str, Any]:
        """Execute the complete current email command"""
        try:
            self.session_should_end = True
            
            if self.email_manager.has_more_emails():
                return {
                    "success": True,
                    "message": "Moving to next email...",
                    "action": "complete_current_email_continue"
                }
            else:
                return {
                    "success": True,
                    "message": "You've reached the end of your inbox. All emails have been reviewed.",
                    "action": "complete_current_email_complete"
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error completing current email: {str(e)}",
                "action": "complete_current_email_error"
            }
    
    def should_end_session(self) -> bool:
        """Check if the session should end"""
        return self.session_should_end
    
    def reset_session_state(self):
        """Reset the session state for a new session"""
        self.session_should_end = False
    
    def end_session(self):
        """End the current session"""
        self.session_should_end = True 