#!/usr/bin/env python3
"""
Integration tests for the email voice agent.
Tests the full end-to-end flow with real Gemini Live API but mocked Gmail responses.
"""

import asyncio
import wave
import struct
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from typing import List, Any
import sys
import os
import subprocess
import tempfile

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import main
from mcp_agent.agents.agent import Agent


class MockPyAudio:
    """Mock PyAudio to prevent actual audio device initialization"""
    def __init__(self):
        pass
        
    def terminate(self):
        pass


class AudioStreamMock:
    """Mock for AudioRecorder.get_audio_data() that streams WAV file data"""
    
    def __init__(self, wav_path: str):
        self.wav_path = wav_path
        self.audio_chunks = self._load_and_convert_wav()
        self.chunk_index = 0
        self.agent_is_speaking = False
        self.call_count = 0
        
    def _load_and_convert_wav(self) -> List[bytes]:
        """Load WAV file and convert to PCM chunks using ffmpeg"""
        chunks = []
        
        # Use ffmpeg to convert to the format we need (16-bit PCM at 16kHz mono)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_path = tmp_file.name
            
        try:
            # Convert using ffmpeg
            cmd = [
                'ffmpeg', '-i', self.wav_path,
                '-acodec', 'pcm_s16le',  # 16-bit PCM
                '-ar', '16000',           # 16kHz sample rate
                '-ac', '1',               # Mono
                '-y',                     # Overwrite output
                tmp_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                pytest.fail(f"FFmpeg conversion failed: {result.stderr}")
            
            # Now load the converted file
            try:
                with wave.open(tmp_path, 'rb') as wav_file:
                    # Read all frames
                    frames = wav_file.readframes(wav_file.getnframes())
                    
                    # Split into small chunks (similar to real-time streaming)
                    chunk_size = 1600  # 100ms at 16kHz
                    for i in range(0, len(frames), chunk_size):
                        chunks.append(frames[i:i + chunk_size])
            except Exception as e:
                pytest.fail(f"Error loading WAV file: {e}")
                
        finally:
            # Clean up temp file
            if tmp_path != self.wav_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)
                
        return chunks
    
    def get_audio_data(self) -> bytes:
        """Return next audio chunk, respecting agent speaking state"""
        self.call_count += 1
        
        # Don't send audio while agent is speaking (non-interrupting behavior)
        if self.agent_is_speaking:
            return b''
            
        # Return chunks sequentially, then empty bytes
        if self.chunk_index < len(self.audio_chunks):
            chunk = self.audio_chunks[self.chunk_index]
            self.chunk_index += 1
            return chunk
            
        return b''


class GmailToolMock:
    """Mock for gmail_agent.call_tool() that returns controlled responses"""
    
    def __init__(self):
        self.tool_calls = []  # Track all tool calls for verification
        
    async def mock_call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Mock Gmail tool execution"""
        # Record the call
        self.tool_calls.append({
            'name': tool_name,
            'arguments': arguments
        })
        
        # Return appropriate mock response based on tool
        if tool_name == "gmail_search_emails":
            # Mock email search results
            result = MagicMock()
            result.content = [MagicMock()]
            result.content[0].text = """ID: 123abc
Subject: Project Update
From: alice@example.com  
Date: 2024-01-15"""
            return result
            
        elif tool_name == "gmail_modify_email":
            # Mock successful modification
            result = MagicMock()
            result.content = [MagicMock()]
            result.content[0].text = "Email modified successfully"
            return result
            
        else:
            # Default response
            result = MagicMock()
            result.content = [MagicMock()]
            result.content[0].text = f"Tool {tool_name} executed successfully"
            return result


# Pytest Fixtures for Professional Test Organization

@pytest.fixture
def audio_mock():
    """Fixture providing configured audio stream mock"""
    return AudioStreamMock('input/archive.wav')


@pytest.fixture  
def gmail_mock():
    """Fixture providing configured Gmail tool mock"""
    return GmailToolMock()


@pytest.fixture
def complete_current_email_tracker():
    """Fixture for tracking complete_current_email calls while executing real function"""
    call_count = 0
    original_execute_complete_current_email = main.EmailNavigationTools.execute_complete_current_email
    
    async def wrapped_execute_complete_current_email(self):
        nonlocal call_count
        call_count += 1
        return await original_execute_complete_current_email(self)
    
    # Return both the wrapper and a way to check call count
    class CompleteCurrentEmailTracker:
        def __init__(self):
            self.wrapper = wrapped_execute_complete_current_email
            
        @property
        def call_count(self):
            return call_count
    
    return CompleteCurrentEmailTracker()


@pytest.fixture
def mock_audio_system(audio_mock):
    """Fixture that patches all audio-related components"""
    
    def track_agent_speaking(self, audio_data):
        audio_mock.agent_is_speaking = True
        asyncio.create_task(clear_speaking_flag())
    
    async def clear_speaking_flag():
        await asyncio.sleep(0.1)
        audio_mock.agent_is_speaking = False
    
    with patch('pyaudio.PyAudio', MockPyAudio), \
         patch.object(main.AudioRecorder, 'get_audio_data', side_effect=audio_mock.get_audio_data), \
         patch.object(main.AudioRecorder, 'start_recording', return_value=None), \
         patch.object(main.AudioRecorder, 'stop_recording', return_value=None), \
         patch.object(main.AudioPlayer, 'queue_audio', track_agent_speaking), \
         patch.object(main.AudioPlayer, 'start_output_stream', return_value=None), \
         patch.object(main.AudioPlayer, 'close', return_value=None):
        yield


@pytest.fixture
def mock_gmail_system(gmail_mock):
    """Fixture that patches Gmail-related components"""
    with patch.object(Agent, 'call_tool', new=gmail_mock.mock_call_tool):
        yield


@pytest.fixture  
def mock_complete_current_email_system(complete_current_email_tracker):
    """Fixture that patches complete_current_email with tracking"""
    with patch.object(main.EmailNavigationTools, 'execute_complete_current_email', complete_current_email_tracker.wrapper):
        yield


# Test Functions - Clean and Focused

@pytest.mark.asyncio
async def test_archive_email(audio_mock, gmail_mock, complete_current_email_tracker, 
                           mock_audio_system, mock_gmail_system, mock_complete_current_email_system):
    """Test archiving an email using voice command from archive.wav"""
    
    # Test execution - all setup is handled by fixtures
    try:
        await asyncio.wait_for(main.main(), timeout=15.0)
    except asyncio.TimeoutError:
        pytest.fail("Test timed out - complete_current_email may not have worked properly")
                                    
    # Verification - clean and focused on test logic
    assert audio_mock.call_count > 0, "Audio should have been processed"
    assert len(gmail_mock.tool_calls) >= 2, "Expected at least 2 tool calls (search + modify)"
    
    # First call should be search
    assert gmail_mock.tool_calls[0]['name'] == "gmail_search_emails", "First call should be email search"
    
    # Should have a modify call for archiving (removing inbox label)
    modify_calls = [c for c in gmail_mock.tool_calls if c['name'] == "gmail_modify_email"]
    assert len(modify_calls) > 0, "Expected gmail_modify_email to be called for archiving"
    
    # Verify the modify call has correct parameters for archiving
    archive_call = modify_calls[0]
    assert 'removeLabelIds' in archive_call['arguments'], "Archive should remove labels"
    assert 'INBOX' in archive_call['arguments']['removeLabelIds'], "Archive should remove INBOX label"
    
    # Verify that complete_current_email tool was called to move to next email
    assert complete_current_email_tracker.call_count > 0, "Expected complete_current_email to be called after email action"


# Future tests can easily reuse fixtures
@pytest.mark.asyncio  
async def test_mark_unread_email(audio_mock, gmail_mock, mock_audio_system, mock_gmail_system):
    """Example of how easy it is to add more tests with fixtures"""
    # Could test with 'input/mark_unread.wav' 
    # All the setup is handled by reusable fixtures!
    pytest.skip("Example test - not implemented yet")


if __name__ == "__main__":
    # Allow running with python directly for development
    pytest.main([__file__, "-v"]) 