# Voice-Driven Email Agent

A real-time voice-driven email assistant using Google Gemini's audio capabilities with tool integration.

## Features

- **Real-time voice input** with Voice Activity Detection (VAD)
- **Text streaming** responses in terminal
- **Tool integration** for email actions (mark unread, archive)
- **Hands-free operation** perfect for commutes

## Quick Start

1. Set your `GEMINI_API_KEY` in `.env`
2. Install dependencies: `uv sync`
3. Run: `python main.py`
4. Speak commands like "mark this email as unread" or "archive this email"

## Available Tools

- `markUnread` - Marks email as unread
- `archive` - Archives email

## Requirements

- Python 3.11+
- Google Gemini API key
- Microphone access
