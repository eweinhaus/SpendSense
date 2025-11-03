"""
Rationale generation module for SpendSense MVP.
Generates data-driven rationales for recommendations.
"""

import sqlite3
import json
from typing import Dict, Optional
from .database import get_db_connection


def get_credit_card_data(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict]:
    """
    Get credit card data for rationale generation.
    Returns the card with highest utilization.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with card details or None
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get credit card with highest utilization
        cursor.execute("""
            SELECT a.account_id, a.current_balance, a."limit"
            FROM accounts a
            WHERE a.user_id = ? AND a.type = 'credit'
            ORDER BY (a.current_balance / NULLIF(a."limit", 0)) DESC
            LIMIT 1
        """, (user_id,))
        
        result = cursor.fetchone()
        if not result:
            return None
        
        account_id, balance, limit = result
        
        return {
            'account_id': account_id,
            'balance': balance or 0,
            'limit': limit or 0,
            'last_4': account_id[-4:] if len(account_id) >= 4 else "XXXX"
        }
    finally:
        if close_conn:
            conn.close()


def generate_rationale(user_id: int, recommendation: Dict, signals: Dict,
                      conn: Optional[sqlite3.Connection] = None) -> str:
    """
    Generate data-driven rationale for a recommendation.
    
    Args:
        user_id: User ID
        recommendation: Recommendation dictionary with title, persona_matched
        signals: Dictionary of signal types to signal data
        conn: Database connection (creates new if None)
        
    Returns:
        Rationale string with data citations
    """
    persona = recommendation.get('persona_matched', 'neutral')
    title = recommendation.get('title', '')
    
    if persona == "high_utilization":
        # Get credit card data
        card_data = get_credit_card_data(user_id, conn)
        
        # Get utilization from signals
        utilization = signals.get('credit_utilization_max', {}).get('value', 0) or 0
        interest = signals.get('credit_interest_charges', {}).get('value', 0) or 0
        
        # Build rationale with fallbacks
        if card_data and card_data['limit'] > 0:
            balance = card_data['balance']
            limit = card_data['limit']
            last_4 = card_data['last_4']
            
            rationale = (f"We noticed your credit card ending in {last_4} is at "
                       f"{utilization:.0f}% utilization "
                       f"(${balance:,.0f} of ${limit:,.0f} limit). ")
        else:
            rationale = (f"We noticed your credit card utilization is at "
                       f"{utilization:.0f}%. ")
        
        if interest > 0:
            rationale += (f"Bringing this below 30% could improve your credit score "
                        f"and reduce interest charges of ${interest:.2f}/month.")
        else:
            rationale += "Bringing this below 30% could improve your credit score."
    
    elif persona == "subscription_heavy":
        count = signals.get('subscription_count', {}).get('value', 0) or 0
        monthly_spend = signals.get('subscription_monthly_spend', {}).get('value', 0) or 0
        share = signals.get('subscription_share', {}).get('value', 0) or 0
        
        # Get merchant names if available
        sub_metadata = signals.get('subscription_merchants', {}).get('metadata', {})
        merchants = sub_metadata.get('merchants', [])
        
        if merchants:
            merchant_list = ", ".join(merchants[:3])  # Show first 3
            if len(merchants) > 3:
                merchant_list += f", and {len(merchants) - 3} more"
            rationale = (f"You have {int(count)} recurring subscriptions ({merchant_list}) "
                       f"totaling ${monthly_spend:.2f}/month, which represents "
                       f"{share:.1f}% of your total spending. ")
        else:
            rationale = (f"You have {int(count)} recurring subscriptions totaling "
                       f"${monthly_spend:.2f}/month, which represents {share:.1f}% "
                       f"of your total spending. ")
        
        rationale += "Reviewing and canceling unused services could save you money each month."
    
    else:  # neutral
        rationale = ("Based on your financial activity, we've identified some "
                   "general financial education opportunities that may help you.")
    
    # Add disclaimer
    rationale += "\n\n*This is educational content, not financial advice. Consult a licensed advisor for personalized guidance.*"
    
    return rationale


def add_disclaimer(rationale: str) -> str:
    """
    Add disclaimer to rationale if not already present.
    
    Args:
        rationale: Rationale string
        
    Returns:
        Rationale with disclaimer
    """
    disclaimer = "\n\n*This is educational content, not financial advice. Consult a licensed advisor for personalized guidance.*"
    
    if disclaimer.strip() not in rationale:
        rationale += disclaimer
    
    return rationale

