## Web Migration Plan (Voice-Only Gmail Agent with MCP)

### Goals
- Preserve hands-free, continuous voice UX.
- Keep Gmail MCP via a tiny always-on backend.
- Frontend on Vercel; backend on a small always-on host.

### Final Architecture (server-hosted Realtime)
- Frontend (Next.js on Vercel)
  - Single page with a "Start session" entry.
  - Captures mic, streams to backend over WebSocket.
  - Plays returned audio from backend.
  - Minimal status/transcripts; no action buttons.

- Backend (FastAPI on Railway/Fly/Render)
  - Boots `MCPApp` and persistent Gmail `Agent` (spawns Gmail MCP server with `npx -y @gongrzhe/server-gmail-autoauth-mcp`).
  - Endpoints:
    - REST: `/mcp/tools`, `/mcp/inbox`, `/mcp/execute` (already implemented)
    - WebSocket: `/realtime` (Gemini Realtime session hosted on server)
  - Server handles Gemini tool calls directly (calls Gmail MCP, sends function responses). Client only streams audio and plays back.

### Server Realtime session flow
1. Client connects to `/realtime` WebSocket.
2. Server fetches inbox via MCP, sets up `EmailManager` and `EmailNavigationTools`.
3. Server creates a Gemini Live session (AUDIO in/out) with:
   - Tools = all Gmail MCP tools + `complete_current_email`.
   - System instruction = single-email focus and archive semantics.
4. Server sends an initial prompt for the first email to Gemini.
5. While WebSocket open:
   - Client → Server: binary PCM16 chunks → forwarded to Gemini.
   - Gemini → Server: audio bytes → forwarded to client as binary.
   - Gemini → Server: tool calls → server executes via MCP, sends function responses back to Gemini.
   - When `complete_current_email` is called or user says next/skip → server advances to the next email and sends a new prompt.
6. When all emails are processed or client disconnects → server closes session and cleans up.

### Client WebSocket protocol
- Client → Server messages:
  - `{"type":"start"}`: begin session (optional; server may start on connect).
  - Binary frames: PCM16 mono, 16kHz chunks.
  - Optional: `{"type":"stop"}` to end session.

- Server → Client messages:
  - `{"type":"ready","email":{...}}`: session ready / current email.
  - Binary frames: audio bytes (PCM16 or WAV-chunk) to play.
  - `{"type":"status","message":"..."}`: lightweight status/errors.
  - `{"type":"complete"}`: all emails processed.

### Security
- Backend holds Gmail and Gemini creds; MCP tokens are mounted/seeded.
- CORS locked to Vercel origin; WebSocket origin checked (optional).

### Deployment
- Backend: build Docker image with Python + Node; run FastAPI with uvicorn; set `ALLOWED_ORIGINS`, `GEMINI_API_KEY`, and mount MCP token dir.
- Frontend: deploy Next.js on Vercel; configure `NEXT_PUBLIC_MCP_BACKEND_URL` to backend URL.

### Milestones
1. Backend WebSocket route `/realtime` with hosted Gemini Live session; server executes tool calls.
2. Frontend mic capture -> PCM16 over WebSocket; basic audio playback of server binary frames.
3. End-to-end: iterate through inbox with purely voice commands (archive/delete/next).
4. Polish: error toasts, reconnect, session stop, simple transcript log.

### Notes
- This plan supersedes the browser-hosted Realtime approach (WebRTC), avoiding model endpoint mismatches. It reuses your proven Python SDK path.
- Future: we can switch back to browser WebRTC once the exact Realtime REST/WebRTC handshake is confirmed for your account.


