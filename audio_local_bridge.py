"""
LocalAudioBridge: Adapter that implements AudioBridge using existing
`AudioRecorder` and `AudioPlayer` for local development and terminal mode.

Phase 2 deliverable: Provide a drop-in bridge without changing session logic.
"""

from __future__ import annotations

import queue
from typing import Optional

from audio_bridge import AudioBridge, PcmAudioSpec
from audio_handlers import AudioRecorder, AudioPlayer, RATE


class LocalAudioBridge(AudioBridge):
    """Local adapter that pulls from the local microphone and plays audio locally.

    For compatibility with the abstract interface:
    - `put_user_audio` is accepted but ignored (local mic is the source).
    - `get_user_audio` returns data from the local `AudioRecorder`.
    - `put_ai_audio` queues data into the local `AudioPlayer`.
    - `get_ai_audio` is accepted but returns None (local playback is push-driven).
    """

    def __init__(self) -> None:
        self._recorder: Optional[AudioRecorder] = None
        self._player: Optional[AudioPlayer] = None
        self._closed: bool = True
        self._current_output_rate: Optional[int] = None

        # Specs: keep user input at 16 kHz mono 16-bit for Gemini
        self.USER_INPUT_SPEC = PcmAudioSpec(sample_rate_hz=RATE)
        # We do not assume a fixed Gemini output sample rate; will adapt.
        self.AI_OUTPUT_SPEC = PcmAudioSpec(sample_rate_hz=24000)

    def start(self) -> None:
        if not self._closed:
            return
        self._recorder = AudioRecorder()
        self._player = None  # lazy-init on first AI audio to match its rate
        self._recorder.start_recording()
        self._closed = False

    def stop(self) -> None:
        if self._closed:
            return
        try:
            if self._recorder is not None:
                self._recorder.stop_recording()
                # Ensure underlying PyAudio instance is terminated
                try:
                    if hasattr(self._recorder, 'audio') and self._recorder.audio:
                        self._recorder.audio.terminate()
                except Exception:
                    pass
                # terminate handled in existing cleanup paths
        finally:
            try:
                if self._player is not None:
                    self._player.close()
            finally:
                self._recorder = None
                self._player = None
                self._closed = True

    def closed(self) -> bool:
        return self._closed

    # User (mic) path
    def put_user_audio(self, frame_bytes: bytes, sample_rate_hz: int, num_channels: int, sample_width_bytes: int = 2) -> None:
        # Ignored in local mode: microphone is captured directly by AudioRecorder
        return

    def get_user_audio(self, timeout_seconds: float = 0.05) -> Optional[bytes]:
        if self._closed or self._recorder is None:
            return None
        data = self._recorder.get_audio_data()
        return data if data else None

    # AI (speaker) path
    def put_ai_audio(self, frame_bytes: bytes, sample_rate_hz: int, num_channels: int, sample_width_bytes: int = 2) -> None:
        if self._closed:
            return
        # Lazy-init or reconfigure the output stream to match provided rate
        if self._player is None:
            self._player = AudioPlayer()
            self._player.start_output_stream(rate=sample_rate_hz)
            self._current_output_rate = sample_rate_hz
        elif self._current_output_rate != sample_rate_hz:
            try:
                self._player.close()
            except Exception:
                pass
            self._player = AudioPlayer()
            self._player.start_output_stream(rate=sample_rate_hz)
            self._current_output_rate = sample_rate_hz
        # Queue bytes for playback
        self._player.queue_audio(frame_bytes)

    def get_ai_audio(self, timeout_seconds: float = 0.05) -> Optional[bytes]:
        # Not used in local mode since playback is push-driven by put_ai_audio
        return None

    def clear_ai_audio(self) -> None:
        if self._player is None:
            return
        try:
            self._player.clear_queue()
        except Exception:
            pass


__all__ = ["LocalAudioBridge"]


