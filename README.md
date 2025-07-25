# Voice-Driven Email Agent with MCP Integration

A real-time voice-driven email assistant using Google Gemini's audio capabilities with Gmail integration through Model Context Protocol (MCP).

## Features

- **Real-time voice input** with Voice Activity Detection (VAD)
- **Audio streaming responses** with natural speech synthesis
- **Gmail integration via MCP** for robust email operations
- **Action queueing system** with undo capability for safer email processing
- **Hands-free operation** perfect for commutes or multitasking
- **Automatic inbox clearing** with sequential email processing

## Quick Start

1. **Install dependencies:**
   ```bash
   uv sync
   ```

2. **Set up Gmail MCP server:**
   ```bash
   npm install -g @gongrzhe/server-gmail-autoauth-mcp
   ```

3. **Configure environment:**
   - Copy `mcp_agent.secrets.yaml.example` to `mcp_agent.secrets.yaml`
   - Add your Gemini API key and other credentials

4. **Run the agent:**
   ```bash
   uv run python main.py
   ```

5. **Start speaking!** Commands like:
   - "Archive this email"
   - "Mark as read"
   - "Delete this email"
   - "Read the content"
   - "Undo" (cancels pending action)

## Available Voice Commands

### Email Actions (Queued)
- **"Archive this email"** - Removes from inbox
- **"Delete this email"** - Moves to trash
- **"Mark as read/unread"** - Changes read status
- **"Skip"** - Alias for mark as unread

### Immediate Actions
- **"Read the content"** - Reads full email body
- **"Summarize this email"** - Provides concise summary
- **"Get inbox stats"** - Reports total/unread counts
- **"Undo"** - Cancels pending action and goes back

### Draft Management
- **"Draft a reply saying..."** - Creates draft response
- **"Edit draft to say..."** - Modifies current draft
- **"Read the draft"** - Reads draft content
- **"Send the draft"** - Sends and moves to next email

## Action Safety System

The agent uses a queuing system for state-changing actions:

1. **Actions are queued, not immediate** - Gives you time to reconsider
2. **Execution on next action** - Previous action executes when you request a new one
3. **Undo capability** - Say "undo" to cancel and go back to previous email
4. **Final action execution** - Last queued action executes on session end

## Technical Architecture

- **Google Gemini Live API** - Real-time audio streaming and tool calling
- **MCP-Agent Framework** - Manages MCP server connections
- **Gmail MCP Server** - Provides Gmail API access through standardized interface
- **PyAudio** - Handles microphone input and audio playback

## Requirements

- Python 3.11+
- Google Gemini API key
- Node.js and npm (for Gmail MCP server)
- Microphone and speaker access
- Gmail account with API access enabled

## Configuration

The project uses two configuration files:

- `mcp_agent.config.yaml` - MCP server configuration
- `mcp_agent.secrets.yaml` - API keys and credentials (create from example)

See `GMAIL_SETUP.md` for detailed Gmail API setup instructions.
