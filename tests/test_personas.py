"""
Unit tests for persona assignment module.
"""

import sqlite3
import os
import sys
import pytest
import json

# Add src directory to path to import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from spendsense.database import init_database, get_db_connection
from spendsense.detect_signals import store_signal
from spendsense.personas import (
    get_user_signals, matches_high_utilization, matches_subscription_heavy,
    assign_persona, get_criteria_matched, store_persona_assignment
)


@pytest.fixture
def test_db():
    """Create a test database with sample data."""
    test_db_path = "test_personas.db"
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
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_matches_high_utilization_by_utilization():
    """Test High Utilization matching via utilization >= 50%."""
    signals = [
        {'signal_type': 'credit_utilization_max', 'value': 75.0, 'metadata': {}}
    ]
    assert matches_high_utilization(signals) == True


def test_matches_high_utilization_by_interest():
    """Test High Utilization matching via interest charges."""
    signals = [
        {'signal_type': 'credit_interest_charges', 'value': 50.0, 'metadata': {}}
    ]
    assert matches_high_utilization(signals) == True


def test_matches_high_utilization_by_overdue():
    """Test High Utilization matching via overdue status."""
    signals = [
        {'signal_type': 'credit_overdue', 'value': 1.0, 'metadata': {}}
    ]
    assert matches_high_utilization(signals) == True


def test_matches_high_utilization_no_match():
    """Test High Utilization not matching when criteria not met."""
    signals = [
        {'signal_type': 'credit_utilization_max', 'value': 30.0, 'metadata': {}}
    ]
    assert matches_high_utilization(signals) == False


def test_matches_subscription_heavy_by_count_and_spend():
    """Test Subscription-Heavy matching via count >= 3 and spend >= $50."""
    signals = [
        {'signal_type': 'subscription_count', 'value': 5.0, 'metadata': {}},
        {'signal_type': 'subscription_monthly_spend', 'value': 75.0, 'metadata': {}}
    ]
    assert matches_subscription_heavy(signals) == True


def test_matches_subscription_heavy_by_count_and_share():
    """Test Subscription-Heavy matching via count >= 3 and share >= 10%."""
    signals = [
        {'signal_type': 'subscription_count', 'value': 4.0, 'metadata': {}},
        {'signal_type': 'subscription_share', 'value': 15.0, 'metadata': {}}
    ]
    assert matches_subscription_heavy(signals) == True


def test_matches_subscription_heavy_no_match_low_count():
    """Test Subscription-Heavy not matching when count < 3."""
    signals = [
        {'signal_type': 'subscription_count', 'value': 2.0, 'metadata': {}}
    ]
    assert matches_subscription_heavy(signals) == False


def test_matches_subscription_heavy_no_match_low_spend():
    """Test Subscription-Heavy not matching when spend/share too low."""
    signals = [
        {'signal_type': 'subscription_count', 'value': 5.0, 'metadata': {}},
        {'signal_type': 'subscription_monthly_spend', 'value': 30.0, 'metadata': {}},
        {'signal_type': 'subscription_share', 'value': 5.0, 'metadata': {}}
    ]
    assert matches_subscription_heavy(signals) == False


def test_assign_persona_high_utilization(test_db):
    """Test persona assignment for High Utilization user."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals for high utilization
    store_signal(user_id, 'credit_utilization_max', 80.0, {}, '30d', conn)
    store_signal(user_id, 'credit_interest_charges', 100.0, {}, '30d', conn)
    
    # Assign persona
    persona = assign_persona(user_id, conn)
    
    assert persona == "high_utilization"
    
    # Verify stored in database
    cursor = conn.cursor()
    cursor.execute("SELECT persona_type, criteria_matched FROM personas WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "high_utilization"
    assert "utilization" in result[1].lower() or "interest" in result[1].lower()
    
    conn.close()


def test_assign_persona_subscription_heavy(test_db):
    """Test persona assignment for Subscription-Heavy user."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals for subscription heavy
    store_signal(user_id, 'subscription_count', 5.0, {}, '30d', conn)
    store_signal(user_id, 'subscription_monthly_spend', 100.0, {}, '30d', conn)
    
    # Assign persona
    persona = assign_persona(user_id, conn)
    
    assert persona == "subscription_heavy"
    
    conn.close()


def test_assign_persona_priority_high_utilization_wins(test_db):
    """Test that High Utilization takes priority over Subscription-Heavy."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals matching both personas
    store_signal(user_id, 'credit_utilization_max', 75.0, {}, '30d', conn)
    store_signal(user_id, 'subscription_count', 5.0, {}, '30d', conn)
    store_signal(user_id, 'subscription_monthly_spend', 100.0, {}, '30d', conn)
    
    # Assign persona - should be high_utilization due to priority
    persona = assign_persona(user_id, conn)
    
    assert persona == "high_utilization"
    
    conn.close()


def test_assign_persona_neutral_fallback(test_db):
    """Test Neutral persona assignment when no criteria match."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals that don't match any persona
    store_signal(user_id, 'credit_utilization_max', 30.0, {}, '30d', conn)
    store_signal(user_id, 'subscription_count', 1.0, {}, '30d', conn)
    
    # Assign persona
    persona = assign_persona(user_id, conn)
    
    assert persona == "neutral"
    
    # Verify stored in database
    cursor = conn.cursor()
    cursor.execute("SELECT persona_type, criteria_matched FROM personas WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "neutral"
    
    conn.close()


def test_get_criteria_matched_high_utilization():
    """Test criteria matching explanation for High Utilization."""
    signals = [
        {
            'signal_type': 'credit_utilization_max',
            'value': 75.0,
            'metadata': {
                'cards': [{
                    'account_id': 'acc123456',
                    'balance': 3750.0,
                    'limit': 5000.0
                }]
            }
        }
    ]
    
    criteria = get_criteria_matched("high_utilization", signals)
    assert "75%" in criteria or "utilization" in criteria.lower()


def test_get_criteria_matched_subscription_heavy():
    """Test criteria matching explanation for Subscription-Heavy."""
    signals = [
        {
            'signal_type': 'subscription_merchants',
            'value': None,
            'metadata': {
                'merchants': ['Netflix', 'Spotify', 'Gym']
            }
        },
        {'signal_type': 'subscription_count', 'value': 3.0, 'metadata': {}},
        {'signal_type': 'subscription_monthly_spend', 'value': 90.0, 'metadata': {}}
    ]
    
    criteria = get_criteria_matched("subscription_heavy", signals)
    assert "3" in criteria or "recurring" in criteria.lower()


def test_get_user_signals(test_db):
    """Test retrieving user signals."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Store signals
    store_signal(user_id, 'credit_utilization_max', 75.0, {'test': 'data'}, '30d', conn)
    store_signal(user_id, 'subscription_count', 3.0, {}, '30d', conn)
    
    # Get signals
    signals = get_user_signals(user_id, conn)
    
    assert len(signals) == 2
    signal_types = {s['signal_type'] for s in signals}
    assert 'credit_utilization_max' in signal_types
    assert 'subscription_count' in signal_types
    
    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

