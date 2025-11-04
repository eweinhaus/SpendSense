"""
Tests for evaluation harness module.
"""

import pytest
import os
import tempfile
import json
from spendsense.database import init_database, get_db_connection
from spendsense.evaluation import (
    calculate_coverage, calculate_explainability, calculate_relevance,
    calculate_latency, calculate_fairness
)


@pytest.fixture
def test_db_with_data():
    """Create a test database with sample data."""
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database
    init_database(test_db_path)
    
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # Create users
    for i in range(5):
        cursor.execute("""
            INSERT INTO users (name, email, consent_given)
            VALUES (?, ?, ?)
        """, (f"User {i}", f"user{i}@example.com", 1))
        user_id = cursor.lastrowid
        
        # Assign personas
        cursor.execute("""
            INSERT INTO personas (user_id, persona_type, criteria_matched)
            VALUES (?, ?, ?)
        """, (user_id, "high_utilization", "utilization > 80%"))
        
        # Add signals (≥3 for coverage)
        for j in range(3):
            cursor.execute("""
                INSERT INTO signals (user_id, signal_type, value, metadata, window)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, f"signal_{j}", 10.0, '{}', '30d'))
        
        # Add recommendations with rationales
        cursor.execute("""
            INSERT INTO recommendations (user_id, title, content, rationale, persona_matched)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            "Reduce Credit Utilization",
            "Content here",
            "Based on your utilization of 85%",
            "high_utilization"
        ))
    
    conn.commit()
    conn.close()
    
    yield test_db_path
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_calculate_coverage(test_db_with_data):
    """Test coverage calculation."""
    test_db_path = test_db_with_data
    conn = get_db_connection(test_db_path)
    
    try:
        coverage = calculate_coverage(conn)
        
        assert 'total_users' in coverage
        assert 'users_with_personas' in coverage
        assert 'users_with_3plus_behaviors' in coverage
        assert 'users_with_both' in coverage
        assert 'combined_coverage_pct' in coverage
        assert coverage['total_users'] == 5
        assert coverage['users_with_personas'] == 5
        assert coverage['users_with_3plus_behaviors'] == 5
        assert coverage['users_with_both'] == 5
        assert coverage['combined_coverage_pct'] == 100.0
        assert coverage['target_met'] is True
    finally:
        conn.close()


def test_calculate_explainability(test_db_with_data):
    """Test explainability calculation."""
    test_db_path = test_db_with_data
    conn = get_db_connection(test_db_path)
    
    try:
        explainability = calculate_explainability(conn)
        
        assert 'total_recommendations' in explainability
        assert 'recommendations_with_rationales' in explainability
        assert 'explainability_pct' in explainability
        assert explainability['total_recommendations'] == 5
        assert explainability['recommendations_with_rationales'] == 5
        assert explainability['explainability_pct'] == 100.0
        assert explainability['target_met'] is True
    finally:
        conn.close()


def test_calculate_relevance(test_db_with_data):
    """Test relevance calculation."""
    test_db_path = test_db_with_data
    conn = get_db_connection(test_db_path)
    
    try:
        relevance = calculate_relevance(conn)
        
        assert 'total_recommendations' in relevance
        assert 'relevant_recommendations' in relevance
        assert 'relevance_pct' in relevance
        assert 'average_fit_score' in relevance
        assert relevance['total_recommendations'] == 5
        # Credit utilization recommendation should match high_utilization persona
        assert relevance['relevant_recommendations'] >= 1
    finally:
        conn.close()


def test_calculate_fairness(test_db_with_data):
    """Test fairness calculation."""
    test_db_path = test_db_with_data
    conn = get_db_connection(test_db_path)
    
    try:
        fairness = calculate_fairness(conn)
        
        assert 'persona_distribution' in fairness
        assert 'recommendation_distribution' in fairness
        assert 'persona_percentages' in fairness
        assert 'recommendation_percentages' in fairness
        assert 'high_utilization' in fairness['persona_distribution']
        assert fairness['persona_distribution']['high_utilization'] == 5
    finally:
        conn.close()


def test_calculate_latency_empty_db():
    """Test latency calculation with empty database."""
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    
    try:
        latency = calculate_latency(conn, sample_size=5)
        
        assert 'sample_size' in latency
        assert 'average_latency_seconds' in latency
        assert latency['sample_size'] == 0
    finally:
        conn.close()
        if os.path.exists(test_db_path):
            os.remove(test_db_path)

