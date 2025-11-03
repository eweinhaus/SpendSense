"""
Unit tests for recommendation generation module.
"""

import sqlite3
import os
import sys
import pytest

# Add src directory to path to import modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from spendsense.database import init_database, get_db_connection
from spendsense.detect_signals import store_signal
from spendsense.personas import assign_persona, store_persona_assignment
from spendsense.recommendations import (
    get_templates_for_persona, select_template, get_user_persona,
    store_recommendation, generate_recommendations
)


@pytest.fixture
def test_db():
    """Create a test database with sample data."""
    test_db_path = "test_recommendations.db"
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


def test_get_templates_for_persona_high_utilization():
    """Test getting templates for High Utilization persona."""
    templates = get_templates_for_persona("high_utilization")
    assert len(templates) >= 3
    assert any(t['key'] == 'reduce_utilization' for t in templates)
    assert any(t['key'] == 'credit_scores' for t in templates)


def test_get_templates_for_persona_subscription_heavy():
    """Test getting templates for Subscription-Heavy persona."""
    templates = get_templates_for_persona("subscription_heavy")
    assert len(templates) >= 3
    assert any(t['key'] == 'audit_subscriptions' for t in templates)
    assert any(t['key'] == 'bill_alerts' for t in templates)


def test_get_templates_for_persona_neutral():
    """Test getting templates for Neutral persona."""
    templates = get_templates_for_persona("neutral")
    assert len(templates) >= 3
    assert any(t['key'] == 'financial_habits' for t in templates)


def test_select_template():
    """Test selecting a specific template by key."""
    templates = get_templates_for_persona("high_utilization")
    template = select_template("reduce_utilization", templates)
    assert template is not None
    assert template['key'] == 'reduce_utilization'
    assert 'title' in template
    assert 'content' in template


def test_select_template_not_found():
    """Test selecting a template that doesn't exist."""
    templates = get_templates_for_persona("high_utilization")
    template = select_template("nonexistent", templates)
    assert template is None


def test_get_user_persona(test_db):
    """Test retrieving user persona."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Assign persona
    store_persona_assignment(user_id, "high_utilization", "Test criteria", conn)
    
    # Get persona
    persona = get_user_persona(user_id, conn)
    assert persona == "high_utilization"
    
    conn.close()


def test_store_recommendation(test_db):
    """Test storing a recommendation in database."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Store recommendation
    rec_id = store_recommendation(
        user_id,
        "Test Title",
        "Test Content",
        "Test Rationale",
        "high_utilization",
        conn
    )
    
    assert rec_id > 0
    
    # Verify stored
    cursor = conn.cursor()
    cursor.execute("SELECT title, content FROM recommendations WHERE id = ?", (rec_id,))
    result = cursor.fetchone()
    assert result is not None
    assert result[0] == "Test Title"
    assert result[1] == "Test Content"
    
    conn.close()


def test_generate_recommendations_high_utilization(test_db):
    """Test generating recommendations for High Utilization user."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals and assign persona
    store_signal(user_id, 'credit_utilization_max', 75.0, {}, '30d', conn)
    assign_persona(user_id, conn)
    
    # Generate recommendations
    rec_ids = generate_recommendations(user_id, conn)
    
    # Should generate 2-3 recommendations
    assert 2 <= len(rec_ids) <= 3
    
    # Verify recommendations stored
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM recommendations WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    assert count == len(rec_ids)
    
    # Verify all have rationales
    cursor.execute("SELECT rationale FROM recommendations WHERE user_id = ?", (user_id,))
    results = cursor.fetchall()
    for row in results:
        assert row[0] is not None
        assert len(row[0]) > 0
    
    conn.close()


def test_generate_recommendations_subscription_heavy(test_db):
    """Test generating recommendations for Subscription-Heavy user."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals and assign persona
    store_signal(user_id, 'subscription_count', 5.0, {}, '30d', conn)
    store_signal(user_id, 'subscription_monthly_spend', 100.0, {}, '30d', conn)
    assign_persona(user_id, conn)
    
    # Generate recommendations
    rec_ids = generate_recommendations(user_id, conn)
    
    # Should generate 2-3 recommendations
    assert 2 <= len(rec_ids) <= 3
    
    conn.close()


def test_generate_recommendations_neutral(test_db):
    """Test generating recommendations for Neutral user."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals that result in neutral persona
    store_signal(user_id, 'credit_utilization_max', 30.0, {}, '30d', conn)
    assign_persona(user_id, conn)
    
    # Generate recommendations
    rec_ids = generate_recommendations(user_id, conn)
    
    # Should generate 2-3 recommendations
    assert 2 <= len(rec_ids) <= 3
    
    conn.close()


def test_generate_recommendations_with_decision_traces(test_db):
    """Test that decision traces are generated for recommendations."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals and assign persona
    store_signal(user_id, 'credit_utilization_max', 75.0, {}, '30d', conn)
    assign_persona(user_id, conn)
    
    # Generate recommendations
    rec_ids = generate_recommendations(user_id, conn)
    
    # Verify decision traces stored (4 steps per recommendation)
    cursor = conn.cursor()
    for rec_id in rec_ids:
        cursor.execute("""
            SELECT COUNT(*) FROM decision_traces 
            WHERE user_id = ? AND recommendation_id = ?
        """, (user_id, rec_id))
        trace_count = cursor.fetchone()[0]
        assert trace_count == 4  # Should have 4 steps
    
    conn.close()


def test_generate_recommendations_autopay_condition(test_db):
    """Test that autopay recommendation is included when overdue/interest present."""
    test_db_path, user_id = test_db
    
    conn = get_db_connection(test_db_path)
    
    # Create signals with overdue/interest
    store_signal(user_id, 'credit_utilization_max', 75.0, {}, '30d', conn)
    store_signal(user_id, 'credit_overdue', 1.0, {}, '30d', conn)
    store_signal(user_id, 'credit_interest_charges', 50.0, {}, '30d', conn)
    assign_persona(user_id, conn)
    
    # Generate recommendations
    rec_ids = generate_recommendations(user_id, conn)
    
    # Verify autopay recommendation is included
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title FROM recommendations 
        WHERE user_id = ? AND title LIKE '%Autopay%'
    """, (user_id,))
    result = cursor.fetchone()
    assert result is not None
    
    conn.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

