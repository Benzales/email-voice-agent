### Streamlit WebRTC UI Plan for Voice Gmail Agent

#### Goal
Browser-based mic/speaker UI (Streamlit) that keeps the current Gemini Live + MCP Gmail logic, replacing local `AudioRecorder`/`AudioPlayer` with WebRTC.

### High-level architecture
- **Streamlit frontend**: Renders Start/Stop buttons, shows current email (sender/subject), displays status/logs. Uses `streamlit-webrtc` to capture mic and play returned audio.
- **Audio bridge (server-side)**: A bidirectional queue that:
  - Pushes browser mic frames → Gemini Live session as 16 kHz mono PCM
  - Pulls Gemini audio bytes ← converts to WebRTC-friendly frames (48 kHz) → browser
- **Gemini Live session**: Same as now (tools, `system_instruction`, MCP Gmail). Reads/writes audio via the bridge.
- **MCP Gmail agent**: Unchanged (server-side). Tools are dynamically exposed to Gemini.

### Key refactors (no functional changes)
- **Abstract audio I/O**: Introduce an `AudioIO`/`AudioBridge` interface.
  - Input: `put_user_audio(frame_bytes, sample_rate, channels)`
  - Output: `get_ai_audio(timeout)` returning PCM bytes at a declared rate, or `None` if not available
  - Control: `start()`, `stop()`, `closed()`
- **Wire into `process_single_email_session`**:
  - Replace `AudioRecorder`/`AudioPlayer` usage with calls to the bridge:
    - “Read” mic: poll `audio_in_queue` and send chunks to Gemini as `audio/pcm;rate=16000`
    - “Write” speaker: enqueue Gemini `response.data` into `audio_out_queue`

### Streamlit/WebRTC design
- **Component**: `webrtc_streamer` with `mode="SENDRECV"` and appropriately tuned buffer sizes for low latency.
- **Processor**:
  - On `recv_audio_frame`: convert `av.AudioFrame` to mono 16 kHz 16-bit PCM and `bridge.put_user_audio(...)`
  - On “send” side: pull from `bridge.get_ai_audio(...)`, convert PCM 16 kHz → 48 kHz `av.AudioFrame` for browser playback
- **UI controls**:
  - Start: initializes UI state, then calls helpers from `main.py` to init MCP/Agent, fetch inbox, and build tools; starts background per-email loop
  - Stop: signals bridge and session to end; cleans up
- **State**: Store `EmailManager`, `nav_tools`, `gmail_agent`, `gemini_task`, `bridge` in `st.session_state` to avoid re-inits on reruns.

### Concurrency model
- **Background task**: Run the Gemini session loop in an asyncio task per Streamlit session.
- **Thread-safety**: Use `asyncio.Queue` or `queue.Queue` with careful cross-thread use (Streamlit callbacks run in main thread; aiortc threads handle audio). Wrap with non-blocking pushes and bounded queues to avoid backpressure issues.
- **Timing**: Keep current small sleeps (e.g., 5 ms) or rely on queues with timeouts to maintain low latency.

### Audio format handling
- **Browser → Gemini**:
  - Typical input is 48 kHz stereo float. Convert to mono 16 kHz signed 16-bit PCM.
  - Chunk size ~20–40 ms to balance latency and overhead.
- **Gemini → Browser**:
  - Expect PCM bytes (16 kHz mono). Resample to 48 kHz mono and return as `av.AudioFrame`.
- **Libraries**: `numpy`, `av` resampler, or `scipy.signal.resample_poly` for minimal deps.

### UI layout (simple)
- **Header**: “Voice Gmail Triage”
- **Controls**: Start/Stop
- **Current email**: Sender, subject, index (e.g., “3/25”)
- **Status**: Live text lines for tool calls, confirmations, and errors
- **Privacy note**: Mic permission disclosure

### Error handling and cleanup
- Propagate errors to a status panel and keep the session responsive.
- On Stop or exception:
  - Close Gemini session, cancel background task, stop bridge, close MCP connections.
  - Drain queues to prevent stale audio.
- Guard against Streamlit reruns (idempotent init via `st.session_state` checks).

### Dependencies and environment
- Add: `streamlit`, `streamlit-webrtc`, `av`, `numpy`, `scipy` (or `resampy`); keep existing Google GenAI + MCP deps.
- macOS note: `av` may require FFmpeg; if issues, prefer `scipy` for resampling and let `streamlit-webrtc` manage frames.

### Rollout steps
1. Create `AudioBridge` abstraction and refactor `process_single_email_session` to use it.
2. Add Streamlit app that:
   - Creates `webrtc_streamer` with audio processor bound to the bridge
   - Uses extracted helpers from `main.py` to initialize MCP/Gmail agent and fetch inbox on Start
   - Spawns asyncio task running the existing per-email loop
3. Implement resampling utilities and robust queues.
4. Add Stop handler and reliable cleanup.
5. Test end-to-end on macOS Safari/Chrome; validate archiving, reply, skip commands by voice.
6. Optimize latency (queue sizes, frame durations, resampler choice) and add minimal logs.

### Risks and mitigations
- **Audio device/permission**: Use `streamlit-webrtc` defaults; add clear UI prompts.
- **Resampling glitches**: Start with `resample_poly`, fixed chunk sizes; add small fade/zero-pad if needed.
- **Concurrency bugs**: Centralize state in `st.session_state`, keep queues bounded, ensure cancellation paths mirror current finally-blocks.
- **Library build issues (PyAV)**: Pin versions; provide fallback instructions.

### Acceptance criteria
- Start button initiates a browser mic session; the app speaks the email sender/subject.
- Saying “archive/delete/reply/next” triggers the right MCP tool and then advances via `complete_current_email`.
- Audio is real-time in both directions with stable latency (<300–500 ms perceived).
- Stop cleanly tears down without orphaned tasks or stuck mic.



### Implementation subtasks

1) Define audio abstraction (no behavior change)
- Deliverable: `AudioBridge` interface (methods: start, stop, closed, put_user_audio, get_ai_audio; define sample rates).
- Acceptance: Type-checks; no references outside the new file.

2) Local adapter to keep current flow working
- Deliverable: `LocalAudioBridge` that wraps `AudioRecorder`/`AudioPlayer`.
- Acceptance: A tiny harness can create and start/stop without errors.

3) Refactor session to use `AudioBridge` only
- Deliverable: Update `process_single_email_session` to read from `AudioBridge` in and write to out; remove direct recorder/player usage.
- Acceptance: Running `python main.py` still works as before using `LocalAudioBridge`.

4) Streamlit scaffold (no audio yet)
- Deliverable: `streamlit_app.py` with Start/Stop, shows current email (sender/subject), status area; initializes MCP and fetches inbox.
- Acceptance: `streamlit run streamlit_app.py` renders; Start populates inbox; Stop cleans up.

5) WebRTC wiring (UI only, loopback test)
- Deliverable: `webrtc_streamer` SENDRECV; loopback that plays mic back to speaker (no Gemini).
- Acceptance: You hear yourself with acceptable latency; Stop releases mic.

6) WebRTC audio bridge
- Deliverable: `WebRTCAudioBridge` backed by bounded queues; converts browser frames to 16 kHz mono PCM and vice versa.
- Acceptance: Unit tests for resampling round-trip; queue backpressure doesn’t block UI.

7) Integrate WebRTCAudioBridge into session
- Deliverable: Streamlit Start creates `WebRTCAudioBridge` and spawns the per-email Gemini session using it.
- Acceptance: The app speaks sender/subject through the browser; Stop halts cleanly.

8) Tool-call path and “next” workflow (voice only)
- Deliverable: Confirm Gmail MCP tool execution and the `complete_current_email` advance logic (no Next button, voice only).
- Acceptance: Saying “archive” or “next” advances; emails decrement until exhausted.

9) Cleanup, cancellation, and rerun safety
- Deliverable: Robust Stop handler; mirrors `finally` cleanup from `main.py`; `st.session_state` guards prevent double-starts.
- Acceptance: Start/Stop multiple times without orphaned tasks or audio device lock.

10) Latency tuning and reliability
- Deliverable: Tune chunk sizes (20–40 ms), queue sizes, and resampler to keep perceived latency <300–500 ms.
- Acceptance: Subjective latency within target across Chrome/Safari; no buffer underruns/overflows in logs.

11) Packaging and docs
- Deliverable: Add deps (`streamlit`, `streamlit-webrtc`, `av`, `numpy`, `scipy`), README run instructions, macOS notes (FFmpeg).
- Acceptance: Fresh clone can run both terminal and Streamlit modes.

12) Smoke tests for core flows
- Deliverable: Quick scripts/checklists for: read, archive, delete, reply, skip; error recovery if MCP/network hiccups.
- Acceptance: All flows pass twice in a row without restarts.
