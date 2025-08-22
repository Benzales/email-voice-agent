# Gmail OAuth Implementation Plan

## Overview

This document outlines the implementation plan for adding a user-facing Gmail OAuth flow to the Voice Email Agent web application. Currently, the app relies on pre-authenticated credentials stored globally via the MCP server. We will add a proper OAuth flow that allows users to authenticate directly through the web interface.

## Current State Analysis

### Current Authentication Flow
1. **MCP Server**: Uses `@gongrzhe/server-gmail-autoauth-mcp` with global credentials in `~/.gmail-mcp/`
2. **Backend**: FastAPI server connects to MCP server (assumes authentication is already done)
3. **Frontend**: Next.js app has no authentication UI - assumes backend has Gmail access
4. **Credentials**: `credentials.json` file in project root (gitignored) + global MCP credentials

### Current Architecture
```
Web Frontend → FastAPI Backend → MCP Gmail Server → Gmail API
     ↑                ↑               ↑
No Auth UI    No Auth Logic    Pre-authenticated
```

## Target Architecture

### New OAuth Flow
```
Web Frontend → FastAPI Backend → Google OAuth → Gmail API
     ↑              ↑                ↑
OAuth UI      OAuth Logic       User Consent
```

### User Experience Flow
1. **Landing Page**: User sees "Sign in with Google" button
2. **OAuth Flow**: User redirected to Google for consent
3. **Callback**: User returned to app with authorization code
4. **Token Exchange**: Backend exchanges code for access/refresh tokens
5. **Session Management**: Frontend shows authenticated state
6. **Voice Session**: User can now use voice commands with their Gmail

## Implementation Plan

### Phase 1: Backend OAuth Integration

#### 1.1 Dependencies and Configuration
- **Add OAuth Dependencies**:
  ```bash
  uv add google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
  ```
- **Environment Variables** (`.env`):
  ```
  GOOGLE_CLIENT_ID=your_client_id
  GOOGLE_CLIENT_SECRET=your_client_secret
  GOOGLE_REDIRECT_URI=http://localhost:3000/auth/callback
  ```
- **Update `credentials.json`**: Ensure it's configured as "Web application" type with proper redirect URIs

#### 1.2 OAuth Service Implementation
- **File**: `oauth_service.py`
- **Features**:
  - Generate OAuth authorization URLs
  - Handle authorization code exchange
  - Manage access/refresh tokens
  - Token refresh logic
  - User session management
  - Gmail API client creation with user tokens

#### 1.3 User Session Management
- **File**: `user_session.py`
- **Features**:
  - Store user OAuth tokens (in-memory or database)
  - Session validation
  - Token refresh handling
  - User logout functionality

#### 1.4 FastAPI Endpoints
- **New Endpoints**:
  - `GET /auth/login` - Initiate OAuth flow
  - `POST /auth/callback` - Handle OAuth callback
  - `GET /auth/status` - Check authentication status
  - `POST /auth/logout` - Clear user session
  - `GET /auth/user-info` - Get authenticated user info

#### 1.5 Modified Email Service
- **Update `email_service.py`**:
  - Accept user-specific Gmail client instead of global MCP agent
  - Create Gmail service with user's OAuth tokens
  - Handle token refresh during operations

### Phase 2: Frontend OAuth Integration

#### 2.1 Authentication State Management
- **File**: `hooks/useAuth.ts`
- **Features**:
  - Authentication state management
  - Login/logout functions
  - Token refresh handling
  - User information storage

#### 2.2 OAuth Components
- **File**: `components/AuthButton.tsx`
- **Features**:
  - "Sign in with Google" button
  - Loading states during OAuth flow
  - User profile display when authenticated
  - Logout functionality

#### 2.3 Protected Routes
- **File**: `components/ProtectedRoute.tsx`
- **Features**:
  - Redirect unauthenticated users to login
  - Show loading state during auth check
  - Handle authentication errors

#### 2.4 OAuth Callback Page
- **File**: `app/auth/callback/page.tsx`
- **Features**:
  - Handle OAuth callback from Google
  - Extract authorization code from URL
  - Send code to backend for token exchange
  - Redirect to main app on success

### Phase 3: Integration and Migration

#### 3.1 Dual Authentication Support
- **Backwards Compatibility**:
  - Support both MCP-based auth (development) and OAuth (production)
  - Environment variable to toggle authentication modes
  - Graceful fallback for existing setups

#### 3.2 Updated Voice Session Flow
- **Modified `useVoiceSession.ts`**:
  - Check authentication status before connecting
  - Pass user tokens to backend for Gmail operations
  - Handle authentication errors during voice sessions

#### 3.3 UI/UX Updates
- **Landing Page**:
  - Show authentication status
  - "Sign in with Google" for unauthenticated users
  - User profile and logout for authenticated users
- **Voice Interface**:
  - Show authenticated user's email
  - Display Gmail account information
  - Handle authentication expiry gracefully

### Phase 4: Production Deployment

#### 4.1 Google Cloud Console Setup
- **OAuth Consent Screen**:
  - Configure for external users
  - Add required scopes: `https://www.googleapis.com/auth/gmail.modify`
  - Set up proper branding and privacy policy
- **OAuth Credentials**:
  - Create "Web application" OAuth client
  - Configure authorized redirect URIs for production domain
  - Download updated `credentials.json`

#### 4.2 Environment Configuration
- **Production Environment Variables**:
  ```
  GOOGLE_CLIENT_ID=production_client_id
  GOOGLE_CLIENT_SECRET=production_client_secret
  GOOGLE_REDIRECT_URI=https://yourdomain.com/auth/callback
  AUTH_MODE=oauth  # vs 'mcp' for development
  ```

#### 4.3 Security Considerations
- **HTTPS Only**: Ensure all OAuth flows use HTTPS in production
- **Secure Token Storage**: Consider database storage for user tokens
- **PKCE Implementation**: Add Proof Key for Code Exchange for enhanced security
- **Rate Limiting**: Implement rate limiting on OAuth endpoints
- **Session Management**: Secure session cookies with proper flags

## File Structure Changes

### New Files
```
backend/
├── oauth_service.py          # OAuth flow management
├── user_session.py           # User session management
└── models/
    └── auth_models.py        # OAuth-related Pydantic models

frontend/src/
├── hooks/
│   └── useAuth.ts           # Authentication state management
├── components/
│   ├── AuthButton.tsx       # Login/logout button
│   ├── ProtectedRoute.tsx   # Route protection
│   └── UserProfile.tsx      # User profile display
└── app/auth/callback/
    └── page.tsx             # OAuth callback handler
```

### Modified Files
```
backend/
├── fastapi_server.py        # Add OAuth endpoints
├── email_service.py         # User-specific Gmail clients
├── models.py                # Add auth-related models
└── requirements-fastapi.txt # Add OAuth dependencies

frontend/src/
├── components/VoiceEmailAgent.tsx  # Add authentication UI
├── hooks/useVoiceSession.ts        # Auth-aware session management
└── app/page.tsx                    # Landing page with auth
```

## Implementation Timeline

### Week 1: Backend OAuth Foundation
- [ ] Set up OAuth dependencies
- [ ] Implement `oauth_service.py`
- [ ] Create OAuth endpoints in FastAPI
- [ ] Test OAuth flow with Postman/curl

### Week 2: Frontend OAuth Integration
- [ ] Implement `useAuth` hook
- [ ] Create authentication components
- [ ] Add OAuth callback page
- [ ] Test full OAuth flow

### Week 3: Integration and Testing
- [ ] Integrate OAuth with voice session
- [ ] Update email service for user-specific clients
- [ ] Add dual authentication support
- [ ] End-to-end testing

### Week 4: Production Deployment
- [ ] Configure Google Cloud Console
- [ ] Set up production environment
- [ ] Security review and hardening
- [ ] Deploy and test in production

## Technical Considerations

### Security
- **Token Storage**: Initially in-memory, consider Redis/database for production
- **HTTPS Enforcement**: Required for OAuth in production
- **CSRF Protection**: Use state parameter in OAuth flow
- **Token Refresh**: Implement automatic refresh token handling

### User Experience
- **Seamless Flow**: Minimize redirects and loading states
- **Error Handling**: Clear error messages for OAuth failures
- **Progressive Enhancement**: App works without JavaScript for initial auth
- **Mobile Support**: Ensure OAuth flow works on mobile devices

### Performance
- **Token Caching**: Cache valid tokens to avoid unnecessary API calls
- **Concurrent Sessions**: Support multiple users simultaneously
- **Rate Limiting**: Respect Gmail API rate limits per user

### Monitoring
- **OAuth Metrics**: Track success/failure rates of OAuth flows
- **Error Logging**: Detailed logging for OAuth failures
- **User Analytics**: Track authentication funnel

## Success Criteria

### Functional Requirements
- [ ] Users can sign in with their Google account
- [ ] Voice sessions work with user's personal Gmail
- [ ] Multiple users can use the app simultaneously
- [ ] Tokens refresh automatically without user intervention
- [ ] Users can sign out and sign back in

### Technical Requirements
- [ ] Secure OAuth implementation following best practices
- [ ] Backwards compatibility with existing MCP setup
- [ ] Production-ready deployment configuration
- [ ] Comprehensive error handling and logging

### User Experience Requirements
- [ ] Intuitive authentication flow
- [ ] Clear indication of authentication status
- [ ] Graceful handling of authentication errors
- [ ] Responsive design for all screen sizes

## Risk Mitigation

### OAuth Flow Failures
- **Mitigation**: Comprehensive error handling and user-friendly error messages
- **Fallback**: Clear instructions for users to retry or contact support

### Token Expiry
- **Mitigation**: Automatic refresh token handling with graceful degradation
- **Fallback**: Prompt user to re-authenticate when refresh fails

### Google API Changes
- **Mitigation**: Use official Google client libraries and stay updated
- **Monitoring**: Set up alerts for API errors and changes

### Production Deployment Issues
- **Mitigation**: Thorough testing in staging environment
- **Rollback Plan**: Ability to quickly revert to MCP-based authentication

## Future Enhancements

### Advanced Features
- **Multi-Account Support**: Allow users to connect multiple Gmail accounts
- **Account Switching**: Quick switching between authenticated accounts
- **Granular Permissions**: Request only necessary Gmail scopes
- **Offline Support**: Handle offline scenarios gracefully

### Enterprise Features
- **Google Workspace Integration**: Support for organization accounts
- **Admin Controls**: Enterprise admin controls for app usage
- **Audit Logging**: Detailed audit logs for enterprise customers

### Developer Experience
- **OAuth Testing Tools**: Development tools for testing OAuth flows
- **Documentation**: Comprehensive OAuth setup documentation
- **Debug Mode**: Enhanced debugging for OAuth issues

This implementation plan provides a comprehensive roadmap for adding Gmail OAuth to the Voice Email Agent, ensuring security, usability, and maintainability while preserving the existing functionality.
