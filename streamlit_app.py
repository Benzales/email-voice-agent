import asyncio
import contextlib
import threading
from typing import Optional

import numpy as np
import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase, WebRtcStreamerContext
import av

from app_helpers import initialize_mcp_and_gmail_agent, fetch_inbox_emails, build_gemini_tools, cleanup_mcp_and_gmail
from audio_webrtc_bridge import WebRTCAudioBridge
from custom_tools import EmailNavigationTools
from main import EmailManager, process_single_email_session


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
    
    # Instructions
    st.info("📖 **How to use:** 1️⃣ Enable audio below, 2️⃣ Click Start to begin email triage")

    # Controls
    col1, col2 = st.columns(2)
    start_clicked = col1.button("Start Email Triage", type="primary", disabled=st.session_state.runner_task is not None)
    stop_clicked = col2.button("Stop", disabled=st.session_state.runner_task is None)

    status = st.empty()
    current_email_box = st.empty()

    # WebRTC audio with Gemini bridge (Phase 7)
    with st.expander("🎤 Audio Controls (REQUIRED)", expanded=True):
        st.warning("⚠️ You MUST click the START button below to hear the agent!")
        
        # Audio processor that connects to the bridge
        class BridgeAudioProcessor(AudioProcessorBase):
            def __init__(self, bridge: WebRTCAudioBridge):
                self.bridge = bridge
                self.frame_count = 0
                self.audio_buffer = np.array([], dtype=np.int16)  # Buffer for leftover audio
                print(f"🎧 BridgeAudioProcessor initialized with bridge at {id(bridge)}, closed: {bridge.closed()}")
                
            def recv(self, frame: av.AudioFrame) -> av.AudioFrame:
                """Process audio frame: send mic to Gemini, return AI audio to speaker"""
                try:
                    self.frame_count += 1
                    
                    # Send mic audio to Gemini (every 3rd frame for better voice capture)
                    if self.frame_count % 3 == 0:
                        try:
                            # Get mic audio from frame
                            mic_data = frame.to_ndarray()
                            
                            # Handle different array shapes
                            if len(mic_data.shape) == 2:
                                # If stereo (shape: [channels, samples]), average channels
                                if mic_data.shape[0] == 2:  # Stereo with channels first
                                    mic_data = mic_data.mean(axis=0)
                                elif mic_data.shape[1] == 2:  # Stereo with channels last
                                    mic_data = mic_data.mean(axis=1)
                                else:
                                    mic_data = mic_data.flatten()
                            
                            # Flatten to ensure 1D array
                            mic_data = mic_data.flatten()
                            
                            # Only process if we have reasonable audio
                            if len(mic_data) >= 480:  # At least 10ms at 48kHz
                                # Convert to int16
                                if mic_data.dtype != np.int16:
                                    mic_data = (mic_data * 32767).astype(np.int16)
                                
                                # Debug: Log occasionally to confirm mic is working
                                if self.frame_count % 300 == 0:  # Every ~6 seconds at 50fps
                                    print(f"🎙️ Mic active: sending {len(mic_data)} samples to bridge")
                                
                                # Send to bridge (will be downsampled to 16kHz internally)
                                self.bridge.put_user_audio(
                                    mic_data.tobytes(),
                                    sample_rate_hz=frame.sample_rate,
                                    num_channels=1
                                )
                        except Exception as e:
                            if self.frame_count % 100 == 0:
                                print(f"⚠️ Mic processing error: {e}")
                    
                    # Debug logging
                    if self.frame_count % 100 == 0:
                        if hasattr(self.bridge, '_ai_audio_queue'):
                            queue_size = self.bridge._ai_audio_queue.qsize()
                            buffer_size = len(self.audio_buffer)
                            print(f"📡 Frame {self.frame_count}: Queue={queue_size} chunks, Buffer={buffer_size} samples")
                    
                    # First check if we have buffered audio to play
                    if len(self.audio_buffer) >= frame.samples:
                        # Use buffered audio
                        output_samples = self.audio_buffer[:frame.samples]
                        self.audio_buffer = self.audio_buffer[frame.samples:]  # Keep remainder
                        
                        # Log playing audio occasionally for debugging
                        if self.frame_count % 500 == 0:  # Much less frequent
                            max_val = np.max(np.abs(output_samples))
                            print(f"🔊 Audio flowing: buffer={len(self.audio_buffer)} samples")
                        
                        # Try using int16 format directly (more compatible)
                        # Amplify the audio first
                        output_samples = (output_samples.astype(np.float32) * 1.5).astype(np.int16)
                        output_samples = np.clip(output_samples, -32768, 32767)
                        
                        # Create frame using int16 format
                        # For PyAV, we need shape (channels, samples)
                        output_data = output_samples.reshape(1, -1)
                        
                        out_frame = av.AudioFrame.from_ndarray(output_data, format='s16', layout='mono')
                        out_frame.sample_rate = 48000  # Explicitly set to 48kHz
                        return out_frame
                    
                    # If buffer is low, try to get more audio from queue
                    if hasattr(self.bridge, '_ai_audio_queue') and not self.bridge._ai_audio_queue.empty():
                        try:
                            # Get new audio chunk
                            ai_pcm = self.bridge._ai_audio_queue.get_nowait()
                            new_samples = np.frombuffer(ai_pcm, dtype=np.int16)
                            
                            # Add to buffer
                            self.audio_buffer = np.concatenate([self.audio_buffer, new_samples])
                            
                            # Now try to return audio if we have enough
                            if len(self.audio_buffer) >= frame.samples:
                                output_samples = self.audio_buffer[:frame.samples]
                                self.audio_buffer = self.audio_buffer[frame.samples:]
                                
                                # Amplify and use int16 format
                                output_samples = (output_samples.astype(np.float32) * 1.5).astype(np.int16)
                                output_samples = np.clip(output_samples, -32768, 32767)
                                output_data = output_samples.reshape(1, -1)
                                
                                out_frame = av.AudioFrame.from_ndarray(output_data, format='s16', layout='mono')
                                out_frame.sample_rate = 48000
                                return out_frame
                                
                        except Exception as e:
                            if self.frame_count % 100 == 0:
                                print(f"⚠️ Error getting audio: {e}")
                    
                    # If we have partial buffer but not enough for full frame, pad with silence
                    if len(self.audio_buffer) > 0 and len(self.audio_buffer) < frame.samples:
                        padding = np.zeros(frame.samples - len(self.audio_buffer), dtype=np.int16)
                        output_samples = np.concatenate([self.audio_buffer, padding])
                        self.audio_buffer = np.array([], dtype=np.int16)  # Clear buffer
                        
                        # Amplify and use int16 format
                        output_samples = (output_samples.astype(np.float32) * 1.5).astype(np.int16)
                        output_samples = np.clip(output_samples, -32768, 32767)
                        output_data = output_samples.reshape(1, -1)
                        
                        out_frame = av.AudioFrame.from_ndarray(output_data, format='s16', layout='mono')
                        out_frame.sample_rate = 48000
                        return out_frame
                    
                    # Return silence if no audio available
                    silence = np.zeros((1, frame.samples), dtype=np.int16)
                    silent_frame = av.AudioFrame.from_ndarray(silence, format='s16', layout='mono')
                    silent_frame.sample_rate = 48000
                    return silent_frame
                    
                except Exception as e:
                    print(f"❌ Fatal error in recv: {e}")
                    import traceback
                    traceback.print_exc()
                    # Return silence as fallback
                    silence = np.zeros((1, frame.samples), dtype=np.int16)
                    silent_frame = av.AudioFrame.from_ndarray(silence, format='s16', layout='mono')
                    silent_frame.sample_rate = 48000
                    return silent_frame
        
        # Capture bridge reference to avoid session_state access in background thread
        bridge_ref = st.session_state.bridge
        
        ctx = webrtc_streamer(
            key="voice-bridge",
            mode=WebRtcMode.SENDRECV,
            media_stream_constraints={
                "audio": {
                    "echoCancellation": False,
                    "noiseSuppression": False,
                    "autoGainControl": False,
                },
                "video": False
            },
            audio_processor_factory=lambda: BridgeAudioProcessor(bridge_ref),
            async_processing=False,
            rtc_configuration={
                "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}],
            },
        )
        
        if ctx and ctx.state.playing:
            st.success("✅ Audio is ACTIVE - You should hear the agent now!")
            # Ensure bridge is started when WebRTC is active
            if st.session_state.bridge.closed():
                st.session_state.bridge.start()
                print("🔗 Started WebRTC audio bridge")
            
            # Check if there's audio waiting in the queue
            queue_size = st.session_state.bridge._ai_audio_queue.qsize() if hasattr(st.session_state.bridge, '_ai_audio_queue') else 0
            if queue_size > 0:
                st.info(f"📦 {queue_size} audio chunks waiting to play...")
        else:
            st.error("❌ Audio is NOT active - Click START above to hear the agent!")

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
            # Ensure bridge is started
            if bridge.closed():
                bridge.start()
                print("🚀 Started bridge for runner")
            print(f"🎯 Runner started, bridge closed: {bridge.closed()}")
            
            # Wait a moment for WebRTC to initialize
            await asyncio.sleep(2)
            
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


