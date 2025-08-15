"""
Helper functions for Gmail MCP response parsing (vendored for backend service)
"""

from typing import List, Dict, Any


def parse_gmail_search_results(search_result) -> List[Dict[str, str]]:
    """
    Parse Gmail MCP search results into a list of email dictionaries.

    Args:
        search_result: The result from gmail_agent.call_tool("gmail_search_emails", ...)

    Returns:
        List of email dictionaries with keys: id, subject, from, date
    """
    emails = []

    if hasattr(search_result, 'content') and search_result.content:
        for content_item in search_result.content:
            if hasattr(content_item, 'text'):
                text_content = content_item.text

                # Parse the Gmail MCP response format
                lines = text_content.split('\n')
                current_email = {}

                for line in lines:
                    line = line.strip()

                    if line.startswith('ID: '):
                        # Save previous email if it exists
                        if current_email and 'id' in current_email:
                            emails.append(current_email)
                        # Start new email
                        current_email = {'id': line.replace('ID: ', '').strip()}

                    elif line.startswith('Subject: ') and 'id' in current_email:
                        current_email['subject'] = line.replace('Subject: ', '').strip()

                    elif line.startswith('From: ') and 'id' in current_email:
                        current_email['from'] = line.replace('From: ', '').strip()

                    elif line.startswith('Date: ') and 'id' in current_email:
                        current_email['date'] = line.replace('Date: ', '').strip()

                # Don't forget the last email
                if current_email and 'id' in current_email:
                    emails.append(current_email)

    return emails


