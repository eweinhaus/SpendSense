"""
Unit tests for signal detection module.
"""

import sqlite3
import os
import sys
import pytest
from datetime import date, timedelta

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database, get_db_connection
from detect_signals import (
    is_similar_amount, is_monthly_cadence, 
    detect_credit_signals, detect_subscription_signals
)


@pytest.fixture
def test_db():
    """Create a test database with sample data."""
    test_db_path = "test_signals.db"
    # Remove test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Initialize test database
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Create test user
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("Test User", "test@example.com"))
    user_id = cursor.lastrowid
    
    # Create credit card account
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance, "limit"
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, "acc_test", "credit", "credit card", 3750.0, 5000.0))
    account_id = cursor.lastrowid
    
    # Create credit card liability data
    cursor.execute("""
        INSERT INTO credit_cards (
            account_id, apr, minimum_payment_amount, is_overdue
        ) VALUES (?, ?, ?, ?)
    """, (account_id, 22.0, 75.0, False))
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_is_similar_amount():
    """Test amount similarity detection."""
    # Similar amounts within tolerance
    assert is_similar_amount([15.99, 15.99, 16.99], tolerance=1.0) == True
    
    # Amounts vary too much
    assert is_similar_amount([15.99, 15.99, 25.99], tolerance=1.0) == False
    
    # Empty list
    assert is_similar_amount([], tolerance=1.0) == False


def test_is_monthly_cadence():
    """Test monthly cadence detection."""
    today = date.today()
    
    # Valid monthly cadence (30 days apart)
    dates = [
        today - timedelta(days=90),
        today - timedelta(days=60),
        today - timedelta(days=30)
    ]
    assert is_monthly_cadence(dates, days_range=(27, 33)) == True
    
    # Irregular spacing
    dates = [
        today - timedelta(days=90),
        today - timedelta(days=50),
        today - timedelta(days=30)
    ]
    assert is_monthly_cadence(dates, days_range=(27, 33)) == False
    
    # Less than 3 occurrences
    dates = [
        today - timedelta(days=90),
        today - timedelta(days=60)
    ]
    assert is_monthly_cadence(dates, days_range=(27, 33)) == False


def test_credit_utilization_calculation(test_db):
    """Test credit utilization calculation."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    result = detect_credit_signals(user_id, conn)
    
    assert result['signals_stored'] == 8
    assert result['cards_processed'] == 1
    # Utilization should be 3750 / 5000 = 75%
    assert abs(result['max_utilization'] - 75.0) < 0.1
    
    conn.close()


def test_credit_utilization_division_by_zero(test_db):
    """Test that zero limit doesn't cause division by zero."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Add a card with zero limit
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance, "limit"
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, "acc_zero", "credit", "credit card", 1000.0, 0.0))
    
    conn.commit()
    
    # Should not crash
    result = detect_credit_signals(user_id, conn)
    assert result['signals_stored'] == 8  # Still stores signals for valid card
    
    conn.close()


def test_subscription_pattern_matching(test_db):
    """Test subscription pattern detection."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Get account ID (checking account)
    cursor.execute("SELECT id FROM accounts WHERE user_id = ? AND type = ? LIMIT 1", (user_id, 'depository'))
    result = cursor.fetchone()
    if not result:
        # Create checking account
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, current_balance
            ) VALUES (?, ?, ?, ?, ?)
        """, (user_id, "acc_checking", "depository", "checking", 1000.0))
        account_id = cursor.lastrowid
    else:
        account_id = result[0]
    
    # Create subscription transactions (Netflix, 3 occurrences, monthly)
    today = date.today()
    for i in range(3):
        tx_date = today - timedelta(days=90 - (i * 30))
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel,
                personal_finance_category, pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (account_id, tx_date, 15.99, "Netflix", "online", 
              "GENERAL_SERVICES", False))
    
    conn.commit()
    
    # Detect subscriptions
    result = detect_subscription_signals(user_id, conn)
    
    assert result['signals_stored'] == 4
    assert result['subscriptions_found'] >= 1
    assert "Netflix" in result['merchants']
    
    conn.close()


def test_user_with_no_credit_cards(test_db):
    """Test handling of user with no credit cards."""
    test_db_path = test_db[0]
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Create user with no credit cards
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("No Cards User", "nocards@example.com"))
    user_id = cursor.lastrowid
    conn.commit()
    
    # Should not crash
    result = detect_credit_signals(user_id, conn)
    assert result['signals_stored'] == 0
    assert result['cards_processed'] == 0
    
    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


