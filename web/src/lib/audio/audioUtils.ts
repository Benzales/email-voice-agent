/**
 * Audio processing utilities for voice session
 * Minimal implementation to satisfy imports
 */

export class AudioProcessor {
  private audioContext: AudioContext | null = null;
  private stream: MediaStream | null = null;
  private processor: ScriptProcessorNode | null = null;
  private isRecording = false;
  private audioQueue: ArrayBuffer[] = [];
  private isPlaying = false;
  private currentAudio: HTMLAudioElement | null = null;

  static isSupported(): boolean {
    return !!(typeof navigator !== 'undefined' && 
              navigator.mediaDevices && 
              typeof navigator.mediaDevices.getUserMedia === 'function' && 
              (typeof window !== 'undefined' && 
               (window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext)));
  }

  async initialize(): Promise<void> {
    // Initialize any necessary audio context or setup
    // This is a minimal implementation
    return Promise.resolve();
  }

  async startRecording(onAudioData: (data: ArrayBuffer) => void): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          sampleRate: 48000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true
        } 
      });
      
      this.audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext || AudioContext)();
      const source = this.audioContext.createMediaStreamSource(this.stream);
      
      this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
      this.processor.onaudioprocess = (event) => {
        if (this.isRecording) {
          const inputData = event.inputBuffer.getChannelData(0);
          const int16Array = new Int16Array(inputData.length);
          
          for (let i = 0; i < inputData.length; i++) {
            int16Array[i] = Math.max(-32768, Math.min(32767, inputData[i] * 32768));
          }
          
          onAudioData(int16Array.buffer);
        }
      };
      
      source.connect(this.processor);
      this.processor.connect(this.audioContext.destination);
      this.isRecording = true;
    } catch (error) {
      console.error('Failed to start recording:', error);
      throw error;
    }
  }

  stopRecording(): void {
    this.isRecording = false;
    
    if (this.processor) {
      this.processor.disconnect();
      this.processor = null;
    }
    
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }
    
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
  }

  isCurrentlyRecording(): boolean {
    return this.isRecording;
  }

  playAudio(audioData: ArrayBuffer): void {
    // Handle raw PCM audio data from Gemini Live
    try {
      // Add audio data to queue
      this.audioQueue.push(audioData);
      
      // Process queue if not already playing
      if (!this.isPlaying) {
        this.processAudioQueue();
      }
    } catch (error) {
      console.error('Audio playback error:', error);
    }
  }

  private async processAudioQueue(): Promise<void> {
    if (this.isPlaying || this.audioQueue.length === 0) {
      return;
    }

    this.isPlaying = true;

    try {
      while (this.audioQueue.length > 0) {
        const audioData = this.audioQueue.shift()!;
        
        // Debug: Log audio data info and first bytes
        console.log(`🎵 Processing audio chunk: ${audioData.byteLength} bytes`);
        const firstBytes = new Uint8Array(audioData.slice(0, 16));
        console.log('🔍 First 16 bytes:', Array.from(firstBytes).map(b => b.toString(16).padStart(2, '0')).join(' '));
        
        // Try to play as raw PCM first (most likely from Gemini Live)
        const pcmSuccess = await this.tryPlayPCM(audioData);
        if (pcmSuccess) {
          console.log('✅ Successfully played as PCM audio');
          continue;
        }

        // If PCM fails, try compressed formats
        const compressedSuccess = await this.tryPlayCompressed(audioData);
        if (!compressedSuccess) {
          console.error('🚫 Failed to play audio with any method');
        }
      }
    } catch (error) {
      console.error('Error processing audio queue:', error);
    } finally {
      this.isPlaying = false;
    }
  }

  private async tryPlayPCM(audioData: ArrayBuffer): Promise<boolean> {
    try {
      // Initialize audio context if needed
      if (!this.audioContext) {
        this.audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext || AudioContext)();
      }

      // Assume 16-bit PCM, mono, sample rate from Gemini (likely 24kHz or 48kHz)
      const sampleRates = [24000, 48000, 16000, 22050, 44100]; // Try common rates
      
      for (const sampleRate of sampleRates) {
        try {
          // Convert raw bytes to Float32Array for Web Audio API
          const int16Array = new Int16Array(audioData);
          const float32Array = new Float32Array(int16Array.length);
          
          // Convert 16-bit PCM to float32 (-1.0 to 1.0)
          for (let i = 0; i < int16Array.length; i++) {
            float32Array[i] = int16Array[i] / 32768.0;
          }

          // Create audio buffer
          const audioBuffer = this.audioContext.createBuffer(1, float32Array.length, sampleRate);
          audioBuffer.getChannelData(0).set(float32Array);

          // Play the audio
          const source = this.audioContext.createBufferSource();
          source.buffer = audioBuffer;
          source.connect(this.audioContext.destination);

          // Wait for audio to finish
          await new Promise<void>((resolve) => {
            source.onended = () => {
              console.log(`✅ PCM audio played successfully at ${sampleRate}Hz`);
              resolve();
            };
            source.start();
          });

          return true; // Success!

        } catch (error) {
          console.warn(`❌ PCM playback failed at ${sampleRate}Hz:`, error);
          // Try next sample rate
        }
      }

      return false;
    } catch (error) {
      console.warn('❌ PCM audio processing failed:', error);
      return false;
    }
  }

  private async tryPlayCompressed(audioData: ArrayBuffer): Promise<boolean> {
    const audioFormats = [
      'audio/mpeg',     // MP3
      'audio/mp4',      // AAC in MP4
      'audio/aac',      // Raw AAC
      'audio/wav',      // WAV
      'audio/webm',     // WebM
      'audio/ogg',      // Ogg
      ''                // Auto-detect
    ];

    for (const mimeType of audioFormats) {
      try {
        const audioBlob = new Blob([audioData], { type: mimeType });
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        this.currentAudio = audio;

        const success = await new Promise<boolean>((resolve) => {
          const cleanup = () => {
            URL.revokeObjectURL(audioUrl);
            this.currentAudio = null;
          };

          const timeout = setTimeout(() => {
            audio.pause();
            cleanup();
            resolve(false);
          }, 3000);

          audio.onended = () => {
            clearTimeout(timeout);
            cleanup();
            console.log(`✅ Compressed audio played with format: ${mimeType || 'auto-detect'}`);
            resolve(true);
          };
          
          audio.onerror = () => {
            clearTimeout(timeout);
            cleanup();
            resolve(false);
          };

          audio.play().catch(() => {
            clearTimeout(timeout);
            cleanup();
            resolve(false);
          });
        });

        if (success) return true;

      } catch (error) {
        console.warn(`💥 Compressed format ${mimeType || 'auto-detect'} error:`, error);
      }
    }

    return false;
  }

  clearAudioQueue(): void {
    // Clear the audio queue and stop current audio
    this.audioQueue = [];
    
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio = null;
    }
    
    this.isPlaying = false;
    console.log('Audio queue cleared');
  }

  cleanup(): void {
    // Cleanup all resources
    this.stopRecording();
    this.clearAudioQueue();
  }
}
