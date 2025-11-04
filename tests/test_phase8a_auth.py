"""
Unit tests for Phase 8A authentication functions.
Tests the auth module directly without FastAPI dependencies.
"""

import pytest
import os
import tempfile
from spendsense.database import init_database, get_db_connection
from spendsense.auth import (
    get_user_by_email, get_user_by_id, get_session_secret_key
)


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Set environment variable for test database
    original_db_path = os.environ.get('DATABASE_PATH')
    os.environ['DATABASE_PATH'] = test_db_path
    
    # Initialize database
    init_database(test_db_path)
    
    # Create test users
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Test User", "test@example.com", 1))
    user_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Another User", "another@example.com", 0))
    another_user_id = cursor.lastrowid
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id, another_user_id
    
    # Cleanup
    if original_db_path:
        os.environ['DATABASE_PATH'] = original_db_path
    elif 'DATABASE_PATH' in os.environ:
        del os.environ['DATABASE_PATH']
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_get_user_by_email(test_db):
    """Test get_user_by_email function."""
    test_db_path, user_id, _ = test_db
    
    with pytest.MonkeyPatch().context() as m:
        m.setenv('DATABASE_PATH', test_db_path)
        
        user = get_user_by_email("test@example.com")
        assert user is not None
        assert user["id"] == user_id
        assert user["email"] == "test@example.com"
        assert user["consent_given"] is True
        
        # Test non-existent user
        user = get_user_by_email("nonexistent@example.com")
        assert user is None


def test_get_user_by_id(test_db):
    """Test get_user_by_id function."""
    test_db_path, user_id, another_user_id = test_db
    
    with pytest.MonkeyPatch().context() as m:
        m.setenv('DATABASE_PATH', test_db_path)
        
        user = get_user_by_id(user_id)
        assert user is not None
        assert user["id"] == user_id
        assert user["email"] == "test@example.com"
        
        # Test non-existent user
        user = get_user_by_id(99999)
        assert user is None


def test_get_session_secret_key():
    """Test get_session_secret_key function."""
    # Test with environment variable
    import os
    original_key = os.environ.get('SESSION_SECRET_KEY')
    
    try:
        os.environ['SESSION_SECRET_KEY'] = 'test-secret-key'
        key = get_session_secret_key()
        assert key == 'test-secret-key'
    finally:
        if original_key:
            os.environ['SESSION_SECRET_KEY'] = original_key
        elif 'SESSION_SECRET_KEY' in os.environ:
            del os.environ['SESSION_SECRET_KEY']
    
    # Test without environment variable (should use default)
    if 'SESSION_SECRET_KEY' in os.environ:
        del os.environ['SESSION_SECRET_KEY']
    key = get_session_secret_key()
    assert key is not None
    assert len(key) > 0

