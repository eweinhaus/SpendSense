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


def get_signal_value(signals: List[Dict], signal_type: str, window: str = '30d') -> Optional[float]:
    """
    Get signal value by type, preferring window-specific signals.
    
    Some signals are stored with window suffix (e.g., 'cash_flow_buffer_30d'),
    others are stored without (e.g., 'median_pay_gap', 'credit_utilization_max').
    
    Args:
        signals: List of signal dictionaries
        signal_type: Base signal type (e.g., 'credit_utilization_max', 'cash_flow_buffer')
        window: Window preference ('30d' or '180d') - only used if signal has window suffix
        
    Returns:
        Signal value or None if not found
    """
    if not signals:
        return None
    
    # Convert to dict for easier lookup
    signals_dict = {s['signal_type']: s for s in signals}
    
    # Try window-specific signal first (e.g., 'cash_flow_buffer_30d')
    window_signal_type = f"{signal_type}_{window}"
    if window_signal_type in signals_dict:
        return signals_dict[window_signal_type].get('value')
    
    # Fall back to base signal type (for signals without window suffix)
    if signal_type in signals_dict:
        return signals_dict[signal_type].get('value')
    
    # Try other window if not found (e.g., try 'cash_flow_buffer_180d' if 'cash_flow_buffer_30d' not found)
    other_window = '180d' if window == '30d' else '30d'
    other_window_signal_type = f"{signal_type}_{other_window}"
    if other_window_signal_type in signals_dict:
        return signals_dict[other_window_signal_type].get('value')
    
    return None


def matches_high_utilization(signals: List[Dict]) -> bool:
    """
    Check if user matches High Utilization persona criteria.
    
    Criteria (OR logic - match any):
    - credit_utilization_max >= 50%
    - credit_interest_charges >= 50 (meaningful monthly interest)
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
    
    # Check credit_interest_charges >= 50 (meaningful debt)
    if 'credit_interest_charges' in signals_dict:
        interest = signals_dict['credit_interest_charges'].get('value')
        if interest is not None and interest >= 50.0:
            return True
    
    # Check credit_overdue = 1.0
    if 'credit_overdue' in signals_dict:
        overdue = signals_dict['credit_overdue'].get('value')
        if overdue is not None and overdue == 1.0:
            return True
    
    return False


def matches_variable_income(signals: List[Dict]) -> bool:
    """
    Check if user matches Variable Income Budgeter persona criteria.
    
    Criteria (AND logic - match all):
    - median_pay_gap > 45 days
    - cash_flow_buffer_30d < 1.0
    
    Args:
        signals: List of signal dictionaries
        
    Returns:
        True if matches Variable Income Budgeter criteria, False otherwise
    """
    if not signals:
        return False
    
    median_gap = get_signal_value(signals, 'median_pay_gap')
    cash_buffer = get_signal_value(signals, 'cash_flow_buffer', '30d')
    
    if median_gap is None or cash_buffer is None:
        return False
    
    return median_gap > 45.0 and cash_buffer < 1.0


def matches_savings_builder(signals: List[Dict]) -> bool:
    """
    Check if user matches Savings Builder persona criteria.
    
    Criteria (AND logic - match all):
    - (savings_growth_rate_30d >= 2.0 OR savings_net_inflow_30d >= 200.0)
    - AND credit_utilization_max < 30.0
    
    Args:
        signals: List of signal dictionaries
        
    Returns:
        True if matches Savings Builder criteria, False otherwise
    """
    if not signals:
        return False
    
    growth_rate = get_signal_value(signals, 'savings_growth_rate', '30d')
    net_inflow = get_signal_value(signals, 'savings_net_inflow', '30d')
    max_util = get_signal_value(signals, 'credit_utilization_max')
    
    # Check savings condition
    savings_condition = False
    if growth_rate is not None and growth_rate >= 2.0:
        savings_condition = True
    elif net_inflow is not None and net_inflow >= 200.0:
        savings_condition = True
    
    # Check credit condition
    credit_condition = True
    if max_util is not None:
        credit_condition = max_util < 30.0
    
    return savings_condition and credit_condition


def matches_financial_newcomer(signals: List[Dict], user_id: int, conn: Optional[sqlite3.Connection] = None) -> bool:
    """
    Check if user matches Financial Newcomer persona criteria.
    
    Criteria (AND logic - match all):
    - Low credit utilization (<20%) OR no credit cards
    - Few accounts (<3 total accounts)
    - Low transaction volume (<50 transactions in 30-day window)
    
    Args:
        signals: List of signal dictionaries
        user_id: User ID (for transaction count lookup)
        conn: Database connection (creates new if None)
        
    Returns:
        True if matches Financial Newcomer criteria, False otherwise
    """
    if not signals:
        return False
    
    # Get credit utilization
    max_util = get_signal_value(signals, 'credit_utilization_max')
    credit_card_count = get_signal_value(signals, 'credit_card_count')
    
    # Credit condition: low utilization or no credit cards
    credit_condition = True
    if max_util is not None:
        credit_condition = max_util < 20.0
    elif credit_card_count is not None and credit_card_count > 0:
        credit_condition = False
    
    # Account condition: few accounts (<3)
    # Get total account count from database
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM accounts WHERE user_id = ?
        """, (user_id,))
        total_accounts = cursor.fetchone()[0]
        account_condition = total_accounts < 3
        
        # Transaction condition: low volume (<50 in 30 days)
        from datetime import date, timedelta
        from .detect_signals import TODAY
        window_start = TODAY - timedelta(days=30)
        
        cursor.execute("""
            SELECT COUNT(*) FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? AND t.date >= ? AND t.pending = 0
        """, (user_id, window_start))
        transaction_count = cursor.fetchone()[0]
        transaction_condition = transaction_count < 50
        
        return credit_condition and account_condition and transaction_condition
        
    finally:
        if close_conn:
            conn.close()


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
    
    elif persona_type == "variable_income_budgeter":
        signals_dict = {s['signal_type']: s for s in signals}
        
        median_gap = get_signal_value(signals, 'median_pay_gap')
        cash_buffer = get_signal_value(signals, 'cash_flow_buffer', '30d')
        
        criteria_parts = []
        if median_gap is not None:
            criteria_parts.append(f"Median pay gap: {median_gap:.0f} days")
        if cash_buffer is not None:
            criteria_parts.append(f"Cash-flow buffer: {cash_buffer:.2f} months")
        
        if criteria_parts:
            return ", ".join(criteria_parts)
        else:
            return "Variable income pattern detected"
    
    elif persona_type == "savings_builder":
        signals_dict = {s['signal_type']: s for s in signals}
        
        growth_rate = get_signal_value(signals, 'savings_growth_rate', '30d')
        net_inflow = get_signal_value(signals, 'savings_net_inflow', '30d')
        max_util = get_signal_value(signals, 'credit_utilization_max')
        
        criteria_parts = []
        if growth_rate is not None and growth_rate >= 2.0:
            criteria_parts.append(f"Savings growth rate: {growth_rate:.1f}%")
        elif net_inflow is not None and net_inflow >= 200.0:
            criteria_parts.append(f"Net savings inflow: ${net_inflow:.0f}/month")
        if max_util is not None:
            criteria_parts.append(f"Credit utilization: {max_util:.0f}%")
        
        if criteria_parts:
            return ", ".join(criteria_parts)
        else:
            return "Savings builder pattern detected"
    
    elif persona_type == "financial_newcomer":
        signals_dict = {s['signal_type']: s for s in signals}
        
        max_util = get_signal_value(signals, 'credit_utilization_max')
        credit_card_count = get_signal_value(signals, 'credit_card_count')
        
        criteria_parts = []
        if max_util is not None:
            criteria_parts.append(f"Credit utilization: {max_util:.0f}%")
        elif credit_card_count is None or credit_card_count == 0:
            criteria_parts.append("No credit cards")
        
        if criteria_parts:
            return ", ".join(criteria_parts) + " (new to financial management)"
        else:
            return "Early financial journey detected"
    
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
    2. Variable Income Budgeter (second priority)
    3. Savings Builder (third priority)
    4. Custom Persona #5 (fourth priority - to be implemented)
    5. Subscription-Heavy (fifth priority)
    6. Neutral (fallback)
    
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
        
        # Check Variable Income Budgeter (second priority)
        elif matches_variable_income(signals):
            persona_type = "variable_income_budgeter"
            criteria = get_criteria_matched(persona_type, signals)
        
        # Check Savings Builder (third priority)
        elif matches_savings_builder(signals):
            persona_type = "savings_builder"
            criteria = get_criteria_matched(persona_type, signals)
        
        # Check Financial Newcomer (fourth priority)
        elif matches_financial_newcomer(signals, user_id, conn):
            persona_type = "financial_newcomer"
            criteria = get_criteria_matched(persona_type, signals)
        
        # Check Subscription-Heavy (fifth priority)
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

