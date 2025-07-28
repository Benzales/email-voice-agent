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
test_integration.py::test_archive_multiple_emails PASSED [100%]
```

## Multiple Email Testing

The test suite includes a sophisticated test for processing multiple emails in sequence:

### Synchronization Approach

The `test_archive_multiple_emails` test uses event-based synchronization to coordinate audio input across multiple emails:

1. **Accepts Interruptions**: Rather than trying to prevent interruptions (which are normal in voice interfaces), the test allows them to happen and verifies the agent recovers correctly.

2. **Event-Based Coordination**: Uses `asyncio.Event` to signal when each email processing is complete before sending the next audio input.

3. **Monitors Progress**: Tracks `complete_current_email` calls to know when to proceed to the next email.

This approach is more robust than trying to track agent speaking state and reflects real-world voice interaction patterns where interruptions are common and expected.

# Comprehensive Test Suite Plan

## Goals

To ensure the reliability and robustness of the email voice agent, we will implement a comprehensive test suite that covers all aspects of the system. This suite will:
- Test every available tool call (Gmail actions, session management, etc.)
- Validate sequential email processing (exactly 3 actions per test for most tests, to keep tests concise)
- Ensure correct session and workflow management

## List of Actions and Tool Mapping

The following actions are covered by the test suite, with their corresponding tool names:

### Actions That Trigger `complete_current_email`
These actions complete processing of the current email and move to the next:

- **Send Email** (`gmail_send_email`)
- **Draft Email** (`gmail_draft_email`)
- **Delete Email** (`gmail_delete_email`)
- **Mark as Unread** (`gmail_modify_email` with 'mark unread')
- **Mark as Read** (`gmail_modify_email` with 'mark read')
- **Archive Email** (`gmail_modify_email` with 'archive')
- **Move to Label** (`gmail_modify_email` with 'move to label')

### Actions That Shouldn't Trigger `complete_current_email`
These actions do not move to the next email because the current email still needs to be processed:

- **Read Email** (`gmail_read_email`)
- **List Labels** (`gmail_list_email_labels`)
- **Create Label** (`gmail_create_label`)
- **Update Label** (`gmail_update_label`)
- **Delete Label** (`gmail_delete_label`)

## What Will Be Tested

### 1. **Every Action**
- Every action will be tested with exactly 3 calls to action on 3 different emails.

### 2. **Sequential Actions**
- Every test will perform exactly two actions on 2 different emails in sequence (e.g., archive then mark unread, or delete then mark read email)

### 3. **Session and Workflow Management**
- Verify that sessions start and end correctly by asserting that complete_current_email is called after each action
- Test that the agent can resume after interruptions or errors

## Example Test Scenarios

Each test scenario will process exactly 3 emails from the Gmail search results, performing the same action 3 times with different phrasings:

- **Archive 3 emails**: Process 3 emails in sequence, each with a different way of saying "archive" (e.g., "archive this email", "move this to archive", "get rid of this email")
- **Delete 3 emails**: Process 3 emails in sequence, each with a different way of saying "delete" (e.g., "delete this email", "remove this message", "trash this")
- **Mark 3 emails as unread**: Process 3 emails in sequence, each with different phrasing for marking unread (e.g., "mark as unread", "make this unread", "I haven't read this yet")

## Audio Input Collection
- Record 3 WAV files for each action and scenario
- Organize files by action and scenario (see folder structure below)
- Document the intended command and expected outcome for each file

---

## Evaluation Folder Structure

To organize the comprehensive test suite, the `evaluation` folder will be structured as follows:

```
evaluation/
  README.md
  test_integration.py
  audio_inputs/
    archive/
      archive_1.wav
      archive_2.wav
      archive_3.wav
    delete/
      delete_1.wav
      delete_2.wav
      delete_3.wav
    mark_unread/
      mark_unread_1.wav
      mark_unread_2.wav
      mark_unread_3.wav
    # ...repeat for each action
  scenarios/
    test_archive_three_emails.py
    test_delete_three_emails.py
    # ...one script per scenario if needed
```

- `audio_inputs/` contains subfolders for each action, each with 3 main phrasings.
- `test_integration.py` contains tests for each scenario.
- `README.md` documents the test plan.

---
