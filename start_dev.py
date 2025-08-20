#!/usr/bin/env python3
"""
Development startup script for Email Voice Agent
Starts both FastAPI backend and Next.js frontend concurrently
"""

import subprocess
import sys
import time
import signal
import os
from pathlib import Path

def check_ports():
    """Check if required ports are available"""
    import socket
    
    ports = [8000, 3000]  # FastAPI backend, Next.js frontend
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            result = sock.connect_ex(('localhost', port))
            if result == 0:
                print(f"⚠️ Port {port} is already in use")
                return False
    return True

def start_backend():
    """Start the FastAPI backend"""
    print("🚀 Starting FastAPI backend on port 8000...")
    return subprocess.Popen([
        sys.executable, "start_server.py"
    ], cwd=".")

def start_frontend():
    """Start the Next.js frontend"""
    print("🚀 Starting Next.js frontend on port 3000...")
    return subprocess.Popen([
        "npm", "run", "dev"
    ], cwd="web")

def main():
    """Main function to start both services"""
    print("🔧 Email Voice Agent - Development Startup")
    print("=" * 50)
    
    # Check if ports are available
    if not check_ports():
        print("❌ Required ports are not available. Stop other services and try again.")
        sys.exit(1)
    
    # Check if web directory exists
    if not Path("web").exists():
        print("❌ Frontend directory 'web' not found")
        sys.exit(1)
    
    # Check if backend files exist
    if not Path("start_server.py").exists():
        print("❌ Backend start script 'start_server.py' not found")
        sys.exit(1)
    
    backend_process = None
    frontend_process = None
    
    try:
        # Start backend
        backend_process = start_backend()
        time.sleep(3)  # Give backend time to start
        
        # Check if backend started successfully
        if backend_process.poll() is not None:
            print("❌ Backend failed to start")
            sys.exit(1)
        
        # Start frontend
        frontend_process = start_frontend()
        time.sleep(3)  # Give frontend time to start
        
        # Check if frontend started successfully
        if frontend_process.poll() is not None:
            print("❌ Frontend failed to start")
            sys.exit(1)
        
        print("\n✅ Both services started successfully!")
        print("📍 Access points:")
        print("   - Frontend: http://localhost:3000")
        print("   - Backend API: http://localhost:8000")
        print("   - Backend Health: http://localhost:8000/health")
        print("   - Backend Docs: http://localhost:8000/docs")
        print("\n🎤 Voice Session Flow:")
        print("   1. Open http://localhost:3000 in your browser")
        print("   2. Click 'Connect to Backend'")
        print("   3. Click 'Start Voice Session'")
        print("   4. Allow microphone access")
        print("   5. Speak your email commands!")
        print("\n🛑 Press Ctrl+C to stop both services")
        
        # Wait for user interrupt
        try:
            backend_process.wait()
        except KeyboardInterrupt:
            pass
    
    except KeyboardInterrupt:
        print("\n\n👋 Stopping services...")
    
    finally:
        # Clean shutdown
        if backend_process:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                backend_process.kill()
        
        if frontend_process:
            frontend_process.terminate()
            try:
                frontend_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                frontend_process.kill()
        
        print("✅ All services stopped")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Startup cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Startup failed: {e}")
        sys.exit(1)
