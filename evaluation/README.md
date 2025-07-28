# Email Voice Agent Integration Test Plan

### Overview

End-to-end integration tests for the email voice agent that verify Gemini Live's ability to:

- Understand voice commands from pre-recorded audio files
- Call the correct Gmail tools with appropriate parameters
- Handle the email workflow correctly

## Test Philosophy

- **Real Gemini Live API**: We want to test the actual AI's ability to understand and respond
- **Real MCP Agent**: The tool discovery and registration should work as in production
- **Mocked Gmail Results**: Only the actual Gmail API calls are mocked to avoid needing real emails
- **Simulated Audio Input**: Use pre-recorded WAV files converted to PCM format
- **Optional Audio Output**: We don't need to hear the responses, just verify tool calls

## What We're Testing

1. **Voice Understanding**: Can Gemini correctly understand voice commands?
2. **Tool Selection**: Does it choose the right Gmail tool for each action?
3. **Parameter Extraction**: Does it extract correct parameters (email IDs, etc.)?
4. **Workflow Logic**: Does it follow the email processing flow correctly?
5. **Session Management**: Does it properly end sessions after actions?

## What We're Mocking

1. **Audio Input**: Mock `AudioRecorder.get_audio_data()` to return pre-converted audio from WAV files
2. **Gmail Tool Results**: Mock `gmail_agent.call_tool()` to return controlled responses

## Implementation Plan

### 1. Test Fixtures

- Mock Gmail search results with multiple test emails
- Mock tool responses for different Gmail operations
- Predefined email IDs and content for consistent testing

### 2. Audio Conversion

- Load WAV files from `input/` directory
- Convert to PCM format (16-bit, 16kHz mono)
- Mock `AudioRecorder.get_audio_data()` to return chunks of converted audio
- Simulate streaming behavior by returning audio data in small chunks over time

### 3. Mocking Strategy

- Use `unittest.mock` to patch `AudioRecorder.get_audio_data()` for audio input
- Use `unittest.mock` to patch `gmail_agent.call_tool()` for Gmail responses
- Capture all tool calls for verification
- Return appropriate mock responses based on tool name
- **Non-interrupting audio**: Mock audio input to pause when agent is speaking (avoids interruptions during initial tests)

### 4. Test Structure

- Test class for email voice integration scenarios
- Setup method to initialize MCP app, agent, and prepare test data
- Test scenario method that:
  - Mocks audio input and Gmail responses
  - Runs the main application
  - Verifies tool calls and workflow completion

### 5. Verification Points

- Tool name and parameters
- Call sequence and timing
- Session management (end_session calls)
- Error handling

## Success Criteria

1. All test scenarios pass with correct tool calls
2. Gemini understands various phrasings of commands
3. Email workflow completes properly
4. No real Gmail API calls are made
5. Tests are deterministic and repeatable

## Future Enhancements

- Test error scenarios (invalid commands, network issues)
- Test interruption handling
- Measure response latency
- Test with different voice accents/speeds
- Validate response content (not just tool calls)

## Running the Tests

To run the integration tests:

```bash
# Install test dependencies
uv sync --group dev

# Run tests with pytest
pytest evaluation/test_integration.py -v

# Run with output capturing disabled (shows print statements in real-time)
pytest evaluation/test_integration.py -v -s

# Or run all tests in evaluation directory
pytest evaluation/ -v

# For development, you can also run directly
python evaluation/test_integration.py
```

The test will:
1. Load the archive.wav file and convert it to PCM format
2. Stream the audio to Gemini Live as if it were real-time input
3. Verify that the correct Gmail tools are called with proper parameters
4. Confirm the end_session tool is called to complete the workflow

## Test Output Options

### Standard Output (default)
```bash
pytest evaluation/test_integration.py -v
```
Shows clean test results with pass/fail status and timing.

### With Live Output (recommended for debugging)
```bash
pytest evaluation/test_integration.py -v -s
```
The `-s` flag disables **output capturing**, allowing you to see:
- Real-time print statements from the application (like "📧 Processing Email 1/1")
- Audio processing progress
- Gmail tool execution logs
- All stdout/stderr output as it happens

This is useful for debugging and understanding the test flow in detail.

Requirements:
- GEMINI_API_KEY must be set in environment or .env file
- input/archive.wav must exist and contain "archive this email" command
- FFmpeg must be installed for audio conversion
- All project dependencies must be installed

## Test Output

Pytest will provide detailed output showing:
- Test status and assertions
- Clear error messages if tests fail
- Timing information
- Coverage of test scenarios

Example successful output:
```
test_integration.py::test_archive_email PASSED [100%]
```
