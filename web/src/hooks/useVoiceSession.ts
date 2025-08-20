/**
 * React hook for managing voice sessions with the FastAPI backend
 * Combines audio processing and WebSocket communication
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { AudioProcessor } from '@/lib/audio/audioUtils';
import { VoiceWebSocketClient, createVoiceWebSocketClient, SessionStatus } from '@/lib/websocket/client';

export interface VoiceSessionState {
  isConnected: boolean;
  isRecording: boolean;
  sessionStatus: 'idle' | 'initializing' | 'active' | 'processing' | 'completed' | 'error';
  statusMessage: string;
  progress: {
    current: number;
    total: number;
    remaining: number;
  } | null;
  error: string | null;
}

export interface VoiceSessionControls {
  connect: () => Promise<void>;
  disconnect: () => void;
  startSession: (emailQuery?: string, maxResults?: number) => void;
  stopSession: () => void;
}

export function useVoiceSession(backendUrl?: string): [VoiceSessionState, VoiceSessionControls] {
  const [state, setState] = useState<VoiceSessionState>({
    isConnected: false,
    isRecording: false,
    sessionStatus: 'idle',
    statusMessage: 'Ready to connect',
    progress: null,
    error: null,
  });

  const audioProcessorRef = useRef<AudioProcessor | null>(null);
  const wsClientRef = useRef<VoiceWebSocketClient | null>(null);

  /**
   * Update state helper
   */
  const updateState = useCallback((updates: Partial<VoiceSessionState>) => {
    setState(prev => ({ ...prev, ...updates }));
  }, []);

  /**
   * Initialize audio processor
   */
  const initializeAudio = useCallback(async () => {
    if (!AudioProcessor.isSupported()) {
      throw new Error('Audio not supported in this browser');
    }

    if (!audioProcessorRef.current) {
      audioProcessorRef.current = new AudioProcessor();
      await audioProcessorRef.current.initialize();
    }
  }, []);

  /**
   * Connect to the backend
   */
  const connect = useCallback(async () => {
    try {
      updateState({ statusMessage: 'Connecting...', error: null });

      // Initialize audio first
      await initializeAudio();

      // Create WebSocket client
      wsClientRef.current = createVoiceWebSocketClient(backendUrl, {
        onConnect: () => {
          updateState({
            isConnected: true,
            statusMessage: 'Connected to backend',
            error: null
          });
        },

        onDisconnect: () => {
          updateState({
            isConnected: false,
            isRecording: false,
            sessionStatus: 'idle',
            statusMessage: 'Disconnected from backend'
          });
        },

        onError: (error) => {
          updateState({
            error,
            statusMessage: `Error: ${error}`,
            sessionStatus: 'error'
          });
        },

        onSessionStatus: (status: SessionStatus) => {
          updateState({
            sessionStatus: status.status,
            statusMessage: status.message || `Status: ${status.status}`,
            progress: status.progress || null
          });
        },

        onAudioData: (audioData: ArrayBuffer) => {
          // Debug audio data
          const uint8Array = new Uint8Array(audioData);
          const sample = uint8Array.slice(0, Math.min(20, uint8Array.length));
          const sampleStr = Array.from(sample).map(b => String.fromCharCode(b)).join('');
          
          console.log(`🎵 Received audio chunk: ${audioData.byteLength} bytes`);
          console.log(`🎵 First 20 bytes as chars: "${sampleStr}"`);
          console.log(`🎵 First 20 bytes as hex: ${Array.from(sample).map(b => b.toString(16).padStart(2, '0')).join(' ')}`);
          
          // Play audio through speakers
          audioProcessorRef.current?.playAudio(audioData);
        }
      });

      // Connect to WebSocket
      await wsClientRef.current.connect();

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Connection failed';
      updateState({
        error: errorMsg,
        statusMessage: `Connection failed: ${errorMsg}`,
        sessionStatus: 'error'
      });
      throw error;
    }
  }, [backendUrl, initializeAudio, updateState]);

  /**
   * Disconnect from the backend
   */
  const disconnect = useCallback(() => {
    // Stop recording
    if (audioProcessorRef.current && state.isRecording) {
      audioProcessorRef.current.stopRecording();
    }

    // Disconnect WebSocket
    wsClientRef.current?.disconnect();
    wsClientRef.current = null;

    updateState({
      isConnected: false,
      isRecording: false,
      sessionStatus: 'idle',
      statusMessage: 'Disconnected',
      progress: null,
      error: null
    });
  }, [state.isRecording, updateState]);

  /**
   * Start a voice session
   */
  const startSession = useCallback((emailQuery = 'in:inbox', maxResults = 50) => {
    if (!wsClientRef.current?.isConnected()) {
      updateState({ error: 'Not connected to backend' });
      return;
    }

    if (!audioProcessorRef.current) {
      updateState({ error: 'Audio not initialized' });
      return;
    }

    try {
      // Start recording audio
      audioProcessorRef.current.startRecording((audioData: ArrayBuffer) => {
        wsClientRef.current?.sendAudio(audioData);
      });

      // Start session on backend
      wsClientRef.current.startSession(emailQuery, maxResults);

      updateState({
        isRecording: true,
        sessionStatus: 'initializing',
        statusMessage: 'Starting voice session...',
        error: null
      });

    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to start session';
      updateState({
        error: errorMsg,
        statusMessage: `Failed to start: ${errorMsg}`,
        sessionStatus: 'error'
      });
    }
  }, [updateState]);

  /**
   * Stop the current session
   */
  const stopSession = useCallback(() => {
    // Stop recording
    if (audioProcessorRef.current) {
      audioProcessorRef.current.stopRecording();
    }

    // Stop session on backend
    wsClientRef.current?.stopSession();

    updateState({
      isRecording: false,
      sessionStatus: 'idle',
      statusMessage: 'Session stopped'
    });
  }, [updateState]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    return () => {
      if (audioProcessorRef.current) {
        audioProcessorRef.current.cleanup();
        audioProcessorRef.current = null;
      }
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }
    };
  }, []);

  /**
   * Auto-cleanup on page visibility change
   */
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && state.isRecording) {
        stopSession();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [state.isRecording, stopSession]);

  const controls: VoiceSessionControls = {
    connect,
    disconnect,
    startSession,
    stopSession
  };

  return [state, controls];
}
