# Email Voice Agent with Gmail MCP Server

A voice-driven email agent that processes Gmail commands using audio files and the Model Context Protocol (MCP).

## Features

- 🎤 Process voice commands from audio files
- 📧 Gmail integration via MCP (Model Context Protocol) Server
- 🤖 Powered by Google's Gemini AI
- 🔄 Action queue system with undo capability
- 🚀 Async operation for efficient processing

## Architecture

This application uses the Gmail MCP Server to interact with Gmail APIs. The MCP (Model Context Protocol) provides a standardized way for AI applications to interact with external services.

```
Voice Commands (.wav) → Gemini AI → MCP Client → Gmail MCP Server → Gmail API
```

## Prerequisites

- Python 3.11+
- Node.js 16+ (for MCP server)
- Google Cloud Project with Gmail API enabled
- Gemini API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd email-voice-agent
```

2. Install Python dependencies:
```bash
uv sync
# or
pip install -r requirements.txt
```

3. The Gmail MCP Server is already included and built in `Gmail-MCP-Server/dist/`

## Configuration

1. Create a `.env` file in the project root:
```bash
# Gmail OAuth2 Credentials
GMAIL_CLIENT_ID=your-client-id-here
GMAIL_CLIENT_SECRET=your-client-secret-here
GMAIL_REDIRECT_URI=http://localhost:3000/auth/google/callback

# Gemini API Key
GEMINI_API_KEY=your-gemini-api-key-here
```

2. Set up Gmail API credentials (see [MCP_SETUP.md](MCP_SETUP.md) for detailed instructions)

## Usage

1. Place audio files (.wav format) in the `input/` directory with voice commands

2. Run the application:
```bash
python main.py
```

3. The application will:
   - Connect to the Gmail MCP Server
   - Process each audio file sequentially
   - Execute Gmail actions based on voice commands
   - Display results in the console

## Voice Commands

Supported commands include:
- "Read my latest email" - Reads the most recent unread email
- "Mark this email as unread" - Queues marking the email as unread
- "Archive this email" - Queues archiving the email
- "Delete this email" - Queues moving the email to trash
- "Generate a draft reply" - Creates an AI-generated response
- "Undo" - Cancels the last queued action

## Project Structure

```
email-voice-agent/
├── main.py              # Main application entry point
├── gmail_mcp_client.py  # MCP client wrapper for Gmail
├── tool_handlers.py     # Handles tool calls from Gemini
├── Gmail-MCP-Server/    # Gmail MCP server (TypeScript)
├── input/              # Place audio files here
├── MCP_SETUP.md        # Detailed MCP setup guide
└── README.md           # This file
```

## How It Works

1. **Audio Processing**: Audio files are sent to Gemini AI for transcription and intent recognition
2. **Tool Calling**: Gemini identifies the appropriate Gmail action and calls the corresponding tool
3. **MCP Communication**: The tool handler communicates with the Gmail MCP Server via stdio
4. **Action Execution**: Gmail actions are either executed immediately or queued for later execution
5. **Feedback**: Results are displayed in the console

## Security

- OAuth tokens are managed securely by the MCP server
- The MCP server runs locally and communicates via stdio
- Never commit `.env` files or credentials to version control

## Troubleshooting

- **MCP Connection Issues**: Ensure Node.js is installed and the MCP server is built
- **Gmail API Errors**: Check that Gmail API is enabled and credentials are correct
- **Audio Processing Issues**: Ensure audio files are in WAV format and properly recorded

For detailed setup and troubleshooting, see [MCP_SETUP.md](MCP_SETUP.md).

## License

[Your License Here]
