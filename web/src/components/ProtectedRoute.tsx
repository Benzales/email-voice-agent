/**
 * Protected Route Component
 * Provides authentication guards and conditional rendering based on auth state
 */

'use client';

import { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import AuthButton from './AuthButton';

interface ProtectedRouteProps {
  children: ReactNode;
  fallback?: ReactNode;
  requireAuth?: boolean;
  showAuthUI?: boolean;
  className?: string;
}

/**
 * ProtectedRoute - Renders children only if user is authenticated
 * Shows authentication UI or custom fallback if not authenticated
 */
export default function ProtectedRoute({ 
  children, 
  fallback,
  requireAuth = true,
  showAuthUI = true,
  className = ''
}: ProtectedRouteProps) {
  const [authState] = useAuth();

  // Loading state
  if (authState.isLoading) {
    return (
      <div className={`flex items-center justify-center min-h-[200px] ${className}`}>
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="text-sm text-gray-600">Checking authentication...</p>
        </div>
      </div>
    );
  }

  // If authentication is not required, always show children
  if (!requireAuth) {
    return <div className={className}>{children}</div>;
  }

  // If authenticated, show children
  if (authState.isAuthenticated) {
    return <div className={className}>{children}</div>;
  }

  // Not authenticated - show fallback or auth UI
  if (fallback) {
    return <div className={className}>{fallback}</div>;
  }

  if (showAuthUI) {
    return (
      <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
        <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-6">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              🔐 Authentication Required
            </h2>
            <p className="text-gray-600">
              Please sign in to access your Gmail and use voice commands
            </p>
          </div>
          
          <AuthButton className="w-full" />
          
          {authState.error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-600">{authState.error}</p>
            </div>
          )}
        </div>
      </div>
    );
  }

  // No fallback or auth UI - return null
  return null;
}

/**
 * AuthGuard - Higher-order component wrapper for protected routes
 */
export function AuthGuard({ 
  children, 
  fallback,
  className = '' 
}: { 
  children: ReactNode; 
  fallback?: ReactNode;
  className?: string;
}) {
  return (
    <ProtectedRoute 
      requireAuth={true} 
      showAuthUI={true} 
      fallback={fallback}
      className={className}
    >
      {children}
    </ProtectedRoute>
  );
}

/**
 * ConditionalAuth - Shows different content based on auth state
 */
export function ConditionalAuth({
  authenticated,
  unauthenticated,
  loading,
  className = ''
}: {
  authenticated: ReactNode;
  unauthenticated: ReactNode;
  loading?: ReactNode;
  className?: string;
}) {
  const [authState] = useAuth();

  if (authState.isLoading && loading) {
    return <div className={className}>{loading}</div>;
  }

  if (authState.isLoading) {
    return (
      <div className={`flex items-center justify-center p-4 ${className}`}>
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className={className}>
      {authState.isAuthenticated ? authenticated : unauthenticated}
    </div>
  );
}

/**
 * AuthStatus - Simple component to display current auth status
 */
export function AuthStatus({ className = '' }: { className?: string }) {
  const [authState] = useAuth();

  return (
    <div className={`text-sm ${className}`}>
      {authState.isLoading && (
        <div className="flex items-center space-x-2 text-yellow-600">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600"></div>
          <span>Checking authentication...</span>
        </div>
      )}
      
      {!authState.isLoading && authState.isAuthenticated && (
        <div className="flex items-center space-x-2 text-green-600">
          <span>✅</span>
          <span>Authenticated as {authState.user?.email}</span>
        </div>
      )}
      
      {!authState.isLoading && !authState.isAuthenticated && (
        <div className="flex items-center space-x-2 text-red-600">
          <span>❌</span>
          <span>Not authenticated</span>
        </div>
      )}
      
      {authState.error && (
        <div className="flex items-center space-x-2 text-red-600 mt-1">
          <span>⚠️</span>
          <span>{authState.error}</span>
        </div>
      )}
    </div>
  );
}

/**
 * RequireScope - Only render children if user has required OAuth scopes
 */
export function RequireScope({
  scopes,
  children,
  fallback,
  className = ''
}: {
  scopes: string[];
  children: ReactNode;
  fallback?: ReactNode;
  className?: string;
}) {
  const [authState] = useAuth();

  if (!authState.isAuthenticated) {
    return fallback ? <div className={className}>{fallback}</div> : null;
  }

  const userScopes = authState.scopes || [];
  const hasRequiredScopes = scopes.every(scope => userScopes.includes(scope));

  if (!hasRequiredScopes) {
    return fallback ? (
      <div className={className}>{fallback}</div>
    ) : (
      <div className={`p-4 bg-yellow-50 border border-yellow-200 rounded-lg ${className}`}>
        <p className="text-sm text-yellow-700">
          ⚠️ Additional permissions required. Please re-authenticate to grant access.
        </p>
        <div className="mt-2">
          <AuthButton />
        </div>
      </div>
    );
  }

  return <div className={className}>{children}</div>;
}
