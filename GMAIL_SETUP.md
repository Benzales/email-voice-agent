# Gmail API Setup Guide

This guide will walk you through setting up Gmail API access for your voice-driven email agent.

## Prerequisites

- A Google Account
- Python 3.11+ installed
- The email-voice-agent project set up

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown (top left) and select "New Project"
3. Give your project a name (e.g., "Voice Email Agent")
4. Click "Create"

## Step 2: Enable Gmail API

1. In the Google Cloud Console, ensure your new project is selected
2. Go to "APIs & Services" > "Library"
3. Search for "Gmail API"
4. Click on "Gmail API" and then click "Enable"

## Step 3: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" (unless you have a Google Workspace account)
   - Fill in the required fields:
     - App name: "Voice Email Agent"
     - User support email: Your email
     - Developer contact: Your email
   - Add scopes:
     - Click "Add or Remove Scopes"
     - Search and select: `https://www.googleapis.com/auth/gmail.modify`
   - Add your email as a test user
   - Click "Save and Continue"

4. Back in "Create OAuth client ID":
   - Application type: "Desktop app"
   - Name: "Voice Email Agent Client"
   - Click "Create"

5. Download the credentials:
   - Click the download button (⬇️) next to your OAuth 2.0 Client ID
   - Save the file as `credentials.json` in your project root directory

## Step 4: Install Dependencies

Run the following command in your project directory:

```bash
uv pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Or if using pip directly:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Step 5: First Run Authentication

1. Run your application:
   ```bash
   python main.py
   ```

2. On first run, it will:
   - Open a browser window for authentication
   - Ask you to log in to your Google account
   - Request permission to access Gmail
   - After approval, create a `token.pickle` file

3. The `token.pickle` file stores your authentication tokens for future use

## Security Notes

- **NEVER** commit `credentials.json` or `token.pickle` to version control
- These files are already in `.gitignore` for your protection
- Keep these files secure as they provide access to your Gmail account

## Troubleshooting

### "File not found" error
- Ensure `credentials.json` is in the project root directory
- Check that the filename is exactly `credentials.json`

### "Access blocked" error
- Make sure you added your email as a test user in the OAuth consent screen
- If your app is in "Testing" mode, only test users can authenticate

### "Scope not authorized" error
- Go back to OAuth consent screen settings
- Ensure `https://www.googleapis.com/auth/gmail.modify` scope is added

### Token expired
- Delete `token.pickle` and run the app again to re-authenticate

## Available Gmail Operations

Once set up, your voice agent can:
- Read and summarize emails
- Mark emails as read/unread
- Archive emails
- Delete emails (move to trash)
- List emails with search filters

## Voice Commands Examples

- "Read my latest unread email"
- "Mark this email as unread"
- "Archive this email"
- "Delete this email"
- "List emails from John"

## Next Steps

After setup, you can start using voice commands to manage your Gmail inbox hands-free! 