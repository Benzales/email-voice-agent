/**
 * Voice Email Agent - Main UI Component
 * Simple, voice-only interface for email processing
 */

'use client';

import { useState } from 'react';
import { useVoiceSession } from '@/hooks/useVoiceSession';

interface VoiceEmailAgentProps {
  backendUrl?: string;
}

export default function VoiceEmailAgent({ backendUrl }: VoiceEmailAgentProps) {
  const wsUrl = backendUrl || process.env.NEXT_PUBLIC_BACKEND_WS_URL || 'ws://localhost:8000/ws/voice-session';
  const [sessionState, sessionControls] = useVoiceSession(wsUrl);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      await sessionControls.connect();
    } catch (error) {
      console.error('Failed to connect:', error);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleStartSession = async () => {
    try {
      await sessionControls.startSession('in:inbox', 50);
    } catch (error) {
      console.error('Failed to start session:', error);
    }
  };

  const getStatusColor = () => {
    switch (sessionState.sessionStatus) {
      case 'active':
      case 'processing':
        return 'text-green-600';
      case 'error':
        return 'text-red-600';
      case 'initializing':
        return 'text-yellow-600';
      case 'completed':
        return 'text-blue-600';
      default:
        return 'text-gray-600';
    }
  };

  const getStatusIcon = () => {
    if (sessionState.isRecording) return '🎤';
    if (sessionState.sessionStatus === 'processing') return '⚡';
    if (sessionState.sessionStatus === 'error') return '❌';
    if (sessionState.sessionStatus === 'completed') return '✅';
    if (sessionState.isConnected) return '🔗';
    return '🔌';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            📧 Voice Email Agent
          </h1>
          <p className="text-gray-600">
            Clear your inbox with voice commands
          </p>
        </div>

        {/* Status Display */}
        <div className="bg-gray-50 rounded-lg p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Status</span>
            <span className="text-2xl">{getStatusIcon()}</span>
          </div>
          <p className={`text-sm font-medium ${getStatusColor()}`}>
            {sessionState.statusMessage}
          </p>
          
          {/* Progress Display */}
          {sessionState.progress && (
            <div className="mt-3">
              <div className="flex justify-between text-xs text-gray-600 mb-1">
                <span>Email Progress</span>
                <span>
                  {sessionState.progress.current} / {sessionState.progress.total}
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{
                    width: `${(sessionState.progress.current / sessionState.progress.total) * 100}%`
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                {sessionState.progress.remaining} emails remaining
              </p>
            </div>
          )}

          {/* Error Display */}
          {sessionState.error && (
            <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">
              {sessionState.error}
            </div>
          )}
        </div>

        {/* Controls */}
        <div className="space-y-3">
          {!sessionState.isConnected ? (
            <button
              onClick={handleConnect}
              disabled={isConnecting}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              {isConnecting ? 'Connecting...' : 'Connect to Backend'}
            </button>
          ) : (
            <>
              {!sessionState.isRecording ? (
                <button
                  onClick={handleStartSession}
                  disabled={sessionState.sessionStatus === 'initializing'}
                  className="w-full bg-green-600 hover:bg-green-700 disabled:bg-green-300 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
                >
                  🎤 Start Voice Session
                </button>
              ) : (
                <button
                  onClick={sessionControls.stopSession}
                  className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
                >
                  🛑 Stop Session
                </button>
              )}
              
              <button
                onClick={sessionControls.disconnect}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
              >
                Disconnect
              </button>
            </>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-8 text-center">
          <details className="text-left">
            <summary className="text-sm text-gray-500 cursor-pointer hover:text-gray-700 mb-2">
              📋 How it works
            </summary>
            <div className="text-xs text-gray-600 space-y-1 bg-gray-50 p-3 rounded">
              <p>• <strong>Connect:</strong> Establishes connection to your email backend</p>
              <p>• <strong>Start Session:</strong> Begins processing your inbox emails</p>
              <p>• <strong>Voice Commands:</strong> Say &quot;archive&quot;, &quot;delete&quot;, &quot;reply&quot;, or &quot;skip&quot;</p>
              <p>• <strong>Automatic:</strong> Moves to next email after each action</p>
              <p>• <strong>Complete:</strong> Processes all emails until inbox is clear</p>
            </div>
          </details>
        </div>

        {/* Audio Indicator */}
        {sessionState.isRecording && (
          <div className="fixed bottom-4 right-4 bg-red-500 text-white px-4 py-2 rounded-full shadow-lg animate-pulse">
            🎤 Recording...
          </div>
        )}
      </div>
    </div>
  );
}
