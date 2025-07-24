"""
Test script to verify Gmail MCP Server connection
"""
import asyncio
import os
from dotenv import load_dotenv
from gmail_mcp_client import get_gmail_client, cleanup_gmail_client

# Load environment variables
load_dotenv()

async def test_connection():
    """Test the MCP connection and list available tools"""
    print("Testing Gmail MCP Server connection...")
    
    # Check environment variables
    if not os.getenv("GMAIL_CLIENT_ID"):
        print("❌ Error: GMAIL_CLIENT_ID not set in environment")
        return
    
    if not os.getenv("GMAIL_CLIENT_SECRET"):
        print("❌ Error: GMAIL_CLIENT_SECRET not set in environment")
        return
    
    try:
        # Connect to MCP server
        print("📡 Connecting to Gmail MCP Server...")
        client = await get_gmail_client()
        print("✅ Connected successfully!")
        
        # Test listing emails
        print("\n📧 Testing email list...")
        emails = await client.gmail_list(query="is:unread", max_results=5)
        print(f"Found {len(emails)} unread emails")
        
        for i, email in enumerate(emails, 1):
            print(f"{i}. From: {email.sender[:50]}... | Subject: {email.subject[:50]}...")
        
        print("\n✅ All tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await cleanup_gmail_client()
        print("\n🔌 Disconnected from MCP server")

if __name__ == "__main__":
    asyncio.run(test_connection())