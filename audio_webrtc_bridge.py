"""
WebRTCAudioBridge: Bridge between browser WebRTC audio and Gemini Live session.

Phase 6 deliverable: Handles bidirectional audio with resampling and queuing.
Browser mic (48 kHz) -> downsample to 16 kHz -> Gemini
Gemini (24 kHz) -> upsample to 48 kHz -> browser speaker
"""

from __future__ import annotations

import asyncio
import queue
import threading
from typing import Optional
import numpy as np
import librosa

from audio_bridge import AudioBridge, PcmAudioSpec


class WebRTCAudioBridge(AudioBridge):
    """WebRTC adapter that uses queues to bridge browser audio and Gemini.
    
    Browser sends 48 kHz frames -> we downsample to 16 kHz for Gemini input.
    Gemini sends audio -> we prepare it at 48 kHz for browser playback.
    """

    def __init__(self, max_queue_size: int = 100):
        # Input queue: browser mic -> Gemini (16 kHz PCM16)
        self._user_audio_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        # Output queue: Gemini -> browser speaker (48 kHz PCM16)
        self._ai_audio_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._closed = True
        self._lock = threading.Lock()
        
        # Audio specs
        self.USER_INPUT_SPEC = PcmAudioSpec(sample_rate_hz=16000)  # Gemini expects 16 kHz
        self.AI_OUTPUT_SPEC = PcmAudioSpec(sample_rate_hz=24000)   # Gemini outputs 24 kHz
        self.BROWSER_RATE = 48000  # Browser WebRTC typically uses 48 kHz

    def start(self) -> None:
        with self._lock:
            if not self._closed:
                return
            self._closed = False
            # Clear queues on start
            while not self._user_audio_queue.empty():
                try:
                    self._user_audio_queue.get_nowait()
                except queue.Empty:
                    break
            while not self._ai_audio_queue.empty():
                try:
                    self._ai_audio_queue.get_nowait()
                except queue.Empty:
                    break

    def stop(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            # Clear queues
            while not self._user_audio_queue.empty():
                try:
                    self._user_audio_queue.get_nowait()
                except queue.Empty:
                    break
            while not self._ai_audio_queue.empty():
                try:
                    self._ai_audio_queue.get_nowait()
                except queue.Empty:
                    break

    def closed(self) -> bool:
        with self._lock:
            return self._closed

    def put_user_audio(
        self,
        frame_bytes: bytes,
        sample_rate_hz: int,
        num_channels: int,
        sample_width_bytes: int = 2,
    ) -> None:
        """Receive audio from browser mic, downsample to 16 kHz, and queue for Gemini."""
        if self._closed:
            return
            
        try:
            # Convert bytes to float32 for resampling
            audio = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32767.0
            
            # Handle stereo -> mono if needed
            if num_channels == 2 and len(audio) > 0:
                # Reshape and average channels
                audio = audio.reshape(-1, 2).mean(axis=1)
            
            # Resample to 16 kHz for Gemini if needed
            if sample_rate_hz != self.USER_INPUT_SPEC.sample_rate_hz and len(audio) > 0:
                audio = librosa.resample(
                    audio, 
                    orig_sr=sample_rate_hz, 
                    target_sr=self.USER_INPUT_SPEC.sample_rate_hz,
                    res_type="kaiser_fast"
                )
            
            # Convert back to int16 PCM
            audio = np.clip(audio, -1.0, 1.0)
            pcm16 = (audio * 32767.0).astype(np.int16).tobytes()
            
            # Queue with non-blocking put (drop if full)
            try:
                self._user_audio_queue.put_nowait(pcm16)
            except queue.Full:
                pass  # Drop frame if queue is full
                
        except Exception as e:
            print(f"⚠️ WebRTC bridge put_user_audio error: {e}")

    def get_user_audio(self, timeout_seconds: float = 0.05) -> Optional[bytes]:
        """Retrieve queued user audio for Gemini (16 kHz PCM16)."""
        if self._closed:
            return None
        try:
            return self._user_audio_queue.get(timeout=timeout_seconds)
        except queue.Empty:
            return None

    def put_ai_audio(
        self,
        frame_bytes: bytes,
        sample_rate_hz: int,
        num_channels: int,
        sample_width_bytes: int = 2,
    ) -> None:
        """Receive AI audio from Gemini, upsample to 48 kHz, and queue for browser."""
        if self._closed:
            return
            
        # Debug: log when AI audio is received
        if len(frame_bytes) > 0:
            print(f"[Bridge] Received AI audio: {len(frame_bytes)} bytes at {sample_rate_hz} Hz (queue size: {self._ai_audio_queue.qsize()})")
            
        try:
            # Convert to float32 for resampling
            audio = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32) / 32767.0
            
            # Resample to 48 kHz for browser if needed
            if sample_rate_hz != self.BROWSER_RATE and len(audio) > 0:
                audio = librosa.resample(
                    audio,
                    orig_sr=sample_rate_hz,
                    target_sr=self.BROWSER_RATE,
                    res_type="kaiser_fast"
                )
            
            # Convert back to int16 PCM
            audio = np.clip(audio, -1.0, 1.0)
            pcm16 = (audio * 32767.0).astype(np.int16).tobytes()
            
            # Queue with non-blocking put
            try:
                self._ai_audio_queue.put_nowait(pcm16)
            except queue.Full:
                print(f"[Bridge] WARNING: AI audio queue full, dropping {len(pcm16)} bytes")
                
        except Exception as e:
            print(f"⚠️ WebRTC bridge put_ai_audio error: {e}")

    def get_ai_audio(self, timeout_seconds: float = 0.05) -> Optional[bytes]:
        """Retrieve queued AI audio for browser playback (48 kHz PCM16)."""
        if self._closed:
            return None
        try:
            audio = self._ai_audio_queue.get(timeout=timeout_seconds)
            if audio:
                print(f"[Bridge] Delivering {len(audio)} bytes to WebRTC")
            return audio
        except queue.Empty:
            return None

    def clear_ai_audio(self) -> None:
        """Clear queued AI audio (for interruptions)."""
        while not self._ai_audio_queue.empty():
            try:
                self._ai_audio_queue.get_nowait()
            except queue.Empty:
                break


__all__ = ["WebRTCAudioBridge"]
