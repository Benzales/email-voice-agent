/**
 * React hook for managing voice sessions with the FastAPI backend
 * Combines audio processing and WebSocket communication
 */

import { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { AudioProcessor } from '@/lib/audio/audioUtils';
import { VoiceWebSocketClient, createVoiceWebSocketClient, SessionStatus } from '@/lib/websocket/client';

export interface VoiceSessionState {
  isConnected: boolean;
  isRecording: boolean;
  sessionStatus: 'idle' | 'initializing' | 'ready' | 'active' | 'processing' | 'completed' | 'error';
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

export function useVoiceSession(backendUrl?: string, sessionId?: string): [VoiceSessionState, VoiceSessionControls] {
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

      // Create WebSocket client with session authentication
      const wsUrl = backendUrl || 'ws://localhost:8000/ws/voice-session';
      const authenticatedWsUrl = sessionId ? `${wsUrl}?session_id=${sessionId}` : wsUrl;
      
      wsClientRef.current = createVoiceWebSocketClient(authenticatedWsUrl, {
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
          const errorMessage = error instanceof Error ? error.message : String(error);
          updateState({
            error: errorMessage,
            statusMessage: `Error: ${errorMessage}`,
            sessionStatus: 'error'
          });
        },

        onSessionStatus: (status: { status: SessionStatus; message?: string; progress?: unknown }) => {
          const progress = status.progress && typeof status.progress === 'object' && 
                          'current' in status.progress && 'total' in status.progress && 'remaining' in status.progress
                          ? status.progress as { current: number; total: number; remaining: number }
                          : null;
          updateState({
            sessionStatus: status.status,
            statusMessage: status.message || `Status: ${status.status}`,
            progress
          });
        },

        onAudioData: (audioData: ArrayBuffer) => {
          // Play audio through speakers (removed spammy debug logs)
          audioProcessorRef.current?.playAudio(audioData);
        },

        onInterruption: () => {
          // Clear audio queue when backend signals interruption
          console.log('🔄 Clearing audio queue due to interruption');
          audioProcessorRef.current?.clearAudioQueue();
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
  }, [backendUrl, sessionId, initializeAudio, updateState]);

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
  const startSession = useCallback(async (emailQuery = 'in:inbox', maxResults = 50) => {
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
      await audioProcessorRef.current.startRecording((audioData: ArrayBuffer) => {
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
   * Auto-cleanup on page visibility change and improve reliability
   */
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden && state.isRecording) {
        console.log('🔄 Page hidden - stopping session for reliability');
        stopSession();
      } else if (!document.hidden && state.isConnected && !state.isRecording) {
        // Resume audio context when page becomes visible
        if (audioProcessorRef.current) {
          // Try to resume audio context (private property, so we'll call a method)
          try {
            audioProcessorRef.current.initialize();
          } catch (e) {
            console.log('Could not resume audio context:', e);
          }
        }
      }
    };

    const handleBeforeUnload = () => {
      if (state.isRecording) {
        stopSession();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [state.isRecording, state.isConnected, stopSession]);

  const controls: VoiceSessionControls = useMemo(() => ({
    connect,
    disconnect,
    startSession,
    stopSession
  }), [connect, disconnect, startSession, stopSession]);

  return [state, controls];
}
