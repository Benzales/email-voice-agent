"""
OAuth Gmail Tools for Gemini Live
Creates Gmail tools that work with OAuth authentication instead of MCP
"""

from typing import List, Dict, Any
from google import genai
from google.genai import types
from googleapiclient.discovery import Resource


class OAuthGmailTools:
    """
    Creates Gmail tools for Gemini Live that use OAuth authentication
    """
    
    def __init__(self, gmail_service: Resource):
        """
        Initialize OAuth Gmail tools with authenticated Gmail service
        
        Args:
            gmail_service: Authenticated Gmail API service from OAuth
        """
        self.gmail_service = gmail_service
    
    def get_gemini_tools(self) -> List[types.Tool]:
        """
        Get Gmail tools formatted for Gemini Live
        
        Returns:
            List of Gemini tools for Gmail operations
        """
        tools = []
        
        # Gmail modify email tool
        modify_email_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_modify_email",
                    description="Modify Gmail email labels (archive, move to trash, mark read/unread, etc.). Use addLabelIds: ['TRASH'] to trash emails, removeLabelIds: ['UNREAD'] to mark as read, addLabelIds: ['UNREAD'] to mark as unread.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "id": types.Schema(
                                type=types.Type.STRING,
                                description="Email ID to modify"
                            ),
                            "addLabelIds": types.Schema(
                                type=types.Type.ARRAY,
                                description="Label IDs to add to the email",
                                items=types.Schema(type=types.Type.STRING)
                            ),
                            "removeLabelIds": types.Schema(
                                type=types.Type.ARRAY,
                                description="Label IDs to remove from the email",
                                items=types.Schema(type=types.Type.STRING)
                            ),
                            "mark_as_read": types.Schema(
                                type=types.Type.BOOLEAN,
                                description="Mark email as read (true) or unread (false)"
                            ),
                            "mark_as_unread": types.Schema(
                                type=types.Type.BOOLEAN,
                                description="Mark email as unread (true) or read (false)"
                            )
                        },
                        required=["id"]
                    )
                )
            ]
        )
        tools.append(modify_email_tool)
        

        
        # Gmail create draft tool
        create_draft_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_create_draft",
                    description="Create a draft email that can be edited and sent later. Use this when user wants to save an email for later or prepare a response.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "to": types.Schema(
                                type=types.Type.STRING,
                                description="Recipient email address"
                            ),
                            "subject": types.Schema(
                                type=types.Type.STRING,
                                description="Email subject"
                            ),
                            "body": types.Schema(
                                type=types.Type.STRING,
                                description="Email body content"
                            ),
                            "cc": types.Schema(
                                type=types.Type.STRING,
                                description="CC email addresses (comma-separated)"
                            ),
                            "bcc": types.Schema(
                                type=types.Type.STRING,
                                description="BCC email addresses (comma-separated)"
                            ),
                            "reply_to": types.Schema(
                                type=types.Type.STRING,
                                description="Email ID this is a reply to (for threading)"
                            )
                        },
                        required=["to", "subject", "body"]
                    )
                )
            ]
        )
        tools.append(create_draft_tool)
        
        # Gmail create label tool
        create_label_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_create_label",
                    description="Create a new Gmail label",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "name": types.Schema(
                                type=types.Type.STRING,
                                description="Name of the label to create"
                            ),
                            "messageListVisibility": types.Schema(
                                type=types.Type.STRING,
                                description="Visibility in message list (show/hide)"
                            ),
                            "labelListVisibility": types.Schema(
                                type=types.Type.STRING,
                                description="Visibility in label list (labelShow/labelHide)"
                            )
                        },
                        required=["name"]
                    )
                )
            ]
        )
        tools.append(create_label_tool)
        
        # Gmail read email content tool
        read_email_content_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_read_email_content",
                    description="Read the full content/body of an email. Use this when user asks to read, see content, or know what an email says.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "id": types.Schema(
                                type=types.Type.STRING,
                                description="Email ID to read content from"
                            ),
                            "format": types.Schema(
                                type=types.Type.STRING,
                                description="Content format preference: 'text' for plain text, 'html' for HTML content. Defaults to 'text'."
                            )
                        },
                        required=["id"]
                    )
                )
            ]
        )
        tools.append(read_email_content_tool)
        
        # Gmail list labels tool
        list_labels_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_list_labels",
                    description="List all Gmail labels (folders) available in the user's account, including both system labels (Inbox, Sent, etc.) and user-created labels.",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "include_system_labels": types.Schema(
                                type=types.Type.BOOLEAN,
                                description="Include system labels like INBOX, SENT, DRAFT, etc. Defaults to true."
                            )
                        }
                    )
                )
            ]
        )
        tools.append(list_labels_tool)
        
        return tools
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a Gmail tool with OAuth authentication
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Tool arguments
            
        Returns:
            Tool execution result
        """
        try:
            if tool_name == "gmail_modify_email":
                return await self._modify_email(arguments)
            elif tool_name == "gmail_create_draft":
                return await self._create_draft(arguments)
            elif tool_name == "gmail_create_label":
                return await self._create_label(arguments)
            elif tool_name == "gmail_read_email_content":
                return await self._read_email_content(arguments)
            elif tool_name == "gmail_list_labels":
                return await self._list_labels(arguments)
            else:
                return {"error": f"Unknown tool: {tool_name}"}
                
        except Exception as e:
            return {"error": f"Tool execution failed: {e}"}
    
    async def _modify_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Modify email labels and read status"""
        email_id = args["id"]
        
        # Build modification request
        body = {}
        
        # Handle label modifications
        if "addLabelIds" in args and args["addLabelIds"]:
            body["addLabelIds"] = args["addLabelIds"]
        if "removeLabelIds" in args and args["removeLabelIds"]:
            body["removeLabelIds"] = args["removeLabelIds"]
            
        # Handle read/unread status
        if "mark_as_read" in args:
            if args["mark_as_read"]:
                body.setdefault("removeLabelIds", []).append("UNREAD")
            else:
                body.setdefault("addLabelIds", []).append("UNREAD")
        elif "mark_as_unread" in args:
            if args["mark_as_unread"]:
                body.setdefault("addLabelIds", []).append("UNREAD")
            else:
                body.setdefault("removeLabelIds", []).append("UNREAD")
        
        # Execute modification
        result = self.gmail_service.users().messages().modify(
            userId='me',
            id=email_id,
            body=body
        ).execute()
        
        return {"success": True, "message_id": result["id"]}
    

    
    async def _create_draft(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a draft email"""
        import base64
        import email.mime.text
        import email.mime.multipart
        
        try:
            # Create email message
            if args.get("reply_to"):
                # This is a reply draft - get original message for proper threading
                original = self.gmail_service.users().messages().get(
                    userId='me', id=args["reply_to"]
                ).execute()
                
                msg = email.mime.multipart.MIMEMultipart()
                msg['to'] = args["to"]
                msg['subject'] = f"Re: {args['subject']}" if not args['subject'].startswith('Re:') else args['subject']
                
                # Add threading headers
                if 'payload' in original and 'headers' in original['payload']:
                    headers = {h['name']: h['value'] for h in original['payload']['headers']}
                    if 'Message-ID' in headers:
                        msg['In-Reply-To'] = headers['Message-ID']
                        msg['References'] = headers.get('References', '') + ' ' + headers['Message-ID']
                
                # Add body
                msg.attach(email.mime.text.MIMEText(args["body"], 'plain'))
            else:
                msg = email.mime.text.MIMEText(args["body"])
                msg['to'] = args["to"]
                msg['subject'] = args["subject"]
            
            if args.get("cc"):
                msg['cc'] = args["cc"]
            if args.get("bcc"):
                msg['bcc'] = args["bcc"]
                
            # Encode message for draft creation
            raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
            
            # Create draft
            draft_body = {
                'message': {
                    'raw': raw_message
                }
            }
            
            result = self.gmail_service.users().drafts().create(
                userId='me',
                body=draft_body
            ).execute()
            
            return {
                "success": True, 
                "draft_id": result["id"],
                "message_id": result["message"]["id"],
                "recipient": args["to"],
                "subject": args["subject"]
            }
            
        except Exception as e:
            return {"error": f"Failed to create draft: {e}"}
    
    async def _create_label(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new Gmail label"""
        label_body = {
            'name': args["name"],
            'messageListVisibility': args.get("messageListVisibility", "show"),
            'labelListVisibility': args.get("labelListVisibility", "labelShow")
        }
        
        result = self.gmail_service.users().labels().create(
            userId='me',
            body=label_body
        ).execute()
        
        return {"success": True, "label_id": result["id"], "name": result["name"]}
    
    async def _read_email_content(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Read the full content/body of an email"""
        email_id = args["id"]
        format_preference = args.get("format", "text").lower()
        
        try:
            # Get the full email message
            message = self.gmail_service.users().messages().get(
                userId='me',
                id=email_id,
                format='full'
            ).execute()
            
            # Extract email content
            content_info = self._extract_email_content(message, format_preference)
            
            return {
                "success": True,
                "email_id": email_id,
                "content": content_info["content"],
                "content_type": content_info["content_type"],
                "has_attachments": content_info["has_attachments"],
                "attachment_count": content_info["attachment_count"]
            }
            
        except Exception as e:
            return {"error": f"Failed to read email content: {e}"}
    
    async def _list_labels(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List all Gmail labels"""
        include_system = args.get("include_system_labels", True)
        
        try:
            # Get all labels
            results = self.gmail_service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Process labels
            processed_labels = []
            for label in labels:
                label_info = {
                    "id": label["id"],
                    "name": label["name"],
                    "type": "system" if label["type"] == "system" else "user"
                }
                
                # Filter system labels if requested
                if not include_system and label_info["type"] == "system":
                    continue
                    
                processed_labels.append(label_info)
            
            # Sort labels: user labels first, then system labels, alphabetically within each group
            processed_labels.sort(key=lambda x: (x["type"] == "system", x["name"].lower()))
            
            return {
                "success": True,
                "labels": processed_labels,
                "total_count": len(processed_labels),
                "user_labels": [l for l in processed_labels if l["type"] == "user"],
                "system_labels": [l for l in processed_labels if l["type"] == "system"]
            }
            
        except Exception as e:
            return {"error": f"Failed to list labels: {e}"}
    
    def _extract_email_content(self, message: Dict[str, Any], format_preference: str = "text") -> Dict[str, Any]:
        """
        Extract email content from Gmail API message response
        
        Args:
            message: Gmail API message object
            format_preference: 'text' or 'html'
            
        Returns:
            Dictionary with content, content_type, and attachment info
        """
        content = ""
        content_type = "text"
        has_attachments = False
        attachment_count = 0
        
        def extract_from_payload(payload):
            nonlocal content, content_type, has_attachments, attachment_count
            
            # Check for attachments
            if payload.get('filename'):
                has_attachments = True
                attachment_count += 1
                return
            
            # Handle multipart messages
            if payload.get('mimeType', '').startswith('multipart/'):
                if 'parts' in payload:
                    for part in payload['parts']:
                        extract_from_payload(part)
                return
            
            # Extract text content
            mime_type = payload.get('mimeType', '')
            if mime_type == 'text/plain' and format_preference == 'text':
                if 'data' in payload.get('body', {}):
                    import base64
                    decoded_content = base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8', errors='ignore')
                    content = decoded_content
                    content_type = "text"
            elif mime_type == 'text/html' and (format_preference == 'html' or not content):
                if 'data' in payload.get('body', {}):
                    import base64
                    decoded_content = base64.urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8', errors='ignore')
                    
                    if format_preference == 'html':
                        content = decoded_content
                        content_type = "html"
                    else:
                        # Convert HTML to plain text for voice reading
                        import re
                        # Simple HTML to text conversion
                        text_content = re.sub(r'<[^>]+>', '', decoded_content)
                        text_content = re.sub(r'\s+', ' ', text_content).strip()
                        if not content:  # Only use if no plain text found
                            content = text_content
                            content_type = "text"
        
        # Start extraction from the message payload
        if 'payload' in message:
            extract_from_payload(message['payload'])
        
        # Fallback if no content found
        if not content:
            content = "[No readable content found in this email]"
            content_type = "text"
        
        # Truncate very long content for voice reading
        if len(content) > 2000:
            content = content[:2000] + "... [Content truncated for voice reading. This email is longer than displayed.]"
        
        return {
            "content": content,
            "content_type": content_type,
            "has_attachments": has_attachments,
            "attachment_count": attachment_count
        }


def create_oauth_gmail_tools(gmail_service: Resource) -> List[types.Tool]:
    """
    Create OAuth Gmail tools for Gemini Live
    
    Args:
        gmail_service: Authenticated Gmail API service
        
    Returns:
        List of Gemini tools for Gmail operations
    """
    oauth_tools = OAuthGmailTools(gmail_service)
    return oauth_tools.get_gemini_tools()


def create_oauth_gmail_tool_executor(gmail_service: Resource):
    """
    Create OAuth Gmail tool executor for handling tool calls
    
    Args:
        gmail_service: Authenticated Gmail API service
        
    Returns:
        OAuthGmailTools instance for executing tool calls
    """
    return OAuthGmailTools(gmail_service)
