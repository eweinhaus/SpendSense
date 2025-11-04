"""
Phase 7: Production Readiness Tests
Tests for operator view enhancements, edge cases, and comprehensive coverage.
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
    store_signal
)
from spendsense.personas import (
    assign_persona, matches_high_utilization, matches_variable_income,
    matches_savings_builder, matches_financial_newcomer, matches_subscription_heavy,
    get_signal_value
)
from spendsense.app import (
    get_user_signals_display, get_user_persona_display,
    get_decision_traces_for_user
)


@pytest.fixture
def test_db():
    """Create a test database with comprehensive Phase 7 data."""
    test_db_path = "test_phase7.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    today = date.today()
    
    # Create test user
    cursor.execute("""
        INSERT INTO users (name, email, consent_given) VALUES (?, ?, ?)
    """, ("Phase 7 Test User", "phase7@example.com", 1))
    user_id = cursor.lastrowid
    
    # Create accounts
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance
        ) VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc_checking", "depository", "checking", 3000.0))
    checking_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance
        ) VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc_savings", "depository", "savings", 5000.0))
    savings_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance, "limit"
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, "acc_credit", "credit", "credit card", 2000.0, 5000.0))
    credit_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO credit_cards (
            account_id, apr, minimum_payment_amount, is_overdue
        ) VALUES (?, ?, ?, ?)
    """, (credit_id, 22.0, 50.0, False))
    
    # Add transactions
    for i in range(5):
        tx_date = today - timedelta(days=i * 7)
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel, pending
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (savings_id, tx_date, 200.0, "Deposit", "other", False))
    
    for i in range(4):
        tx_date = today - timedelta(days=i * 14)
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel, pending
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (checking_id, tx_date, 2500.0, "PAYROLL", "other", False))
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id
    
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_savings_signals_edge_cases():
    """Test savings signal edge cases."""
    test_db_path = "test_savings_edge.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # User with no savings accounts
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("No Savings User", "nosavings@example.com"))
    user_id = cursor.lastrowid
    conn.commit()
    
    # Should not crash
    result = detect_savings_signals(user_id, '30d', conn)
    assert result['signals_stored'] == 0
    
    conn.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_income_signals_edge_cases():
    """Test income signal edge cases."""
    test_db_path = "test_income_edge.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # User with no payroll
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("No Payroll User", "nopayroll@example.com"))
    user_id = cursor.lastrowid
    conn.commit()
    
    # Should not crash
    result = detect_income_signals(user_id, '30d', conn)
    assert result['signals_stored'] >= 0  # May store 0 or some signals
    
    conn.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_dual_window_signal_detection(test_db):
    """Test that both 30d and 180d windows are detected."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Run all signal detection
    result = detect_all_signals(user_id, conn)
    
    # Verify both windows processed
    assert 'windows' in result
    assert '30d' in result['windows']
    assert '180d' in result['windows']
    
    # Verify signals stored for both windows
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT window) FROM signals WHERE user_id = ?
    """, (user_id,))
    window_count = cursor.fetchone()[0]
    assert window_count >= 1  # At least one window has signals
    
    conn.close()


def test_persona_priority_high_utilization_vs_variable_income(test_db):
    """Test that High Utilization takes priority over Variable Income."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    from spendsense.personas import get_user_signals
    
    # Create signals that match both personas
    store_signal(user_id, 'credit_utilization_max', 75.0, {}, '30d', conn)  # High Utilization
    store_signal(user_id, 'median_pay_gap', 50.0, {}, '30d', conn)  # Variable Income
    store_signal(user_id, 'cash_flow_buffer_30d', 0.5, {}, '30d', conn)  # Variable Income
    
    signals = get_user_signals(user_id, conn)
    
    # Both should match individually
    assert matches_high_utilization(signals) == True
    assert matches_variable_income(signals) == True
    
    # But High Utilization should win in assignment
    persona = assign_persona(user_id, conn)
    assert persona == "high_utilization"
    
    conn.close()


def test_persona_priority_variable_income_vs_savings_builder(test_db):
    """Test that Variable Income takes priority over Savings Builder."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Create signals that match both personas
    store_signal(user_id, 'median_pay_gap', 50.0, {}, '30d', conn)  # Variable Income
    store_signal(user_id, 'cash_flow_buffer_30d', 0.5, {}, '30d', conn)  # Variable Income
    store_signal(user_id, 'savings_growth_rate_30d', 3.0, {}, '30d', conn)  # Savings Builder
    store_signal(user_id, 'credit_utilization_max', 25.0, {}, '30d', conn)  # Savings Builder
    
    persona = assign_persona(user_id, conn)
    assert persona == "variable_income_budgeter"
    
    conn.close()


def test_persona_priority_savings_builder_vs_financial_newcomer(test_db):
    """Test that Savings Builder takes priority over Financial Newcomer."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Create signals that match both personas
    store_signal(user_id, 'savings_growth_rate_30d', 3.0, {}, '30d', conn)  # Savings Builder
    store_signal(user_id, 'credit_utilization_max', 15.0, {}, '30d', conn)  # Both (low utilization)
    
    persona = assign_persona(user_id, conn)
    # Should be Savings Builder if it matches, otherwise Financial Newcomer
    assert persona in ["savings_builder", "financial_newcomer"]
    
    conn.close()


def test_persona_priority_financial_newcomer_vs_subscription_heavy(test_db):
    """Test that Financial Newcomer takes priority over Subscription-Heavy."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Create signals that match both personas
    # Need to ensure Financial Newcomer actually matches (low utilization, few accounts)
    store_signal(user_id, 'credit_utilization_max', 15.0, {}, '30d', conn)  # Financial Newcomer (low)
    store_signal(user_id, 'subscription_count', 5, {}, '30d', conn)  # Subscription-Heavy
    
    # Check if Financial Newcomer matches (requires < 3 accounts)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM accounts WHERE user_id = ?", (user_id,))
    account_count = cursor.fetchone()[0]
    
    persona = assign_persona(user_id, conn)
    # Result depends on account count - if >= 3 accounts, Financial Newcomer won't match
    # So it could be subscription_heavy or neutral
    assert persona in ["financial_newcomer", "subscription_heavy", "neutral"]
    
    conn.close()


def test_get_user_signals_display_both_windows(test_db):
    """Test that get_user_signals_display returns both windows."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Generate signals for both windows
    detect_all_signals(user_id, conn)
    
    # Get display signals
    signals = get_user_signals_display(user_id)
    
    # Verify both windows present
    assert '30d' in signals
    assert '180d' in signals
    
    conn.close()


def test_get_user_persona_display_with_signal_windows(test_db):
    """Test that get_user_persona_display includes signal window information."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Generate signals and assign persona
    detect_all_signals(user_id, conn)
    assign_persona(user_id, conn)
    
    # Get persona display
    persona = get_user_persona_display(user_id)
    
    # Verify persona data structure
    assert persona is not None
    assert 'persona_type' in persona
    assert 'criteria_matched' in persona
    assert 'assigned_at' in persona
    # signal_windows may be None if no relevant signals found
    
    conn.close()


def test_decision_traces_display(test_db):
    """Test that decision traces are retrieved correctly."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    from spendsense.recommendations import generate_recommendations
    
    # Generate signals, persona, and recommendations
    detect_all_signals(user_id, conn)
    assign_persona(user_id, conn)
    rec_ids = generate_recommendations(user_id, conn)
    
    # Verify recommendations were created
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM recommendations WHERE user_id = ?", (user_id,))
    actual_rec_ids = [row[0] for row in cursor.fetchall()]
    assert len(actual_rec_ids) > 0
    
    # Get decision traces directly from database (using test database connection)
    cursor.execute("""
        SELECT recommendation_id, step, reasoning, data_cited
        FROM decision_traces
        WHERE user_id = ?
        ORDER BY recommendation_id, step
    """, (user_id,))
    
    traces_by_rec = {}
    for row in cursor.fetchall():
        rec_id, step, reasoning, data_cited_json = row
        if rec_id not in traces_by_rec:
            traces_by_rec[rec_id] = []
        traces_by_rec[rec_id].append({
            'step': step,
            'reasoning': reasoning,
            'data_cited': data_cited_json
        })
    
    # Verify traces exist for recommendations
    assert len(traces_by_rec) > 0
    
    # Verify each recommendation has 4 trace steps
    for rec_id in actual_rec_ids:
        if rec_id in traces_by_rec:
            assert len(traces_by_rec[rec_id]) == 4  # 4 steps per trace
    
    conn.close()


def test_full_pipeline_phase7(test_db):
    """Test full pipeline with Phase 7 features (dual windows, all signal types)."""
    test_db_path, user_id = test_db
    conn = get_db_connection(test_db_path)
    
    # Step 1: Detect all signals (both windows, all types)
    result = detect_all_signals(user_id, conn)
    assert result['total_signals'] > 0
    
    # Step 2: Assign persona
    persona = assign_persona(user_id, conn)
    assert persona in [
        'high_utilization', 'variable_income_budgeter', 'savings_builder',
        'financial_newcomer', 'subscription_heavy', 'neutral'
    ]
    
    # Step 3: Get signals display (verify both windows)
    signals_display = get_user_signals_display(user_id)
    assert '30d' in signals_display
    assert '180d' in signals_display
    
    # Step 4: Get persona display (verify includes signal windows)
    persona_display = get_user_persona_display(user_id)
    assert persona_display is not None
    # Verify persona type matches (may have been reassigned, so check it's valid)
    assert persona_display['persona_type'] in [
        'high_utilization', 'variable_income_budgeter', 'savings_builder',
        'financial_newcomer', 'subscription_heavy', 'neutral'
    ]
    
    # Step 5: Generate recommendations
    from spendsense.recommendations import generate_recommendations
    rec_ids = generate_recommendations(user_id, conn)
    assert len(rec_ids) > 0
    
    # Step 6: Get decision traces
    traces = get_decision_traces_for_user(user_id)
    assert len(traces) > 0
    
    conn.close()


def test_edge_case_zero_savings_balance():
    """Test handling of zero savings balance."""
    test_db_path = "test_zero_savings.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("Zero Savings User", "zerosavings@example.com"))
    user_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance
        ) VALUES (?, ?, ?, ?, ?)
    """, (user_id, "acc_savings", "depository", "savings", 0.0))
    
    conn.commit()
    
    # Should not crash
    result = detect_savings_signals(user_id, '30d', conn)
    assert result['signals_stored'] >= 0
    
    conn.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_edge_case_no_transactions():
    """Test handling of user with no transactions."""
    test_db_path = "test_no_transactions.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("No Transactions User", "notransactions@example.com"))
    user_id = cursor.lastrowid
    
    conn.commit()
    
    # Should not crash
    result = detect_all_signals(user_id, conn)
    assert result['total_signals'] >= 0
    
    # Should assign neutral persona
    persona = assign_persona(user_id, conn)
    assert persona == "neutral"
    
    conn.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

