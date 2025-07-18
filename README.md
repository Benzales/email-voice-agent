# Voice-Driven Email Agent

A next-generation, voice-driven email agent designed for hands-free email processing during commutes. This agent uses Google Gemini's advanced audio capabilities to process voice commands and respond with natural speech.

## Features

- **Voice Command Processing**: Convert voice commands to email actions
- **Natural Speech Response**: Gemini responds with clear, friendly audio
- **Core Email Actions**:
  - `repeat` - Repeat the last spoken message
  - `markUnread` - Mark an email as unread
  - `archive` - Archive an email
  - `undo` - Revert the previous action
  - `draftReply` - Create a draft reply with provided content

## Prerequisites

- Python 3.11 or higher
- Google Gemini API access
- Audio processing libraries

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd email-voice-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   # or using uv:
   uv sync
   ```

3. **Set up Google Gemini API**:
   - Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Set the environment variable:
     ```bash
     export GOOGLE_API_KEY="your-api-key-here"
     ```

## Usage

1. **Prepare your voice command**:
   - Record your voice command as a WAV file
   - Name it `sample.wav` and place it in the project directory
   - Or use the test file: `https://storage.googleapis.com/generativeai-downloads/data/16000.wav`

2. **Run the agent**:
   ```bash
   python main.py
   ```

3. **Listen to the response**:
   - The agent will process your voice command
   - Response audio will be saved as `response.wav`
   - Play the response file to hear the agent's reply

## Audio Format Requirements

- **Input**: WAV file (will be converted to 16kHz PCM)
- **Output**: 24kHz WAV file
- **Channels**: Mono (1 channel)

## Project Structure

```
email-voice-agent/
├── main.py              # Main application with Gemini audio integration
├── pyproject.toml       # Project configuration and dependencies
├── README.md           # This file
├── .gitignore          # Git ignore rules
├── sample.wav          # Input voice command (you provide this)
└── response.wav        # Output response (generated)
```

## Development

The system follows an **agentic architecture** where:
- Voice commands are processed through Google Gemini's audio capabilities
- The agent maintains context across interactions
- All actions are modular and composable
- Privacy-first design with minimal data retention

## Example Voice Commands

- "Archive the latest email from John"
- "Mark the meeting reminder as unread"
- "Draft a reply saying I'll be there"
- "Repeat what you just said"
- "Undo my last action"

## Troubleshooting

- **"sample.wav not found"**: Ensure you have an audio file named `sample.wav` in the project directory
- **API Key issues**: Verify your `GOOGLE_API_KEY` environment variable is set correctly
- **Audio format issues**: The system automatically converts audio to the required format

## Contributing

This is a voice-driven email agent designed for hands-free operation. Contributions should focus on:
- Improving voice command recognition
- Adding new email actions
- Enhancing the agent's reasoning capabilities
- Maintaining privacy and security standards

## License

[Add your license information here]
