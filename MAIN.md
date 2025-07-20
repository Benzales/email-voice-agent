# Voice-Driven Email Agent

## Overview

A next-generation, voice-driven email agent designed for hands-free email processing during commutes or other scenarios. The system provides a high-quality, voice-first experience for triaging emails when users cannot use their hands.

## Core Philosophy

### Agentic Architecture

The system operates as an intelligent agent that:

- **Reasons** about each user command using LLM calls
- **Resolves ambiguity** in voice commands through intelligent parsing
- **Maintains context** across interactions (active email, previous actions, etc.)
- **Makes decisions** about the best sequence of actions
- **Provides reversible actions** for user safety



## Core Voice Actions

The agent provides a limited, focused set of core actions. Some examples include:

- `repeat` - Repeats the last spoken message
- `markUnread` - Marks an email as unread  
- `archive` - Archives an email
- `undo` - Reverts the previous action
- `draftReply` - Creates a draft reply with provided content




