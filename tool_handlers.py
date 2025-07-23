"""
Tool handlers for the voice-driven email agent
Handles all tool function calls from the Gemini API
"""

from gmail_service import GmailService

class PendingAction:
    """Represents a pending action that can be executed or undone"""
    def __init__(self, action_type, email_id, handler_method, description):
        self.action_type = action_type
        self.email_id = email_id  
        self.handler_method = handler_method
        self.description = description

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
        
        # Action undo mechanism
        self.pending_action = None
        
    def _execute_pending_action(self):
        """Execute the currently pending action, if any"""
        if self.pending_action:
            print(f"🔄 Executing pending action: {self.pending_action.description}")
            success = self.pending_action.handler_method(self.pending_action.email_id)
            if success:
                self.emails_processed += 1
                self.should_get_next_email = True
                print(f"✅ {self.pending_action.description}")
            else:
                print(f"❌ Failed to {self.pending_action.description.lower()}")
            self.pending_action = None
            return success
        return False
        
    def execute_final_action(self):
        """Execute any remaining pending action before session ends"""
        if self.pending_action:
            print(f"\n🏁 Executing final pending action before exit: {self.pending_action.description}")
            return self._execute_pending_action()
        return False
        
    def _store_action(self, action_type, handler_method, description):
        """Store an action for later execution"""
        if self.current_email_id:
            # Execute any existing pending action first
            self._execute_pending_action()
            
            # Store the new action
            self.pending_action = PendingAction(
                action_type=action_type,
                email_id=self.current_email_id,
                handler_method=handler_method,
                description=description
            )
            print(f"📝 Action queued: {description} (will execute when next action is requested)")
            return f"Action queued: {description}. Say 'undo' to cancel, or request another action to confirm."
        else:
            return "No email currently selected."
    
    def _go_back_to_previous_email(self):
        """Go back to the previous email by decrementing the index"""
        if self.gmail_service.current_email_index > 0:
            # Go back to previous email
            self.gmail_service.current_email_index -= 2  # -2 because get_next_email will increment by 1
            email, remaining = self.gmail_service.get_next_email()
            if email:
                self.current_email_id = email['id']
                return f"Went back to previous email from {email['sender']}. Subject: {email['subject']}."
        return "Cannot go back to previous email."
            
    def handle_get_next_email(self):
        """
        Get the next email in the inbox clearing sequence
        
        Returns:
            Tuple of (result_message, should_exit)
        """
        # Removed _execute_pending_action() call - actions only execute when new actions are requested
        
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
        Mark the current email as unread (stores action for later execution)
        
        Returns:
            Result message
        """
        return self._store_action(
            action_type="mark_unread",
            handler_method=self.gmail_service.mark_as_unread,
            description="Mark as unread"
        )
            
    def handle_mark_read(self):
        """
        Mark the current email as read (stores action for later execution)
        
        Returns:
            Result message
        """
        return self._store_action(
            action_type="mark_read", 
            handler_method=self.gmail_service.mark_as_read,
            description="Mark as read"
        )
            
    def handle_archive(self):
        """
        Archive the current email (stores action for later execution)
        
        Returns:
            Result message
        """
        return self._store_action(
            action_type="archive",
            handler_method=self.gmail_service.archive_message,
            description="Archive"
        )
            
    def handle_delete_email(self):
        """
        Delete the current email (stores action for later execution)
        
        Returns:
            Result message
        """
        return self._store_action(
            action_type="delete",
            handler_method=self.gmail_service.delete_message,
            description="Delete"
        )
    
    def handle_undo_action(self):
        """
        Cancel the currently pending action and go back to the previous email
        
        Returns:
            Result message
        """
        if self.pending_action:
            cancelled_action = self.pending_action.description
            self.pending_action = None
            
            # Go back to the previous email
            back_result = self._go_back_to_previous_email()
            
            result = f"Cancelled: {cancelled_action}. {back_result}"
            print(f"↩️  Cancelled: {cancelled_action}")
            print(f"⬅️  {back_result}")
            return result
        else:
            result = "No action to undo."
            print(f"❌ {result}")
            return result
            
    def handle_read_email_content(self):
        """
        Read the body content of the current email (immediate execution - no state change)
        
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
        Get inbox statistics (immediate execution - no state change)
        
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
            
        elif function_call.name == "undoAction":
            result = self.handle_undo_action()
            
        elif function_call.name == "readEmailContent":
            result = self.handle_read_email_content()
            
        elif function_call.name == "getInboxStats":
            result = self.handle_get_inbox_stats()
            
        else:
            result = "Unknown tool called"
            
        return result, should_exit 