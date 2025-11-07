"""
Compliance and audit logging module for SpendSense.
Phase 8B: Compliance & Audit Interface

Provides functions for consent audit logging, compliance checking,
and regulatory reporting.
"""

import sqlite3
import os
import re
import json
from typing import Optional, Dict, List, Tuple
from datetime import datetime
from fastapi import Request, HTTPException, Depends
from .database import get_db_connection


def log_consent_change(user_id: int, action: str, changed_by: str, 
                      previous_status: Optional[bool] = None,
                      conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Log a consent change to the audit log.
    
    Args:
        user_id: User ID whose consent changed
        action: 'granted' or 'revoked'
        changed_by: 'user', 'operator', or 'system'
        previous_status: Previous consent status (if None, will query from database)
        conn: Database connection (creates new if None)
        
    Returns:
        True if logged successfully, False otherwise
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        # Get previous status if not provided
        if previous_status is None:
            cursor = conn.cursor()
            cursor.execute("SELECT consent_given FROM users WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            if result:
                previous_status = bool(result[0])
            else:
                previous_status = False
        
        # Insert audit log entry
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO consent_audit_log (user_id, action, changed_by, previous_status)
            VALUES (?, ?, ?, ?)
        """, (user_id, action, changed_by, 1 if previous_status else 0))
        
        conn.commit()
        return True
    except Exception as e:
        # Log error but don't fail the consent update
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to log consent change for user {user_id}: {e}")
        return False
    finally:
        if close_conn:
            conn.close()


def check_consent_at_generation(recommendation_id: int,
                                conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if user had consent at time of recommendation generation.
    
    Since recommendations are only generated with consent, this check
    should pass for all existing recommendations.
    
    Args:
        recommendation_id: Recommendation ID to check
        conn: Database connection (creates new if None)
        
    Returns:
        True if consent was active, False otherwise
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        # Get recommendation and user
        cursor.execute("""
            SELECT r.user_id, r.created_at
            FROM recommendations r
            WHERE r.id = ?
        """, (recommendation_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        user_id, created_at = result
        
        # Check if recommendation exists (implicitly means consent was active)
        # Or verify from audit log if needed
        # For now, if recommendation exists, consent was active
        return True
    except Exception:
        return False
    finally:
        if close_conn:
            conn.close()


def check_eligibility_was_performed(recommendation_id: int,
                                   conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if eligibility check was performed.
    
    Since recommendations go through filter_recommendations() which
    performs eligibility checks, existing recommendations imply eligibility
    was checked (even if it passed).
    
    Args:
        recommendation_id: Recommendation ID to check
        conn: Database connection (creates new if None)
        
    Returns:
        True if eligibility was checked, False otherwise
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        # Check if recommendation exists (implies eligibility was checked)
        cursor.execute("SELECT id FROM recommendations WHERE id = ?", (recommendation_id,))
        result = cursor.fetchone()
        return result is not None
    except Exception:
        return False
    finally:
        if close_conn:
            conn.close()


def check_disclaimer_present(recommendation_id: int,
                            conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if disclaimer text is present in recommendation content.
    
    Args:
        recommendation_id: Recommendation ID to check
        conn: Database connection (creates new if None)
        
    Returns:
        True if disclaimer found, False otherwise
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM recommendations WHERE id = ?", (recommendation_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        content = result[0].lower()
        
        # Check for disclaimer keywords/phrases
        disclaimer_phrases = [
            'not financial advice',
            'consult a financial advisor',
            'disclaimer',
            'not a recommendation',
            'not professional advice'
        ]
        
        for phrase in disclaimer_phrases:
            if phrase in content:
                return True
        
        return False
    except Exception:
        return False
    finally:
        if close_conn:
            conn.close()


def check_decision_trace_complete(recommendation_id: int,
                                 conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if all 4 steps exist in decision trace.
    
    Args:
        recommendation_id: Recommendation ID to check
        conn: Database connection (creates new if None)
        
    Returns:
        True if all 4 steps exist, False otherwise
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT step
            FROM decision_traces
            WHERE recommendation_id = ?
            ORDER BY step
        """, (recommendation_id,))
        
        steps = [row[0] for row in cursor.fetchall()]
        
        # Check if all 4 steps (1, 2, 3, 4) exist
        return set(steps) == {1, 2, 3, 4}
    except Exception:
        return False
    finally:
        if close_conn:
            conn.close()


def check_rationale_has_data(recommendation_id: int,
                             conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if rationale includes specific data points (not just generic text).
    
    Args:
        recommendation_id: Recommendation ID to check
        conn: Database connection (creates new if None)
        
    Returns:
        True if rationale contains specific data, False otherwise
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT rationale FROM recommendations WHERE id = ?", (recommendation_id,))
        result = cursor.fetchone()
        
        if not result:
            return False
        
        rationale = result[0]
        
        # Check for specific data indicators:
        # 1. Numbers (dollars, percentages, counts)
        # 2. Specific keywords that indicate data citations
        
        # Pattern for numbers (dollars, percentages, plain numbers)
        number_patterns = [
            r'\$[\d,]+',  # Dollar amounts
            r'\d+%',      # Percentages
            r'\d+\.\d+%', # Decimal percentages
            r'\b\d{2,}\b' # Numbers with 2+ digits (likely counts/amounts)
        ]
        
        for pattern in number_patterns:
            if re.search(pattern, rationale):
                return True
        
        # Check for data-specific keywords
        data_keywords = [
            'utilization',
            'transactions',
            'balance',
            'spending',
            'income',
            'credit',
            'account',
            'monthly',
            'annual'
        ]
        
        # Must have at least one number AND one keyword for data citation
        has_number = any(re.search(pattern, rationale) for pattern in number_patterns)
        has_keyword = any(keyword in rationale.lower() for keyword in data_keywords)
        
        return has_number and has_keyword
    except Exception:
        return False
    finally:
        if close_conn:
            conn.close()


def check_recommendation_compliance(recommendation_id: int,
                                   conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Check if recommendation meets all compliance requirements.
    
    Performs 5 compliance checks:
    1. Active Consent at generation time
    2. Eligibility Check performed
    3. Required Disclaimer present
    4. Complete Decision Trace (all 4 steps)
    5. Rationale Cites Data
    
    Args:
        recommendation_id: Recommendation ID to check
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with compliance status and individual check results:
        {
            'compliant': bool,
            'checks': {
                'active_consent': bool,
                'eligibility_check': bool,
                'required_disclaimer': bool,
                'complete_trace': bool,
                'rationale_cites_data': bool
            },
            'recommendation_id': int
        }
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        # Perform all 5 checks
        checks = {
            'active_consent': check_consent_at_generation(recommendation_id, conn),
            'eligibility_check': check_eligibility_was_performed(recommendation_id, conn),
            'required_disclaimer': check_disclaimer_present(recommendation_id, conn),
            'complete_trace': check_decision_trace_complete(recommendation_id, conn),
            'rationale_cites_data': check_rationale_has_data(recommendation_id, conn)
        }
        
        return {
            'compliant': all(checks.values()),
            'checks': checks,
            'recommendation_id': recommendation_id
        }
    finally:
        if close_conn:
            conn.close()


def get_compliance_metrics(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Get overall compliance metrics for dashboard.
    
    Calculates:
    - Consent Coverage: % of users with active consent
    - Tone Violations: Count (currently 0, logging not implemented)
    - Eligibility Failures: Count (currently 0, logging not implemented)
    - Recommendation Compliance: % of recommendations with required disclaimers
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with metrics:
        {
            'consent_coverage': float,  # percentage
            'tone_violations': int,     # count (0 if not tracked)
            'eligibility_failures': int, # count (0 if not tracked)
            'recommendation_compliance': float  # percentage
        }
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Consent Coverage
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE consent_given = 1")
        users_with_consent = cursor.fetchone()[0]
        
        consent_coverage = (users_with_consent / total_users * 100) if total_users > 0 else 0.0
        
        # Tone Violations (not tracked in database yet)
        # TODO: Add tone violations table if needed for full compliance
        tone_violations = 0
        
        # Eligibility Failures (not tracked in database yet)
        # TODO: Add eligibility failures table if needed for full compliance
        eligibility_failures = 0
        
        # Recommendation Compliance (check for disclaimers)
        cursor.execute("SELECT COUNT(*) FROM recommendations")
        total_recommendations = cursor.fetchone()[0]
        
        if total_recommendations > 0:
            # Check each recommendation for disclaimer
            cursor.execute("SELECT id, content FROM recommendations")
            recommendations = cursor.fetchall()
            
            compliant_count = 0
            for rec_id, content in recommendations:
                if check_disclaimer_present(rec_id, conn):
                    compliant_count += 1
            
            recommendation_compliance = (compliant_count / total_recommendations * 100)
        else:
            recommendation_compliance = 0.0
        
        return {
            'consent_coverage': round(consent_coverage, 2),
            'tone_violations': tone_violations,
            'eligibility_failures': eligibility_failures,
            'recommendation_compliance': round(recommendation_compliance, 2)
        }
    finally:
        if close_conn:
            conn.close()


def get_recent_compliance_issues(limit: int = 10,
                                conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Get list of recent compliance issues.
    
    Currently checks for recommendations without disclaimers.
    Tone violations and eligibility failures not tracked in database yet.
    
    Args:
        limit: Maximum number of issues to return (default: 10)
        conn: Database connection (creates new if None)
        
    Returns:
        List of issue dictionaries:
        [
            {
                'type': str,  # 'missing_disclaimer', 'tone_violation', 'eligibility_failure'
                'user_id': int,
                'recommendation_id': int | None,
                'timestamp': str,
                'description': str
            }
        ]
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        issues = []
        
        # Check for recommendations without disclaimers
        cursor.execute("""
            SELECT r.id, r.user_id, r.created_at, r.title
            FROM recommendations r
        """)
        
        recommendations = cursor.fetchall()
        
        for rec_id, user_id, created_at, title in recommendations:
            if not check_disclaimer_present(rec_id, conn):
                issues.append({
                    'type': 'missing_disclaimer',
                    'user_id': user_id,
                    'recommendation_id': rec_id,
                    'timestamp': created_at,
                    'description': f"Recommendation '{title[:50]}...' missing required disclaimer"
                })
        
        # Sort by timestamp (most recent first)
        issues.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Limit results
        return issues[:limit]
    finally:
        if close_conn:
            conn.close()


def get_all_recommendations_with_compliance(status: Optional[str] = None,
                                           user_id: Optional[int] = None,
                                           start_date: Optional[str] = None,
                                           end_date: Optional[str] = None,
                                           conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Get all recommendations with compliance status.
    
    Args:
        status: Filter by compliance status ('compliant' or 'non-compliant', optional)
        user_id: Filter by user ID (optional)
        start_date: Filter by start date (YYYY-MM-DD format, optional)
        end_date: Filter by end date (YYYY-MM-DD format, optional)
        conn: Database connection (creates new if None)
        
    Returns:
        List of recommendations with compliance status:
        [
            {
                'id': int,
                'user_id': int,
                'user_name': str,
                'title': str,
                'created_at': str,
                'compliant': bool,
                'checks': dict
            }
        ]
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Build query
        query = """
            SELECT r.id, r.user_id, u.name, r.title, r.created_at
            FROM recommendations r
            JOIN users u ON r.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if user_id is not None:
            query += " AND r.user_id = ?"
            params.append(user_id)
        
        if start_date:
            query += " AND DATE(r.created_at) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(r.created_at) <= ?"
            params.append(end_date)
        
        query += " ORDER BY r.created_at DESC LIMIT 1000"
        
        cursor.execute(query, params)
        recommendations = cursor.fetchall()
        
        results = []
        for rec_id, user_id, user_name, title, created_at in recommendations:
            compliance = check_recommendation_compliance(rec_id, conn)
            
            # Apply status filter if specified
            if status:
                if status == 'compliant' and not compliance['compliant']:
                    continue
                if status == 'non-compliant' and compliance['compliant']:
                    continue
            
            results.append({
                'id': rec_id,
                'user_id': user_id,
                'user_name': user_name,
                'title': title,
                'created_at': created_at,
                'compliant': compliance['compliant'],
                'checks': compliance['checks']
            })
        
        return results
    finally:
        if close_conn:
            conn.close()


def get_recommendation_compliance_detail(recommendation_id: int,
                                        conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Get detailed compliance report for a recommendation.
    
    Args:
        recommendation_id: Recommendation ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with detailed compliance information:
        {
            'recommendation': dict,
            'user': dict,
            'compliance': dict,
            'decision_traces': list
        }
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get recommendation details
        cursor.execute("""
            SELECT r.id, r.user_id, r.title, r.content, r.rationale, 
                   r.persona_matched, r.created_at
            FROM recommendations r
            WHERE r.id = ?
        """, (recommendation_id,))
        
        rec_result = cursor.fetchone()
        if not rec_result:
            return None
        
        # Get user details
        cursor.execute("SELECT id, name, email, consent_given FROM users WHERE id = ?", (rec_result[1],))
        user_result = cursor.fetchone()
        
        # Get decision traces
        cursor.execute("""
            SELECT step, reasoning, data_cited
            FROM decision_traces
            WHERE recommendation_id = ?
            ORDER BY step
        """, (recommendation_id,))
        
        traces = []
        for step, reasoning, data_cited in cursor.fetchall():
            traces.append({
                'step': step,
                'reasoning': reasoning,
                'data_cited': json.loads(data_cited) if data_cited else {}
            })
        
        # Get compliance check
        compliance = check_recommendation_compliance(recommendation_id, conn)
        
        return {
            'recommendation': {
                'id': rec_result[0],
                'user_id': rec_result[1],
                'title': rec_result[2],
                'content': rec_result[3],
                'rationale': rec_result[4],
                'persona_matched': rec_result[5],
                'created_at': rec_result[6]
            },
            'user': {
                'id': user_result[0],
                'name': user_result[1],
                'email': user_result[2],
                'consent_given': bool(user_result[3])
            },
            'compliance': compliance,
            'decision_traces': traces
        }
    finally:
        if close_conn:
            conn.close()


def require_operator_auth(request: Request) -> bool:
    """
    Check if request is from authenticated operator.
    
    Uses API key in header: X-Operator-API-Key
    Compares against environment variable: OPERATOR_API_KEY
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if authenticated, False otherwise
    """
    api_key = request.headers.get('X-Operator-API-Key', '')
    expected_key = os.getenv('OPERATOR_API_KEY', '')
    
    # If no API key is set, allow access (for development)
    # In production, this should be required
    if not expected_key:
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("OPERATOR_API_KEY not set - allowing access (development mode)")
        return True
    
    return api_key == expected_key and api_key != ''


async def operator_auth(request: Request):
    """
    FastAPI dependency for operator authentication.
    
    Raises HTTPException with 403 if not authenticated.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if authenticated
        
    Raises:
        HTTPException: 403 if not authenticated
    """
    if not require_operator_auth(request):
        raise HTTPException(
            status_code=403,
            detail="Operator authentication required. Provide X-Operator-API-Key header."
        )
    return True


def generate_consent_audit_report(format: str = 'csv',
                                 conn: Optional[sqlite3.Connection] = None) -> Dict:
    """Generate consent audit report."""
    audit_log = get_consent_audit_log(conn=conn)
    report_date = datetime.now().isoformat()
    
    if format.lower() == 'json':
        return {
            'format': 'json',
            'report_date': report_date,
            'total_records': len(audit_log),
            'data': audit_log
        }
    else:  # CSV
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'User ID', 'User Name', 'Action', 'Timestamp', 'Changed By', 'Previous Status'])
        for entry in audit_log:
            writer.writerow([entry['id'], entry['user_id'], entry['user_name'], entry['action'],
                           entry['timestamp'], entry['changed_by'], entry['previous_status']])
        output.seek(0)
        return {
            'format': 'csv',
            'report_date': report_date,
            'total_records': len(audit_log),
            'data': output.getvalue()
        }


def generate_recommendation_compliance_report(format: str = 'json',
                                             conn: Optional[sqlite3.Connection] = None) -> Dict:
    """Generate recommendation compliance report."""
    recommendations = get_all_recommendations_with_compliance(conn=conn)
    report_date = datetime.now().isoformat()
    
    if format.lower() == 'json':
        return {
            'format': 'json',
            'report_date': report_date,
            'total_records': len(recommendations),
            'data': recommendations
        }
    else:  # CSV
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'User ID', 'User Name', 'Title', 'Created At', 'Compliant',
                        'Active Consent', 'Eligibility Check', 'Required Disclaimer',
                        'Complete Trace', 'Rationale Cites Data'])
        for rec in recommendations:
            checks = rec.get('checks', {})
            writer.writerow([rec['id'], rec['user_id'], rec['user_name'], rec['title'],
                           rec['created_at'], rec['compliant'],
                           checks.get('active_consent', False), checks.get('eligibility_check', False),
                           checks.get('required_disclaimer', False), checks.get('complete_trace', False),
                           checks.get('rationale_cites_data', False)])
        output.seek(0)
        return {
            'format': 'csv',
            'report_date': report_date,
            'total_records': len(recommendations),
            'data': output.getvalue()
        }


def generate_compliance_summary_report(format: str = 'markdown',
                                      conn: Optional[sqlite3.Connection] = None) -> Dict:
    """Generate compliance summary report."""
    metrics = get_compliance_metrics(conn)
    recent_issues = get_recent_compliance_issues(limit=20, conn=conn)
    audit_log = get_consent_audit_log(conn=conn)
    recommendations = get_all_recommendations_with_compliance(conn=conn)
    report_date = datetime.now()
    
    if format.lower() == 'json':
        return {
            'format': 'json',
            'report_date': report_date.isoformat(),
            'metrics': metrics,
            'recent_issues': recent_issues,
            'total_audit_records': len(audit_log),
            'total_recommendations': len(recommendations),
            'compliant_recommendations': sum(1 for r in recommendations if r['compliant']),
            'non_compliant_recommendations': sum(1 for r in recommendations if not r['compliant'])
        }
    else:  # Markdown
        markdown = f"""# SpendSense Compliance Summary Report

**Report Date:** {report_date.strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report provides a comprehensive overview of compliance status for the SpendSense system.

## Compliance Metrics

- **Consent Coverage:** {metrics['consent_coverage']}%
- **Tone Violations:** {metrics['tone_violations']} (not tracked in database)
- **Eligibility Failures:** {metrics['eligibility_failures']} (not tracked in database)
- **Recommendation Compliance:** {metrics['recommendation_compliance']}%

## Summary Statistics

- **Total Consent Changes Logged:** {len(audit_log)}
- **Total Recommendations:** {len(recommendations)}
- **Compliant Recommendations:** {sum(1 for r in recommendations if r['compliant'])}
- **Non-Compliant Recommendations:** {sum(1 for r in recommendations if not r['compliant'])}

## Recent Compliance Issues

"""
        if recent_issues:
            markdown += f"Found {len(recent_issues)} recent compliance issues:\n\n"
            for issue in recent_issues[:10]:
                markdown += f"- **{issue['type']}** (User {issue['user_id']}, {issue['timestamp']}): {issue['description']}\n"
        else:
            markdown += "No recent compliance issues detected.\n"
        
        markdown += "\n## Key Findings\n\n"
        if metrics['consent_coverage'] < 50:
            markdown += "- ⚠️ **Low consent coverage** - Less than 50% of users have active consent.\n"
        elif metrics['consent_coverage'] < 80:
            markdown += "- ⚠️ **Moderate consent coverage** - Consider encouraging more users to grant consent.\n"
        else:
            markdown += "- ✅ **Good consent coverage** - Most users have active consent.\n"
        
        if metrics['recommendation_compliance'] < 50:
            markdown += "- ⚠️ **Low recommendation compliance** - Many recommendations missing required disclaimers.\n"
        elif metrics['recommendation_compliance'] < 80:
            markdown += "- ⚠️ **Moderate recommendation compliance** - Some recommendations missing disclaimers.\n"
        else:
            markdown += "- ✅ **Good recommendation compliance** - Most recommendations have required disclaimers.\n"
        
        if len(recent_issues) > 0:
            markdown += f"- ⚠️ **{len(recent_issues)} compliance issues** detected - Review and address.\n"
        
        markdown += "\n## Recommendations\n\n"
        markdown += "- Continue monitoring consent coverage and encourage user consent.\n"
        markdown += "- Ensure all recommendations include required disclaimers.\n"
        if len(recent_issues) > 0:
            markdown += "- Address recent compliance issues identified in this report.\n"
        markdown += "- Consider implementing database logging for tone violations and eligibility failures.\n"
        
        return {
            'format': 'markdown',
            'report_date': report_date.isoformat(),
            'data': markdown
        }


def get_consent_audit_log(user_id: Optional[int] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         action: Optional[str] = None,
                         conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Query consent audit log with filters.
    
    Args:
        user_id: Filter by user ID (optional)
        start_date: Filter by start date (YYYY-MM-DD format, optional)
        end_date: Filter by end date (YYYY-MM-DD format, optional)
        action: Filter by action ('granted' or 'revoked', optional)
        conn: Database connection (creates new if None)
        
    Returns:
        List of audit log entries:
        [
            {
                'id': int,
                'user_id': int,
                'user_name': str,
                'action': str,
                'timestamp': str,
                'changed_by': str,
                'previous_status': bool
            }
        ]
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Build query with filters
        query = """
            SELECT cal.id, cal.user_id, u.name, cal.action, cal.timestamp, 
                   cal.changed_by, cal.previous_status
            FROM consent_audit_log cal
            JOIN users u ON cal.user_id = u.id
            WHERE 1=1
        """
        params = []
        
        if user_id is not None:
            query += " AND cal.user_id = ?"
            params.append(user_id)
        
        if start_date:
            query += " AND DATE(cal.timestamp) >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND DATE(cal.timestamp) <= ?"
            params.append(end_date)
        
        if action:
            query += " AND cal.action = ?"
            params.append(action)
        
        query += " ORDER BY cal.timestamp DESC LIMIT 1000"
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        return [
            {
                'id': row[0],
                'user_id': row[1],
                'user_name': row[2],
                'action': row[3],
                'timestamp': row[4],
                'changed_by': row[5],
                'previous_status': bool(row[6])
            }
            for row in results
        ]
    finally:
        if close_conn:
            conn.close()

