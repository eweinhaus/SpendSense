"""
Eligibility checks module for SpendSense MVP.
Filters recommendations based on user's existing accounts and requirements.
"""

import sqlite3
import logging
from typing import Tuple, Optional, Dict
from .database import get_db_connection

# Configure logging for eligibility failures
logger = logging.getLogger(__name__)


# Product catalog with eligibility rules
ELIGIBILITY_RULES = {
    'balance_transfer_card': {
        'min_income': 30000,  # Annual income in USD
        'min_credit_score': 650,  # If available
        'exclude_accounts': ['balance_transfer_card'],
        'blacklist': False,
        'keywords': ['balance transfer', 'balance transfer card']
    },
    'high_yield_savings': {
        'min_income': None,
        'exclude_accounts': ['high_yield_savings', 'savings'],
        'blacklist': False,
        'keywords': ['high-yield', 'high yield', 'hysa', 'savings account']
    },
    'budgeting_app': {
        'min_income': None,
        'blacklist': False,
        'keywords': ['budget', 'budgeting']
    },
    'subscription_tool': {
        'min_income': None,
        'blacklist': False,
        'keywords': ['subscription', 'recurring']
    },
    'credit_card': {
        'min_income': 20000,  # Annual income in USD
        'min_credit_score': 600,  # If available
        'exclude_accounts': ['credit_card'],
        'blacklist': False,
        'keywords': ['credit card', 'credit']
    },
    'savings_account': {
        'min_income': None,
        'exclude_accounts': ['savings'],
        'blacklist': False,
        'keywords': ['savings', 'emergency fund']
    }
}


def map_recommendation_to_product(recommendation_title: str) -> Optional[str]:
    """
    Map a recommendation title to a product category.
    
    Args:
        recommendation_title: Title of the recommendation
        
    Returns:
        Product category string or None if no match
    """
    title_lower = recommendation_title.lower()
    
    for product, rules in ELIGIBILITY_RULES.items():
        keywords = rules.get('keywords', [])
        for keyword in keywords:
            if keyword in title_lower:
                return product
    
    return None


def estimate_annual_income(user_id: int, conn: Optional[sqlite3.Connection] = None,
                          db_path: Optional[str] = None) -> Optional[float]:
    """
    Estimate annual income from payroll transactions.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Estimated annual income in USD or None if cannot estimate
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
        
        # Look for income frequency signal metadata
        cursor.execute("""
            SELECT metadata FROM signals
            WHERE user_id = ? AND signal_type = 'income_frequency'
            ORDER BY detected_at DESC
            LIMIT 1
        """, (user_id,))
        
        result = cursor.fetchone()
        if result and result[0]:
            import json
            metadata = json.loads(result[0])
            payroll_groups = metadata.get('payroll_groups', [])
            
            if payroll_groups:
                # Use the largest payroll group
                largest_group = max(payroll_groups, key=lambda x: x.get('count', 0))
                mean_amount = largest_group.get('mean_amount', 0)
                frequency = metadata.get('frequency', 'irregular')
                
                # Estimate monthly income based on frequency
                if frequency == 'weekly':
                    monthly_income = mean_amount * 4.33  # Average weeks per month
                elif frequency == 'bi-weekly':
                    monthly_income = mean_amount * 2.17  # Average bi-weekly periods per month
                elif frequency == 'monthly':
                    monthly_income = mean_amount
                else:
                    # Irregular - use mean_amount * 2 as conservative estimate
                    monthly_income = mean_amount * 2
                
                annual_income = monthly_income * 12
                return annual_income
        
        # Fallback: try to detect from recent transactions
        from datetime import datetime, timedelta
        window_start = datetime.now() - timedelta(days=180)
        
        cursor.execute("""
            SELECT SUM(t.amount)
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            AND t.date >= ?
            AND t.amount > 0
            AND (t.merchant_name LIKE '%PAYROLL%' 
                 OR t.merchant_name LIKE '%SALARY%'
                 OR t.merchant_name LIKE '%PAYCHECK%')
        """, (user_id, window_start.strftime('%Y-%m-%d')))
        
        result = cursor.fetchone()
        if result and result[0]:
            total_income_180d = result[0]
            # Estimate annual: (180d income / 180) * 365
            annual_income = (total_income_180d / 180) * 365
            return annual_income
        
        return None
        
    finally:
        if close_conn:
            conn.close()


def get_user_credit_score(user_id: int, conn: Optional[sqlite3.Connection] = None,
                         db_path: Optional[str] = None) -> Optional[int]:
    """
    Get user's credit score if available.
    
    Note: Credit score is not currently tracked in the database.
    This is a placeholder for future implementation.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Credit score or None if not available
    """
    # Credit score is not currently stored in the database
    # For MVP, we'll return None and eligibility checks will skip this requirement
    return None


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


def check_income_requirement(user_id: int, product: str, conn: Optional[sqlite3.Connection] = None,
                            db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if user meets income requirement for a product.
    
    Args:
        user_id: User ID
        product: Product category
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Tuple of (meets_requirement: bool, reason: str)
    """
    if product not in ELIGIBILITY_RULES:
        return True, "No income requirement"
    
    rules = ELIGIBILITY_RULES[product]
    min_income = rules.get('min_income')
    
    if min_income is None:
        return True, "No income requirement"
    
    annual_income = estimate_annual_income(user_id, conn, db_path)
    
    if annual_income is None:
        # Cannot estimate income - allow by default but log
        logger.warning(f"Could not estimate income for user {user_id}, allowing product {product}")
        return True, "Income cannot be estimated, allowing"
    
    if annual_income >= min_income:
        return True, f"Income requirement met (${annual_income:,.0f} >= ${min_income:,})"
    else:
        return False, f"Income requirement not met (${annual_income:,.0f} < ${min_income:,})"


def check_credit_score_requirement(user_id: int, product: str, conn: Optional[sqlite3.Connection] = None,
                                   db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if user meets credit score requirement for a product.
    
    Args:
        user_id: User ID
        product: Product category
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Tuple of (meets_requirement: bool, reason: str)
    """
    if product not in ELIGIBILITY_RULES:
        return True, "No credit score requirement"
    
    rules = ELIGIBILITY_RULES[product]
    min_credit_score = rules.get('min_credit_score')
    
    if min_credit_score is None:
        return True, "No credit score requirement"
    
    credit_score = get_user_credit_score(user_id, conn, db_path)
    
    if credit_score is None:
        # Credit score not available - allow by default but log
        logger.warning(f"Credit score not available for user {user_id}, allowing product {product}")
        return True, "Credit score not available, allowing"
    
    if credit_score >= min_credit_score:
        return True, f"Credit score requirement met ({credit_score} >= {min_credit_score})"
    else:
        return False, f"Credit score requirement not met ({credit_score} < {min_credit_score})"


def check_existing_accounts(user_id: int, product: str, conn: Optional[sqlite3.Connection] = None,
                           db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if user already has accounts that exclude them from a product.
    
    Args:
        user_id: User ID
        product: Product category
        conn: Database connection (creates new if None)
        db_path: Database path (only used if conn is None)
        
    Returns:
        Tuple of (is_eligible: bool, reason: str)
    """
    if product not in ELIGIBILITY_RULES:
        return True, "No account exclusion rules"
    
    rules = ELIGIBILITY_RULES[product]
    exclude_accounts = rules.get('exclude_accounts', [])
    
    if not exclude_accounts:
        return True, "No account exclusions"
    
    accounts = get_user_accounts(user_id, conn, db_path)
    account_types = [acc['type'].lower() for acc in accounts]
    account_subtypes = [acc['subtype'].lower() if acc['subtype'] else '' 
                       for acc in accounts]
    all_account_identifiers = account_types + account_subtypes
    
    for excluded in exclude_accounts:
        if excluded.lower() in all_account_identifiers:
            return False, f"User already has {excluded} account"
    
    return True, "No conflicting accounts"


def check_harmful_product_blacklist(product: str) -> Tuple[bool, str]:
    """
    Check if product is on harmful product blacklist.
    
    Args:
        product: Product category
        
    Returns:
        Tuple of (is_safe: bool, reason: str)
    """
    if product not in ELIGIBILITY_RULES:
        return True, "Product not in catalog"
    
    rules = ELIGIBILITY_RULES[product]
    is_blacklisted = rules.get('blacklist', False)
    
    if is_blacklisted:
        return False, "Product is on harmful blacklist"
    
    return True, "Product is safe"


def check_eligibility(user_id: int, recommendation_title: str, 
                     conn: Optional[sqlite3.Connection] = None,
                     db_path: Optional[str] = None) -> Tuple[bool, str]:
    """
    Check if a user is eligible for a recommendation.
    
    Comprehensive eligibility checks:
    - Income requirements per product
    - Credit score requirements (if available)
    - Existing account checks (comprehensive)
    - Harmful product blacklist
    
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
        # Map recommendation to product category
        product = map_recommendation_to_product(recommendation_title)
        
        # If no product mapping, use legacy checks
        if product is None:
            # Legacy checks for backward compatibility
            accounts = get_user_accounts(user_id, conn, db_path)
            account_types = [acc['type'].lower() for acc in accounts]
            account_subtypes = [acc['subtype'].lower() if acc['subtype'] else '' 
                               for acc in accounts]
            
            if "savings" in recommendation_title.lower() or "hysa" in recommendation_title.lower():
                if "savings" in account_types or "savings" in account_subtypes:
                    reason = "User already has savings account"
                    logger.info(f"Eligibility check failed for user {user_id}: {reason}")
                    return False, reason
                
                if "checking" not in account_types and "depository" not in account_types:
                    reason = "User needs checking account to transfer funds"
                    logger.info(f"Eligibility check failed for user {user_id}: {reason}")
                    return False, reason
            
            if "credit card" in recommendation_title.lower() and "balance transfer" not in recommendation_title.lower():
                if "credit" in account_types:
                    reason = "User already has credit card"
                    logger.info(f"Eligibility check failed for user {user_id}: {reason}")
                    return False, reason
            
            if "balance transfer" in recommendation_title.lower():
                if "credit" not in account_types:
                    reason = "User needs credit card for balance transfer"
                    logger.info(f"Eligibility check failed for user {user_id}: {reason}")
                    return False, reason
            
            return True, "Eligible"
        
        # Check harmful product blacklist
        is_safe, reason = check_harmful_product_blacklist(product)
        if not is_safe:
            logger.warning(f"Eligibility check failed for user {user_id}, product {product}: {reason}")
            return False, reason
        
        # Check existing accounts
        has_accounts, reason = check_existing_accounts(user_id, product, conn, db_path)
        if not has_accounts:
            logger.info(f"Eligibility check failed for user {user_id}, product {product}: {reason}")
            return False, reason
        
        # Check income requirement
        meets_income, reason = check_income_requirement(user_id, product, conn, db_path)
        if not meets_income:
            logger.info(f"Eligibility check failed for user {user_id}, product {product}: {reason}")
            return False, reason
        
        # Check credit score requirement
        meets_credit, reason = check_credit_score_requirement(user_id, product, conn, db_path)
        if not meets_credit:
            logger.info(f"Eligibility check failed for user {user_id}, product {product}: {reason}")
            return False, reason
        
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
        else:
            # Log eligibility failures for operator review
            logger.info(f"Filtered recommendation '{rec.get('title', '')}' for user {user_id}: {reason}")
    
    return eligible_recs

