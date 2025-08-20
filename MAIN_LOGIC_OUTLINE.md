# Email Voice Agent - Main Logic Outline

## Overview
This is a voice-driven Gmail assistant that processes emails sequentially using Gemini Live API with direct MCP (Model Control Protocol) integration. The app creates isolated sessions for each email to maintain clean state management.

## Core Architecture

### 1. Main Components

#### EmailManager Class
- **Purpose**: Manages sequential email reading with deterministic state
- **Key Methods**:
  - `set_emails(emails)`: Store emails from search results and reset index
  - `get_current_email()`: Get current email or None if exhausted
  - `next_email()`: Move to next email
  - `has_more_emails()`: Check if more emails exist
  - `is_exhausted()`: Check if all emails processed

#### Audio Components
- **AudioRecorder**: Handles real-time voice input from user
- **AudioPlayer**: Manages audio output from Gemini Live

#### MCP Integration
- **MCPApp**: Initializes MCP application for Gmail tools
- **Agent**: Gmail agent with server connection for tool execution
- **Tool Discovery**: Dynamically discovers and converts MCP tools to Gemini format

### 2. Core Workflow

#### Initialization Phase (`process_realtime_voice()`)
1. **MCP Setup**:
   - Initialize MCPApp and Gmail Agent
   - Establish connection to Gmail MCP server
   - Discover available Gmail tools dynamically

2. **Email Fetching**:
   - Search inbox using `gmail_search_emails` tool
   - Parse results using `parse_gmail_search_results()`
   - Load emails into EmailManager

3. **Tool Preparation**:
   - Convert MCP tools to Gemini-compatible format
   - Add custom `complete_current_email` navigation tool
   - Prepare tool array for Gemini sessions

#### Per-Email Session Processing (`process_single_email_session()`)
Each email gets its own isolated Gemini Live session:

1. **Session Setup**:
   - Extract email details (ID, sender, subject)
   - Initialize audio recorder and player
   - Create Gemini session config with tools
   - Reset navigation tools state

2. **Audio Streaming**:
   - Start continuous audio recording
   - Stream audio data to Gemini Live as PCM
   - Handle audio streaming errors gracefully

3. **Session Interaction**:
   - Send initial email info to Gemini: "From [sender] - [subject]"
   - Wait for user voice commands
   - Process Gemini responses (audio, tool calls, interruptions)

4. **Tool Execution**:
   - Handle custom `complete_current_email` tool (ends session)
   - Execute MCP Gmail tools (modify, delete, send, etc.)
   - Convert MCP results to Gemini function responses
   - Handle tool execution errors

5. **Session Cleanup**:
   - Cancel audio streaming tasks
   - Clean up audio resources (recorder, player)
   - Handle cleanup errors gracefully

#### Main Loop
- Process emails sequentially until exhausted
- Handle session failures and interruptions
- Brief pause between sessions
- Comprehensive resource cleanup on exit

### 3. Key Features

#### Voice Interaction Pattern
- **Email Announcement**: "From [sender] - [subject]"
- **Action Prompt**: "What would you like to do with this email?"
- **Supported Actions**: Reply, archive, delete, mark read/unread, skip
- **Workflow**: Action → `complete_current_email` → Next email session

#### Error Handling
- Session-level error recovery
- Tool execution error handling
- Audio streaming error management
- Resource cleanup on failures
- Timeout protection (2 minutes per session, 5 minutes total)

#### State Management
- **Session Isolation**: Each email in separate Gemini session
- **Clean State**: Navigation tools reset per session
- **Deterministic Flow**: Sequential email processing
- **Resource Management**: Proper cleanup between sessions

### 4. Technical Details

#### Gemini Live Configuration
```python
config = {
    "response_modalities": ["AUDIO"],
    "tools": gemini_tools,
    "system_instruction": [system_instruction]
}
```

#### Audio Specifications
- **Format**: PCM audio at 16kHz sample rate
- **Streaming**: Continuous 5ms intervals
- **Bidirectional**: Real-time input/output

#### MCP Tool Integration
- **Dynamic Discovery**: Tools discovered at runtime
- **Format Conversion**: MCP schema → Gemini tool format
- **Error Resilience**: Tool failures don't crash sessions

#### System Instruction Highlights
- Single email focus per session
- Mandatory `complete_current_email` after actions
- Archive = remove from INBOX (not add ARCHIVED label)
- Concise voice responses

### 5. Current Limitations

#### Terminal-Only Interface
- Requires terminal for audio I/O
- No visual feedback for user
- Limited accessibility options

#### Audio Dependencies
- Relies on system audio devices
- May have platform-specific issues
- No fallback for audio failures

#### Session Management
- Fixed timeout values
- No pause/resume functionality
- No session recovery mechanisms

### 6. Extension Points for UI Integration

#### State Exposure Opportunities
- EmailManager state (current email, progress)
- Session status and errors
- Tool execution results
- Audio streaming status

#### UI Integration Hooks
- Email display and navigation
- Action buttons as voice alternatives
- Progress indicators
- Error message display
- Session controls (pause, skip, stop)

#### Configuration Options
- Audio device selection
- Timeout adjustments
- Email query customization
- Tool availability toggles
