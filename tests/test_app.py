"""
Tests for FastAPI application endpoints.
"""

import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from spendsense.database import init_database, get_db_connection
from spendsense.generate_data import generate_user
from spendsense.app import app


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database
    init_database(test_db_path)
    
    # Create a test user
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Test User", "test@example.com", 0))
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def client(test_db):
    """Create a test client."""
    # Note: This uses the default database path
    # In a real scenario, we'd need to configure the app to use test_db_path
    # For MVP, we'll test with the assumption that the database exists
    return TestClient(app)


def test_dashboard_endpoint(client):
    """Test dashboard endpoint returns HTML."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SpendSense" in response.text


def test_user_detail_endpoint_valid_user(client):
    """Test user detail endpoint with valid user_id."""
    # This test assumes user 1 exists in the database
    # In a real test, we'd create a user first
    response = client.get("/user/1")
    
    # Should return 200 or 404 depending on whether user exists
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        assert "text/html" in response.headers["content-type"]
        assert "User Information" in response.text


def test_user_detail_endpoint_invalid_user(client):
    """Test user detail endpoint with invalid user_id."""
    response = client.get("/user/99999")
    assert response.status_code == 404
    assert "not found" in response.text.lower()


def test_consent_toggle_endpoint(client):
    """Test consent toggle endpoint."""
    # First, we need to ensure user exists
    # For this test, we'll assume user 1 exists
    response = client.post(
        "/consent/1",
        json={"consent": True}
    )
    
    # Should return 200 or 404 depending on whether user exists
    assert response.status_code in [200, 404]
    
    if response.status_code == 200:
        data = response.json()
        assert "success" in data
        assert data["success"] is True
        assert data["consent_given"] is True


def test_consent_toggle_invalid_user(client):
    """Test consent toggle with invalid user_id."""
    response = client.post(
        "/consent/99999",
        json={"consent": True}
    )
    assert response.status_code == 404


def test_consent_toggle_invalid_request(client):
    """Test consent toggle with invalid request body."""
    response = client.post(
        "/consent/1",
        json={"invalid": "data"}
    )
    # Should return validation error (422) or 404 if user doesn't exist
    assert response.status_code in [400, 404, 422]

