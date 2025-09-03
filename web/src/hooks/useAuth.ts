/**
 * Authentication hook for managing OAuth state and operations
 * Handles login, logout, session management, and authentication status
 */

'use client';

import { useState, useEffect, useCallback } from 'react';

// Types for authentication
interface User {
  id: string;
  email: string;
  name?: string;
  picture?: string;
  verified_email: boolean;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  sessionId: string | null;
  expiresAt: string | null;
  scopes: string[];
  isLoading: boolean;
  error: string | null;
}

interface AuthOperations {
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refreshStatus: () => Promise<void>;
  clearError: () => void;
}

import { BACKEND_URL } from '@/config/backend';

export function useAuth(): [AuthState, AuthOperations] {
  const [authState, setAuthState] = useState<AuthState>({
    isAuthenticated: false,
    user: null,
    sessionId: null,
    expiresAt: null,
    scopes: [],
    isLoading: true,
    error: null,
  });

  // Helper to update auth state
  const updateAuthState = useCallback((updates: Partial<AuthState>) => {
    setAuthState(prev => ({ ...prev, ...updates }));
  }, []);

  // Get session ID from localStorage
  const getStoredSessionId = useCallback((): string | null => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('auth_session_id');
  }, []);

  // Store session ID in localStorage
  const storeSessionId = useCallback((sessionId: string | null) => {
    if (typeof window === 'undefined') return;
    if (sessionId) {
      localStorage.setItem('auth_session_id', sessionId);
    } else {
      localStorage.removeItem('auth_session_id');
    }
  }, []);

  // Create authorization header
  const createAuthHeader = useCallback((sessionId: string) => ({
    'Authorization': `Bearer ${sessionId}`,
    'Content-Type': 'application/json',
  }), []);

  // Check authentication status
  const checkAuthStatus = useCallback(async (sessionId?: string): Promise<void> => {
    const currentSessionId = sessionId || getStoredSessionId();
    
    console.log('🔍 Checking auth status with session ID:', currentSessionId?.substring(0, 8) + '...' || 'None');
    
    if (!currentSessionId) {
      console.log('❌ No session ID found, setting unauthenticated state');
      updateAuthState({
        isAuthenticated: false,
        user: null,
        sessionId: null,
        expiresAt: null,
        scopes: [],
        isLoading: false,
        error: null,
      });
      return;
    }

    try {
      const response = await fetch(`${BACKEND_URL}/auth/status`, {
        headers: createAuthHeader(currentSessionId),
      });

      if (response.ok) {
        const data = await response.json();
        
        console.log('📡 Auth status response:', data.status);
        
        if (data.status === 'authenticated') {
          console.log('✅ Authentication successful for user:', data.user?.email);
          updateAuthState({
            isAuthenticated: true,
            user: data.user,
            sessionId: currentSessionId,
            expiresAt: data.expires_at,
            scopes: data.scopes || [],
            isLoading: false,
            error: null,
          });
        } else {
          console.log('❌ Authentication failed, status:', data.status);
          // Session invalid or expired
          storeSessionId(null);
          updateAuthState({
            isAuthenticated: false,
            user: null,
            sessionId: null,
            expiresAt: null,
            scopes: [],
            isLoading: false,
            error: data.status === 'expired' ? 'Session expired' : 'Authentication required',
          });
        }
      } else {
        // API error
        storeSessionId(null);
        updateAuthState({
          isAuthenticated: false,
          user: null,
          sessionId: null,
          expiresAt: null,
          scopes: [],
          isLoading: false,
          error: 'Failed to check authentication status',
        });
      }
    } catch (error) {
      console.error('Auth status check failed:', error);
      // If it's a network error, don't clear the session ID immediately
      // The user might be temporarily offline
      updateAuthState({
        isLoading: false,
        error: 'Network error checking authentication',
        isAuthenticated: false, // But still mark as not authenticated for UI purposes
      });
    }
  }, [getStoredSessionId, createAuthHeader, updateAuthState, storeSessionId]);

  // Initiate login flow
  const login = useCallback(async (): Promise<void> => {
    try {
      updateAuthState({ isLoading: true, error: null });

      const response = await fetch(`${BACKEND_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          redirect_uri: `${BACKEND_URL}/auth/callback`
        }),
      });

      if (response.ok) {
        const data = await response.json();
        
        // Store state for CSRF protection
        if (data.state) {
          sessionStorage.setItem('oauth_state', data.state);
        }
        
        // Redirect to Google OAuth
        window.location.href = data.authorization_url;
      } else {
        const errorData = await response.json();
        updateAuthState({
          isLoading: false,
          error: errorData.detail || 'Failed to initiate login',
        });
      }
    } catch (error) {
      console.error('Login failed:', error);
      updateAuthState({
        isLoading: false,
        error: 'Network error during login',
      });
    }
  }, [updateAuthState]);

  // Handle logout
  const logout = useCallback(async (): Promise<void> => {
    const sessionId = getStoredSessionId();
    
    try {
      updateAuthState({ isLoading: true, error: null });

      if (sessionId) {
        // Call logout endpoint
        await fetch(`${BACKEND_URL}/auth/logout`, {
          method: 'POST',
          headers: createAuthHeader(sessionId),
        });
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local logout even if API fails
    }

    // Clear local state regardless of API success
    storeSessionId(null);
    sessionStorage.removeItem('oauth_state');
    
    updateAuthState({
      isAuthenticated: false,
      user: null,
      sessionId: null,
      expiresAt: null,
      scopes: [],
      isLoading: false,
      error: null,
    });
  }, [getStoredSessionId, createAuthHeader, updateAuthState, storeSessionId]);

  // Refresh authentication status
  const refreshStatus = useCallback(async (): Promise<void> => {
    updateAuthState({ isLoading: true, error: null });
    await checkAuthStatus();
  }, [checkAuthStatus, updateAuthState]);

  // Clear error state
  const clearError = useCallback(() => {
    updateAuthState({ error: null });
  }, [updateAuthState]);

  // Handle OAuth callback completion
  const handleOAuthCallback = useCallback(async (sessionId: string): Promise<void> => {
    console.log('🔑 OAuth callback received session ID:', sessionId?.substring(0, 8) + '...');
    
    // Ensure we're not in loading state during callback
    updateAuthState({ isLoading: true, error: null });
    
    storeSessionId(sessionId);
    console.log('💾 Session ID stored in localStorage');
    
    // Small delay to ensure localStorage is updated
    await new Promise(resolve => setTimeout(resolve, 100));
    
    await checkAuthStatus(sessionId);
    console.log('✅ Auth status checked after OAuth callback');
  }, [storeSessionId, checkAuthStatus, updateAuthState]);

  // Check authentication status on mount only
  useEffect(() => {
    const initialCheck = async () => {
      const sessionId = getStoredSessionId();
      if (sessionId) {
        await checkAuthStatus(sessionId);
      } else {
        updateAuthState({ isLoading: false });
      }
    };
    initialCheck();
  }, []); // Empty dependency array to run only once

  // Set up periodic token refresh
  useEffect(() => {
    if (!authState.isAuthenticated || !authState.expiresAt) return;

    const expiryTime = new Date(authState.expiresAt).getTime();
    const currentTime = Date.now();
    const timeUntilExpiry = expiryTime - currentTime;

    // Refresh 5 minutes before expiry
    const refreshTime = Math.max(0, timeUntilExpiry - 5 * 60 * 1000);

    const refreshTimer = setTimeout(() => {
      console.log('🔄 Refreshing authentication status...');
      checkAuthStatus();
    }, refreshTime);

    return () => clearTimeout(refreshTimer);
  }, [authState.isAuthenticated, authState.expiresAt, checkAuthStatus]);

  const operations: AuthOperations = {
    login,
    logout,
    refreshStatus,
    clearError,
  };

  // Expose handleOAuthCallback for callback page
  (operations as typeof operations & { handleOAuthCallback: typeof handleOAuthCallback }).handleOAuthCallback = handleOAuthCallback;

  return [authState, operations];
}
