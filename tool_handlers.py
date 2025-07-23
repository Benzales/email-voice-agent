"""
Tool handlers for the voice-driven email agent
Handles all tool function calls from the Gemini API
"""

from gmail_service import GmailService

class ToolHandlers:
    def __init__(self, gmail_service: GmailService):
        """
        Initialize tool handlers with Gmail service instance
        
        Args:
            gmail_service: Authenticated GmailService instance
        """
        self.gmail_service = gmail_service
        self.current_email_id = None
        self.emails_processed = 0
        self.should_get_next_email = False
        
    def handle_get_next_email(self):
        """
        Get the next email in the inbox clearing sequence
        
        Returns:
            Tuple of (result_message, should_exit)
        """
        email, remaining = self.gmail_service.get_next_email()
        if email:
            self.current_email_id = email['id']
            result = f"Email from {email['sender']}. Subject: {email['subject']}."
            if remaining > 0:
                result += f" {remaining} emails remaining."
            print(f"📬 Processing email {self.emails_processed + 1}")
            return result, False
        else:
            # No more emails
            result = f"Inbox clearing complete! Processed {self.emails_processed} emails."
            if self.emails_processed > 0:
                stats = self.gmail_service.get_inbox_stats()
                result += f" Inbox now has {stats['total']} emails, {stats['unread']} unread."
            print("✅ Inbox clearing completed")
            return result, True  # Signal to exit
            
    def handle_mark_unread(self):
        """
        Mark the current email as unread
        
        Returns:
            Result message
        """
        if self.current_email_id:
            success = self.gmail_service.mark_as_unread(self.current_email_id)
            result = "Marked as unread." if success else "Failed to mark as unread."
            if success:
                self.emails_processed += 1
                self.should_get_next_email = True
            print(f"📧 {result}")
            return result
        else:
            return "No email currently selected."
            
    def handle_mark_read(self):
        """
        Mark the current email as read
        
        Returns:
            Result message
        """
        if self.current_email_id:
            success = self.gmail_service.mark_as_read(self.current_email_id)
            result = "Marked as read." if success else "Failed to mark as read."
            if success:
                self.emails_processed += 1
                self.should_get_next_email = True
            print(f"📧 {result}")
            return result
        else:
            return "No email currently selected."
            
    def handle_archive(self):
        """
        Archive the current email
        
        Returns:
            Result message
        """
        if self.current_email_id:
            success = self.gmail_service.archive_message(self.current_email_id)
            result = "Archived." if success else "Failed to archive."
            if success:
                self.emails_processed += 1
                self.should_get_next_email = True
            print(f"📁 {result}")
            return result
        else:
            return "No email currently selected."
            
    def handle_delete_email(self):
        """
        Delete the current email (move to trash)
        
        Returns:
            Result message
        """
        if self.current_email_id:
            success = self.gmail_service.delete_message(self.current_email_id)
            result = "Deleted." if success else "Failed to delete."
            if success:
                self.emails_processed += 1
                self.should_get_next_email = True
            print(f"🗑️  {result}")
            return result
        else:
            return "No email currently selected."
            
    def handle_read_email_content(self):
        """
        Read the body content of the current email
        
        Returns:
            Result message with email body content only
        """
        if self.current_email_id:
            email_details = self.gmail_service.get_message_details(self.current_email_id)
            if email_details:
                if email_details['body']:
                    result = email_details['body']
                else:
                    result = "No text content available"
                
                print(f"📖 Reading email body")
                return result
            else:
                return "Failed to retrieve email content."
        else:
            return "No email currently selected."
            
    def handle_get_inbox_stats(self):
        """
        Get inbox statistics
        
        Returns:
            Result message
        """
        stats = self.gmail_service.get_inbox_stats()
        result = f"Inbox has {stats['total']} total emails: {stats['unread']} unread, {stats['read']} read."
        print(f"📊 Inbox stats retrieved")
        return result
        
    def process_tool_call(self, function_call):
        """
        Process a single tool function call
        
        Args:
            function_call: Function call object from Gemini API
            
        Returns:
            Tuple of (result, should_exit)
        """
        print(f"\n🔧 Tool called: {function_call.name}")
        
        # Reset the flag
        self.should_get_next_email = False
        should_exit = False
        
        # Handle different tool functions
        if function_call.name == "getNextEmail":
            result, should_exit = self.handle_get_next_email()
            
        elif function_call.name == "markUnread":
            result = self.handle_mark_unread()
            
        elif function_call.name == "markRead":
            result = self.handle_mark_read()
            
        elif function_call.name == "archive":
            result = self.handle_archive()
            
        elif function_call.name == "deleteEmail":
            result = self.handle_delete_email()
            
        elif function_call.name == "readEmailContent":
            result = self.handle_read_email_content()
            
        elif function_call.name == "getInboxStats":
            result = self.handle_get_inbox_stats()
            
        else:
            result = "Unknown tool called"
            
        return result, should_exit 