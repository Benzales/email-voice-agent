# Gmail MCP Server Setup Guide

This guide will help you set up the Gmail MCP (Model Context Protocol) Server for the email voice agent.

## Prerequisites

- Node.js (v16 or higher)
- npm (comes with Node.js)
- A Google Cloud Project with Gmail API enabled
- OAuth 2.0 credentials

## Setup Steps

### 1. Build the MCP Server

The MCP server has already been cloned and built. The built files are in `Gmail-MCP-Server/dist/`.

### 2. Configure Gmail API Credentials

You'll need to set up OAuth 2.0 credentials for the Gmail API:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create or select a project
3. Enable the Gmail API:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click on it and enable it

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Configure consent screen if needed
   - Choose "Web application" as the application type
   - Add authorized redirect URIs:
     - `http://localhost:3000/auth/google/callback`
   - Download the credentials JSON

### 3. Set Environment Variables

Create a `.env` file in the project root with your Gmail OAuth credentials:

```bash
# Gmail OAuth2 Credentials
GMAIL_CLIENT_ID=your-client-id-here
GMAIL_CLIENT_SECRET=your-client-secret-here
GMAIL_REDIRECT_URI=http://localhost:3000/auth/google/callback

# Gemini API Key
GEMINI_API_KEY=your-gemini-api-key-here
```

### 4. Authentication Flow

When you first run the application, the Gmail MCP Server will:
1. Start a local server on port 3000
2. Open your browser for OAuth authentication
3. Ask you to log in to Google and grant permissions
4. Save the authentication tokens for future use

## Running the Application

1. Make sure environment variables are set
2. Run the main application:
   ```bash
   python main.py
   ```

The application will:
- Connect to the Gmail MCP Server via stdio
- Initialize the Gmail API connection
- Process voice commands from the `input/` directory

## Available Gmail Operations via MCP

The Gmail MCP Server provides these tools:
- `gmail_list` - List emails with search queries
- `gmail_get` - Get full email details
- `gmail_modify` - Modify email labels (mark read/unread, archive)
- `gmail_send` - Send emails
- `gmail_trash` - Move emails to trash
- `gmail_generate_response` - Generate AI-powered email responses

## Voice Commands

Place `.wav` audio files in the `input/` directory with commands like:
- "Read my latest email"
- "Mark this email as unread"
- "Archive this email"
- "Delete this email"
- "Generate a draft reply"
- "Undo"

## Troubleshooting

### MCP Server Connection Issues
- Check that Node.js is installed: `node --version`
- Verify the MCP server is built: Check `Gmail-MCP-Server/dist/index.js` exists
- Check environment variables are set correctly

### Gmail API Issues
- Ensure Gmail API is enabled in Google Cloud Console
- Verify OAuth credentials are correct
- Check that redirect URI matches exactly
- Delete any cached tokens and re-authenticate

### Permission Errors
- Make sure you've granted all required Gmail permissions during OAuth flow
- The app needs permission to read, modify, and send emails

## Security Notes

- Keep your `.env` file secure and never commit it to version control
- OAuth tokens are stored securely by the MCP server
- The MCP server runs locally and communicates via stdio for security