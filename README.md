# Voice-Driven Email Agent

A real-time voice-driven email assistant using Google Gemini's audio capabilities with tool integration.

## Features

- **Real-time voice input** with Voice Activity Detection (VAD)
- **Text streaming** responses in terminal
- **Tool integration** for email actions with undo capability
- **Action queueing system** for safer email processing
- **Hands-free operation** perfect for commutes

## Quick Start

1. Set your `GEMINI_API_KEY` in `.env`
2. Install dependencies: `uv sync`
3. Run: `python main.py`
4. Speak commands like "mark this email as unread", "archive this email", or "undo" to cancel

## Available Tools

- `getNextEmail` - Get the next email in the inbox clearing sequence
- `markUnread` - Marks email as unread (queued for execution)
- `markRead` - Marks email as read (queued for execution)
- `archive` - Archives email (queued for execution)
- `deleteEmail` - Deletes email (queued for execution)
- `readEmailContent` - Read the full email content (immediate execution)
- `getInboxStats` - Get inbox statistics (immediate execution)
- `undoAction` - Cancel the currently queued action

## Action Undo System

The email agent now includes an action undo mechanism for safety:

- **State-changing actions** (mark as read/unread, archive, delete) are **queued** first, not executed immediately
- Actions are only **executed** when the next state-changing action is requested or when moving to the next email
- Users can say **"undo"** to cancel the currently queued action
- **Reading content** and **getting stats** execute immediately as they don't change email state
- The final queued action is automatically executed when the session ends

## Requirements

- Python 3.11+
- Google Gemini API key
- Microphone access
