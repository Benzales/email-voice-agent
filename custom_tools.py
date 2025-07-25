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
    
    def get_next_email_tool(self) -> types.Tool:
        """Create a Gemini tool for advancing to the next email"""
        return types.Tool(
            function_declarations=[{
                "name": "next_email",
                "description": "Move to the next email in the inbox sequence. Call this when the user says 'next', 'skip', or similar navigation commands.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }]
        )
    
    async def execute_next_email(self) -> Dict[str, Any]:
        """Execute the next email navigation"""
        try:
            if self.email_manager.is_exhausted():
                return {
                    "success": False,
                    "message": "You've reached the end of your inbox. All emails have been reviewed.",
                    "next_email": None
                }
            
            # Move to next email
            self.email_manager.next_email()
            
            if self.email_manager.is_exhausted():
                return {
                    "success": True,
                    "message": "You've reached the end of your inbox. All emails have been reviewed.",
                    "next_email": None
                }
            
            # Get the next email
            current_email = self.email_manager.get_current_email()
            
            if current_email:
                email_id = current_email.get('id', '')
                sender = current_email.get('from', 'Unknown')
                subject = current_email.get('subject', 'No subject')
                
                return {
                    "success": True,
                    "message": f"From {sender} - {subject}\n[Current email ID: {email_id}]\nWhat would you like to do with this email?",
                    "next_email": {
                        "id": email_id,
                        "sender": sender,
                        "subject": subject
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Error retrieving next email",
                    "next_email": None
                }
                
        except Exception as e:
            return {
                "success": False,
                "message": f"Error moving to next email: {str(e)}",
                "next_email": None
            } 