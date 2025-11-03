"""
Integration tests for full Phase 2 pipeline.
Tests signals → personas → recommendations flow.
"""

import sqlite3
import os
import sys
import pytest

# Add src directory to path to import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from spendsense.database import init_database, get_db_connection
from spendsense.detect_signals import detect_credit_signals, detect_subscription_signals
from spendsense.personas import assign_persona
from spendsense.recommendations import generate_recommendations


@pytest.fixture
def test_db():
    """Create a test database with sample data."""
    test_db_path = "test_integration.db"
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
    """, ("Integration Test User", "integration@example.com"))
    user_id = cursor.lastrowid
    
    # Create credit card account
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, current_balance, "limit"
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, "acc_credit_001", "credit", "credit card", 4500.0, 5000.0))
    account_id = cursor.lastrowid
    
    # Create credit card liability data
    cursor.execute("""
        INSERT INTO credit_cards (
            account_id, apr, minimum_payment_amount, is_overdue
        ) VALUES (?, ?, ?, ?)
    """, (account_id, 22.0, 90.0, False))
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user_id
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_full_pipeline_high_utilization(test_db):
    """Test full pipeline: signals → persona → recommendations for High Utilization."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Step 1: Detect signals
    credit_result = detect_credit_signals(user_id, conn)
    assert credit_result['signals_stored'] > 0
    
    # Step 2: Assign persona
    persona = assign_persona(user_id, conn)
    assert persona == "high_utilization"
    
    # Verify persona stored
    cursor = conn.cursor()
    cursor.execute("SELECT persona_type FROM personas WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "high_utilization"
    
    # Step 3: Generate recommendations
    rec_ids = generate_recommendations(user_id, conn)
    assert 2 <= len(rec_ids) <= 3
    
    # Verify recommendations stored
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    assert count == len(rec_ids)
    
    # Verify all recommendations have rationales
    cursor.execute("SELECT rationale FROM recommendations WHERE user_id = ?", (user_id,))
    results = cursor.fetchall()
    for row in results:
        assert row[0] is not None
        assert len(row[0]) > 0
        assert "This is educational content" in row[0]  # Disclaimer present
    
    # Verify decision traces stored
    cursor.execute("""
        SELECT COUNT(DISTINCT recommendation_id) FROM decision_traces 
        WHERE user_id = ?
    """, (user_id,))
    trace_count = cursor.fetchone()[0]
    assert trace_count == len(rec_ids)
    
    # Verify each recommendation has 4 trace steps
    for rec_id in rec_ids:
        cursor.execute("""
            SELECT COUNT(*) FROM decision_traces 
            WHERE user_id = ? AND recommendation_id = ?
        """, (user_id, rec_id))
        step_count = cursor.fetchone()[0]
        assert step_count == 4
    
    conn.close()


def test_full_pipeline_multiple_users():
    """Test full pipeline for multiple users."""
    test_db_path = "test_integration_multi.db"
    # Remove test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Initialize test database
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Create multiple users
    user_ids = []
    for i in range(3):
        cursor.execute("""
            INSERT INTO users (name, email) VALUES (?, ?)
        """, (f"User {i+1}", f"user{i+1}@example.com"))
        user_id = cursor.lastrowid
        user_ids.append(user_id)
        
        # Create credit card for first two users
        if i < 2:
            cursor.execute("""
                INSERT INTO accounts (
                    user_id, account_id, type, subtype, current_balance, "limit"
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, f"acc_{i}", "credit", "credit card", 
                  4000.0 if i == 0 else 2000.0, 5000.0))
            account_id = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO credit_cards (
                    account_id, apr, minimum_payment_amount
                ) VALUES (?, ?, ?)
            """, (account_id, 22.0, 80.0))
    
    conn.commit()
    
    # Process each user
    for user_id in user_ids:
        # Detect signals
        detect_credit_signals(user_id, conn)
        
        # Assign persona
        persona = assign_persona(user_id, conn)
        assert persona in ["high_utilization", "neutral", "subscription_heavy"]
        
        # Generate recommendations
        rec_ids = generate_recommendations(user_id, conn)
        assert 2 <= len(rec_ids) <= 3
    
    # Verify all users have personas
    cursor.execute("SELECT COUNT(*) FROM personas")
    persona_count = cursor.fetchone()[0]
    assert persona_count == 3
    
    # Verify all users have recommendations
    cursor.execute("SELECT COUNT(DISTINCT user_id) FROM recommendations")
    rec_user_count = cursor.fetchone()[0]
    assert rec_user_count == 3
    
    conn.close()
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_edge_case_no_signals():
    """Test handling of user with no signals."""
    test_db_path = "test_integration_no_signals.db"
    # Remove test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Initialize test database
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Create user with no signals
    cursor.execute("""
        INSERT INTO users (name, email) VALUES (?, ?)
    """, ("No Signals User", "nosignals@example.com"))
    user_id = cursor.lastrowid
    conn.commit()
    
    # Assign persona (should be neutral)
    persona = assign_persona(user_id, conn)
    assert persona == "neutral"
    
    # Generate recommendations (should still work)
    rec_ids = generate_recommendations(user_id, conn)
    assert 2 <= len(rec_ids) <= 3
    
    conn.close()
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

