"""
Pydantic models for WebSocket message types and API contracts
Provides type safety for communication between frontend and backend
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from enum import Enum


# Enums for message types
class MessageType(str, Enum):
    # Frontend → Backend
    AUDIO_CHUNK = "audio_chunk"
    START_SESSION = "start_session"
    STOP_SESSION = "stop_session"
    
    # Backend → Frontend  
    AUDIO_RESPONSE = "audio_response"
    AUDIO_INTERRUPTED = "audio_interrupted"
    AUDIO_STATUS = "audio_status"
    ERROR = "error"
    SESSION_STATUS = "session_status"


class SessionStatus(str, Enum):
    INITIALIZING = "initializing"
    READY = "ready"
    ACTIVE = "active" 
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class AudioStatus(str, Enum):
    STARTED = "started"
    STOPPED = "stopped"
    ERROR = "error"


# Base WebSocket message model
class WebSocketMessage(BaseModel):
    type: MessageType
    timestamp: Optional[float] = None


# Frontend → Backend Messages
class AudioChunkMessage(WebSocketMessage):
    """Audio data from frontend microphone"""
    type: MessageType = MessageType.AUDIO_CHUNK
    data: bytes = Field(..., description="Raw audio data in PCM format")


class StartSessionMessage(WebSocketMessage):
    """Start a new email processing session"""
    type: MessageType = MessageType.START_SESSION
    email_query: Optional[str] = Field(default="in:inbox", description="Gmail search query")
    max_results: Optional[int] = Field(default=50, description="Maximum emails to process")


class StopSessionMessage(WebSocketMessage):
    """Stop the current session"""
    type: MessageType = MessageType.STOP_SESSION
    reason: Optional[str] = Field(default="user_requested", description="Reason for stopping")


# Backend → Frontend Messages  
class AudioResponseMessage(WebSocketMessage):
    """Audio response from Gemini Live"""
    type: MessageType = MessageType.AUDIO_RESPONSE
    data: bytes = Field(..., description="Audio data for playback")


class AudioInterruptedMessage(WebSocketMessage):
    """Audio stream was interrupted"""
    type: MessageType = MessageType.AUDIO_INTERRUPTED


class AudioStatusMessage(WebSocketMessage):
    """Audio streaming status update"""
    type: MessageType = MessageType.AUDIO_STATUS
    status: AudioStatus
    message: Optional[str] = None


class ErrorMessage(WebSocketMessage):
    """Error occurred during processing"""
    type: MessageType = MessageType.ERROR
    message: str = Field(..., description="Error description")
    recoverable: bool = Field(default=True, description="Whether the error is recoverable")
    details: Optional[Dict[str, Any]] = None


class SessionStatusMessage(WebSocketMessage):
    """Session status update"""
    type: MessageType = MessageType.SESSION_STATUS
    status: SessionStatus
    message: Optional[str] = None
    progress: Optional[Dict[str, int]] = None  # {"current": 1, "total": 5, "remaining": 4}


# Email-related models
class EmailInfo(BaseModel):
    """Email information"""
    id: str = Field(..., description="Gmail message ID")
    sender: str = Field(..., description="Email sender")
    subject: str = Field(..., description="Email subject")
    date: Optional[str] = None
    display_text: str = Field(..., description="Formatted display text")


class ProgressInfo(BaseModel):
    """Email processing progress"""
    current: int = Field(..., description="Current email number (1-based)")
    total: int = Field(..., description="Total number of emails")
    remaining: int = Field(..., description="Remaining emails to process")


# API Response models (for potential REST endpoints)
class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    timestamp: float
    services: Dict[str, bool] = Field(default_factory=dict)  # {"mcp": True, "gemini": True}


class SessionInfoResponse(BaseModel):
    """Current session information"""
    active: bool
    status: SessionStatus
    current_email: Optional[EmailInfo] = None
    progress: Optional[ProgressInfo] = None
    started_at: Optional[float] = None


# Configuration models
class SessionConfig(BaseModel):
    """Configuration for email processing session"""
    email_query: str = Field(default="in:inbox", description="Gmail search query")
    max_results: int = Field(default=50, description="Maximum emails to fetch")
    session_timeout: float = Field(default=120.0, description="Session timeout in seconds")
    audio_format: str = Field(default="audio/pcm;rate=16000", description="Audio format")


# Union types for message parsing
WebSocketMessageUnion = Union[
    AudioChunkMessage,
    StartSessionMessage, 
    StopSessionMessage,
    AudioResponseMessage,
    AudioInterruptedMessage,
    AudioStatusMessage,
    ErrorMessage,
    SessionStatusMessage
]


# Helper functions for message creation
def create_error_message(message: str, recoverable: bool = True, details: Optional[Dict[str, Any]] = None) -> ErrorMessage:
    """Create a standardized error message"""
    return ErrorMessage(
        message=message,
        recoverable=recoverable,
        details=details
    )


def create_session_status_message(status: SessionStatus, message: Optional[str] = None, progress: Optional[Dict[str, int]] = None) -> SessionStatusMessage:
    """Create a session status message"""
    return SessionStatusMessage(
        status=status,
        message=message,
        progress=progress
    )


def create_audio_status_message(status: AudioStatus, message: Optional[str] = None) -> AudioStatusMessage:
    """Create an audio status message"""
    return AudioStatusMessage(
        status=status,
        message=message
    )


# Validation helpers
def validate_audio_chunk(data: bytes) -> bool:
    """Validate audio chunk data"""
    if not data:
        return False
    
    # Audio chunks should be reasonably sized
    # For 16kHz PCM at ~5ms intervals, expect roughly 160 bytes per chunk
    if len(data) < 10 or len(data) > 10000:
        return False
    
    return True


def parse_websocket_message(message_data: Union[str, bytes]) -> Optional[WebSocketMessage]:
    """
    Parse incoming WebSocket message
    
    Args:
        message_data: Raw message data from WebSocket
        
    Returns:
        Parsed WebSocketMessage or None if parsing fails
    """
    try:
        if isinstance(message_data, bytes):
            # Assume raw audio data
            return AudioChunkMessage(data=message_data)
        
        elif isinstance(message_data, str):
            # Parse JSON message
            import json
            data = json.loads(message_data)
            message_type = data.get("type")
            
            if message_type == MessageType.START_SESSION:
                return StartSessionMessage(**data)
            elif message_type == MessageType.STOP_SESSION:
                return StopSessionMessage(**data)
            elif message_type == MessageType.AUDIO_CHUNK:
                # Audio data in JSON format
                return AudioChunkMessage(**data)
            else:
                print(f"Unknown message type: {message_type}")
                return None
    
    except Exception as e:
        print(f"Failed to parse WebSocket message: {e}")
        return None
