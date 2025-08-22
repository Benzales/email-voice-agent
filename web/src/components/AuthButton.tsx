/**
 * Authentication Button Component
 * Handles login/logout UI and user profile display
 */

'use client';

import { useAuth } from '@/hooks/useAuth';

interface AuthButtonProps {
  className?: string;
  showProfile?: boolean;
}

export default function AuthButton({ className = '', showProfile = true }: AuthButtonProps) {
  const [authState, authOperations] = useAuth();

  // Loading state
  if (authState.isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
        <span className="text-sm text-gray-600">Loading...</span>
      </div>
    );
  }

  // Error state
  if (authState.error) {
    return (
      <div className={`flex flex-col space-y-2 ${className}`}>
        <div className="flex items-center space-x-2 text-red-600 text-sm">
          <span>❌</span>
          <span>{authState.error}</span>
        </div>
        <button
          onClick={authOperations.clearError}
          className="text-xs text-blue-600 hover:text-blue-800 underline"
        >
          Clear error
        </button>
      </div>
    );
  }

  // Authenticated state
  if (authState.isAuthenticated && authState.user) {
    return (
      <div className={`flex items-center space-x-3 ${className}`}>
        {showProfile && (
          <div className="flex items-center space-x-2">
            {authState.user.picture && (
              <img
                src={authState.user.picture}
                alt={authState.user.name || authState.user.email}
                className="w-8 h-8 rounded-full border-2 border-green-500"
              />
            )}
            <div className="flex flex-col">
              <span className="text-sm font-medium text-gray-900">
                {authState.user.name || 'User'}
              </span>
              <span className="text-xs text-gray-500">
                {authState.user.email}
              </span>
            </div>
          </div>
        )}
        
        <button
          onClick={authOperations.logout}
          disabled={authState.isLoading}
          className="bg-red-600 hover:bg-red-700 disabled:bg-red-300 text-white text-sm font-medium py-2 px-4 rounded-lg transition-colors duration-200"
        >
          Sign Out
        </button>
      </div>
    );
  }

  // Unauthenticated state
  return (
    <div className={`flex flex-col space-y-3 ${className}`}>
      <button
        onClick={authOperations.login}
        disabled={authState.isLoading}
        className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 px-6 rounded-lg transition-all duration-200 transform hover:scale-105 disabled:hover:scale-100 flex items-center space-x-2"
      >
        <svg className="w-5 h-5" viewBox="0 0 24 24">
          <path
            fill="currentColor"
            d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
          />
          <path
            fill="currentColor"
            d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
          />
          <path
            fill="currentColor"
            d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
          />
          <path
            fill="currentColor"
            d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
          />
        </svg>
        <span>Sign in with Google</span>
      </button>
      
      <p className="text-xs text-gray-500 text-center">
        Sign in to access your Gmail and use voice commands
      </p>
    </div>
  );
}

/**
 * Compact version of AuthButton for use in headers/navbars
 */
export function CompactAuthButton({ className = '' }: { className?: string }) {
  const [authState, authOperations] = useAuth();

  if (authState.isLoading) {
    return (
      <div className={`animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 ${className}`}></div>
    );
  }

  if (authState.isAuthenticated && authState.user) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        {authState.user.picture && (
          <img
            src={authState.user.picture}
            alt={authState.user.name || authState.user.email}
            className="w-6 h-6 rounded-full border border-green-500"
          />
        )}
        <button
          onClick={authOperations.logout}
          className="text-sm text-red-600 hover:text-red-800 font-medium"
        >
          Sign Out
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={authOperations.login}
      disabled={authState.isLoading}
      className={`bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium py-1 px-3 rounded transition-colors ${className}`}
    >
      Sign In
    </button>
  );
}

/**
 * User Profile Display Component
 */
export function UserProfile({ className = '' }: { className?: string }) {
  const [authState] = useAuth();

  if (!authState.isAuthenticated || !authState.user) {
    return null;
  }

  const user = authState.user;
  const expiresAt = authState.expiresAt ? new Date(authState.expiresAt) : null;
  const isExpiringSoon = expiresAt ? expiresAt.getTime() - Date.now() < 30 * 60 * 1000 : false; // 30 minutes

  return (
    <div className={`bg-green-50 border border-green-200 rounded-lg p-4 ${className}`}>
      <div className="flex items-center space-x-3">
        {user.picture && (
          <img
            src={user.picture}
            alt={user.name || user.email}
            className="w-12 h-12 rounded-full border-2 border-green-500"
          />
        )}
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900">
            {user.name || 'User'}
          </h3>
          <p className="text-sm text-gray-600">{user.email}</p>
          {user.verified_email && (
            <div className="flex items-center space-x-1 mt-1">
              <span className="text-xs text-green-600">✓</span>
              <span className="text-xs text-green-600">Verified</span>
            </div>
          )}
        </div>
      </div>
      
      {expiresAt && (
        <div className="mt-3 pt-3 border-t border-green-200">
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Session expires:</span>
            <span className={isExpiringSoon ? 'text-orange-600 font-medium' : 'text-gray-600'}>
              {expiresAt.toLocaleString()}
            </span>
          </div>
          {isExpiringSoon && (
            <p className="text-xs text-orange-600 mt-1">
              ⚠️ Session expires soon
            </p>
          )}
        </div>
      )}
    </div>
  );
}
