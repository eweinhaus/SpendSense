"""
Signal detection module for SpendSense MVP.
Detects credit utilization and subscription patterns from transaction data.
"""

import sqlite3
import json
from datetime import date, timedelta
from typing import List, Dict, Optional
from .database import get_db_connection

# Today's date for relative calculations
TODAY = date.today()


def store_signal(user_id: int, signal_type: str, value: Optional[float], 
                 metadata: Dict, window: str = '30d', 
                 conn: Optional[sqlite3.Connection] = None) -> int:
    """
    Store a detected signal in the database.
    
    Args:
        user_id: User ID
        signal_type: Type of signal (e.g., 'credit_utilization_max')
        value: Signal value (can be None)
        metadata: Additional signal data as dictionary
        window: Time window ('30d' or '180d')
        conn: Database connection (creates new if None)
        
    Returns:
        Signal ID
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        metadata_json = json.dumps(metadata)
        
        cursor.execute("""
            INSERT INTO signals (user_id, signal_type, value, metadata, window)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, signal_type, value, metadata_json, window))
        
        signal_id = cursor.lastrowid
        conn.commit()
        
        return signal_id
    finally:
        if close_conn:
            conn.close()


def detect_credit_signals(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Detect all credit utilization signals for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with detection results
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get all credit card accounts for user
        cursor.execute("""
            SELECT a.id, a.account_id, a.current_balance, a."limit"
            FROM accounts a
            WHERE a.user_id = ? AND a.type = 'credit'
        """, (user_id,))
        
        credit_cards = cursor.fetchall()
        
        if not credit_cards:
            # User has no credit cards - skip gracefully
            return {'signals_stored': 0, 'cards_processed': 0}
        
        # Process each credit card
        utilizations = []
        card_details = []
        any_overdue = False
        
        for card_id, account_id, balance, limit in credit_cards:
            if limit is None or limit <= 0:
                # Skip cards with zero or missing limit
                continue
            
            # Calculate utilization
            utilization = (balance / limit) * 100 if limit > 0 else 0
            
            # Handle negative balance (credit balance)
            if balance < 0:
                utilization = 0
            
            utilizations.append(utilization)
            
            # Get overdue status
            cursor.execute("""
                SELECT is_overdue FROM credit_cards
                WHERE account_id = ?
            """, (card_id,))
            
            overdue_result = cursor.fetchone()
            is_overdue = overdue_result[0] if overdue_result else False
            if is_overdue:
                any_overdue = True
            
            card_details.append({
                'account_id': account_id,
                'balance': balance,
                'limit': limit,
                'utilization': utilization,
                'is_overdue': is_overdue
            })
        
        if not utilizations:
            # No valid cards to process
            return {'signals_stored': 0, 'cards_processed': 0}
        
        # Calculate aggregate signals
        max_utilization = max(utilizations)
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        card_count = len(utilizations)
        
        # Get interest charges (if detectable from credit card data)
        # For MVP, we'll estimate based on APR and balance
        total_interest = 0
        for card_id, account_id, balance, limit in credit_cards:
            if limit and limit > 0:
                cursor.execute("""
                    SELECT apr FROM credit_cards
                    WHERE account_id = ?
                """, (card_id,))
                
                apr_result = cursor.fetchone()
                if apr_result and apr_result[0]:
                    apr = apr_result[0]
                    # Monthly interest = (balance * apr / 100) / 12
                    monthly_interest = (balance * apr / 100) / 12
                    total_interest += monthly_interest
        
        # Store signals
        signals_stored = 0
        
        # Signal 1: credit_utilization_max
        store_signal(user_id, 'credit_utilization_max', max_utilization,
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 2: credit_utilization_avg
        store_signal(user_id, 'credit_utilization_avg', avg_utilization,
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 3: credit_card_count
        store_signal(user_id, 'credit_card_count', float(card_count),
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 4: credit_interest_charges
        store_signal(user_id, 'credit_interest_charges', round(total_interest, 2),
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 5: credit_overdue
        store_signal(user_id, 'credit_overdue', 1.0 if any_overdue else 0.0,
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 6: credit_utilization_flag_30
        store_signal(user_id, 'credit_utilization_flag_30', 
                     1.0 if max_utilization >= 30 else 0.0,
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 7: credit_utilization_flag_50
        store_signal(user_id, 'credit_utilization_flag_50',
                     1.0 if max_utilization >= 50 else 0.0,
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        # Signal 8: credit_utilization_flag_80
        store_signal(user_id, 'credit_utilization_flag_80',
                     1.0 if max_utilization >= 80 else 0.0,
                     {'cards': card_details}, '30d', conn)
        signals_stored += 1
        
        return {
            'signals_stored': signals_stored,
            'cards_processed': card_count,
            'max_utilization': max_utilization,
            'avg_utilization': avg_utilization
        }
        
    finally:
        if close_conn:
            conn.close()


def is_similar_amount(amounts: List[float], tolerance: float = 1.0) -> bool:
    """
    Check if all amounts are within tolerance of each other.
    
    Args:
        amounts: List of transaction amounts
        tolerance: Maximum difference allowed (default $1.00)
        
    Returns:
        True if all amounts are similar, False otherwise
    """
    if not amounts:
        return False
    
    # Use absolute amounts (ignore sign)
    abs_amounts = [abs(amt) for amt in amounts]
    
    min_amount = min(abs_amounts)
    max_amount = max(abs_amounts)
    
    return (max_amount - min_amount) <= tolerance


def is_monthly_cadence(dates: List[date], days_range: tuple = (27, 33)) -> bool:
    """
    Check if dates follow a monthly cadence (approximately 30 days apart).
    
    Args:
        dates: List of transaction dates (sorted)
        days_range: Acceptable range of days between occurrences (default 27-33)
        
    Returns:
        True if dates follow monthly cadence, False otherwise
    """
    if len(dates) < 3:
        return False
    
    # Sort dates
    sorted_dates = sorted(dates)
    
    # Check spacing between consecutive dates
    min_days, max_days = days_range
    
    for i in range(len(sorted_dates) - 1):
        days_between = (sorted_dates[i + 1] - sorted_dates[i]).days
        
        # All gaps should be approximately monthly (27-33 days)
        if not (min_days <= days_between <= max_days):
            return False
    
    return True


def detect_subscription_signals(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Detect subscription patterns from transactions.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with detection results
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        cursor = conn.cursor()
        
        # Get all transactions for user in last 90 days
        window_start = TODAY - timedelta(days=90)
        
        cursor.execute("""
            SELECT t.date, t.amount, t.merchant_name, t.account_id
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? 
            AND t.date >= ?
            AND t.pending = 0
            ORDER BY t.date
        """, (user_id, window_start))
        
        transactions = cursor.fetchall()
        
        if not transactions:
            # User has no transactions - skip gracefully
            return {'signals_stored': 0, 'subscriptions_found': 0}
        
        # Group transactions by merchant (case-insensitive)
        by_merchant = {}
        for tx_date, amount, merchant, account_id in transactions:
            if not merchant:
                continue  # Skip transactions without merchant names
            
            # Normalize merchant name (lowercase, strip whitespace)
            merchant_normalized = merchant.strip().lower()
            
            if merchant_normalized not in by_merchant:
                by_merchant[merchant_normalized] = []
            
            by_merchant[merchant_normalized].append({
                'date': date.fromisoformat(tx_date) if isinstance(tx_date, str) else tx_date,
                'amount': amount,
                'merchant': merchant  # Keep original name
            })
        
        # Find recurring subscriptions
        recurring_subscriptions = []
        
        for merchant_normalized, txs in by_merchant.items():
            if len(txs) < 3:
                continue  # Need at least 3 occurrences
            
            # Check amount similarity
            amounts = [tx['amount'] for tx in txs]
            if not is_similar_amount(amounts, tolerance=1.0):
                continue  # Amounts vary too much
            
            # Check date spacing (monthly cadence)
            dates = [tx['date'] for tx in txs]
            if not is_monthly_cadence(dates, days_range=(27, 33)):
                continue  # Not monthly cadence
            
            # This is a recurring subscription!
            recurring_subscriptions.append({
                'merchant': txs[0]['merchant'],  # Use original merchant name
                'count': len(txs),
                'amount': abs(amounts[0]),  # Use absolute amount
                'monthly_spend': abs(amounts[0])
            })
        
        # Calculate aggregate signals
        subscription_count = len(recurring_subscriptions)
        subscription_monthly_spend = sum(sub['monthly_spend'] for sub in recurring_subscriptions)
        subscription_merchants = [sub['merchant'] for sub in recurring_subscriptions]
        
        # Calculate subscription share (recurring / total spend in 30-day window)
        thirty_days_ago = TODAY - timedelta(days=30)
        
        cursor.execute("""
            SELECT SUM(ABS(t.amount))
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            AND t.date >= ?
            AND t.pending = 0
        """, (user_id, thirty_days_ago))
        
        total_spend_result = cursor.fetchone()
        total_spend_30d = total_spend_result[0] if total_spend_result[0] else 0
        
        subscription_share = (subscription_monthly_spend / total_spend_30d * 100) if total_spend_30d > 0 else 0
        
        # Store signals
        signals_stored = 0
        
        metadata = {
            'subscriptions': recurring_subscriptions,
            'total_spend_30d': total_spend_30d
        }
        
        # Signal 1: subscription_count
        store_signal(user_id, 'subscription_count', float(subscription_count),
                     metadata, '30d', conn)
        signals_stored += 1
        
        # Signal 2: subscription_monthly_spend
        store_signal(user_id, 'subscription_monthly_spend', round(subscription_monthly_spend, 2),
                     metadata, '30d', conn)
        signals_stored += 1
        
        # Signal 3: subscription_merchants (JSON array)
        store_signal(user_id, 'subscription_merchants', None,
                     {**metadata, 'merchants': subscription_merchants}, '30d', conn)
        signals_stored += 1
        
        # Signal 4: subscription_share
        store_signal(user_id, 'subscription_share', round(subscription_share, 2),
                     metadata, '30d', conn)
        signals_stored += 1
        
        return {
            'signals_stored': signals_stored,
            'subscriptions_found': subscription_count,
            'monthly_spend': subscription_monthly_spend,
            'merchants': subscription_merchants
        }
        
    finally:
        if close_conn:
            conn.close()


def detect_all_signals(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Run all signal detection for a user.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with all detection results
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        results = {
            'user_id': user_id,
            'credit_signals': {},
            'subscription_signals': {},
            'total_signals': 0
        }
        
        # Detect credit signals
        try:
            credit_results = detect_credit_signals(user_id, conn)
            results['credit_signals'] = credit_results
            results['total_signals'] += credit_results.get('signals_stored', 0)
        except Exception as e:
            results['credit_signals'] = {'error': str(e)}
        
        # Detect subscription signals
        try:
            subscription_results = detect_subscription_signals(user_id, conn)
            results['subscription_signals'] = subscription_results
            results['total_signals'] += subscription_results.get('signals_stored', 0)
        except Exception as e:
            results['subscription_signals'] = {'error': str(e)}
        
        return results
        
    finally:
        if close_conn:
            conn.close()


def detect_signals_for_all_users(conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Run signal detection for all users in the database.
    
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
            'total_signals': 0,
            'results': []
        }
        
        for user_id in user_ids:
            print(f"Detecting signals for user {user_id}...")
            result = detect_all_signals(user_id, conn)
            summary['results'].append(result)
            summary['users_processed'] += 1
            summary['total_signals'] += result['total_signals']
            
            credit_info = result.get('credit_signals', {})
            sub_info = result.get('subscription_signals', {})
            
            print(f"  ✓ Credit signals: {credit_info.get('signals_stored', 0)} "
                  f"(max util: {credit_info.get('max_utilization', 0):.1f}%)")
            print(f"  ✓ Subscription signals: {sub_info.get('signals_stored', 0)} "
                  f"(found: {sub_info.get('subscriptions_found', 0)})")
        
        return summary
        
    finally:
        if close_conn:
            conn.close()


if __name__ == "__main__":
    """Run signal detection for all users."""
    print("=" * 60)
    print("SpendSense - Signal Detection")
    print("=" * 60)
    print()
    
    summary = detect_signals_for_all_users()
    
    print()
    print("=" * 60)
    print("Detection Summary:")
    print(f"  Users processed: {summary['users_processed']}")
    print(f"  Total signals stored: {summary['total_signals']}")
    print("=" * 60)

