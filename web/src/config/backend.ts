/**
 * Backend configuration for Voice Email Agent
 * Handles environment-specific URLs for API and WebSocket connections
 */

// Production backend URLs (custom subdomain on owned domain)
const PRODUCTION_BACKEND_URL = 'https://api.courieragent.ai';
const PRODUCTION_WS_URL = 'wss://api.courieragent.ai/ws/voice-session';

// Development backend URLs (local development)
const DEVELOPMENT_BACKEND_URL = 'http://localhost:8000';
const DEVELOPMENT_WS_URL = 'ws://localhost:8000/ws/voice-session';

// Environment detection
const isDevelopment = process.env.NODE_ENV === 'development';
const isLocalBackend = process.env.NEXT_PUBLIC_USE_LOCAL_BACKEND === 'true';

// Default to production backend for better deployment experience
export const BACKEND_CONFIG = {
  // API URL (HTTP/HTTPS)
  API_URL: process.env.NEXT_PUBLIC_BACKEND_URL || 
           (isDevelopment && isLocalBackend ? DEVELOPMENT_BACKEND_URL : PRODUCTION_BACKEND_URL),
  
  // WebSocket URL (WS/WSS)  
  WS_URL: process.env.NEXT_PUBLIC_BACKEND_WS_URL || 
          (isDevelopment && isLocalBackend ? DEVELOPMENT_WS_URL : PRODUCTION_WS_URL),
};

// Export individual URLs for backward compatibility
export const BACKEND_URL = BACKEND_CONFIG.API_URL;
export const WEBSOCKET_URL = BACKEND_CONFIG.WS_URL;

// Debug logging in development
if (isDevelopment) {
  console.log('🔧 Backend Configuration:', {
    apiUrl: BACKEND_CONFIG.API_URL,
    wsUrl: BACKEND_CONFIG.WS_URL,
    useLocalBackend: isLocalBackend,
    environment: process.env.NODE_ENV,
  });
}
