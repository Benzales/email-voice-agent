"""
Email management service extracted from main.py
Handles email fetching, parsing, and sequential processing logic
"""

from typing import List, Dict, Any, Optional
from gmail_helpers import parse_gmail_search_results


class EmailManager:
    """Manages sequential email reading with deterministic state"""
    def __init__(self):
        self.emails = []
        self.current_index = 0
        
    def set_emails(self, emails):
        """Store emails from search results"""
        self.emails = emails
        self.current_index = 0
        
    def get_current_email(self):
        """Get the current email or None if exhausted"""
        if self.current_index < len(self.emails):
            return self.emails[self.current_index]
        return None
        
    def next_email(self):
        """Move to next email"""
        self.current_index += 1
        
    def has_more_emails(self):
        """Check if there are more emails to read"""
        return self.current_index < len(self.emails) - 1
        
    def is_exhausted(self):
        """Check if all emails have been read"""
        return self.current_index >= len(self.emails)
    
    def get_progress(self) -> Dict[str, int]:
        """Get current progress information"""
        return {
            "current": self.current_index + 1 if not self.is_exhausted() else len(self.emails),
            "total": len(self.emails),
            "remaining": max(0, len(self.emails) - self.current_index)
        }


async def fetch_inbox_emails(gmail_agent, query: str = "in:inbox", max_results: int = 50) -> List[Dict[str, str]]:
    """
    Fetch emails from inbox using Gmail MCP agent
    
    Args:
        gmail_agent: Initialized Gmail MCP agent
        query: Gmail search query (default: "in:inbox")
        max_results: Maximum number of emails to fetch
        
    Returns:
        List of email dictionaries with keys: id, subject, from, date
        
    Raises:
        Exception: If email fetching fails
    """
    try:
        # Search for emails using the Gmail MCP tool
        search_result = await gmail_agent.call_tool(
            "gmail_search_emails",
            arguments={"query": query, "maxResults": max_results}
        )
        
        # Extract emails from result using helper function
        emails = parse_gmail_search_results(search_result)
        
        if emails:
            print(f"✅ Found {len(emails)} emails for query: {query}")
            return emails
        else:
            print(f"⚠️ No emails found for query: {query}")
            return []
            
    except Exception as e:
        print(f"⚠️ Error fetching emails: {e}")
        raise


async def initialize_email_manager(gmail_agent, query: str = "in:inbox", max_results: int = 50) -> EmailManager:
    """
    Initialize EmailManager with emails from inbox
    
    Args:
        gmail_agent: Initialized Gmail MCP agent
        query: Gmail search query (default: "in:inbox")
        max_results: Maximum number of emails to fetch
        
    Returns:
        EmailManager instance loaded with emails
        
    Raises:
        Exception: If email fetching or initialization fails
    """
    email_manager = EmailManager()
    
    # Fetch emails
    emails = await fetch_inbox_emails(gmail_agent, query, max_results)
    
    if not emails:
        raise Exception(f"No emails found for query: {query}")
    
    # Load emails into manager
    email_manager.set_emails(emails)
    
    return email_manager


def extract_email_details(email: Dict[str, str]) -> Dict[str, str]:
    """
    Extract and format email details for processing
    
    Args:
        email: Email dictionary from EmailManager
        
    Returns:
        Dictionary with formatted email details
    """
    return {
        "id": email.get('id', ''),
        "sender": email.get('from', 'Unknown'),
        "subject": email.get('subject', 'No subject'),
        "date": email.get('date', ''),
        "display_text": f"From {email.get('from', 'Unknown')} - {email.get('subject', 'No subject')}"
    }
