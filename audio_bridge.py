"""
Audio bridge abstraction for browser/WebRTC and local audio integration.

Phase 1 deliverable: Define an interface with no behavior changes.

This interface decouples the email session logic from concrete audio I/O
implementations (e.g., local `AudioRecorder`/`AudioPlayer` or WebRTC streams).

Usage expectations:
- `put_user_audio` receives raw PCM frames from the user microphone path (push API, e.g., WebRTC).
- `get_user_audio` returns raw PCM frames collected from the user microphone path (pull API, e.g., local mic).
- `put_ai_audio` receives raw PCM frames produced by the AI for playback.
- `get_ai_audio` returns raw PCM frames to be played to the user (pull API for browser playback).

All audio frames are expected to be 16-bit signed PCM (little endian), mono.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PcmAudioSpec:
    """Describes linear PCM audio format.

    - sample_rate_hz: Samples per second, e.g., 16000.
    - num_channels: Number of channels, 1 for mono.
    - sample_width_bytes: Bytes per sample per channel, 2 for 16-bit PCM.
    """

    sample_rate_hz: int
    num_channels: int = 1
    sample_width_bytes: int = 2


class AudioBridge(ABC):
    """Abstract interface for bidirectional audio between user and AI.

    Implementations manage buffering, resampling (if needed), and lifecycle.

    Contract:
    - Methods are thread-safe where applicable. Non-blocking preferred.
    - `put_user_audio` should not block indefinitely. It may drop frames under
      backpressure but must not deadlock the UI thread.
    - `get_ai_audio` may block up to `timeout_seconds` and return None if no
      audio is available.
    - `start` and `stop` are idempotent.
    - `closed` returns True after `stop` completes and resources are released.
    """

    # Canonical internal formats for Gemini Live path
    USER_INPUT_SPEC: PcmAudioSpec = PcmAudioSpec(sample_rate_hz=16000)
    AI_OUTPUT_SPEC: PcmAudioSpec = PcmAudioSpec(sample_rate_hz=16000)

    @abstractmethod
    def start(self) -> None:
        """Initialize resources and transition to running state.

        Should be safe to call multiple times; subsequent calls are no-ops.
        """

    @abstractmethod
    def stop(self) -> None:
        """Stop processing and release resources in a timely manner.

        Implementations should drain/flush any internal buffers as appropriate
        and mark the bridge as closed.
        """

    @abstractmethod
    def closed(self) -> bool:
        """Return True if the bridge has been stopped and is no longer usable."""

    @abstractmethod
    def put_user_audio(
        self,
        frame_bytes: bytes,
        sample_rate_hz: int,
        num_channels: int,
        sample_width_bytes: int = 2,
    ) -> None:
        """Submit a chunk of user microphone audio to the bridge.

        Parameters are provided explicitly to allow implementations to resample
        or downmix as needed. Frames are assumed to be tightly packed PCM with
        the specified sample width (default 16-bit), channel count, and rate.
        """

    @abstractmethod
    def get_user_audio(self, timeout_seconds: float = 0.05) -> Optional[bytes]:
        """Retrieve a chunk of user microphone audio, or None if not available.

        Returned bytes MUST be 16-bit PCM, mono, at `USER_INPUT_SPEC.sample_rate_hz`.
        The chunk size should represent roughly 20–40 ms of audio to balance
        latency and overhead.
        """

    @abstractmethod
    def put_ai_audio(
        self,
        frame_bytes: bytes,
        sample_rate_hz: int,
        num_channels: int,
        sample_width_bytes: int = 2,
    ) -> None:
        """Submit a chunk of AI audio for user playback (push API)."""

    @abstractmethod
    def get_ai_audio(self, timeout_seconds: float = 0.05) -> Optional[bytes]:
        """Retrieve a chunk of AI audio for playback, or None if not available.

        Returned bytes MUST be 16-bit PCM, mono, at `AI_OUTPUT_SPEC.sample_rate_hz`.
        The chunk size should represent roughly 20–40 ms of audio to balance
        latency and overhead.
        """

    @abstractmethod
    def clear_ai_audio(self) -> None:
        """Immediately drop any queued AI playback audio.

        Used to handle interruptions so stale TTS audio is not played out.
        Implementations should be safe to call at any time.
        """


__all__ = [
    "PcmAudioSpec",
    "AudioBridge",
]


