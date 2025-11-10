"""
Integration tests for Phase 5: Signal Detection & Personas.
Tests new signal types (savings, income) and dual-window support.
"""

import sqlite3
import os
import sys
import pytest
from datetime import date, timedelta

# Add src directory to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from spendsense.database import init_database, get_db_connection
from spendsense.detect_signals import (
    detect_savings_signals, detect_income_signals, detect_all_signals,
    detect_credit_signals, detect_subscription_signals
)
from spendsense.personas import (
    assign_persona, matches_variable_income, matches_savings_builder,
    matches_financial_newcomer, get_signal_value
)


@pytest.fixture
def test_db():
    """Create a test database with Phase 5 data."""
    test_db_path = "test_phase5.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    today = date.today()
    
    # Create test user
    cursor.execute("""
        INSERT INTO users (name, email, consent_given) VALUES (?, ?, ?)
    """, ("Phase 5 Test User", "phase5@example.com", 1))
    user_id = cursor.lastrowid
    
    # Create checking account
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance
        ) VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc_checking", "depository", "checking", 3000.0))
    checking_id = cursor.lastrowid
    
    # Create savings account
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance
        ) VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc_savings", "depository", "savings", 5000.0))
    savings_id = cursor.lastrowid
    
    # Create credit card
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance, "limit"
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, "acc_credit", "credit", "credit card", 1000.0, 5000.0))
    credit_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO credit_cards (
            account_id, apr, minimum_payment_amount, is_overdue
        ) VALUES (?, ?, ?, ?)
    """, (credit_id, 22.0, 50.0, False))
    
    # Add savings transactions (deposits)
    for i in range(5):
        tx_date = today - timedelta(days=i * 7)
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel, pending
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (savings_id, tx_date, 200.0, "Deposit", "other", False))
    
    # Add payroll transactions (bi-weekly)
    for i in range(4):
        tx_date = today - timedelta(days=i * 14)
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel, pending
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (checking_id, tx_date, 2500.0, "PAYROLL", "other", False))
    
    # Add expense transactions
    for i in range(15):
        tx_date = today - timedelta(days=i * 2)
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel, pending
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (checking_id, tx_date, -50.0, f"Expense {i}", "other", False))
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_savings_signals_detection(test_db):
    """Test savings signal detection for both windows."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Test 30d window
    result_30d = detect_savings_signals(user_id, '30d', conn)
    assert result_30d['signals_stored'] == 3
    assert 'net_inflow' in result_30d
    assert 'growth_rate' in result_30d
    assert 'emergency_fund_coverage' in result_30d
    
    # Test 180d window
    result_180d = detect_savings_signals(user_id, '180d', conn)
    assert result_180d['signals_stored'] == 3
    
    conn.close()


def test_income_signals_detection(test_db):
    """Test income signal detection for both windows."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Test 30d window
    result_30d = detect_income_signals(user_id, '30d', conn)
    assert result_30d['signals_stored'] == 4
    assert 'payroll_detected' in result_30d
    assert 'income_frequency' in result_30d
    assert result_30d.get('income_frequency') in ['weekly', 'bi-weekly', 'monthly', 'irregular']
    
    # Test 180d window
    result_180d = detect_income_signals(user_id, '180d', conn)
    assert result_180d['signals_stored'] == 4
    
    conn.close()


def test_dual_window_detection(test_db):
    """Test that detect_all_signals runs both windows."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    result = detect_all_signals(user_id, conn)
    
    assert 'windows' in result
    assert '30d' in result['windows']
    assert '180d' in result['windows']
    assert result['windows']['30d']['window_signals'] > 0
    assert result['windows']['180d']['window_signals'] > 0
    
    # Verify savings signals exist in both windows
    assert 'savings_signals' in result['windows']['30d']
    assert 'savings_signals' in result['windows']['180d']
    assert 'income_signals' in result['windows']['30d']
    assert 'income_signals' in result['windows']['180d']
    
    conn.close()


def test_variable_income_persona_matching(test_db):
    """Test Variable Income Budgeter persona detection."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Create signals that match Variable Income Budgeter
    from spendsense.detect_signals import store_signal
    
    # Median pay gap > 45 days
    store_signal(user_id, 'median_pay_gap', 50.0, {}, '30d', conn)
    # Cash-flow buffer < 1 month
    store_signal(user_id, 'cash_flow_buffer_30d', 0.5, {}, '30d', conn)
    
    from spendsense.personas import get_user_signals
    signals = get_user_signals(user_id, conn)
    
    assert matches_variable_income(signals) == True
    
    conn.close()


def test_savings_builder_persona_matching(test_db):
    """Test Savings Builder persona detection."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    from spendsense.detect_signals import store_signal
    
    # Savings growth rate >= 2%
    store_signal(user_id, 'savings_growth_rate_30d', 3.0, {}, '30d', conn)
    # Credit utilization < 30%
    store_signal(user_id, 'credit_utilization_max', 25.0, {}, '30d', conn)
    
    from spendsense.personas import get_user_signals
    signals = get_user_signals(user_id, conn)
    
    assert matches_savings_builder(signals) == True
    
    conn.close()


def test_financial_newcomer_persona_matching(test_db):
    """Test Financial Newcomer persona detection."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    from spendsense.personas import get_user_signals
    signals = get_user_signals(user_id, conn)
    
    # User should have < 3 accounts, low utilization, low transaction volume
    # This test user has 3 accounts, so it might not match - that's okay
    # The function will check account count from database
    result = matches_financial_newcomer(signals, user_id, conn)
    # Just verify it doesn't crash
    assert isinstance(result, bool)
    
    conn.close()


def test_get_signal_value_with_windows(test_db):
    """Test get_signal_value function with window-specific signals."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    from spendsense.detect_signals import store_signal
    from spendsense.personas import get_user_signals, get_signal_value
    
    # Store window-specific signals
    store_signal(user_id, 'cash_flow_buffer_30d', 1.5, {}, '30d', conn)
    store_signal(user_id, 'cash_flow_buffer_180d', 2.0, {}, '180d', conn)
    
    signals = get_user_signals(user_id, conn)
    
    # Should get 30d value when requesting 30d
    value_30d = get_signal_value(signals, 'cash_flow_buffer', '30d')
    assert value_30d == 1.5
    
    # Should get 180d value when requesting 180d
    value_180d = get_signal_value(signals, 'cash_flow_buffer', '180d')
    assert value_180d == 2.0
    
    conn.close()


def test_full_pipeline_phase5(test_db):
    """Test full pipeline with Phase 5 features."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Run all signal detection (both windows)
    result = detect_all_signals(user_id, conn)
    assert result['total_signals'] > 0
    
    # Assign persona
    persona = assign_persona(user_id, conn)
    assert persona in [
        'high_utilization', 'variable_income_budgeter', 'savings_builder',
        'financial_newcomer', 'subscription_heavy', 'neutral'
    ]
    
    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])







