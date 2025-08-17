import asyncio
import contextlib
import threading
from typing import Optional
import numpy as np
import logging

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase, WebRtcStreamerContext
import av

from app_helpers import initialize_mcp_and_gmail_agent, fetch_inbox_emails, build_gemini_tools, cleanup_mcp_and_gmail
from audio_webrtc_bridge import WebRTCAudioBridge
from custom_tools import EmailNavigationTools
from main import EmailManager, process_single_email_session

# Set up file logging for debugging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/streamlit_bridge_debug.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_event_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def main() -> None:
    st.set_page_config(page_title="Voice Gmail Triage", layout="centered")
    st.title("Voice Gmail Triage")

    if "initialized" not in st.session_state:
        st.session_state.initialized = False
        st.session_state.mcp_app = None
        st.session_state.gmail_agent = None
        st.session_state.email_manager = EmailManager()
        st.session_state.nav_tools = None
        st.session_state.gemini_tools = None
        st.session_state.runner_task: Optional[asyncio.Task] = None
        st.session_state.loop = get_event_loop()
        st.session_state.bridge = WebRTCAudioBridge()
        st.session_state.session_active = False

    # Controls
    col1, col2 = st.columns(2)
    start_clicked = col1.button("Start", type="primary", disabled=st.session_state.runner_task is not None)
    stop_clicked = col2.button("Stop", disabled=st.session_state.runner_task is None)

    status = st.empty()
    current_email_box = st.empty()

    # WebRTC audio with Gemini bridge (Phase 7)
    with st.expander("Audio (browser)", expanded=True):
        st.caption("Phase 7: Browser audio connected to Gemini via bridge. Click Start below to activate.")
        
        # Audio processor that connects to the bridge
        class BridgeAudioProcessor(AudioProcessorBase):
            def __init__(self, bridge: WebRTCAudioBridge):
                self.bridge = bridge
                self.frame_count = 0
                logger.info(f"[WebRTC] Audio processor initialized with bridge id={id(bridge)}")
                
            def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
                self.frame_count += 1
                # Log first few frames and then every 100
                if self.frame_count <= 10 or self.frame_count % 100 == 0:
                    logger.info(f"[WebRTC] Processing frame {self.frame_count}, samples: {frame.samples}, rate: {frame.sample_rate}, bridge_closed: {self.bridge.closed()}")
                
                # Send mic audio to bridge (for Gemini)
                try:
                    audio_array = frame.to_ndarray()
                    # Convert to int16 PCM
                    if audio_array.dtype != np.int16:
                        audio_array = (audio_array * 32767).astype(np.int16)
                    pcm_bytes = audio_array.tobytes()
                    
                    # Put user audio (browser is typically 48 kHz)
                    self.bridge.put_user_audio(
                        pcm_bytes,
                        sample_rate_hz=frame.sample_rate,
                        num_channels=len(frame.layout.channels)
                    )
                except Exception as e:
                    if self.frame_count == 1:
                        print(f"[WebRTC] Error processing audio: {e}")
                
                # Try to get AI audio from bridge
                # Accumulate multiple chunks if available to prevent queue backup
                ai_chunks = []
                max_chunks = 5  # Process up to 5 chunks per frame
                for _ in range(max_chunks):
                    ai_pcm = self.bridge.get_ai_audio(timeout_seconds=0.001)  # Very short timeout
                    if ai_pcm:
                        ai_chunks.append(ai_pcm)
                        if self.frame_count <= 10:
                            logger.info(f"[WebRTC] Got AI audio chunk {len(ai_pcm)} bytes in frame {self.frame_count}")
                    else:
                        break
                
                if ai_chunks:
                    # Combine all chunks
                    combined_pcm = b''.join(ai_chunks)
                    if self.frame_count <= 20 or self.frame_count % 100 == 0:
                        print(f"[WebRTC] Playing AI audio: {len(combined_pcm)} bytes to browser ({len(ai_chunks)} chunks)")
                    
                    # Convert PCM bytes back to audio frame
                    ai_array = np.frombuffer(combined_pcm, dtype=np.int16)
                    # Create new frame with AI audio
                    new_frame = av.AudioFrame.from_ndarray(
                        ai_array.reshape(-1, 1),  # Mono
                        format='s16',
                        layout='mono'
                    )
                    new_frame.sample_rate = 48000  # Browser expects 48 kHz
                    return new_frame
                elif self.frame_count <= 5:
                    # Debug: Check if bridge has audio in early frames
                    print(f"[WebRTC] No AI audio available in frame {self.frame_count}")
                
                # Return silence instead of echo
                silence = np.zeros((frame.samples, 1), dtype=np.int16)
                silent_frame = av.AudioFrame.from_ndarray(silence, format='s16', layout='mono')
                silent_frame.sample_rate = frame.sample_rate
                return silent_frame
        
        # Capture bridge reference to avoid session_state access in background thread
        bridge_ref = st.session_state.bridge
        logger.info(f"[WebRTC] Using bridge id={id(bridge_ref)} for WebRTC streamer")
        
        # Ensure bridge is started before WebRTC initialization
        if bridge_ref.closed():
            bridge_ref.start()
            logger.info(f"[WebRTC] Started bridge id={id(bridge_ref)} before WebRTC initialization")
        
        # CRITICAL FIX: Use audio_processor_factory with a lambda that returns a new instance
        # This ensures the processor is properly created and registered with WebRTC
        ctx = webrtc_streamer(
            key="voice-bridge",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={"audio": True, "video": False},
            audio_processor_factory=lambda: BridgeAudioProcessor(bridge_ref),
            async_processing=True,  # Enable continuous frame processing
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}],
            },
        )
        
        if ctx and ctx.state.playing:
            st.success("🎤 WebRTC audio is active (connected to bridge)")
            # Ensure bridge is started when WebRTC is active
            if st.session_state.bridge.closed():
                st.session_state.bridge.start()
                print("Bridge started for WebRTC audio")
        else:
            st.info("Click Start above to activate browser audio")

    def _render_current_email():
        email = st.session_state.email_manager.get_current_email()
        if email:
            idx = st.session_state.email_manager.current_index + 1
            total = len(st.session_state.email_manager.emails)
            current_email_box.info(f"Email {idx}/{total}: From {email.get('from','?')} — {email.get('subject','(no subject)')}")
        else:
            current_email_box.info("No email loaded.")

    async def _start_async(initialized, email_manager, bridge, mcp_app, gmail_agent, nav_tools, gemini_tools):
        try:
            print("Starting initialization...")
            if not initialized:
                print("Initializing MCP and Gmail agent...")
                mcp_app, gmail_agent = await initialize_mcp_and_gmail_agent()
                print("Fetching inbox emails...")
                emails = await fetch_inbox_emails(gmail_agent)
                print(f"Found {len(emails)} emails")
                if not emails:
                    print("No emails found in inbox")
                    return None, None, None, None
                email_manager.set_emails(emails)
                nav_tools = EmailNavigationTools(email_manager)
                # Build Gemini tools
                print("Building Gemini tools...")
                gemini_tools = await build_gemini_tools(gmail_agent, nav_tools)
                print("Initialization complete")
            else:
                print("Already initialized, using existing resources")

            print(f"Ready. Found {len(email_manager.emails)} emails. Starting voice session…")
            
            # Start the runner task
            await _runner(email_manager, nav_tools, gmail_agent, gemini_tools, bridge)
            return mcp_app, gmail_agent, nav_tools, gemini_tools
        except Exception as e:
            print(f"Error in _start_async: {e}")
            import traceback
            traceback.print_exc()
            return None, None, None, None

    async def _runner(email_manager, nav_tools, gmail_agent, gemini_tools, bridge):
        # Process emails using the WebRTC bridge
        try:
            logger.info(f"[Runner] Using bridge id={id(bridge)} for Gemini session")
            # Bridge should already be started by WebRTC component
            if bridge.closed():
                bridge.start()
                logger.info(f"[Runner] Started bridge id={id(bridge)}")
            
            while not email_manager.is_exhausted():
                # Process one email with WebRTC bridge
                print(f"Processing email {email_manager.current_index + 1}")
                session_success = await process_single_email_session(
                    email_manager,
                    nav_tools,
                    gmail_agent,
                    gemini_tools,
                    audio_bridge=bridge
                )
                
                if not session_success:
                    print("Session failed or was interrupted")
                    break
                
                # Move to next email
                email_manager.next_email()
                
                if not email_manager.is_exhausted():
                    await asyncio.sleep(1)  # Brief pause between emails
                else:
                    print("All emails processed!")
                    break
                    
        except asyncio.CancelledError:
            print("Session cancelled")
        except Exception as e:
            print(f"Error in runner: {e}")
            import traceback
            traceback.print_exc()
        finally:
            bridge.stop()

    def _start():
        # Capture current state values
        initialized = st.session_state.initialized
        email_manager = st.session_state.email_manager
        bridge = st.session_state.bridge
        mcp_app = st.session_state.mcp_app
        gmail_agent = st.session_state.gmail_agent
        nav_tools = st.session_state.nav_tools
        gemini_tools = st.session_state.gemini_tools
        
        # Run in a separate thread to avoid blocking
        import threading
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_start_async(
                initialized, email_manager, bridge, mcp_app, gmail_agent, nav_tools, gemini_tools
            ))
            # Update session state with results
            if result[0] is not None:
                st.session_state.mcp_app = result[0]
                st.session_state.gmail_agent = result[1]
                st.session_state.nav_tools = result[2]
                st.session_state.gemini_tools = result[3]
                st.session_state.initialized = True
        thread = threading.Thread(target=run_async)
        thread.start()

    def _stop():
        async def _stop_async():
            st.session_state.session_active = False
            if st.session_state.runner_task:
                st.session_state.runner_task.cancel()
                with contextlib.suppress(Exception):
                    await st.session_state.runner_task
                st.session_state.runner_task = None
            if st.session_state.bridge:
                st.session_state.bridge.stop()
            # Cleanup MCP connections
            await cleanup_mcp_and_gmail(st.session_state.mcp_app, st.session_state.gmail_agent)
            st.session_state.initialized = False
            status.info("Stopped and cleaned up.")
        asyncio.run_coroutine_threadsafe(_stop_async(), st.session_state.loop)

    if start_clicked:
        _start()
        st.rerun()
    if stop_clicked:
        _stop()
        st.rerun()

    _render_current_email()
    
    # Show status based on session state
    if st.session_state.initialized and st.session_state.email_manager.emails:
        status.success(f"✅ Ready. {len(st.session_state.email_manager.emails)} emails loaded.")
    elif st.session_state.runner_task:
        status.info("🔄 Processing emails...")
    else:
        status.info("Click Start to begin")


if __name__ == "__main__":
    main()


