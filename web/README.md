# Voice Email Agent - Frontend

A minimal, voice-only Next.js frontend for the Email Voice Agent. Connects to the FastAPI backend via WebSocket for real-time voice interaction.

## 🎯 Design Philosophy

This frontend follows the **voice-first** approach:
- **Minimal UI** - Just connection status and basic controls
- **Voice-only interaction** - All email actions happen through voice commands
- **Real-time audio streaming** - Bidirectional audio with Gemini Live via WebSocket
- **No complex displays** - Gemini announces everything the user needs to know

## 🏗️ Architecture

```
src/
├── components/
│   └── VoiceEmailAgent.tsx     # Main UI component
├── hooks/
│   └── useVoiceSession.ts      # Voice session management hook
├── lib/
│   ├── audio/
│   │   └── audioUtils.ts       # WebRTC & Web Audio API handling
│   └── websocket/
│       └── client.ts           # WebSocket client for backend communication
└── app/
    └── page.tsx                # Main page
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
cd web
npm install
```

### 2. Start Development Server
```bash
npm run dev
```

### 3. Open in Browser
Visit: http://localhost:3000

## 🎵 How It Works

### Voice Session Flow
1. **Connect** - Establishes WebSocket connection to FastAPI backend
2. **Start Session** - Backend fetches inbox emails and starts processing
3. **Voice Interaction** - User speaks commands, audio streams to Gemini Live
4. **Email Processing** - Gemini processes commands (archive, delete, reply, skip)
5. **Automatic Flow** - Moves to next email after each action
6. **Completion** - Processes all emails until inbox is clear

### Audio Pipeline
```
User Microphone → Web Audio API → 16kHz PCM → WebSocket → FastAPI Backend → Gemini Live
Gemini Live → FastAPI Backend → WebSocket → Web Audio API → User Speakers
```

### WebSocket Protocol
- **Audio Data**: Raw binary PCM audio (16kHz)
- **Control Messages**: JSON for session control and status updates
- **Status Updates**: Real-time progress and session state

## 🎤 Voice Commands

Once connected and session started, you can say:
- **"Archive"** / **"Archive this email"** - Moves email to archive
- **"Delete"** / **"Delete this email"** - Permanently deletes email  
- **"Reply"** / **"I want to reply"** - Start composing a reply
- **"Skip"** / **"Next"** / **"Continue"** - Skip to next email
- **"Mark as read"** - Mark email as read
- **"Mark as unread"** - Mark email as unread

## 🔧 Configuration

### Environment Variables
Create `.env.local` in the web directory:
```bash
# Backend WebSocket URL
NEXT_PUBLIC_BACKEND_WS_URL=ws://localhost:8000/ws/voice-session

# Backend HTTP URL  
NEXT_PUBLIC_BACKEND_HTTP_URL=http://localhost:8000
```

### Browser Requirements
- **WebRTC Support** - For microphone access
- **Web Audio API** - For audio processing  
- **WebSocket Support** - For backend communication
- **HTTPS** - Required for microphone access (except localhost)

## 🎨 UI Components

### VoiceEmailAgent
Main component with:
- Connection status display
- Progress indicator (current email / total emails)
- Start/Stop session controls
- Error handling and display
- Recording indicator

### Status Indicators
- 🔌 **Disconnected** - Not connected to backend
- 🔗 **Connected** - Connected, ready to start session
- 🎤 **Recording** - Active voice session, microphone recording
- ⚡ **Processing** - Backend processing email action
- ✅ **Completed** - All emails processed
- ❌ **Error** - Something went wrong

## 🚀 Deployment

### Development
```bash
npm run dev
```

### Production Build
```bash
npm run build
npm run start
```

### Deploy to Vercel
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel --prod
```

Set environment variables in Vercel dashboard:
- `NEXT_PUBLIC_BACKEND_WS_URL` → Your production backend WebSocket URL
- `NEXT_PUBLIC_BACKEND_HTTP_URL` → Your production backend HTTP URL

## 🔍 Troubleshooting

### Common Issues

**Microphone Access Denied**
- Ensure HTTPS (or localhost for development)
- Check browser permissions
- Try refreshing and allowing microphone access

**WebSocket Connection Failed**
- Verify FastAPI backend is running on correct port
- Check CORS settings in backend
- Ensure WebSocket URL is correct

**No Audio Output**
- Check browser audio permissions
- Verify speakers/headphones are working
- Try different browser

**Session Stuck in "Initializing"**
- Check backend logs for MCP/Gmail connection issues
- Verify GEMINI_API_KEY is set in backend
- Ensure Gmail MCP server is accessible

### Debug Mode
Open browser developer tools to see:
- WebSocket connection status
- Audio processing logs  
- Error messages and stack traces

## 🎯 Next Steps

With the frontend complete, you can:
1. **Test locally** - Run both backend and frontend
2. **Deploy backend** - Railway, Render, or DigitalOcean
3. **Deploy frontend** - Vercel (automatic with git push)
4. **Custom domain** - Set up custom domain in Vercel
5. **SSL certificate** - Automatic with Vercel deployment

The voice-only design keeps the interface simple while providing a powerful email management experience through natural voice interaction!