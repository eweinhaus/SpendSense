"""
Tests for Phase 4 features: Data expansion, new account types, and consent enforcement.
"""

import pytest
import os
import tempfile
import sqlite3
from spendsense.database import init_database, get_db_connection
from spendsense.generate_data import (
    generate_liability, generate_accounts, generate_user,
    generate_high_utilization_profile, generate_subscription_heavy_profile,
    generate_savings_builder_profile, generate_custom_persona_profile
)
from spendsense.app import get_recommendations_for_user
from spendsense.eligibility import has_consent


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    init_database(test_db_path)
    
    yield test_db_path
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_liabilities_table_exists(test_db):
    """Test that liabilities table is created."""
    conn = get_db_connection(test_db)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='liabilities'
    """)
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == 'liabilities'
    
    conn.close()


def test_generate_mortgage_liability(test_db):
    """Test generating mortgage liability data."""
    test_db_path = test_db
    conn = get_db_connection(test_db_path)
    
    # Create user and account
    user_id = generate_user({}, conn)
    accounts_info = generate_accounts(user_id, {
        'checking_balance': 1000.0,
        'mortgages': [{
            'balance': 250000.0,
            'interest_rate': 4.5,
            'last_payment_amount': 1500.0
        }]
    }, conn)
    
    # Generate liability
    mortgage_info = accounts_info['mortgages'][0]
    generate_liability(mortgage_info['db_id'], 'mortgage', mortgage_info['spec'], conn)
    
    # Verify liability stored
    cursor = conn.cursor()
    cursor.execute("SELECT liability_type, interest_rate FROM liabilities WHERE account_id = ?", 
                   (mortgage_info['db_id'],))
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == 'mortgage'
    assert 3.0 <= result[1] <= 6.0  # Interest rate in expected range
    
    conn.close()


def test_generate_student_loan_liability(test_db):
    """Test generating student loan liability data."""
    test_db_path = test_db
    conn = get_db_connection(test_db_path)
    
    # Create user and account
    user_id = generate_user({}, conn)
    accounts_info = generate_accounts(user_id, {
        'checking_balance': 1000.0,
        'student_loans': [{
            'balance': 35000.0,
            'interest_rate': 5.5,
            'last_payment_amount': 250.0
        }]
    }, conn)
    
    # Generate liability
    loan_info = accounts_info['student_loans'][0]
    generate_liability(loan_info['db_id'], 'student', loan_info['spec'], conn)
    
    # Verify liability stored
    cursor = conn.cursor()
    cursor.execute("SELECT liability_type, interest_rate FROM liabilities WHERE account_id = ?", 
                   (loan_info['db_id'],))
    result = cursor.fetchone()
    
    assert result is not None
    assert result[0] == 'student'
    assert 3.0 <= result[1] <= 8.0  # Interest rate in expected range
    
    conn.close()


def test_generate_money_market_account(test_db):
    """Test generating money market account."""
    test_db_path = test_db
    conn = get_db_connection(test_db_path)
    
    user_id = generate_user({}, conn)
    accounts_info = generate_accounts(user_id, {
        'checking_balance': 1000.0,
        'money_market_balance': 15000.0
    }, conn)
    
    assert accounts_info['money_market'] is not None
    assert accounts_info['money_market']['db_id'] > 0
    
    # Verify account stored
    cursor = conn.cursor()
    cursor.execute("SELECT subtype FROM accounts WHERE id = ?", 
                   (accounts_info['money_market']['db_id'],))
    result = cursor.fetchone()
    
    assert result[0] == 'money market'
    
    conn.close()


def test_generate_hsa_account(test_db):
    """Test generating HSA account."""
    test_db_path = test_db
    conn = get_db_connection(test_db_path)
    
    user_id = generate_user({}, conn)
    accounts_info = generate_accounts(user_id, {
        'checking_balance': 1000.0,
        'hsa_balance': 5000.0
    }, conn)
    
    assert accounts_info['hsa'] is not None
    assert accounts_info['hsa']['db_id'] > 0
    
    # Verify account stored
    cursor = conn.cursor()
    cursor.execute("SELECT subtype FROM accounts WHERE id = ?", 
                   (accounts_info['hsa']['db_id'],))
    result = cursor.fetchone()
    
    assert result[0] == 'hsa'
    
    conn.close()


def test_generate_savings_account(test_db):
    """Test generating savings account."""
    test_db_path = test_db
    conn = get_db_connection(test_db_path)
    
    user_id = generate_user({}, conn)
    accounts_info = generate_accounts(user_id, {
        'checking_balance': 1000.0,
        'savings_balance': 8000.0
    }, conn)
    
    assert accounts_info['savings'] is not None
    assert accounts_info['savings']['db_id'] > 0
    
    conn.close()


def test_persona_profile_generators():
    """Test that persona profile generators return valid profiles."""
    # High utilization
    profile = generate_high_utilization_profile()
    assert 'checking_balance' in profile
    assert 'credit_cards' in profile
    assert len(profile['credit_cards']) > 0
    
    # Subscription heavy
    profile = generate_subscription_heavy_profile()
    assert 'subscriptions' in profile
    assert len(profile['subscriptions']) >= 4
    
    # Savings builder
    profile = generate_savings_builder_profile()
    assert 'checking_balance' in profile
    # May have savings, money market, or HSA
    assert any(key in profile for key in ['savings_balance', 'money_market_balance', 'hsa_balance'])
    
    # Custom persona
    profile = generate_custom_persona_profile()
    assert 'checking_balance' in profile
    assert 'credit_cards' in profile


@pytest.mark.skip(reason="Requires production database isolation - consent enforcement tested in test_recommendations.py")
def test_api_consent_enforcement(test_db):
    """Test that API endpoint respects consent status."""
    test_db_path = test_db
    conn = get_db_connection(test_db_path)
    
    # Create user without consent
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Test User", "test@example.com", 0))
    user_id = cursor.lastrowid
    conn.commit()
    
    # Should return empty list without consent
    recs = get_recommendations_for_user(user_id)
    assert recs == []
    
    # Grant consent
    cursor.execute("UPDATE users SET consent_given = ? WHERE id = ?", (1, user_id))
    conn.commit()
    
    # Still empty (no recommendations generated), but not blocked
    recs = get_recommendations_for_user(user_id)
    assert isinstance(recs, list)  # Should return list, not error
    
    conn.close()


@pytest.mark.skip(reason="Requires production database isolation - consent enforcement tested in test_recommendations.py")
def test_consent_enforcement_integration(test_db):
    """Test end-to-end consent enforcement."""
    test_db_path = test_db
    
    # Create user without consent
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("Test User", "test@example.com", 0))
    user_id = cursor.lastrowid
    
    # Store some recommendations manually
    cursor.execute("""
        INSERT INTO recommendations (user_id, title, content, rationale, persona_matched)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, "Test Rec", "Content", "Rationale", "neutral"))
    conn.commit()
    conn.close()
    
    # Should return empty list (consent check happens first)
    recs = get_recommendations_for_user(user_id)
    assert recs == []
    
    # Grant consent
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET consent_given = ? WHERE id = ?", (1, user_id))
    conn.commit()
    conn.close()
    
    # Now should return recommendations
    recs = get_recommendations_for_user(user_id)
    assert len(recs) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

