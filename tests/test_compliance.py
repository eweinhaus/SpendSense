"""
Tests for compliance and audit logging module.
Phase 8B: Compliance & Audit Interface
"""

import pytest
import os
import tempfile
import json
from datetime import datetime
from spendsense.database import init_database, get_db_connection
from spendsense.compliance import (
    log_consent_change, check_recommendation_compliance,
    check_consent_at_generation, check_eligibility_was_performed,
    check_disclaimer_present, check_decision_trace_complete,
    check_rationale_has_data, get_compliance_metrics,
    get_recent_compliance_issues, get_consent_audit_log,
    get_all_recommendations_with_compliance,
    get_recommendation_compliance_detail,
    generate_consent_audit_report, generate_recommendation_compliance_report,
    generate_compliance_summary_report
)


@pytest.fixture
def test_db():
    """Create a temporary test database with test data."""
    fd, test_db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Initialize database
    init_database(test_db_path)
    
    # Create test users
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    
    # User 1: With consent
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("User With Consent", "user1@example.com", 1))
    user1_id = cursor.lastrowid
    
    # User 2: Without consent
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, ("User Without Consent", "user2@example.com", 0))
    user2_id = cursor.lastrowid
    
    # Create a recommendation for user 1 with disclaimer
    cursor.execute("""
        INSERT INTO recommendations (user_id, title, content, rationale, persona_matched)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user1_id,
        "Test Recommendation",
        "This is a test recommendation. This is not financial advice. Please consult a financial advisor.",
        "Based on your credit utilization of 75% and $5,000 balance, we recommend reducing spending.",
        "high_utilization"
    ))
    rec_id = cursor.lastrowid
    
    # Create decision traces (all 4 steps)
    for step in range(1, 5):
        cursor.execute("""
            INSERT INTO decision_traces (user_id, recommendation_id, step, reasoning, data_cited)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user1_id,
            rec_id,
            step,
            f"Step {step} reasoning",
            json.dumps({"test": "data"})
        ))
    
    conn.commit()
    conn.close()
    
    yield test_db_path, user1_id, user2_id, rec_id
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_log_consent_change(test_db):
    """Test consent change logging."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Log consent grant
    result = log_consent_change(user1_id, 'granted', 'operator', False, 
                                conn=get_db_connection(test_db_path))
    assert result is True
    
    # Verify log entry
    conn = get_db_connection(test_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM consent_audit_log WHERE user_id = ?", (user1_id,))
    entries = cursor.fetchall()
    assert len(entries) > 0
    assert entries[0][2] == 'granted'  # action
    assert entries[0][4] == 'operator'  # changed_by
    conn.close()


def test_check_consent_at_generation(test_db):
    """Test consent at generation check."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Should pass (recommendation exists, so consent was active)
    result = check_consent_at_generation(rec_id, conn=get_db_connection(test_db_path))
    assert result is True


def test_check_eligibility_was_performed(test_db):
    """Test eligibility check verification."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Should pass (recommendation exists)
    result = check_eligibility_was_performed(rec_id, conn=get_db_connection(test_db_path))
    assert result is True


def test_check_disclaimer_present(test_db):
    """Test disclaimer presence check."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Should pass (content has disclaimer)
    result = check_disclaimer_present(rec_id, conn=get_db_connection(test_db_path))
    assert result is True


def test_check_decision_trace_complete(test_db):
    """Test decision trace completeness check."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Should pass (all 4 steps exist)
    result = check_decision_trace_complete(rec_id, conn=get_db_connection(test_db_path))
    assert result is True


def test_check_rationale_has_data(test_db):
    """Test rationale data citation check."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Should pass (rationale has numbers and keywords)
    result = check_rationale_has_data(rec_id, conn=get_db_connection(test_db_path))
    assert result is True


def test_check_recommendation_compliance(test_db):
    """Test full compliance check."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    result = check_recommendation_compliance(rec_id, conn=get_db_connection(test_db_path))
    
    assert 'compliant' in result
    assert 'checks' in result
    assert 'recommendation_id' in result
    assert result['recommendation_id'] == rec_id
    
    # All checks should pass for this recommendation
    assert result['checks']['active_consent'] is True
    assert result['checks']['eligibility_check'] is True
    assert result['checks']['required_disclaimer'] is True
    assert result['checks']['complete_trace'] is True
    assert result['checks']['rationale_cites_data'] is True
    assert result['compliant'] is True


def test_get_compliance_metrics(test_db):
    """Test compliance metrics calculation."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    metrics = get_compliance_metrics(conn=get_db_connection(test_db_path))
    
    assert 'consent_coverage' in metrics
    assert 'tone_violations' in metrics
    assert 'eligibility_failures' in metrics
    assert 'recommendation_compliance' in metrics
    
    # Should have 50% consent coverage (1 of 2 users)
    assert metrics['consent_coverage'] == 50.0


def test_get_recent_compliance_issues(test_db):
    """Test recent compliance issues detection."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    issues = get_recent_compliance_issues(conn=get_db_connection(test_db_path))
    
    # Should be a list
    assert isinstance(issues, list)
    # Recommendation has disclaimer, so no issues
    assert len(issues) == 0


def test_get_consent_audit_log(test_db):
    """Test consent audit log querying."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Log a change
    log_consent_change(user1_id, 'granted', 'operator', False,
                      conn=get_db_connection(test_db_path))
    
    # Query log
    log = get_consent_audit_log(conn=get_db_connection(test_db_path))
    
    assert len(log) > 0
    assert log[0]['user_id'] == user1_id
    assert log[0]['action'] == 'granted'


def test_get_all_recommendations_with_compliance(test_db):
    """Test getting recommendations with compliance status."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    recommendations = get_all_recommendations_with_compliance(
        conn=get_db_connection(test_db_path)
    )
    
    assert len(recommendations) > 0
    assert recommendations[0]['id'] == rec_id
    assert 'compliant' in recommendations[0]
    assert 'checks' in recommendations[0]


def test_get_recommendation_compliance_detail(test_db):
    """Test detailed compliance report."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    detail = get_recommendation_compliance_detail(
        rec_id, conn=get_db_connection(test_db_path)
    )
    
    assert detail is not None
    assert 'recommendation' in detail
    assert 'user' in detail
    assert 'compliance' in detail
    assert 'decision_traces' in detail
    assert len(detail['decision_traces']) == 4


def test_generate_consent_audit_report(test_db):
    """Test consent audit report generation."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Log a change
    log_consent_change(user1_id, 'granted', 'operator', False,
                      conn=get_db_connection(test_db_path))
    
    # Generate CSV report
    report = generate_consent_audit_report('csv', conn=get_db_connection(test_db_path))
    assert report['format'] == 'csv'
    assert 'data' in report
    assert 'total_records' in report
    
    # Generate JSON report
    report = generate_consent_audit_report('json', conn=get_db_connection(test_db_path))
    assert report['format'] == 'json'
    assert 'data' in report


def test_generate_recommendation_compliance_report(test_db):
    """Test recommendation compliance report generation."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Generate CSV report
    report = generate_recommendation_compliance_report(
        'csv', conn=get_db_connection(test_db_path)
    )
    assert report['format'] == 'csv'
    assert 'data' in report
    
    # Generate JSON report
    report = generate_recommendation_compliance_report(
        'json', conn=get_db_connection(test_db_path)
    )
    assert report['format'] == 'json'
    assert 'data' in report


def test_generate_compliance_summary_report(test_db):
    """Test compliance summary report generation."""
    test_db_path, user1_id, user2_id, rec_id = test_db
    
    # Generate Markdown report
    report = generate_compliance_summary_report(
        'markdown', conn=get_db_connection(test_db_path)
    )
    assert report['format'] == 'markdown'
    assert 'data' in report
    assert 'SpendSense Compliance Summary Report' in report['data']
    
    # Generate JSON report
    report = generate_compliance_summary_report(
        'json', conn=get_db_connection(test_db_path)
    )
    assert report['format'] == 'json'
    assert 'metrics' in report
    assert 'recent_issues' in report

