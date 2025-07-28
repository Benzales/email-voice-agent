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
        # Allow control over when audio is sent
        self.paused = False
        self.should_send_audio = True
        
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
        """Return next audio chunk, respecting pause state"""
        self.call_count += 1
        
        # Don't send audio if paused or disabled
        if self.paused or not self.should_send_audio:
            return b''
            
        # Return chunks sequentially, then empty bytes
        if self.chunk_index < len(self.audio_chunks):
            chunk = self.audio_chunks[self.chunk_index]
            self.chunk_index += 1
            return chunk
            
        return b''
    
    def reset_for_next_input(self):
        """Reset to start of audio for next input"""
        self.chunk_index = 0
        self.paused = False


class MultiEmailAudioStreamMock(AudioStreamMock):
    """Enhanced mock that coordinates audio input for multiple emails
    
    This mock implements event-based synchronization to ensure audio inputs are
    sent at the right time when processing multiple emails. Rather than trying
    to prevent interruptions (which are normal in voice interfaces), it monitors
    when each email is completed via complete_current_email() calls and only
    then sends the next audio input.
    
    This approach is more robust than tracking agent speaking state and handles
    the natural flow of voice interaction where interruptions can occur.
    """
    
    def __init__(self, wav_path: str, num_emails: int):
        super().__init__(wav_path)
        self.num_emails = num_emails
        self.current_email_index = 0
        self.complete_email_event = asyncio.Event()
        # Start paused - we'll unpause when ready
        self.paused = True
        
    async def wait_and_send_next_audio(self):
        """Wait for current email to complete, then send audio for next email"""
        if self.current_email_index < self.num_emails:
            # Unpause to send audio for current email
            self.paused = False
            
            # Wait for this email to be completed
            await self.complete_email_event.wait()
            self.complete_email_event.clear()
            
            # Move to next email
            self.current_email_index += 1
            
            # Reset audio for next input
            if self.current_email_index < self.num_emails:
                await asyncio.sleep(0.5)  # Brief pause between emails
                self.reset_for_next_input()
                # Recurse to handle next email
                await self.wait_and_send_next_audio()
    
    def signal_email_completed(self):
        """Signal that current email processing is complete"""
        self.complete_email_event.set()


class GmailToolMock:
    """Mock for gmail_agent.call_tool() that returns controlled responses"""
    
    def __init__(self, num_emails: int = 1):
        self.tool_calls = []  # Track all tool calls for verification
        self.num_emails = num_emails
        
    async def mock_call_tool(self, tool_name: str, arguments: dict) -> Any:
        """Mock Gmail tool execution"""
        # Record the call
        self.tool_calls.append({
            'name': tool_name,
            'arguments': arguments
        })
        
        # Return appropriate mock response based on tool
        if tool_name == "gmail_search_emails":
            # Mock email search results - return multiple emails if configured
            result = MagicMock()
            result.content = [MagicMock()]
            
            if self.num_emails == 1:
                result.content[0].text = """ID: 123abc
Subject: Project Update
From: alice@example.com  
Date: 2024-01-15"""
            else:
                # Return multiple emails
                email_texts = []
                for i in range(self.num_emails):
                    email_texts.append(f"""ID: {i+1}23abc
Subject: Email {i+1} - Project Update
From: sender{i+1}@example.com
Date: 2024-01-{15+i:02d}""")
                result.content[0].text = "\n\n".join(email_texts)
                
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
def multi_email_audio_mock():
    """Fixture providing multi-email audio stream mock"""
    return MultiEmailAudioStreamMock('input/archive.wav', num_emails=2)


@pytest.fixture  
def gmail_mock():
    """Fixture providing configured Gmail tool mock"""
    return GmailToolMock()


@pytest.fixture
def multi_email_gmail_mock():
    """Fixture providing Gmail mock configured for multiple emails"""
    return GmailToolMock(num_emails=2)


@pytest.fixture
def complete_current_email_tracker(multi_email_audio_mock=None):
    """Fixture for tracking complete_current_email calls while executing real function"""
    call_count = 0
    original_execute_complete_current_email = main.EmailNavigationTools.execute_complete_current_email
    
    async def wrapped_execute_complete_current_email(self):
        nonlocal call_count
        call_count += 1
        
        # Signal audio mock if we have one
        if multi_email_audio_mock:
            multi_email_audio_mock.signal_email_completed()
            
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
    with patch('pyaudio.PyAudio', MockPyAudio), \
         patch.object(main.AudioRecorder, 'get_audio_data', side_effect=audio_mock.get_audio_data), \
         patch.object(main.AudioRecorder, 'start_recording', return_value=None), \
         patch.object(main.AudioRecorder, 'stop_recording', return_value=None), \
         patch.object(main.AudioPlayer, 'queue_audio', return_value=None), \
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


@pytest.mark.asyncio
async def test_archive_multiple_emails():
    """Test archiving multiple emails in sequence"""
    # Create fixtures with multi-email configuration
    multi_audio_mock = MultiEmailAudioStreamMock('input/archive.wav', num_emails=2)
    multi_gmail_mock = GmailToolMock(num_emails=2)
    
    # Create tracker that signals audio mock
    call_count = 0
    original_execute = main.EmailNavigationTools.execute_complete_current_email
    
    async def wrapped_execute(self):
        nonlocal call_count
        call_count += 1
        multi_audio_mock.signal_email_completed()
        return await original_execute(self)
    
    # Apply all patches
    with patch('pyaudio.PyAudio', MockPyAudio), \
         patch.object(main.AudioRecorder, 'get_audio_data', side_effect=multi_audio_mock.get_audio_data), \
         patch.object(main.AudioRecorder, 'start_recording', return_value=None), \
         patch.object(main.AudioRecorder, 'stop_recording', return_value=None), \
         patch.object(main.AudioPlayer, 'queue_audio', return_value=None), \
         patch.object(main.AudioPlayer, 'start_output_stream', return_value=None), \
         patch.object(main.AudioPlayer, 'close', return_value=None), \
         patch.object(Agent, 'call_tool', new=multi_gmail_mock.mock_call_tool), \
         patch.object(main.EmailNavigationTools, 'execute_complete_current_email', wrapped_execute):
        
        # Start the audio coordination task
        audio_task = asyncio.create_task(multi_audio_mock.wait_and_send_next_audio())
        
        # Run main with longer timeout for multiple emails
        try:
            await asyncio.wait_for(main.main(), timeout=30.0)
        except asyncio.TimeoutError:
            pytest.fail("Test timed out processing multiple emails")
        finally:
            # Cancel audio task if still running
            audio_task.cancel()
            try:
                await audio_task
            except asyncio.CancelledError:
                pass
    
    # Verify results
    assert multi_audio_mock.call_count > 0, "Audio should have been processed"
    
    # Should have one search call returning 2 emails
    search_calls = [c for c in multi_gmail_mock.tool_calls if c['name'] == "gmail_search_emails"]
    assert len(search_calls) == 1, "Expected exactly one search call"
    
    # Should have two archive calls (one per email)
    modify_calls = [c for c in multi_gmail_mock.tool_calls if c['name'] == "gmail_modify_email"]
    assert len(modify_calls) == 2, f"Expected 2 modify calls for archiving, got {len(modify_calls)}"
    
    # Verify both emails were archived
    archived_email_ids = set()
    for call in modify_calls:
        assert 'removeLabelIds' in call['arguments'], "Archive should remove labels"
        assert 'INBOX' in call['arguments']['removeLabelIds'], "Archive should remove INBOX label"
        archived_email_ids.add(call['arguments']['messageId'])
    
    # Should have archived both emails with different IDs
    assert len(archived_email_ids) == 2, "Should have archived 2 different emails"
    assert '123abc' in archived_email_ids, "First email should be archived"
    assert '223abc' in archived_email_ids, "Second email should be archived"
    
    # Should have moved to next email twice (once after each archive)
    assert call_count == 2, f"Expected complete_current_email to be called twice, got {call_count}"


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