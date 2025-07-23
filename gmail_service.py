"""
Gmail Service Module for Voice-driven Email Agent
Handles OAuth2 authentication and Gmail API operations
"""

import os
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import base64
from email.mime.text import MIMEText
from datetime import datetime

# Gmail API scopes - modify messages, read email, and manage drafts
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailService:
    def __init__(self, token_file='token.pickle', credentials_file='credentials.json'):
        """
        Initialize Gmail service with OAuth2 authentication
        
        Args:
            token_file: Path to store authentication token
            credentials_file: Path to OAuth2 credentials JSON file
        """
        self.token_file = token_file
        self.credentials_file = credentials_file
        self.service = None
        self.creds = None
        # For sequential email processing
        self.current_email_list = []
        self.current_email_index = -1
        
    def authenticate(self):
        """
        Authenticate with Gmail API using OAuth2
        
        Returns:
            Authenticated Gmail service object
        """
        # Token file stores the user's access and refresh tokens
        if os.path.exists(self.token_file):
            with open(self.token_file, 'rb') as token:
                self.creds = pickle.load(token)
        
        # If there are no (valid) credentials available, let the user log in
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file '{self.credentials_file}' not found. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(self.token_file, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('gmail', 'v1', credentials=self.creds)
        return self.service
    
    def list_messages(self, query='', max_results=10):
        """
        List messages in the user's mailbox
        
        Args:
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            max_results: Maximum number of messages to return
            
        Returns:
            List of message objects
        """
        try:
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            return messages
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []
    
    def get_message(self, msg_id):
        """
        Get a specific message by ID
        
        Args:
            msg_id: The ID of the message to retrieve
            
        Returns:
            Message object with full details
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=msg_id
            ).execute()
            
            return message
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
    
    def get_message_details(self, msg_id):
        """
        Get formatted message details including subject, sender, and snippet
        
        Args:
            msg_id: The ID of the message
            
        Returns:
            Dictionary with message details
        """
        message = self.get_message(msg_id)
        if not message:
            return None
        
        headers = message['payload'].get('headers', [])
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extract body content
        body = self.extract_body(message['payload'])
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'snippet': message.get('snippet', ''),
            'body': body,
            'labelIds': message.get('labelIds', [])
        }
    
    def extract_body(self, payload):
        """
        Extract the body content from email payload
        
        Args:
            payload: Email payload object
            
        Returns:
            Email body as string
        """
        body = ""
        
        # Check if it's a single part message
        if 'parts' not in payload:
            if payload.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
        else:
            # Multi-part message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if part.get('body', {}).get('data'):
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if part.get('body', {}).get('data'):
                        # Basic HTML stripping for readability
                        html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        # Simple regex to remove HTML tags
                        import re
                        body = re.sub('<[^<]+?>', '', html_body)
        
        return body.strip()
    
    def mark_as_unread(self, msg_id):
        """
        Mark a message as unread
        
        Args:
            msg_id: The ID of the message to mark as unread
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def mark_as_read(self, msg_id):
        """
        Mark a message as read
        
        Args:
            msg_id: The ID of the message to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def archive_message(self, msg_id):
        """
        Archive a message (remove from INBOX)
        
        Args:
            msg_id: The ID of the message to archive
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def delete_message(self, msg_id):
        """
        Move a message to trash
        
        Args:
            msg_id: The ID of the message to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=msg_id
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return False
    
    def send_message(self, to, subject, body):
        """
        Send an email message
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            
        Returns:
            Sent message object if successful, None otherwise
        """
        try:
            message = MIMEText(body)
            message['to'] = to
            message['subject'] = subject
            
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            sent_message = self.service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            return sent_message
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return None
    
    def get_latest_unread_message(self):
        """
        Get the most recent unread message
        
        Returns:
            Message details dictionary or None if no unread messages
        """
        messages = self.list_messages(query='is:unread', max_results=1)
        if messages:
            return self.get_message_details(messages[0]['id'])
        return None
    
    def search_messages(self, query, max_results=10):
        """
        Search messages with a Gmail query
        
        Args:
            query: Gmail search query
            max_results: Maximum number of results
            
        Returns:
            List of message detail dictionaries
        """
        messages = self.list_messages(query=query, max_results=max_results)
        results = []
        
        for msg in messages:
            details = self.get_message_details(msg['id'])
            if details:
                results.append(details)
        
        return results
    
    # New methods for sequential inbox processing
    
    def initialize_inbox_session(self, query='in:inbox', max_results=50):
        """
        Initialize a new inbox clearing session
        
        Args:
            query: Gmail search query (default: all inbox messages)
            max_results: Maximum number of emails to process
            
        Returns:
            Number of emails loaded for processing
        """
        messages = self.list_messages(query=query, max_results=max_results)
        self.current_email_list = messages
        self.current_email_index = -1
        return len(self.current_email_list)
    
    def get_next_email(self):
        """
        Get the next email in the current session
        
        Returns:
            Tuple of (email_details, remaining_count) or (None, 0) if no more emails
        """
        if not self.current_email_list:
            return None, 0
        
        self.current_email_index += 1
        
        if self.current_email_index >= len(self.current_email_list):
            # No more emails
            self.current_email_list = []
            self.current_email_index = -1
            return None, 0
        
        msg_id = self.current_email_list[self.current_email_index]['id']
        details = self.get_message_details(msg_id)
        remaining = len(self.current_email_list) - self.current_email_index - 1
        
        return details, remaining
    
    def skip_current_email(self):
        """
        Skip the current email without taking action
        
        Returns:
            True if successful
        """
        # No action needed, just return True
        return True
    
    def get_inbox_stats(self):
        """
        Get inbox statistics
        
        Returns:
            Dictionary with inbox stats
        """
        try:
            # Get unread count
            unread_result = self.service.users().messages().list(
                userId='me',
                q='is:unread in:inbox'
            ).execute()
            unread_count = unread_result.get('resultSizeEstimate', 0)
            
            # Get total inbox count
            inbox_result = self.service.users().messages().list(
                userId='me',
                q='in:inbox'
            ).execute()
            total_count = inbox_result.get('resultSizeEstimate', 0)
            
            return {
                'total': total_count,
                'unread': unread_count,
                'read': total_count - unread_count
            }
        except HttpError as error:
            print(f'An error occurred: {error}')
            return {'total': 0, 'unread': 0, 'read': 0}
    
    # Draft reply functionality
    
    def create_draft_reply(self, original_msg_id, reply_body):
        """
        Create a draft reply to an email
        
        Args:
            original_msg_id: The ID of the original message to reply to
            reply_body: The body text of the reply
            
        Returns:
            Draft object if successful, None otherwise
        """
        try:
            # Get the original message to extract reply details
            original_message = self.get_message(original_msg_id)
            if not original_message:
                return None
            
            headers = original_message['payload'].get('headers', [])
            original_subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
            original_from = next((h['value'] for h in headers if h['name'] == 'From'), '')
            original_message_id = next((h['value'] for h in headers if h['name'] == 'Message-ID'), '')
            
            # Extract email address from "Name <email@domain.com>" format
            import re
            email_match = re.search(r'<([^>]+)>', original_from)
            reply_to = email_match.group(1) if email_match else original_from
            
            # Create reply subject
            reply_subject = f"Re: {original_subject}" if not original_subject.startswith('Re:') else original_subject
            
            # Create the reply message
            message = MIMEText(reply_body)
            message['to'] = reply_to
            message['subject'] = reply_subject
            message['In-Reply-To'] = original_message_id
            message['References'] = original_message_id
            
            # Create draft
            draft_message = {
                'message': {
                    'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8'),
                    'threadId': original_message.get('threadId')
                }
            }
            
            draft = self.service.users().drafts().create(
                userId='me',
                body=draft_message
            ).execute()
            
            return draft
            
        except HttpError as error:
            print(f'An error occurred creating draft: {error}')
            return None
    
    def update_draft(self, draft_id, new_body):
        """
        Update an existing draft with new content
        
        Args:
            draft_id: The ID of the draft to update
            new_body: The new body text for the draft
            
        Returns:
            Updated draft object if successful, None otherwise
        """
        try:
            # Get the existing draft
            existing_draft = self.service.users().drafts().get(
                userId='me',
                id=draft_id
            ).execute()
            
            if not existing_draft:
                return None
            
            # Decode the existing message to get headers
            existing_raw = existing_draft['message']['raw']
            existing_decoded = base64.urlsafe_b64decode(existing_raw).decode('utf-8')
            
            # Extract headers from existing message
            lines = existing_decoded.split('\n')
            headers = {}
            body_start = 0
            
            for i, line in enumerate(lines):
                if line.strip() == '':
                    body_start = i + 1
                    break
                if ':' in line:
                    key, value = line.split(':', 1)
                    headers[key.strip()] = value.strip()
            
            # Create new message with updated body
            message = MIMEText(new_body)
            for key, value in headers.items():
                if key.lower() not in ['content-type', 'content-transfer-encoding', 'mime-version']:
                    message[key] = value
            
            # Update the draft
            updated_draft = {
                'message': {
                    'raw': base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8'),
                    'threadId': existing_draft['message'].get('threadId')
                }
            }
            
            draft = self.service.users().drafts().update(
                userId='me',
                id=draft_id,
                body=updated_draft
            ).execute()
            
            return draft
            
        except HttpError as error:
            print(f'An error occurred updating draft: {error}')
            return None
    
    def get_draft(self, draft_id):
        """
        Get a draft by ID
        
        Args:
            draft_id: The ID of the draft to retrieve
            
        Returns:
            Draft details dictionary or None if not found
        """
        try:
            draft = self.service.users().drafts().get(
                userId='me',
                id=draft_id
            ).execute()
            
            if not draft:
                return None
            
            # Decode the message
            message_raw = draft['message']['raw']
            message_decoded = base64.urlsafe_b64decode(message_raw).decode('utf-8')
            
            # Parse headers and body
            lines = message_decoded.split('\n')
            headers = {}
            body_lines = []
            in_body = False
            
            for line in lines:
                if not in_body:
                    if line.strip() == '':
                        in_body = True
                        continue
                    if ':' in line:
                        key, value = line.split(':', 1)
                        headers[key.strip().lower()] = value.strip()
                else:
                    body_lines.append(line)
            
            body = '\n'.join(body_lines).strip()
            
            return {
                'id': draft_id,
                'to': headers.get('to', ''),
                'subject': headers.get('subject', ''),
                'body': body,
                'message_id': draft['message']['id']
            }
            
        except HttpError as error:
            print(f'An error occurred getting draft: {error}')
            return None
    
    def send_draft(self, draft_id):
        """
        Send a draft
        
        Args:
            draft_id: The ID of the draft to send
            
        Returns:
            Sent message object if successful, None otherwise
        """
        try:
            sent_message = self.service.users().drafts().send(
                userId='me',
                body={'id': draft_id}
            ).execute()
            
            return sent_message
            
        except HttpError as error:
            print(f'An error occurred sending draft: {error}')
            return None
    
    def delete_draft(self, draft_id):
        """
        Delete a draft
        
        Args:
            draft_id: The ID of the draft to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().drafts().delete(
                userId='me',
                id=draft_id
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f'An error occurred deleting draft: {error}')
            return False 