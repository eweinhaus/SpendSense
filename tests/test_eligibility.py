"""
Tests for eligibility checks module.
"""

import pytest
import os
import tempfile
from spendsense.database import init_database, get_db_connection
from spendsense.eligibility import check_eligibility, filter_recommendations, get_user_accounts, has_consent


@pytest.fixture
def test_db():
    """Create a temporary test database with a user."""
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


def test_get_user_accounts_empty(test_db):
    """Test getting accounts for user with no accounts."""
    test_db_path, user_id = test_db
    
    accounts = get_user_accounts(user_id, db_path=test_db_path)
    assert accounts == []


def test_get_user_accounts_with_accounts(test_db):
    """Test getting accounts for user with accounts."""
    test_db_path, user_id = test_db
    
    # Add accounts
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, subtype, current_balance)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc1", "depository", "checking", 1000.0))
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, subtype, current_balance)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc2", "depository", "savings", 5000.0))
    conn.commit()
    conn.close()
    
    accounts = get_user_accounts(user_id, db_path=test_db_path)
    assert len(accounts) == 2
    assert any(acc['type'] == 'depository' for acc in accounts)


def test_check_eligibility_savings_account_already_exists(test_db):
    """Test eligibility check when user already has savings account."""
    test_db_path, user_id = test_db
    
    # Add savings account
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, subtype, current_balance)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc1", "depository", "savings", 5000.0))
    conn.commit()
    conn.close()
    
    is_eligible, reason = check_eligibility(user_id, "Open a High-Yield Savings Account", db_path=test_db_path)
    assert is_eligible is False
    assert "already has savings" in reason.lower()


def test_check_eligibility_savings_no_checking(test_db):
    """Test eligibility check for savings when user has no checking account."""
    test_db_path, user_id = test_db
    
    # Don't add savings account - user has no accounts at all
    # This tests the checking account requirement for HYSA
    
    is_eligible, reason = check_eligibility(user_id, "Open a High-Yield Savings Account", db_path=test_db_path)
    # Should be ineligible because no checking account
    assert is_eligible is False
    assert "checking" in reason.lower()


def test_check_eligibility_credit_card_already_exists(test_db):
    """Test eligibility check when user already has credit card."""
    test_db_path, user_id = test_db
    
    # Add credit card
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, current_balance, "limit")
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "cc1", "credit", 1000.0, 5000.0))
    conn.commit()
    conn.close()
    
    is_eligible, reason = check_eligibility(user_id, "Get a New Credit Card", db_path=test_db_path)
    assert is_eligible is False
    assert "already has credit card" in reason.lower()


def test_check_eligibility_eligible(test_db):
    """Test eligibility check for eligible recommendation."""
    test_db_path, user_id = test_db
    
    # Add checking account (for savings eligibility)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, subtype, current_balance)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc1", "depository", "checking", 1000.0))
    conn.commit()
    conn.close()
    
    is_eligible, reason = check_eligibility(user_id, "Open a High-Yield Savings Account", db_path=test_db_path)
    assert is_eligible is True
    assert "eligible" in reason.lower()


def test_filter_recommendations(test_db):
    """Test filtering recommendations based on eligibility."""
    test_db_path, user_id = test_db
    
    # Add savings account
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO accounts (user_id, account_id, type, subtype, current_balance)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc1", "depository", "savings", 5000.0))
    conn.commit()
    conn.close()
    
    recommendations = [
        {'title': 'Open a High-Yield Savings Account', 'content': 'Test'},
        {'title': 'Reduce Credit Utilization', 'content': 'Test'},
        {'title': 'Review Subscriptions', 'content': 'Test'}
    ]
    
    filtered = filter_recommendations(user_id, recommendations, db_path=test_db_path)
    # Should filter out the savings account recommendation
    assert len(filtered) < len(recommendations)
    assert not any('High-Yield Savings' in rec['title'] for rec in filtered)


def test_has_consent_false(test_db):
    """Test has_consent returns False when consent not given."""
    test_db_path, user_id = test_db
    
    # User created with consent_given = 0
    assert has_consent(user_id, db_path=test_db_path) is False


def test_has_consent_true(test_db):
    """Test has_consent returns True when consent given."""
    test_db_path, user_id = test_db
    
    # Update consent
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET consent_given = ? WHERE id = ?", (1, user_id))
    conn.commit()
    conn.close()
    
    assert has_consent(user_id, db_path=test_db_path) is True


def test_has_consent_nonexistent_user(test_db):
    """Test has_consent returns False for nonexistent user."""
    test_db_path, _ = test_db
    
    assert has_consent(99999, db_path=test_db_path) is False

