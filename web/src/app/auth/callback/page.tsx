/**
 * OAuth Callback Page
 * Handles the OAuth callback from Google and completes the authentication flow
 */

'use client';

import { useEffect, useState, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

interface CallbackState {
  status: 'processing' | 'success' | 'error';
  message: string;
  error?: string;
}

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [authState, authOperations] = useAuth();
  const [callbackState, setCallbackState] = useState<CallbackState>({
    status: 'processing',
    message: 'Processing authentication...'
  });
  const hasProcessedRef = useRef(false);

  useEffect(() => {
    const handleOAuthCallback = async () => {
      // Prevent multiple executions
      if (hasProcessedRef.current || callbackState.status !== 'processing') {
        return;
      }
      
      hasProcessedRef.current = true;

      try {
        // Extract parameters from URL
        const sessionId = searchParams.get('session_id');
        const success = searchParams.get('success');
        const error = searchParams.get('error');

        // Handle OAuth error
        if (error) {
          setCallbackState({
            status: 'error',
            message: 'Authentication failed',
            error: `OAuth error: ${error}`
          });
          return;
        }

        // Check if we have session info from backend redirect
        if (success === 'true' && sessionId) {
          setCallbackState({
            status: 'processing',
            message: 'Authentication successful! Setting up session...'
          });

          // Clean up OAuth state
          sessionStorage.removeItem('oauth_state');

          // Use the auth hook to handle the callback (this will store the session ID)
          if (authOperations && 'handleOAuthCallback' in authOperations) {
            await (authOperations as { handleOAuthCallback: (sessionId: string) => Promise<void> }).handleOAuthCallback(sessionId);
          }

          setCallbackState({
            status: 'success',
            message: 'Welcome! Authentication complete.'
          });

          // Redirect to main app after successful authentication
          setTimeout(() => {
            router.push('/');
          }, 1500); // Reduced timeout for better UX
          
          return;
        }

        // If no session info, this might be an error case
        setCallbackState({
          status: 'error',
          message: 'Authentication failed',
          error: 'No session information received from OAuth callback'
        });

      } catch (error) {
        console.error('OAuth callback error:', error);
        setCallbackState({
          status: 'error',
          message: 'Authentication failed',
          error: error instanceof Error ? error.message : 'Unknown error occurred'
        });
      }
    };

    handleOAuthCallback();
  }, [searchParams, router, callbackState.status]);

  // Auto-retry on error after delay
  useEffect(() => {
    if (callbackState.status === 'error') {
      const retryTimer = setTimeout(() => {
        router.push('/');
      }, 5000);

      return () => clearTimeout(retryTimer);
    }
  }, [callbackState.status, router]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md text-center">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            📧 Voice Email Agent
          </h1>
          <p className="text-gray-600">
            Completing authentication...
          </p>
        </div>

        {/* Status Display */}
        <div className="mb-6">
          {callbackState.status === 'processing' && (
            <div className="flex flex-col items-center space-y-4">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
              <p className="text-blue-600 font-medium">{callbackState.message}</p>
            </div>
          )}

          {callbackState.status === 'success' && (
            <div className="flex flex-col items-center space-y-4">
              <div className="text-6xl">✅</div>
              <p className="text-green-600 font-medium">{callbackState.message}</p>
              <p className="text-sm text-gray-500">Redirecting to the app...</p>
            </div>
          )}

          {callbackState.status === 'error' && (
            <div className="flex flex-col items-center space-y-4">
              <div className="text-6xl">❌</div>
              <p className="text-red-600 font-medium">{callbackState.message}</p>
              {callbackState.error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-left w-full">
                  <p className="text-sm text-red-700">{callbackState.error}</p>
                </div>
              )}
              <p className="text-sm text-gray-500">Redirecting back in 5 seconds...</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        {callbackState.status === 'error' && (
          <div className="space-y-3">
            <button
              onClick={() => router.push('/')}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Return to App
            </button>
            <button
              onClick={() => window.location.reload()}
              className="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Debug Information (only in development) */}
        {process.env.NODE_ENV === 'development' && (
          <details className="mt-6 text-left">
            <summary className="text-xs text-gray-500 cursor-pointer">Debug Info</summary>
            <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
              <p><strong>Code:</strong> {searchParams.get('code') ? 'Present' : 'Missing'}</p>
              <p><strong>State:</strong> {searchParams.get('state') || 'None'}</p>
              <p><strong>Error:</strong> {searchParams.get('error') || 'None'}</p>
              <p><strong>Auth State:</strong> {authState.isAuthenticated ? 'Authenticated' : 'Not authenticated'}</p>
            </div>
          </details>
        )}
      </div>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    }>
      <OAuthCallbackContent />
    </Suspense>
  );
}
