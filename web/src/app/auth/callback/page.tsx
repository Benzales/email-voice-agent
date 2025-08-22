/**
 * OAuth Callback Page
 * Handles the OAuth callback from Google and completes the authentication flow
 */

'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface CallbackState {
  status: 'processing' | 'success' | 'error';
  message: string;
  error?: string;
}

export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [authState, authOperations] = useAuth();
  const [callbackState, setCallbackState] = useState<CallbackState>({
    status: 'processing',
    message: 'Processing authentication...'
  });

  useEffect(() => {
    const handleOAuthCallback = async () => {
      try {
        // Extract parameters from URL
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        // Handle OAuth error
        if (error) {
          setCallbackState({
            status: 'error',
            message: 'Authentication failed',
            error: `Google OAuth error: ${error}`
          });
          return;
        }

        // Validate required parameters
        if (!code) {
          setCallbackState({
            status: 'error',
            message: 'Authentication failed',
            error: 'No authorization code received from Google'
          });
          return;
        }

        // Verify state parameter (CSRF protection)
        const storedState = sessionStorage.getItem('oauth_state');
        if (state && storedState && state !== storedState) {
          setCallbackState({
            status: 'error',
            message: 'Authentication failed',
            error: 'Invalid state parameter - possible CSRF attack'
          });
          return;
        }

        // Exchange authorization code for session
        setCallbackState({
          status: 'processing',
          message: 'Exchanging authorization code...'
        });

        const response = await fetch(`${BACKEND_URL}/auth/callback`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            code,
            state: state || undefined,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to exchange authorization code');
        }

        const data = await response.json();

        if (!data.success || !data.session_id) {
          throw new Error('Invalid response from authentication server');
        }

        // Store session and update auth state
        setCallbackState({
          status: 'processing',
          message: 'Authentication successful! Redirecting...'
        });

        // Clean up OAuth state
        sessionStorage.removeItem('oauth_state');

        // Use the auth hook to handle the callback
        if ((authOperations as any).handleOAuthCallback) {
          await (authOperations as any).handleOAuthCallback(data.session_id);
        }

        setCallbackState({
          status: 'success',
          message: `Welcome, ${data.user?.name || data.user?.email || 'User'}!`
        });

        // Redirect to main app after successful authentication
        setTimeout(() => {
          router.push('/');
        }, 2000);

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
  }, [searchParams, router, authOperations]);

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
