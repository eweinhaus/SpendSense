"""
Eligibility checks module for SpendSense MVP.
Filters recommendations based on user's existing accounts and requirements.
"""

import sqlite3
from typing import Tuple, Optional
from .database import get_db_connection


def has_consent(user_id: int, conn: Optional[sqlite3.Connection] = None,
                db_path: Optional[str] = None) -> bool:
    """
    Check if user has given consent for data processing and recommendations.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        True if consent given, False otherwise
    """
    if conn is None:
        if db_path:
            conn = get_db_connection(db_path)
        else:
            conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT consent_given FROM users WHERE id = ?
        """, (user_id,))
        
        result = cursor.fetchone()
        return bool(result and result[0])
    finally:
        if close_conn:
            conn.close()


def get_user_accounts(user_id: int, conn: Optional[sqlite3.Connection] = None, 
                      db_path: Optional[str] = None) -> list:
    """
    Get all accounts for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        List of account dictionaries with type and subtype
    """
    if conn is None:
        if db_path:
            conn = get_db_connection(db_path)
        else:
            conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT type, subtype FROM accounts
            WHERE user_id = ?
        """, (user_id,))
        
        accounts = []
        for row in cursor.fetchall():
            account_type, subtype = row
            accounts.append({
                'type': account_type,
                'subtype': subtype
            })
        
        return accounts
    finally:
        if close_conn:
            conn.close()


def check_eligibility(user_id: int, recommendation_title: str, 
                     conn: Optional[sqlite3.Connection] = None,
                     db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if a user is eligible for a recommendation.
    
    Simple rules for MVP:
    - Rule 1: Don't recommend products user already has
    - Rule 2: Basic product requirements (e.g., checking account for HYSA)
    
    Args:
        user_id: User ID
        recommendation_title: Title of the recommendation
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Tuple of (is_eligible: bool, reason: str)
    """
    if conn is None:
        if db_path:
            conn = get_db_connection(db_path)
        else:
            conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        accounts = get_user_accounts(user_id, conn, db_path)
        account_types = [acc['type'].lower() for acc in accounts]
        account_subtypes = [acc['subtype'].lower() if acc['subtype'] else '' 
                           for acc in accounts]
        
        # Rule 1: Don't recommend savings account if user already has one
        if "savings" in recommendation_title.lower() or "hysa" in recommendation_title.lower():
            if "savings" in account_types or "savings" in account_subtypes:
                return False, "User already has savings account"
            
            # Rule 2: Need checking account to transfer funds
            if "checking" not in account_types and "depository" not in account_types:
                return False, "User needs checking account to transfer funds"
        
        # Rule 1: Don't recommend credit card if user already has one (unless balance transfer)
        if "credit card" in recommendation_title.lower() and "balance transfer" not in recommendation_title.lower():
            if "credit" in account_types:
                return False, "User already has credit card"
        
        # Rule 1: Don't recommend balance transfer if user has no credit cards
        if "balance transfer" in recommendation_title.lower():
            if "credit" not in account_types:
                return False, "User needs credit card for balance transfer"
        
        return True, "Eligible"
        
    finally:
        if close_conn:
            conn.close()


def filter_recommendations(user_id: int, recommendations: list,
                          conn: Optional[sqlite3.Connection] = None,
                          db_path: Optional[str] = None) -> list:
    """
    Filter recommendations based on eligibility.
    
    Args:
        user_id: User ID
        recommendations: List of recommendation dictionaries with 'title' key
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Filtered list of eligible recommendations
    """
    eligible_recs = []
    
    for rec in recommendations:
        is_eligible, reason = check_eligibility(user_id, rec.get('title', ''), conn, db_path)
        if is_eligible:
            eligible_recs.append(rec)
        # For MVP, we silently filter out ineligible recommendations
        # In production, we might log or display reasons for operator view
    
    return eligible_recs

