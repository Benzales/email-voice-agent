/**
 * WebSocket client for voice session communication
 * Minimal implementation to satisfy imports
 */

export type SessionStatus = 'idle' | 'initializing' | 'ready' | 'active' | 'processing' | 'completed' | 'error';

export interface VoiceWebSocketClient {
  connect(): Promise<void>;
  disconnect(): void;
  sendAudio(data: ArrayBuffer): void;
  startSession(emailQuery: string, maxResults: number): void;
  stopSession(): void;
  isConnected(): boolean;
  onMessage(callback: (data: unknown) => void): void;
  onStatusChange(callback: (status: SessionStatus, message: string, progress?: unknown) => void): void;
  onError(callback: (error: string, recoverable: boolean) => void): void;
  onAudioReceived(callback: (audioData: ArrayBuffer) => void): void;
}

export interface WebSocketCallbacks {
  onConnect: () => void;
  onDisconnect: () => void;
  onError: (error: unknown) => void;
  onSessionStatus: (status: { status: SessionStatus; message?: string; progress?: unknown }) => void;
  onAudioData: (audioData: ArrayBuffer) => void;
  onInterruption: () => void;
}

export function createVoiceWebSocketClient(url: string, clientCallbacks: WebSocketCallbacks): VoiceWebSocketClient {
  let ws: WebSocket | null = null;
  let connected = false;
  
  const internalCallbacks = {
    message: [] as Array<(data: unknown) => void>,
    statusChange: [] as Array<(status: SessionStatus, message: string, progress?: unknown) => void>,
    error: [] as Array<(error: string, recoverable: boolean) => void>,
    audioReceived: [] as Array<(audioData: ArrayBuffer) => void>
  };

  const client: VoiceWebSocketClient = {
    async connect(): Promise<void> {
      return new Promise((resolve, reject) => {
        try {
          const wsUrl = url;
          ws = new WebSocket(wsUrl);
          let opened = false;

          // Fail fast if we cannot open within a reasonable time
          const connectTimeoutMs = 8000;
          const timeoutId = setTimeout(() => {
            if (!opened) {
              try { ws?.close(); } catch {}
              const err = new Error('WebSocket connect timeout');
              clientCallbacks.onError(err);
              internalCallbacks.error.forEach(cb => cb('WebSocket connect timeout', false));
              reject(err);
            }
          }, connectTimeoutMs);
          
          ws.onopen = () => {
            opened = true;
            clearTimeout(timeoutId);
            connected = true;
            clientCallbacks.onConnect();
            resolve();
          };
          
          ws.onmessage = (event) => {
            // Handle binary audio data (ArrayBuffer or Blob)
            if (event.data instanceof ArrayBuffer) {
              console.log(`🎵 Received binary audio data: ${event.data.byteLength} bytes`);
              clientCallbacks.onAudioData(event.data);
              internalCallbacks.audioReceived.forEach(cb => cb(event.data));
            } else if (event.data instanceof Blob) {
              console.log(`🎵 Received Blob audio data: ${event.data.size} bytes`);
              // Convert Blob to ArrayBuffer for audio processing
              event.data.arrayBuffer().then((arrayBuffer) => {
                clientCallbacks.onAudioData(arrayBuffer);
                internalCallbacks.audioReceived.forEach(cb => cb(arrayBuffer));
              });
            } else {
              // Handle text/JSON messages
              try {
                const data = JSON.parse(event.data);
                internalCallbacks.message.forEach(cb => cb(data));
                
                if (data.type === 'session_status') {
                  clientCallbacks.onSessionStatus({ status: data.status, message: data.message, progress: data.progress });
                  internalCallbacks.statusChange.forEach(cb => cb(data.status, data.message, data.progress));
                } else if (data.type === 'error') {
                  clientCallbacks.onError(data.message);
                  internalCallbacks.error.forEach(cb => cb(data.message, data.recoverable || false));
                } else if (data.type === 'audio_interrupted') {
                  clientCallbacks.onInterruption();
                }
              } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
              }
            }
          };
          
          ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            clientCallbacks.onError(error);
            internalCallbacks.error.forEach(cb => cb('WebSocket connection error', false));
            if (!opened) {
              clearTimeout(timeoutId);
              reject(error);
            }
          };
          
          ws.onclose = () => {
            const wasOpened = opened;
            clearTimeout(timeoutId);
            connected = false;
            clientCallbacks.onDisconnect();
            if (!wasOpened) {
              const err = new Error('WebSocket closed before connection established');
              clientCallbacks.onError(err);
              internalCallbacks.error.forEach(cb => cb('WebSocket closed before open', false));
              reject(err);
            }
          };
        } catch (error) {
          reject(error);
        }
      });
    },

    disconnect(): void {
      if (ws) {
        ws.close();
        ws = null;
      }
      connected = false;
    },

    sendAudio(data: ArrayBuffer): void {
      if (ws && connected) {
        ws.send(data);
      }
    },

    startSession(emailQuery: string, maxResults: number): void {
      if (ws && connected) {
        ws.send(JSON.stringify({
          type: 'start_session',
          email_query: emailQuery,
          max_results: maxResults
        }));
      }
    },

    stopSession(): void {
      if (ws && connected) {
        ws.send(JSON.stringify({
          type: 'stop_session',
          reason: 'user_requested'
        }));
      }
    },

    isConnected(): boolean {
      return connected;
    },

    onMessage(callback: (data: unknown) => void): void {
      internalCallbacks.message.push(callback);
    },

    onStatusChange(callback: (status: SessionStatus, message: string, progress?: unknown) => void): void {
      internalCallbacks.statusChange.push(callback);
    },

    onError(callback: (error: string, recoverable: boolean) => void): void {
      internalCallbacks.error.push(callback);
    },

    onAudioReceived(callback: (audioData: ArrayBuffer) => void): void {
      internalCallbacks.audioReceived.push(callback);
    }
  };

  return client;
}
