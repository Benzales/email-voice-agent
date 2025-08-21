#!/usr/bin/env python3
"""
UV Environment startup script for better audio quality
Uses UV instead of .venv for potentially better audio processing
"""

import subprocess
import sys
import os
from pathlib import Path

def check_uv_installed():
    """Check if UV is installed"""
    try:
        result = subprocess.run(['uv', '--version'], capture_output=True, text=True)
        print(f"✅ UV found: {result.stdout.strip()}")
        return True
    except FileNotFoundError:
        print("❌ UV not found. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh")
        return False

def start_with_uv():
    """Start the FastAPI server using UV"""
    print("🚀 Starting Email Voice Agent with UV environment...")
    print("📍 Using UV for potentially better audio quality")
    
    # Check if pyproject.toml exists
    if not Path("pyproject.toml").exists():
        print("❌ pyproject.toml not found")
        return False
    
    try:
        # Run the server with UV
        subprocess.run([
            'uv', 'run', 'python', 'start_server.py'
        ], check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ UV server failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
        return True
    
    return True

def main():
    """Main function"""
    print("🔧 Email Voice Agent - UV Environment Startup")
    print("=" * 50)
    
    if not check_uv_installed():
        print("\n💡 Alternative: Use regular startup with .venv:")
        print("   python start_server.py")
        sys.exit(1)
    
    print("✅ Starting with UV environment for better audio quality...")
    success = start_with_uv()
    
    if not success:
        print("\n💡 If UV fails, try regular startup:")
        print("   python start_server.py")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Startup cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)
