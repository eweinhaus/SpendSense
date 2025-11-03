"""
Persona assignment module for SpendSense MVP.
Assigns personas to users based on detected behavioral signals.
"""

import sqlite3
import json
from typing import List, Dict, Optional
from .database import get_db_connection


def get_user_signals(user_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Dict]:
    """
    Get all signals for a user from the database.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        List of signal dictionaries with signal_type, value, metadata
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT signal_type, value, metadata
            FROM signals
            WHERE user_id = ?
        """, (user_id,))
        
        signals = []
        for row in cursor.fetchall():
            signal_type, value, metadata_json = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            signals.append({
                'signal_type': signal_type,
                'value': value,
                'metadata': metadata
            })
        
        return signals
    finally:
        if close_conn:
            conn.close()


def matches_high_utilization(signals: List[Dict]) -> bool:
    """
    Check if user matches High Utilization persona criteria.
    
    Criteria (OR logic - match any):
    - credit_utilization_max >= 50%
    - credit_interest_charges > 0
    - credit_overdue = 1.0
    
    Args:
        signals: List of signal dictionaries
        
    Returns:
        True if matches High Utilization criteria, False otherwise
    """
    if not signals:
        return False
    
    # Convert signals list to dict for easier lookup
    signals_dict = {s['signal_type']: s for s in signals}
    
    # Check credit_utilization_max >= 50%
    if 'credit_utilization_max' in signals_dict:
        util = signals_dict['credit_utilization_max'].get('value')
        if util is not None and util >= 50.0:
            return True
    
    # Check credit_interest_charges > 0
    if 'credit_interest_charges' in signals_dict:
        interest = signals_dict['credit_interest_charges'].get('value')
        if interest is not None and interest > 0:
            return True
    
    # Check credit_overdue = 1.0
    if 'credit_overdue' in signals_dict:
        overdue = signals_dict['credit_overdue'].get('value')
        if overdue is not None and overdue == 1.0:
            return True
    
    return False


def matches_subscription_heavy(signals: List[Dict]) -> bool:
    """
    Check if user matches Subscription-Heavy persona criteria.
    
    Criteria (AND logic - match all):
    - subscription_count >= 3
    - AND (subscription_monthly_spend >= $50 OR subscription_share >= 10%)
    
    Args:
        signals: List of signal dictionaries
        
    Returns:
        True if matches Subscription-Heavy criteria, False otherwise
    """
    if not signals:
        return False
    
    # Convert signals list to dict for easier lookup
    signals_dict = {s['signal_type']: s for s in signals}
    
    # Check subscription_count >= 3
    if 'subscription_count' not in signals_dict:
        return False
    
    count = signals_dict['subscription_count'].get('value')
    if count is None or count < 3:
        return False
    
    # Check subscription_monthly_spend >= $50 OR subscription_share >= 10%
    monthly_spend = signals_dict.get('subscription_monthly_spend', {}).get('value', 0) or 0
    subscription_share = signals_dict.get('subscription_share', {}).get('value', 0) or 0
    
    if monthly_spend >= 50.0 or subscription_share >= 10.0:
        return True
    
    return False


def get_criteria_matched(persona_type: str, signals: List[Dict]) -> str:
    """
    Generate human-readable explanation of why persona was assigned.
    
    Args:
        persona_type: Persona type (high_utilization, subscription_heavy, neutral)
        signals: List of signal dictionaries
        
    Returns:
        Human-readable criteria explanation
    """
    if persona_type == "high_utilization":
        signals_dict = {s['signal_type']: s for s in signals}
        
        criteria_parts = []
        
        # Check utilization
        if 'credit_utilization_max' in signals_dict:
            util = signals_dict['credit_utilization_max'].get('value')
            if util is not None and util >= 50.0:
                # Try to get card details from metadata
                metadata = signals_dict['credit_utilization_max'].get('metadata', {})
                cards = metadata.get('cards', [])
                if cards:
                    card = cards[0]  # Use first card
                    account_id = card.get('account_id', 'XXXX')
                    balance = card.get('balance', 0)
                    limit = card.get('limit', 0)
                    criteria_parts.append(
                        f"Credit card ending in {account_id[-4:] if len(account_id) >= 4 else 'XXXX'} "
                        f"at {util:.0f}% utilization (${balance:,.0f} of ${limit:,.0f} limit)"
                    )
                else:
                    criteria_parts.append(f"Credit utilization at {util:.0f}%")
        
        # Check interest charges
        if 'credit_interest_charges' in signals_dict:
            interest = signals_dict['credit_interest_charges'].get('value')
            if interest is not None and interest > 0:
                criteria_parts.append(f"Interest charges ${interest:.2f}/month")
        
        # Check overdue
        if 'credit_overdue' in signals_dict:
            overdue = signals_dict['credit_overdue'].get('value')
            if overdue is not None and overdue == 1.0:
                criteria_parts.append("Overdue payment detected")
        
        if criteria_parts:
            return ", ".join(criteria_parts)
        else:
            return "High credit utilization detected"
    
    elif persona_type == "subscription_heavy":
        signals_dict = {s['signal_type']: s for s in signals}
        
        count = signals_dict.get('subscription_count', {}).get('value', 0) or 0
        monthly_spend = signals_dict.get('subscription_monthly_spend', {}).get('value', 0) or 0
        share = signals_dict.get('subscription_share', {}).get('value', 0) or 0
        
        # Get merchant names if available
        metadata = signals_dict.get('subscription_merchants', {}).get('metadata', {})
        merchants = metadata.get('merchants', [])
        
        if merchants:
            merchant_list = ", ".join(merchants[:4])  # Show first 4
            if len(merchants) > 4:
                merchant_list += f", and {len(merchants) - 4} more"
            return (f"{int(count)} recurring merchants detected: {merchant_list}. "
                   f"Monthly spend: ${monthly_spend:.2f}, Share: {share:.1f}%")
        else:
            return (f"{int(count)} recurring subscriptions detected. "
                   f"Monthly spend: ${monthly_spend:.2f}, Share: {share:.1f}%")
    
    else:  # neutral
        return "No matching persona criteria"


def store_persona_assignment(user_id: int, persona_type: str, criteria_matched: str,
                             conn: Optional[sqlite3.Connection] = None) -> None:
    """
    Store persona assignment in database.
    
    Args:
        user_id: User ID
        persona_type: Persona type (high_utilization, subscription_heavy, neutral)
        criteria_matched: Human-readable criteria explanation
        conn: Database connection (creates new if None)
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Use INSERT OR REPLACE to handle updates
        cursor.execute("""
            INSERT OR REPLACE INTO personas (user_id, persona_type, criteria_matched)
            VALUES (?, ?, ?)
        """, (user_id, persona_type, criteria_matched))
        
        conn.commit()
    finally:
        if close_conn:
            conn.close()


def assign_persona(user_id: int, conn: Optional[sqlite3.Connection] = None) -> str:
    """
    Assign persona to user based on signals.
    
    Priority order:
    1. High Utilization (highest priority)
    2. Subscription-Heavy (second priority)
    3. Neutral (fallback)
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Assigned persona type
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        # Get user signals
        signals = get_user_signals(user_id, conn)
        
        # Check High Utilization (highest priority)
        if matches_high_utilization(signals):
            persona_type = "high_utilization"
            criteria = get_criteria_matched(persona_type, signals)
        
        # Check Subscription-Heavy (second priority)
        elif matches_subscription_heavy(signals):
            persona_type = "subscription_heavy"
            criteria = get_criteria_matched(persona_type, signals)
        
        # Fallback to Neutral
        else:
            persona_type = "neutral"
            criteria = get_criteria_matched(persona_type, signals)
        
        # Store assignment
        store_persona_assignment(user_id, persona_type, criteria, conn)
        
        return persona_type
        
    finally:
        if close_conn:
            conn.close()


def assign_personas_for_all_users(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Assign personas to all users in the database.
    
    Args:
        conn: Database connection (creates new if None)
        
    Returns:
        Summary dictionary with results
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        summary = {
            'users_processed': 0,
            'personas_assigned': {},
            'results': []
        }
        
        for user_id in user_ids:
            print(f"Assigning persona for user {user_id}...")
            persona = assign_persona(user_id, conn)
            summary['personas_assigned'][persona] = summary['personas_assigned'].get(persona, 0) + 1
            summary['users_processed'] += 1
            summary['results'].append({
                'user_id': user_id,
                'persona': persona
            })
            print(f"  ✓ Assigned: {persona}")
        
        return summary
        
    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    """Run persona assignment for all users."""
    print("=" * 60)
    print("SpendSense - Persona Assignment")
    print("=" * 60)
    print()
    
    summary = assign_personas_for_all_users()
    
    print()
    print("=" * 60)
    print("Assignment Summary:")
    print(f"  Users processed: {summary['users_processed']}")
    print(f"  Personas assigned: {summary['personas_assigned']}")
    print("=" * 60)

