#!/usr/bin/env python3
"""
Simple test harness for WebRTCAudioBridge to verify resampling and queuing.
Phase 6 acceptance test.
"""

import numpy as np
from audio_webrtc_bridge import WebRTCAudioBridge


def test_webrtc_bridge():
    """Test basic functionality of WebRTCAudioBridge."""
    print("Testing WebRTCAudioBridge...")
    
    bridge = WebRTCAudioBridge()
    
    # Test lifecycle
    assert bridge.closed()
    bridge.start()
    assert not bridge.closed()
    
    # Test user audio path (48 kHz -> 16 kHz)
    # Create a 48 kHz test tone (100 samples)
    test_freq = 440  # A4 note
    duration = 0.01  # 10ms
    sample_rate = 48000
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    test_audio = np.sin(2 * np.pi * test_freq * t)
    test_pcm = (test_audio * 32767).astype(np.int16).tobytes()
    
    # Put 48 kHz audio
    bridge.put_user_audio(test_pcm, sample_rate_hz=48000, num_channels=1)
    
    # Get 16 kHz audio
    resampled = bridge.get_user_audio(timeout_seconds=0.1)
    assert resampled is not None
    # Should be roughly 1/3 the samples (48k -> 16k)
    expected_samples = int(len(test_pcm) / 2 * (16000 / 48000))
    actual_samples = len(resampled) / 2
    assert abs(actual_samples - expected_samples) < 10  # Allow small variance
    print(f"✓ User audio resampling: {len(test_pcm)/2:.0f} samples @ 48kHz -> {actual_samples:.0f} samples @ 16kHz")
    
    # Test AI audio path (24 kHz -> 48 kHz)
    test_pcm_24k = (test_audio[:50] * 32767).astype(np.int16).tobytes()  # Smaller test
    bridge.put_ai_audio(test_pcm_24k, sample_rate_hz=24000, num_channels=1)
    
    # Get 48 kHz audio
    upsampled = bridge.get_ai_audio(timeout_seconds=0.1)
    assert upsampled is not None
    # Should be roughly 2x the samples (24k -> 48k)
    expected_samples = len(test_pcm_24k) / 2 * (48000 / 24000)
    actual_samples = len(upsampled) / 2
    assert abs(actual_samples - expected_samples) < 10
    print(f"✓ AI audio resampling: {len(test_pcm_24k)/2:.0f} samples @ 24kHz -> {actual_samples:.0f} samples @ 48kHz")
    
    # Test clear
    bridge.put_ai_audio(test_pcm_24k, sample_rate_hz=24000, num_channels=1)
    bridge.clear_ai_audio()
    cleared = bridge.get_ai_audio(timeout_seconds=0.01)
    assert cleared is None
    print("✓ Clear AI audio queue works")
    
    # Test stop
    bridge.stop()
    assert bridge.closed()
    print("✓ Bridge lifecycle complete")
    
    print("\n✅ All WebRTCAudioBridge tests passed!")
    return True


if __name__ == "__main__":
    test_webrtc_bridge()
