"""
Authentication helpers for Phase 8A end-user application.
Simple session-based authentication system.
"""

import os
from typing import Optional, Dict
from fastapi import Request, HTTPException, Response
from starlette.middleware.sessions import SessionMiddleware
from .database import get_db_connection


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email address."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, consent_given, created_at
            FROM users WHERE email = ?
        """, (email,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'consent_given': bool(row[3]),
            'created_at': row[4]
        }
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, email, consent_given, created_at
            FROM users WHERE id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            'id': row[0],
            'name': row[1],
            'email': row[2],
            'consent_given': bool(row[3]),
            'created_at': row[4]
        }
    finally:
        conn.close()


def get_current_user(request: Request) -> Dict:
    """
    Dependency to extract current user from session.
    Raises HTTPException if user not authenticated.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    user = get_user_by_id(user_id)
    if not user:
        # Session has invalid user_id, clear it
        request.session.pop("user_id", None)
        raise HTTPException(status_code=401, detail="Invalid session")
    
    return user


def login_user(request: Request, user_id: int) -> None:
    """Set user_id in session after successful login."""
    request.session["user_id"] = user_id


def logout_user(request: Request) -> None:
    """Clear session on logout."""
    request.session.pop("user_id", None)
    request.session.clear()


def get_session_secret_key() -> str:
    """Get session secret key from environment variable or generate default."""
    secret_key = os.getenv("SESSION_SECRET_KEY")
    if not secret_key:
        # For development only - use a default key
        # In production, this should be set via environment variable
        secret_key = "dev-secret-key-change-in-production-phase8a"
        print("⚠️  Warning: Using default SESSION_SECRET_KEY. Set SESSION_SECRET_KEY env var for production.")
    return secret_key







