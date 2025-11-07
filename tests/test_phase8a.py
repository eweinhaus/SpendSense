"""
Tests for Phase 8A: End-User Application
Covers authentication, user routes, and calculators.
"""

import pytest
import os
import tempfile
import json
from fastapi.testclient import TestClient
from fastapi import Request
from unittest.mock import Mock, patch
from spendsense.database import init_database, get_db_connection
from spendsense.generate_data import generate_user
from spendsense.app import app
from spendsense.auth import (
    get_user_by_email, get_user_by_id, login_user, logout_user, get_current_user
)
from spendsense.user_data import (
    get_user_persona_summary, get_user_signal_summary, get_user_account_summary,
    calculate_quick_stats, get_user_transaction_insights
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
    
    # User with consent
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Test User", "test@example.com", 1))
    user_id = cursor.lastrowid
    
    # User without consent
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("No Consent User", "noconsent@example.com", 0))
    no_consent_user_id = cursor.lastrowid
    
    # Create some accounts and transactions for testing
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, current_balance, "limit")
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc1", "credit", 1000.0, 5000.0))
    account_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO credit_cards (account_id, apr, minimum_payment_amount)
        VALUES (?, ?, ?)
    """, (account_id, 18.5, 50.0))
    
    # Create some signals
    cursor.execute("""
        INSERT INTO signals (user_id, signal_type, value, window)
        VALUES (?, ?, ?, ?)
    """, (user_id, "credit_utilization_max", 20.0, "30d"))
    
    cursor.execute("""
        INSERT INTO signals (user_id, signal_type, value, window)
        VALUES (?, ?, ?, ?)
    """, (user_id, "subscription_count", 3, "30d"))
    
    # Create persona
    cursor.execute("""
        INSERT INTO personas (user_id, persona_type, criteria_matched)
        VALUES (?, ?, ?)
    """, (user_id, "savings_builder", "growth_rate >= 2%"))
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id, no_consent_user_id
    
    # Cleanup
    if original_db_path:
        os.environ['DATABASE_PATH'] = original_db_path
    elif 'DATABASE_PATH' in os.environ:
        del os.environ['DATABASE_PATH']
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def client(test_db):
    """Create a test client."""
    test_db_path, user_id, no_consent_user_id = test_db
    
    # Patch database path for this test
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        with patch('spendsense.user_data.get_db_connection') as mock_conn:
            mock_conn.return_value = get_db_connection(test_db_path)
            yield TestClient(app)


# ============================================================================
# Authentication Tests
# ============================================================================

def test_login_page(client):
    """Test login page is accessible."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "Login" in response.text
    assert "Email or User ID" in response.text


def test_login_with_email(client, test_db):
    """Test login with email."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        response = client.post("/login", data={"identifier": "test@example.com"})
        assert response.status_code == 303  # Redirect
        assert "/portal/dashboard" in response.headers["location"]
        
        # Check session was set
        assert "session" in response.cookies


def test_login_with_user_id(client, test_db):
    """Test login with user ID."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        response = client.post("/login", data={"identifier": str(user_id)})
        assert response.status_code == 303
        assert "/portal/dashboard" in response.headers["location"]


def test_login_invalid_user(client, test_db):
    """Test login with invalid user."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        response = client.post("/login", data={"identifier": "invalid@example.com"})
        assert response.status_code == 200
        assert "User not found" in response.text


def test_logout(client, test_db):
    """Test logout functionality."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # First login
        login_response = client.post("/login", data={"identifier": str(user_id)})
        assert login_response.status_code == 303
        
        # Get session cookie
        session_cookie = login_response.cookies.get("session")
        
        # Logout
        logout_response = client.post("/logout", cookies={"session": session_cookie})
        assert logout_response.status_code == 303
        assert "/login" in logout_response.headers["location"]


def test_protected_route_requires_auth(client):
    """Test that protected routes require authentication."""
    response = client.get("/portal/dashboard")
    assert response.status_code == 401  # Unauthorized


# ============================================================================
# Dashboard Tests
# ============================================================================

def test_user_dashboard_authenticated(client, test_db):
    """Test user dashboard when authenticated."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access dashboard
        response = client.get("/portal/dashboard", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Welcome" in response.text
        assert "Dashboard" in response.text


def test_user_dashboard_shows_consent_banner(client, test_db):
    """Test dashboard shows consent banner when consent not granted."""
    test_db_path, user_id, no_consent_user_id = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login as user without consent
        login_response = client.post("/login", data={"identifier": str(no_consent_user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access dashboard
        response = client.get("/portal/dashboard", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Consent Required" in response.text or "consent" in response.text.lower()


# ============================================================================
# Recommendations Tests
# ============================================================================

def test_recommendations_requires_consent(client, test_db):
    """Test recommendations page requires consent."""
    test_db_path, user_id, no_consent_user_id = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login as user without consent
        login_response = client.post("/login", data={"identifier": str(no_consent_user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access recommendations
        response = client.get("/portal/recommendations", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Consent Required" in response.text or "no_consent" in response.text.lower()


# ============================================================================
# Profile Tests
# ============================================================================

def test_profile_page(client, test_db):
    """Test profile page is accessible when authenticated."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access profile
        response = client.get("/portal/profile", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Financial Profile" in response.text


def test_profile_window_toggle(client, test_db):
    """Test profile window toggle (30d/180d)."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access profile with 180d window
        response = client.get("/portal/profile?window=180d", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "180 Days" in response.text or "180d" in response.text


# ============================================================================
# Consent Management Tests
# ============================================================================

def test_consent_page(client, test_db):
    """Test consent management page."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access consent page
        response = client.get("/portal/consent", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Consent Management" in response.text or "Consent" in response.text


# ============================================================================
# Calculator Tests
# ============================================================================

def test_calculators_hub(client, test_db):
    """Test calculators hub page."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access calculators hub
        response = client.get("/portal/calculators", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Financial Calculators" in response.text


def test_emergency_fund_calculator(client, test_db):
    """Test emergency fund calculator."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access calculator
        response = client.get("/portal/calculators/emergency-fund", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Emergency Fund" in response.text
        
        # Test calculation
        calc_response = client.post(
            "/portal/calculators/emergency-fund",
            data={"monthly_expenses": "2000", "months": "6"},
            cookies={"session": session_cookie}
        )
        assert calc_response.status_code == 200
        assert "12000" in calc_response.text or "12,000" in calc_response.text


def test_debt_paydown_calculator(client, test_db):
    """Test debt paydown calculator."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access calculator
        response = client.get("/portal/calculators/debt-paydown", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Debt Paydown" in response.text
        
        # Test calculation
        calc_response = client.post(
            "/portal/calculators/debt-paydown",
            data={"balance": "5000", "apr": "18", "payment": "200"},
            cookies={"session": session_cookie}
        )
        assert calc_response.status_code == 200
        assert "months" in calc_response.text.lower()


def test_savings_goal_calculator(client, test_db):
    """Test savings goal calculator."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.database.get_db_path', return_value=test_db_path):
        # Login first
        login_response = client.post("/login", data={"identifier": str(user_id)})
        session_cookie = login_response.cookies.get("session")
        
        # Access calculator
        response = client.get("/portal/calculators/savings-goal", cookies={"session": session_cookie})
        assert response.status_code == 200
        assert "Savings Goal" in response.text
        
        # Test calculation
        from datetime import datetime, timedelta
        target_date = (datetime.now() + timedelta(days=365)).strftime("%Y-%m-%d")
        calc_response = client.post(
            "/portal/calculators/savings-goal",
            data={"goal_amount": "10000", "target_date": target_date, "current_savings": "1000"},
            cookies={"session": session_cookie}
        )
        assert calc_response.status_code == 200
        assert "monthly" in calc_response.text.lower() or "Monthly" in calc_response.text


# ============================================================================
# User Data Helper Tests
# ============================================================================

def test_get_user_persona_summary(test_db):
    """Test get_user_persona_summary helper."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.user_data.get_db_connection') as mock_conn:
        mock_conn.return_value = get_db_connection(test_db_path)
        persona = get_user_persona_summary(user_id)
        
        assert persona is not None
        assert "type" in persona
        assert "name" in persona
        assert persona["type"] == "savings_builder"


def test_get_user_signal_summary(test_db):
    """Test get_user_signal_summary helper."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.user_data.get_db_connection') as mock_conn:
        mock_conn.return_value = get_db_connection(test_db_path)
        signals = get_user_signal_summary(user_id)
        
        assert isinstance(signals, dict)
        assert "credit_utilization_max" in signals or "subscription_count" in signals


def test_get_user_account_summary(test_db):
    """Test get_user_account_summary helper."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.user_data.get_db_connection') as mock_conn:
        mock_conn.return_value = get_db_connection(test_db_path)
        accounts = get_user_account_summary(user_id)
        
        assert isinstance(accounts, dict)
        assert "total_balance" in accounts
        assert "total_accounts" in accounts


def test_calculate_quick_stats(test_db):
    """Test calculate_quick_stats helper."""
    test_db_path, user_id, _ = test_db
    
    with patch('spendsense.user_data.get_db_connection') as mock_conn:
        mock_conn.return_value = get_db_connection(test_db_path)
        stats = calculate_quick_stats(user_id)
        
        assert isinstance(stats, dict)
        assert "emergency_fund_months" in stats
        assert "credit_utilization" in stats

