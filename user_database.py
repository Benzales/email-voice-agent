"""
SQLite-based user tracking database service
Provides persistent storage for user information and login history
"""

import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from contextlib import asynccontextmanager

from models import UserInfo


@dataclass
class UserRecord:
    """Database record for a user"""
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    verified_email: bool = False
    first_login: Optional[datetime] = None
    last_login: Optional[datetime] = None
    total_logins: int = 0
    total_sessions: int = 0
    total_emails_processed: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serialized datetime fields"""
        data = asdict(self)
        # Convert datetime fields to ISO strings
        for field in ['first_login', 'last_login', 'created_at', 'updated_at']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserRecord':
        """Create UserRecord from dictionary with datetime parsing"""
        # Parse datetime fields
        for field in ['first_login', 'last_login', 'created_at', 'updated_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        return cls(**data)


@dataclass
class LoginRecord:
    """Database record for a login session"""
    id: Optional[int] = None
    user_id: str = ""
    session_id: str = ""
    login_time: Optional[datetime] = None
    logout_time: Optional[datetime] = None
    session_duration: Optional[int] = None  # seconds
    emails_processed: int = 0
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with serialized datetime fields"""
        data = asdict(self)
        # Convert datetime fields to ISO strings
        for field in ['login_time', 'logout_time']:
            if data[field]:
                data[field] = data[field].isoformat()
        return data


class UserDatabase:
    """
    SQLite database service for user tracking
    Provides persistent storage for user information and login history
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database service
        
        Args:
            db_path: Path to SQLite database file (auto-detects production vs development)
        """
        if db_path is None:
            # Auto-detect environment
            import os
            if os.getenv('ENVIRONMENT') == 'production':
                # Use persistent volume in production
                db_path = "/data/users.db"
                # Ensure data directory exists
                os.makedirs("/data", exist_ok=True)
            else:
                # Use local file in development
                db_path = "users.db"
        
        self.db_path = Path(db_path)
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """Initialize database and create tables"""
        async with self._lock:
            await self._create_tables()
            print(f"✅ User database initialized: {self.db_path}")
    
    @asynccontextmanager
    async def _get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        finally:
            if conn:
                conn.close()
    
    async def _create_tables(self):
        """Create database tables if they don't exist"""
        async with self._get_connection() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT,
                    picture TEXT,
                    verified_email BOOLEAN DEFAULT FALSE,
                    first_login TIMESTAMP,
                    last_login TIMESTAMP,
                    total_logins INTEGER DEFAULT 0,
                    total_sessions INTEGER DEFAULT 0,
                    total_emails_processed INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Login history table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS login_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    logout_time TIMESTAMP,
                    session_duration INTEGER,
                    emails_processed INTEGER DEFAULT 0,
                    user_agent TEXT,
                    ip_address TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_login_history_user_id ON login_history (user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_login_history_session_id ON login_history (session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_login_history_login_time ON login_history (login_time)")
            
            conn.commit()
    
    async def create_or_update_user(self, user_info: UserInfo) -> UserRecord:
        """
        Create new user or update existing user information
        
        Args:
            user_info: User information from OAuth
            
        Returns:
            UserRecord with updated information
        """
        async with self._lock:
            async with self._get_connection() as conn:
                now = datetime.now()
                
                # Check if user exists
                existing = conn.execute(
                    "SELECT * FROM users WHERE user_id = ?", 
                    (user_info.id,)
                ).fetchone()
                
                if existing:
                    # Update existing user
                    conn.execute("""
                        UPDATE users SET 
                            email = ?, name = ?, picture = ?, verified_email = ?,
                            last_login = ?, total_logins = total_logins + 1,
                            updated_at = ?
                        WHERE user_id = ?
                    """, (
                        user_info.email, user_info.name, user_info.picture, 
                        user_info.verified_email, now, now, user_info.id
                    ))
                    
                    # Get updated record
                    updated = conn.execute(
                        "SELECT * FROM users WHERE user_id = ?", 
                        (user_info.id,)
                    ).fetchone()
                    
                else:
                    # Create new user
                    conn.execute("""
                        INSERT INTO users (
                            user_id, email, name, picture, verified_email,
                            first_login, last_login, total_logins, created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
                    """, (
                        user_info.id, user_info.email, user_info.name, 
                        user_info.picture, user_info.verified_email,
                        now, now, now, now
                    ))
                    
                    # Get new record
                    updated = conn.execute(
                        "SELECT * FROM users WHERE user_id = ?", 
                        (user_info.id,)
                    ).fetchone()
                
                conn.commit()
                
                # Convert to UserRecord
                return self._row_to_user_record(updated)
    
    async def record_login(self, user_id: str, session_id: str, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> int:
        """
        Record a new login session
        
        Args:
            user_id: Google user ID
            session_id: Session ID
            user_agent: User agent string
            ip_address: IP address
            
        Returns:
            Login record ID
        """
        async with self._lock:
            async with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO login_history (user_id, session_id, user_agent, ip_address)
                    VALUES (?, ?, ?, ?)
                """, (user_id, session_id, user_agent, ip_address))
                
                conn.commit()
                return cursor.lastrowid
    
    async def record_logout(self, session_id: str, emails_processed: int = 0):
        """
        Record logout and session statistics
        
        Args:
            session_id: Session ID
            emails_processed: Number of emails processed in this session
        """
        async with self._lock:
            async with self._get_connection() as conn:
                now = datetime.now()
                
                # Update login record
                conn.execute("""
                    UPDATE login_history SET 
                        logout_time = ?,
                        session_duration = (
                            CASE 
                                WHEN login_time IS NOT NULL 
                                THEN CAST((julianday(?) - julianday(login_time)) * 86400 AS INTEGER)
                                ELSE NULL 
                            END
                        ),
                        emails_processed = ?
                    WHERE session_id = ? AND logout_time IS NULL
                """, (now, now, emails_processed, session_id))
                
                # Update user statistics
                conn.execute("""
                    UPDATE users SET 
                        total_sessions = total_sessions + 1,
                        total_emails_processed = total_emails_processed + ?,
                        updated_at = ?
                    WHERE user_id = (
                        SELECT user_id FROM login_history WHERE session_id = ?
                    )
                """, (emails_processed, now, session_id))
                
                conn.commit()
    
    async def get_user(self, user_id: str) -> Optional[UserRecord]:
        """
        Get user by ID
        
        Args:
            user_id: Google user ID
            
        Returns:
            UserRecord or None if not found
        """
        async with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", 
                (user_id,)
            ).fetchone()
            
            return self._row_to_user_record(row) if row else None
    
    async def get_all_users(self, limit: Optional[int] = None, offset: int = 0) -> List[UserRecord]:
        """
        Get all users with optional pagination
        
        Args:
            limit: Maximum number of users to return
            offset: Number of users to skip
            
        Returns:
            List of UserRecord objects
        """
        async with self._get_connection() as conn:
            query = "SELECT * FROM users ORDER BY last_login DESC"
            params = []
            
            if limit is not None:
                query += " LIMIT ? OFFSET ?"
                params = [limit, offset]
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_user_record(row) for row in rows]
    
    async def get_user_login_history(self, user_id: str, limit: int = 50) -> List[LoginRecord]:
        """
        Get login history for a user
        
        Args:
            user_id: Google user ID
            limit: Maximum number of records to return
            
        Returns:
            List of LoginRecord objects
        """
        async with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM login_history 
                WHERE user_id = ? 
                ORDER BY login_time DESC 
                LIMIT ?
            """, (user_id, limit)).fetchall()
            
            return [self._row_to_login_record(row) for row in rows]
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """
        Get overall user statistics
        
        Returns:
            Dictionary with user statistics
        """
        async with self._get_connection() as conn:
            # Total users
            total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            
            # Users in last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            recent_users = conn.execute(
                "SELECT COUNT(*) FROM users WHERE last_login > ?",
                (thirty_days_ago,)
            ).fetchone()[0]
            
            # Total sessions
            total_sessions = conn.execute("SELECT COUNT(*) FROM login_history").fetchone()[0]
            
            # Total emails processed
            total_emails = conn.execute("SELECT SUM(emails_processed) FROM login_history").fetchone()[0] or 0
            
            # Average session duration
            avg_duration = conn.execute("""
                SELECT AVG(session_duration) FROM login_history 
                WHERE session_duration IS NOT NULL
            """).fetchone()[0] or 0
            
            # Most active users
            active_users = conn.execute("""
                SELECT email, total_logins, total_sessions, total_emails_processed, last_login
                FROM users 
                ORDER BY total_logins DESC 
                LIMIT 10
            """).fetchall()
            
            return {
                "total_users": total_users,
                "recent_users_30_days": recent_users,
                "total_sessions": total_sessions,
                "total_emails_processed": total_emails,
                "average_session_duration_seconds": round(avg_duration or 0, 2),
                "most_active_users": [dict(row) for row in active_users]
            }
    
    async def cleanup_old_sessions(self, days: int = 90):
        """
        Clean up old login history records
        
        Args:
            days: Number of days to keep records
        """
        async with self._lock:
            async with self._get_connection() as conn:
                cutoff_date = datetime.now() - timedelta(days=days)
                
                cursor = conn.execute(
                    "DELETE FROM login_history WHERE login_time < ?",
                    (cutoff_date,)
                )
                
                conn.commit()
                
                if cursor.rowcount > 0:
                    print(f"🧹 Cleaned up {cursor.rowcount} old login records (older than {days} days)")
    
    def _row_to_user_record(self, row) -> UserRecord:
        """Convert SQLite row to UserRecord"""
        return UserRecord(
            user_id=row['user_id'],
            email=row['email'],
            name=row['name'],
            picture=row['picture'],
            verified_email=bool(row['verified_email']),
            first_login=datetime.fromisoformat(row['first_login']) if row['first_login'] else None,
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
            total_logins=row['total_logins'],
            total_sessions=row['total_sessions'],
            total_emails_processed=row['total_emails_processed'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
    
    def _row_to_login_record(self, row) -> LoginRecord:
        """Convert SQLite row to LoginRecord"""
        return LoginRecord(
            id=row['id'],
            user_id=row['user_id'],
            session_id=row['session_id'],
            login_time=datetime.fromisoformat(row['login_time']) if row['login_time'] else None,
            logout_time=datetime.fromisoformat(row['logout_time']) if row['logout_time'] else None,
            session_duration=row['session_duration'],
            emails_processed=row['emails_processed'],
            user_agent=row['user_agent'],
            ip_address=row['ip_address']
        )
    
    async def close(self):
        """Close database connections and cleanup"""
        # SQLite connections are closed automatically in context manager
        print("👋 User database service shutdown")


# Global database instance
_user_database: Optional[UserDatabase] = None


async def get_user_database() -> UserDatabase:
    """
    Get global user database instance
    
    Returns:
        UserDatabase singleton instance
    """
    global _user_database
    if _user_database is None:
        _user_database = UserDatabase()
        await _user_database.initialize()
    return _user_database


async def shutdown_user_database():
    """Shutdown global user database"""
    global _user_database
    if _user_database:
        await _user_database.close()
        _user_database = None
