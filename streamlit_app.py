import asyncio
import contextlib
import threading
from typing import Optional

import streamlit as st
from streamlit_webrtc import webrtc_streamer, WebRtcMode

from app_helpers import initialize_mcp_and_gmail_agent, fetch_inbox_emails
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

    # Controls
    col1, col2 = st.columns(2)
    start_clicked = col1.button("Start", type="primary", disabled=st.session_state.runner_task is not None)
    stop_clicked = col2.button("Stop", disabled=st.session_state.runner_task is None)

    status = st.empty()
    current_email_box = st.empty()

    # WebRTC placeholder (we'll wire in Phase 5-6)
    with st.expander("Audio (browser)"):
        st.caption("Browser audio will be wired in Phase 5-6.")
        webrtc_streamer(key="voice", mode=WebRtcMode.SENDRECV, audio_receiver_size=256, video_frame_callback=None)

    def _render_current_email():
        email = st.session_state.email_manager.get_current_email()
        if email:
            idx = st.session_state.email_manager.current_index + 1
            total = len(st.session_state.email_manager.emails)
            current_email_box.info(f"Email {idx}/{total}: From {email.get('from','?')} — {email.get('subject','(no subject)')}")
        else:
            current_email_box.info("No email loaded.")

    async def _start_async():
        status.write("Initializing…")
        if not st.session_state.initialized:
            st.session_state.mcp_app, st.session_state.gmail_agent = await initialize_mcp_and_gmail_agent()
            emails = await fetch_inbox_emails(st.session_state.gmail_agent)
            if not emails:
                status.error("No emails found in inbox.")
                return
            st.session_state.email_manager.set_emails(emails)
            st.session_state.nav_tools = EmailNavigationTools(st.session_state.email_manager)
            # Build tools via existing flow inside process_single_email_session call site (Phase 7)
            st.session_state.initialized = True

        status.success("Ready. Starting session…")
        _render_current_email()

        async def _runner():
            # Reuse existing per-email loop
            try:
                # Minimal set: defer gemini_tools build to main loop; here we just call per-email sessions via main
                # Use the same helpers as `main.py` path; we rely on `process_single_email_session` to drive one session.
                while not st.session_state.email_manager.is_exhausted():
                    # Note: We need `gemini_tools` built similarly to main; for Phase 4 scaffold, we skip starting audio sessions.
                    status.info("(Phase 4) Session wiring pending. UI scaffold running.")
                    await asyncio.sleep(1.0)
                    break
            finally:
                pass

        st.session_state.runner_task = asyncio.create_task(_runner())

    def _start():
        asyncio.run_coroutine_threadsafe(_start_async(), st.session_state.loop)

    def _stop():
        async def _stop_async():
            if st.session_state.runner_task:
                st.session_state.runner_task.cancel()
                with contextlib.suppress(Exception):
                    await st.session_state.runner_task
                st.session_state.runner_task = None
            status.info("Stopped.")
        asyncio.run_coroutine_threadsafe(_stop_async(), st.session_state.loop)

    if start_clicked:
        _start()
    if stop_clicked:
        _stop()

    _render_current_email()


if __name__ == "__main__":
    main()


