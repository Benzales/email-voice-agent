"""
Audio handling classes for voice input and output
"""

import pyaudio
import queue
import threading

# Audio recording parameters
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000


class AudioRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.audio_queue = queue.Queue()
        
    def start_recording(self):
        self.is_recording = True
        self.frames = []
        
        def callback(in_data, frame_count, time_info, status):
            if self.is_recording:
                self.audio_queue.put(in_data)
            return (in_data, pyaudio.paContinue)
        
        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
            stream_callback=callback
        )
        self.stream.start_stream()
        print("🎤 Recording started... (speak now)")
        
    def stop_recording(self):
        self.is_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        print("⏹️  Recording stopped")
        
    def get_audio_data(self):
        """Get all recorded audio data as PCM bytes"""
        audio_data = b''
        while not self.audio_queue.empty():
            audio_data += self.audio_queue.get()
        return audio_data


class AudioPlayer:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.output_stream = None
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.stop_playback = False
        
    def start_output_stream(self):
        """Start the output audio stream"""
        self.output_stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=24000,
            output=True,
            frames_per_buffer=CHUNK
        )
        
        # Start playback thread
        self.stop_playback = False
        self.playback_thread = threading.Thread(target=self._playback_worker)
        self.playback_thread.daemon = True
        self.playback_thread.start()
    
    def _playback_worker(self):
        """Worker thread that continuously plays audio from the queue"""
        while not self.stop_playback:
            try:
                audio_data = self.audio_queue.get(timeout=0.005)
                if audio_data and self.output_stream:
                    self.output_stream.write(audio_data)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in playback worker: {e}")
    
    def queue_audio(self, audio_data):
        """Queue audio data for playback"""
        self.audio_queue.put(audio_data)
    
    def clear_queue(self):
        """Clear all queued audio"""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
    
    def close(self):
        """Close the audio stream"""
        self.stop_playback = True
        if self.playback_thread:
            self.playback_thread.join(timeout=1)
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        self.audio.terminate() 