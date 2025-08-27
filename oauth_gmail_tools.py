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
                    description="Modify Gmail email labels (archive, mark read/unread, etc.)",
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
        
        # Gmail send email tool
        send_email_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_send_email",
                    description="Send an email through Gmail",
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
                                description="Email ID this is a reply to"
                            )
                        },
                        required=["to", "subject", "body"]
                    )
                )
            ]
        )
        tools.append(send_email_tool)
        
        # Gmail delete email tool
        delete_email_tool = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name="gmail_delete_email",
                    description="Delete an email permanently",
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "id": types.Schema(
                                type=types.Type.STRING,
                                description="Email ID to delete"
                            )
                        },
                        required=["id"]
                    )
                )
            ]
        )
        tools.append(delete_email_tool)
        
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
            elif tool_name == "gmail_send_email":
                return await self._send_email(arguments)
            elif tool_name == "gmail_delete_email":
                return await self._delete_email(arguments)
            elif tool_name == "gmail_create_label":
                return await self._create_label(arguments)
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
    
    async def _send_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Send an email"""
        import base64
        import email.mime.text
        import email.mime.multipart
        
        # Create email message
        if args.get("reply_to"):
            # This is a reply - get original message for proper threading
            original = self.gmail_service.users().messages().get(
                userId='me', id=args["reply_to"]
            ).execute()
            
            msg = email.mime.multipart.MIMEMultipart()
            msg['to'] = args["to"]
            msg['subject'] = f"Re: {args['subject']}"
            
            # Add threading headers
            if 'payload' in original and 'headers' in original['payload']:
                headers = {h['name']: h['value'] for h in original['payload']['headers']}
                if 'Message-ID' in headers:
                    msg['In-Reply-To'] = headers['Message-ID']
                    msg['References'] = headers.get('References', '') + ' ' + headers['Message-ID']
        else:
            msg = email.mime.text.MIMEText(args["body"])
            msg['to'] = args["to"]
            msg['subject'] = args["subject"]
        
        if args.get("cc"):
            msg['cc'] = args["cc"]
        if args.get("bcc"):
            msg['bcc'] = args["bcc"]
            
        # Encode and send
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        result = self.gmail_service.users().messages().send(
            userId='me',
            body={'raw': raw_message}
        ).execute()
        
        return {"success": True, "message_id": result["id"]}
    
    async def _delete_email(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete an email permanently"""
        email_id = args["id"]
        
        self.gmail_service.users().messages().delete(
            userId='me',
            id=email_id
        ).execute()
        
        return {"success": True, "deleted_id": email_id}
    
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
