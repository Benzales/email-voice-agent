/**
 * Voice Email Agent - Main UI Component
 * Simple, voice-only interface for email processing
 */

'use client';

import { useState, useEffect } from 'react';
import { useVoiceSession } from '@/hooks/useVoiceSession';

interface VoiceEmailAgentProps {
  backendUrl?: string;
}

export default function VoiceEmailAgent({ backendUrl }: VoiceEmailAgentProps) {
  const wsUrl = backendUrl || process.env.NEXT_PUBLIC_BACKEND_WS_URL || 'ws://localhost:8000/ws/voice-session';
  const [sessionState, sessionControls] = useVoiceSession(wsUrl);
  const [isStarting, setIsStarting] = useState(false);

  // Auto-connect on component mount
  useEffect(() => {
    const autoConnect = async () => {
      if (!sessionState.isConnected && sessionState.sessionStatus === 'idle') {
        try {
          await sessionControls.connect();
        } catch (error) {
          console.error('Auto-connect failed:', error);
        }
      }
    };
    
    autoConnect();
  }, [sessionState.isConnected, sessionState.sessionStatus, sessionControls]);

  const handleClearInbox = async () => {
    setIsStarting(true);
    try {
      await sessionControls.startSession('in:inbox', 50);
    } catch (error) {
      console.error('Failed to start inbox clearing:', error);
    } finally {
      setIsStarting(false);
    }
  };

  const getStatusColor = () => {
    switch (sessionState.sessionStatus) {
      case 'ready':
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
    if (sessionState.sessionStatus === 'ready') return '📧';
    if (sessionState.sessionStatus === 'initializing') return '🔄';
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
            {sessionState.sessionStatus === 'ready' && sessionState.progress 
              ? `Ready! ${sessionState.progress.total} emails in your inbox`
              : sessionState.statusMessage
            }
          </p>
          
          {/* Progress Display - only show during active processing */}
          {sessionState.progress && sessionState.sessionStatus === 'processing' && sessionState.progress.current > 0 && (
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

        {/* Single Button Interface */}
        <div className="space-y-3">
          {sessionState.sessionStatus === 'idle' || sessionState.sessionStatus === 'initializing' || sessionState.sessionStatus === 'ready' ? (
            <div className="text-center">
              {sessionState.sessionStatus === 'initializing' ? (
                <div className="w-full bg-blue-100 text-blue-800 font-semibold py-3 px-6 rounded-lg">
                  🔄 {sessionState.statusMessage}
                </div>
              ) : (
                <button
                  onClick={handleClearInbox}
                  disabled={isStarting || !sessionState.isConnected}
                  className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 disabled:from-gray-300 disabled:to-gray-400 text-white font-bold py-4 px-8 rounded-xl transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100"
                >
                  {isStarting ? (
                    '🔄 Starting...'
                  ) : sessionState.progress ? (
                    `🎤 Clear My Inbox (${sessionState.progress.total} emails)`
                  ) : (
                    '🎤 Clear My Inbox'
                  )}
                </button>
              )}
            </div>
          ) : sessionState.isRecording ? (
            <div className="space-y-3">
              <button
                onClick={sessionControls.stopSession}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
              >
                🛑 Stop Session
              </button>
              <div className="text-center text-sm text-gray-600">
                Speak your commands: &quot;archive&quot;, &quot;delete&quot;, &quot;skip&quot;, &quot;reply&quot;
              </div>
            </div>
          ) : (
            <div className="text-center">
              <div className="w-full bg-green-100 text-green-800 font-semibold py-3 px-6 rounded-lg mb-3">
                ✅ {sessionState.statusMessage}
              </div>
              <button
                onClick={sessionControls.disconnect}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white font-semibold py-2 px-6 rounded-lg transition-colors"
              >
                Reset
              </button>
            </div>
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
