#!/usr/bin/env python3
"""
Startup script for the Email Voice Agent FastAPI server
Provides easy server startup with proper error handling
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file first
load_dotenv()

def check_environment():
    """Check that required environment variables are set"""
    required_vars = ["GEMINI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these in your .env file or environment")
        return False
    
    return True


def check_dependencies():
    """Check that required dependencies are installed"""
    required_packages = [
        "fastapi", "uvicorn", "websockets", "pydantic",
        "google.genai", "mcp_agent", "dotenv"
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\nInstall with: pip install fastapi uvicorn websockets pydantic")
        return False
    
    return True


async def test_backend_first():
    """Run backend tests before starting server"""
    print("🧪 Running backend integration tests...")
    
    try:
        # Import and run the test
        from test_backend import main as test_main
        success = await test_main()
        return success
    except Exception as e:
        print(f"❌ Backend tests failed: {e}")
        return False


def start_server():
    """Start the FastAPI server using UV environment"""
    try:
        import uvicorn
        print("🚀 Starting Email Voice Agent FastAPI Server...")
        print("📍 Using UV environment for better audio quality")
        print("📍 Server will be available at:")
        print("   - HTTP: http://localhost:8000")
        print("   - WebSocket: ws://localhost:8000/ws/voice-session")
        print("   - Health: http://localhost:8000/health")
        print("   - Docs: http://localhost:8000/docs")
        print("\n🛑 Press Ctrl+C to stop the server")
        
        uvicorn.run(
            "fastapi_server:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Server startup failed: {e}")
        sys.exit(1)


async def main():
    """Main startup sequence"""
    print("🔧 Email Voice Agent - Server Startup")
    print("=" * 40)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    print("✅ Environment and dependencies OK")
    
    # Ask user if they want to run tests first
    run_tests = input("\n🧪 Run backend tests before starting server? (y/n): ").lower().strip()
    
    if run_tests in ['y', 'yes', '']:
        test_success = await test_backend_first()
        if not test_success:
            print("❌ Backend tests failed. Fix issues before starting server.")
            sys.exit(1)
        print("✅ Backend tests passed!")
    
    print("\n" + "=" * 40)
    
    # Start the server
    start_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Startup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)
