#!/usr/bin/env python3
"""
Test script for FastAPI backend integration
Validates that all extracted components work together correctly
"""

import asyncio
import sys
import traceback
from typing import Dict, Any

# Test imports from our extracted modules
try:
    from email_service import EmailManager, initialize_email_manager, extract_email_details
    from gemini_service import (
        setup_mcp_connection, discover_gmail_tools, convert_mcp_to_gemini_tools,
        create_navigation_tools, create_gemini_session_config, cleanup_mcp_resources
    )
    from models import HealthCheckResponse, SessionConfig, create_error_message
    print("✅ All module imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


async def test_mcp_setup():
    """Test MCP connection and Gmail agent setup"""
    print("\n🧪 Testing MCP Setup...")
    
    try:
        mcp_app, gmail_agent = await setup_mcp_connection()
        print("✅ MCP connection established")
        
        # Test tool discovery
        mcp_tools = await discover_gmail_tools(gmail_agent)
        print(f"✅ Discovered {len(mcp_tools)} Gmail tools")
        
        # Test tool conversion
        gemini_tools = convert_mcp_to_gemini_tools(mcp_tools)
        print(f"✅ Converted {len(gemini_tools)} tools to Gemini format")
        
        return mcp_app, gmail_agent, gemini_tools
        
    except Exception as e:
        print(f"❌ MCP setup failed: {e}")
        traceback.print_exc()
        raise


async def test_email_fetching(gmail_agent):
    """Test email fetching and EmailManager"""
    print("\n🧪 Testing Email Fetching...")
    
    try:
        # Test email manager initialization
        email_manager = await initialize_email_manager(gmail_agent, max_results=5)
        print(f"✅ Initialized EmailManager with {len(email_manager.emails)} emails")
        
        if not email_manager.is_exhausted():
            # Test email details extraction
            current_email = email_manager.get_current_email()
            email_info = extract_email_details(current_email)
            print(f"✅ Current email: {email_info['display_text']}")
            
            # Test progress tracking
            progress = email_manager.get_progress()
            print(f"✅ Progress: {progress}")
            
        return email_manager
        
    except Exception as e:
        print(f"❌ Email fetching failed: {e}")
        traceback.print_exc()
        raise


async def test_navigation_tools(email_manager):
    """Test navigation tools creation"""
    print("\n🧪 Testing Navigation Tools...")
    
    try:
        nav_tools = create_navigation_tools(email_manager)
        print("✅ Navigation tools created")
        
        # Test complete_current_email tool creation
        complete_tool = nav_tools.get_complete_current_email_tool()
        print("✅ Complete current email tool created")
        
        return nav_tools
        
    except Exception as e:
        print(f"❌ Navigation tools failed: {e}")
        traceback.print_exc()
        raise


async def test_session_config(gemini_tools, nav_tools):
    """Test Gemini session configuration"""
    print("\n🧪 Testing Session Configuration...")
    
    try:
        # Add navigation tool to gemini tools
        complete_tool = nav_tools.get_complete_current_email_tool()
        all_tools = gemini_tools + [complete_tool]
        
        # Create session config
        session_config = create_gemini_session_config(all_tools)
        print(f"✅ Session config created with {len(session_config['tools'])} tools")
        
        # Validate config structure
        required_keys = ["response_modalities", "tools", "system_instruction"]
        for key in required_keys:
            if key not in session_config:
                raise ValueError(f"Missing required config key: {key}")
        
        print("✅ Session configuration validated")
        return session_config
        
    except Exception as e:
        print(f"❌ Session config failed: {e}")
        traceback.print_exc()
        raise


async def test_models():
    """Test Pydantic models"""
    print("\n🧪 Testing Pydantic Models...")
    
    try:
        # Test health check response
        health = HealthCheckResponse(
            timestamp=1234567890,
            services={"mcp": True, "gmail": True}
        )
        print("✅ HealthCheckResponse model works")
        
        # Test session config
        config = SessionConfig(
            email_query="in:inbox",
            max_results=10
        )
        print("✅ SessionConfig model works")
        
        # Test error message creation
        error = create_error_message("Test error", recoverable=True)
        print("✅ Error message creation works")
        
        return True
        
    except Exception as e:
        print(f"❌ Models test failed: {e}")
        traceback.print_exc()
        raise


async def main():
    """Run all backend integration tests"""
    print("🚀 Starting Backend Integration Tests...")
    
    mcp_app = None
    gmail_agent = None
    
    try:
        # Test 1: Models (no dependencies)
        await test_models()
        
        # Test 2: MCP Setup
        mcp_app, gmail_agent, gemini_tools = await test_mcp_setup()
        
        # Test 3: Email Fetching
        email_manager = await test_email_fetching(gmail_agent)
        
        # Test 4: Navigation Tools
        nav_tools = await test_navigation_tools(email_manager)
        
        # Test 5: Session Configuration
        session_config = await test_session_config(gemini_tools, nav_tools)
        
        print("\n🎉 All backend integration tests passed!")
        print("✅ FastAPI server should work correctly")
        print("\nNext steps:")
        print("1. Run: python fastapi_server.py")
        print("2. Visit: http://localhost:8000/health")
        print("3. Test WebSocket: ws://localhost:8000/ws/voice-session")
        
    except Exception as e:
        print(f"\n❌ Backend integration tests failed: {e}")
        return False
        
    finally:
        # Cleanup
        if mcp_app or gmail_agent:
            print("\n🧹 Cleaning up resources...")
            await cleanup_mcp_resources(mcp_app, gmail_agent)
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n👋 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fatal test error: {e}")
        traceback.print_exc()
        sys.exit(1)
