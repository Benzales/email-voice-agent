"""
OAuth-enabled email management service
Handles email fetching using direct Gmail API clients from OAuth tokens
Maintains backward compatibility with MCP-based approach
"""

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import base64
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from gmail_helpers import parse_gmail_search_results
from models import OAuthTokens
from oauth_service import create_gmail_client_from_tokens


class OAuthEmailManager:
    """
    Enhanced EmailManager that works with OAuth-authenticated Gmail clients
    Supports both MCP agents and direct Gmail API clients
    """
    
    def __init__(self):
        self.emails = []
        self.current_index = 0
        self.gmail_service = None
        self.user_id = None
        self.auth_mode = "mcp"  # "mcp" or "oauth"
        
    def set_emails(self, emails: List[Dict[str, str]]):
        """Store emails from search results"""
        self.emails = emails
        self.current_index = 0
        
    def set_gmail_service(self, gmail_service, user_id: str, auth_mode: str = "oauth"):
        """Set Gmail API service for OAuth mode"""
        self.gmail_service = gmail_service
        self.user_id = user_id
        self.auth_mode = auth_mode
        
    def get_current_email(self) -> Optional[Dict[str, str]]:
        """Get the current email or None if exhausted"""
        if self.current_index < len(self.emails):
            return self.emails[self.current_index]
        return None
        
    def next_email(self):
        """Move to next email"""
        self.current_index += 1
        
    def has_more_emails(self) -> bool:
        """Check if there are more emails to read"""
        return self.current_index < len(self.emails) - 1
        
    def is_exhausted(self) -> bool:
        """Check if all emails have been read"""
        return self.current_index >= len(self.emails)
    
    def get_progress(self) -> Dict[str, int]:
        """Get current progress information"""
        return {
            "current": self.current_index + 1 if not self.is_exhausted() else len(self.emails),
            "total": len(self.emails),
            "remaining": max(0, len(self.emails) - self.current_index)
        }
    
    async def archive_email(self, email_id: str) -> bool:
        """
        Archive an email (remove from INBOX label)
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.auth_mode == "oauth" and self.gmail_service:
                # Use direct Gmail API
                self.gmail_service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabelIds': ['INBOX']}
                ).execute()
                print(f"✅ Archived email {email_id} via OAuth")
                return True
            else:
                # This would need to be handled by the MCP agent in the calling code
                print(f"⚠️ Archive operation requires MCP agent for email {email_id}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to archive email {email_id}: {e}")
            return False
    
    async def delete_email(self, email_id: str) -> bool:
        """
        Delete an email permanently
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.auth_mode == "oauth" and self.gmail_service:
                # Use direct Gmail API
                self.gmail_service.users().messages().delete(
                    userId='me',
                    id=email_id
                ).execute()
                print(f"✅ Deleted email {email_id} via OAuth")
                return True
            else:
                # This would need to be handled by the MCP agent in the calling code
                print(f"⚠️ Delete operation requires MCP agent for email {email_id}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to delete email {email_id}: {e}")
            return False
    
    async def mark_as_read(self, email_id: str) -> bool:
        """
        Mark email as read (remove UNREAD label)
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.auth_mode == "oauth" and self.gmail_service:
                # Use direct Gmail API
                self.gmail_service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'removeLabelIds': ['UNREAD']}
                ).execute()
                print(f"✅ Marked email {email_id} as read via OAuth")
                return True
            else:
                # This would need to be handled by the MCP agent in the calling code
                print(f"⚠️ Mark as read operation requires MCP agent for email {email_id}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to mark email {email_id} as read: {e}")
            return False
    
    async def mark_as_unread(self, email_id: str) -> bool:
        """
        Mark email as unread (add UNREAD label)
        
        Args:
            email_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.auth_mode == "oauth" and self.gmail_service:
                # Use direct Gmail API
                self.gmail_service.users().messages().modify(
                    userId='me',
                    id=email_id,
                    body={'addLabelIds': ['UNREAD']}
                ).execute()
                print(f"✅ Marked email {email_id} as unread via OAuth")
                return True
            else:
                # This would need to be handled by the MCP agent in the calling code
                print(f"⚠️ Mark as unread operation requires MCP agent for email {email_id}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to mark email {email_id} as unread: {e}")
            return False


async def fetch_inbox_emails_oauth(gmail_service, query: str = "in:inbox", max_results: int = 50) -> List[Dict[str, str]]:
    """
    Fetch emails using direct Gmail API client (OAuth mode)
    
    Args:
        gmail_service: Authenticated Gmail API service
        query: Gmail search query (default: "in:inbox")
        max_results: Maximum number of emails to fetch
        
    Returns:
        List of email dictionaries with keys: id, subject, from, date
        
    Raises:
        Exception: If email fetching fails
    """
    try:
        # Search for messages
        results = gmail_service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            print(f"⚠️ No emails found for query: {query}")
            return []
        
        emails = []
        
        # Get details for each message
        for msg in messages:
            try:
                # Get message details
                message = gmail_service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                
                # Extract headers
                headers = message['payload'].get('headers', [])
                email_data = {'id': msg['id']}
                
                for header in headers:
                    name = header['name'].lower()
                    if name == 'subject':
                        email_data['subject'] = header['value']
                    elif name == 'from':
                        email_data['from'] = header['value']
                    elif name == 'date':
                        email_data['date'] = header['value']
                
                # Set defaults for missing fields
                email_data.setdefault('subject', 'No subject')
                email_data.setdefault('from', 'Unknown sender')
                email_data.setdefault('date', '')
                
                emails.append(email_data)
                
            except Exception as e:
                print(f"⚠️ Failed to get details for message {msg['id']}: {e}")
                continue
        
        print(f"✅ Found {len(emails)} emails via OAuth for query: {query}")
        return emails
        
    except Exception as e:
        print(f"❌ Error fetching emails via OAuth: {e}")
        raise


async def fetch_inbox_emails_mcp(gmail_agent, query: str = "in:inbox", max_results: int = 50) -> List[Dict[str, str]]:
    """
    Fetch emails using MCP agent (backward compatibility)
    
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
            print(f"✅ Found {len(emails)} emails via MCP for query: {query}")
            return emails
        else:
            print(f"⚠️ No emails found via MCP for query: {query}")
            return []
            
    except Exception as e:
        print(f"❌ Error fetching emails via MCP: {e}")
        raise


async def initialize_oauth_email_manager(
    gmail_service_or_agent,
    user_id: Optional[str] = None,
    query: str = "in:inbox", 
    max_results: int = 50,
    auth_mode: str = "oauth"
) -> OAuthEmailManager:
    """
    Initialize OAuthEmailManager with emails from inbox
    Supports both OAuth Gmail service and MCP agent
    
    Args:
        gmail_service_or_agent: Either Gmail API service (OAuth) or MCP agent
        user_id: User ID for OAuth mode (required for OAuth)
        query: Gmail search query (default: "in:inbox")
        max_results: Maximum number of emails to fetch
        auth_mode: "oauth" or "mcp"
        
    Returns:
        OAuthEmailManager instance loaded with emails
        
    Raises:
        Exception: If email fetching or initialization fails
    """
    email_manager = OAuthEmailManager()
    
    # Fetch emails based on auth mode
    if auth_mode == "oauth":
        if not user_id:
            raise ValueError("user_id required for OAuth mode")
        
        emails = await fetch_inbox_emails_oauth(gmail_service_or_agent, query, max_results)
        email_manager.set_gmail_service(gmail_service_or_agent, user_id, "oauth")
    else:
        emails = await fetch_inbox_emails_mcp(gmail_service_or_agent, query, max_results)
        email_manager.auth_mode = "mcp"
    
    if not emails:
        raise Exception(f"No emails found for query: {query}")
    
    # Load emails into manager
    email_manager.set_emails(emails)
    
    return email_manager


# Backward compatibility functions
async def fetch_inbox_emails(gmail_agent, query: str = "in:inbox", max_results: int = 50) -> List[Dict[str, str]]:
    """
    Backward compatibility wrapper for MCP-based email fetching
    """
    return await fetch_inbox_emails_mcp(gmail_agent, query, max_results)


async def initialize_email_manager(gmail_agent, query: str = "in:inbox", max_results: int = 50):
    """
    Backward compatibility wrapper for MCP-based email manager
    """
    return await initialize_oauth_email_manager(gmail_agent, None, query, max_results, "mcp")


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


async def create_oauth_email_manager_from_session(session, query: str = "in:inbox", max_results: int = 50) -> OAuthEmailManager:
    """
    Create OAuth email manager from user session
    
    Args:
        session: UserSession object with Gmail service
        query: Gmail search query
        max_results: Maximum number of emails to fetch
        
    Returns:
        OAuthEmailManager configured for OAuth mode
    """
    if not session.gmail_service:
        raise ValueError("Session does not have Gmail service configured")
    
    return await initialize_oauth_email_manager(
        session.gmail_service,
        session.user_info.id,
        query,
        max_results,
        "oauth"
    )
