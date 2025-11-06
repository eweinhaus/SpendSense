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


def _get_window_days(window: str) -> int:
    """
    Convert window string to number of days.
    
    Args:
        window: Window string ('30d' or '180d')
        
    Returns:
        Number of days
    """
    if window == '180d':
        return 180
    elif window == '30d':
        return 30
    else:
        raise ValueError(f"Invalid window: {window}. Must be '30d' or '180d'")


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
        # Ensure metadata is JSON serializable
        try:
            metadata_json = json.dumps(metadata) if metadata else None
        except (TypeError, ValueError):
            # Fallback: convert to string if JSON serialization fails
            metadata_json = json.dumps(str(metadata)) if metadata else None
        
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


def detect_credit_signals(user_id: int, window: str = '30d', conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Detect all credit utilization signals for a user.
    Uses historical transaction data to calculate balance at window start.
    
    Args:
        user_id: User ID
        window: Time window ('30d' or '180d')
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
        
        # Calculate date range based on window
        window_days = _get_window_days(window)
        window_start = TODAY - timedelta(days=window_days)
        
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
        
        for card_id, account_id, current_balance, limit in credit_cards:
            if limit is None or limit <= 0:
                # Skip cards with zero or missing limit
                continue
            
            # Calculate historical balance at window start
            # Sum all transactions from window_start to today
            cursor.execute("""
                SELECT COALESCE(SUM(t.amount), 0)
                FROM transactions t
                WHERE t.account_id = ?
                AND t.date >= ?
                AND t.pending = 0
            """, (card_id, window_start))
            
            tx_summary = cursor.fetchone()
            net_transactions = tx_summary[0] if tx_summary and tx_summary[0] else 0
            
            # Historical balance = current balance - net transactions in window
            # (transactions are typically negative for credit card charges)
            historical_balance = current_balance - net_transactions
            
            # Use historical balance for utilization calculation
            balance = historical_balance
            
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
                'current_balance': current_balance,
                'limit': limit,
                'utilization': utilization,
                'is_overdue': is_overdue,
                'window': window
            })
        
        if not utilizations:
            # No valid cards to process
            return {'signals_stored': 0, 'cards_processed': 0}
        
        # Calculate aggregate signals
        max_utilization = max(utilizations)
        avg_utilization = sum(utilizations) / len(utilizations) if utilizations else 0
        card_count = len(utilizations)
        
        # Get interest charges (if detectable from credit card data)
        # For MVP, we'll estimate based on APR and historical balance
        total_interest = 0
        for card_detail in card_details:
            card_id = None
            # Find the card_id for this account
            for cid, aid, _, _ in credit_cards:
                if aid == card_detail['account_id']:
                    card_id = cid
                    break
            
            if card_id and card_detail['limit'] > 0:
                cursor.execute("""
                    SELECT apr FROM credit_cards
                    WHERE account_id = ?
                """, (card_id,))
                
                apr_result = cursor.fetchone()
                if apr_result and apr_result[0]:
                    apr = apr_result[0]
                    # Monthly interest = (historical balance * apr / 100) / 12
                    monthly_interest = (card_detail['balance'] * apr / 100) / 12
                    total_interest += monthly_interest
        
        # Store signals
        signals_stored = 0
        
        # Signal 1: credit_utilization_max
        store_signal(user_id, 'credit_utilization_max', max_utilization,
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 2: credit_utilization_avg
        store_signal(user_id, 'credit_utilization_avg', avg_utilization,
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 3: credit_card_count
        store_signal(user_id, 'credit_card_count', float(card_count),
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 4: credit_interest_charges
        store_signal(user_id, 'credit_interest_charges', round(total_interest, 2),
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 5: credit_overdue
        store_signal(user_id, 'credit_overdue', 1.0 if any_overdue else 0.0,
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 6: credit_utilization_flag_30
        store_signal(user_id, 'credit_utilization_flag_30', 
                     1.0 if max_utilization >= 30 else 0.0,
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 7: credit_utilization_flag_50
        store_signal(user_id, 'credit_utilization_flag_50',
                     1.0 if max_utilization >= 50 else 0.0,
                     {'cards': card_details}, window, conn)
        signals_stored += 1
        
        # Signal 8: credit_utilization_flag_80
        store_signal(user_id, 'credit_utilization_flag_80',
                     1.0 if max_utilization >= 80 else 0.0,
                     {'cards': card_details}, window, conn)
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


def detect_subscription_signals(user_id: int, window: str = '30d', conn: Optional[sqlite3.Connection] = None) -> Dict:
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
        
        # Calculate date range based on window (use 90 days for subscription detection to find patterns)
        window_days = _get_window_days(window)
        # For subscription detection, we need longer history to find patterns, so use max of 90 days or window
        search_window = max(90, window_days)
        window_start = TODAY - timedelta(days=search_window)
        
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
        
        # Calculate subscription share (recurring / total spend in window)
        window_days_for_spend = _get_window_days(window)
        window_start_for_spend = TODAY - timedelta(days=window_days_for_spend)
        
        cursor.execute("""
            SELECT SUM(ABS(t.amount))
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            AND t.date >= ?
            AND t.pending = 0
        """, (user_id, window_start_for_spend))
        
        total_spend_result = cursor.fetchone()
        total_spend_in_window = total_spend_result[0] if total_spend_result[0] else 0
        
        subscription_share = (subscription_monthly_spend / total_spend_in_window * 100) if total_spend_in_window > 0 else 0
        
        # Store signals
        signals_stored = 0
        
        metadata = {
            'subscriptions': recurring_subscriptions,
            'total_spend_in_window': total_spend_in_window,
            'window_days': window_days_for_spend
        }
        
        # Signal 1: subscription_count
        store_signal(user_id, 'subscription_count', float(subscription_count),
                     metadata, window, conn)
        signals_stored += 1
        
        # Signal 2: subscription_monthly_spend
        store_signal(user_id, 'subscription_monthly_spend', round(subscription_monthly_spend, 2),
                     metadata, window, conn)
        signals_stored += 1
        
        # Signal 3: subscription_merchants (JSON array)
        store_signal(user_id, 'subscription_merchants', None,
                     {**metadata, 'merchants': subscription_merchants}, window, conn)
        signals_stored += 1
        
        # Signal 4: subscription_share
        store_signal(user_id, 'subscription_share', round(subscription_share, 2),
                     metadata, window, conn)
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


def detect_savings_signals(user_id: int, window: str = '30d', conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Detect savings-related behavioral signals for a user.
    
    Detects:
    - Net inflow to savings accounts (deposits - withdrawals)
    - Savings growth rate (ending balance - starting balance) / starting balance * 100
    - Emergency fund coverage (savings balance / average monthly expenses)
    
    Args:
        user_id: User ID
        window: Time window ('30d' or '180d')
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
        
        # Calculate date range based on window
        window_days = _get_window_days(window)
        window_start = TODAY - timedelta(days=window_days)
        
        # Get all savings accounts for user (savings, money market, cash management, HSA)
        cursor.execute("""
            SELECT a.id, a.account_id, a.current_balance, a.type, a.subtype
            FROM accounts a
            WHERE a.user_id = ? 
            AND a.type = 'depository'
            AND a.subtype IN ('savings', 'money market', 'cash management', 'hsa')
        """, (user_id,))
        
        savings_accounts = cursor.fetchall()
        
        if not savings_accounts:
            # User has no savings accounts - skip gracefully
            return {'signals_stored': 0, 'accounts_processed': 0}
        
        # Aggregate data across all savings accounts
        total_starting_balance = 0
        total_ending_balance = 0
        total_net_inflow = 0
        account_details = []
        
        for account_id, account_db_id, current_balance, account_type, subtype in savings_accounts:
            # Get starting balance (balance at window start or earliest transaction)
            # For simplicity, we'll use the current balance as ending balance
            # and calculate starting balance from transactions
            cursor.execute("""
                SELECT 
                    COALESCE(SUM(CASE WHEN t.amount > 0 THEN t.amount ELSE 0 END), 0) as deposits,
                    COALESCE(SUM(CASE WHEN t.amount < 0 THEN ABS(t.amount) ELSE 0 END), 0) as withdrawals,
                    MIN(t.date) as first_tx_date
                FROM transactions t
                WHERE t.account_id = ?
                AND t.date >= ?
                AND t.pending = 0
            """, (account_db_id, window_start))
            
            tx_summary = cursor.fetchone()
            deposits = tx_summary[0] if tx_summary[0] else 0
            withdrawals = tx_summary[1] if tx_summary[1] else 0
            first_tx_date = tx_summary[2]
            
            # Calculate net inflow for this account
            net_inflow = deposits - withdrawals
            
            # Get balance before window start (approximate by going back further)
            # For simplicity, we'll estimate starting balance as current - net_inflow
            # This assumes no interest or other changes
            starting_balance = current_balance - net_inflow
            if starting_balance < 0:
                starting_balance = 0  # Can't have negative starting balance
            
            total_starting_balance += starting_balance
            total_ending_balance += current_balance
            total_net_inflow += net_inflow
            
            account_details.append({
                'account_id': account_db_id,
                'type': account_type,
                'subtype': subtype,
                'starting_balance': starting_balance,
                'ending_balance': current_balance,
                'net_inflow': net_inflow
            })
        
        # Calculate signals
        signals_stored = 0
        metadata = {
            'accounts': account_details,
            'window_days': window_days
        }
        
        # Signal 1: Net Inflow
        signal_type = f'savings_net_inflow_{window}'
        store_signal(user_id, signal_type, round(total_net_inflow, 2), metadata, window, conn)
        signals_stored += 1
        
        # Signal 2: Growth Rate
        growth_rate = 0.0
        if total_starting_balance > 0:
            growth_rate = ((total_ending_balance - total_starting_balance) / total_starting_balance) * 100
        else:
            # If starting balance is zero, growth rate is undefined (or 0 if ending is also 0)
            if total_ending_balance > 0:
                growth_rate = 100.0  # Infinite growth from zero
        
        signal_type = f'savings_growth_rate_{window}'
        store_signal(user_id, signal_type, round(growth_rate, 2), metadata, window, conn)
        signals_stored += 1
        
        # Signal 3: Emergency Fund Coverage
        # Calculate average monthly expenses from all transactions in window
        cursor.execute("""
            SELECT SUM(ABS(t.amount))
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            AND t.date >= ?
            AND t.amount < 0
            AND t.pending = 0
        """, (user_id, window_start))
        
        total_expenses_result = cursor.fetchone()
        total_expenses = total_expenses_result[0] if total_expenses_result[0] else 0
        
        # Average monthly expenses = total expenses / (window_days / 30)
        months_in_window = window_days / 30.0
        average_monthly_expenses = total_expenses / months_in_window if months_in_window > 0 else 0
        
        emergency_fund_coverage = 0.0
        if average_monthly_expenses > 0:
            emergency_fund_coverage = total_ending_balance / average_monthly_expenses
        
        signal_type = f'emergency_fund_coverage_{window}'
        store_signal(user_id, signal_type, round(emergency_fund_coverage, 2), metadata, window, conn)
        signals_stored += 1
        
        return {
            'signals_stored': signals_stored,
            'accounts_processed': len(savings_accounts),
            'net_inflow': round(total_net_inflow, 2),
            'growth_rate': round(growth_rate, 2),
            'emergency_fund_coverage': round(emergency_fund_coverage, 2)
        }
        
    finally:
        if close_conn:
            conn.close()


def detect_payroll_transactions(user_id: int, window_start: date, conn: sqlite3.Connection) -> List[Dict]:
    """
    Detect recurring payroll transactions from transaction data.
    
    Args:
        user_id: User ID
        window_start: Start date for window
        conn: Database connection
        
    Returns:
        List of payroll transaction groups with frequency and amounts
    """
    cursor = conn.cursor()
    
    # Get all positive transactions (deposits) in checking accounts
    cursor.execute("""
        SELECT t.date, t.amount, t.merchant_name, t.account_id
        FROM transactions t
        JOIN accounts a ON t.account_id = a.id
        WHERE a.user_id = ?
        AND a.type = 'depository'
        AND a.subtype = 'checking'
        AND t.date >= ?
        AND t.amount > 0
        AND t.pending = 0
        ORDER BY t.date
    """, (user_id, window_start))
    
    deposits = cursor.fetchall()
    
    if len(deposits) < 2:
        return []
    
    # Group by normalized merchant name (case-insensitive, handle variations)
    by_merchant = {}
    for tx_date, amount, merchant, account_id in deposits:
        if not merchant:
            continue
        
        # Normalize merchant name (lowercase, remove common prefixes/suffixes)
        merchant_normalized = merchant.strip().lower()
        # Handle variations like "PAYROLL", "PAYROLL-DEPOSIT", "ACME PAYROLL"
        if 'payroll' in merchant_normalized:
            merchant_normalized = 'payroll'
        elif 'deposit' in merchant_normalized and 'payroll' in merchant_normalized:
            merchant_normalized = 'payroll'
        
        if merchant_normalized not in by_merchant:
            by_merchant[merchant_normalized] = []
        
        by_merchant[merchant_normalized].append({
            'date': date.fromisoformat(tx_date) if isinstance(tx_date, str) else tx_date,
            'amount': amount,
            'merchant': merchant
        })
    
    # Find recurring payroll patterns
    payroll_groups = []
    
    for merchant_normalized, txs in by_merchant.items():
        if len(txs) < 2:
            continue
        
        # Sort by date
        txs_sorted = sorted(txs, key=lambda x: x['date'])
        amounts = [tx['amount'] for tx in txs_sorted]
        dates = [tx['date'] for tx in txs_sorted]
        
        # Check if amounts are similar (±10% tolerance for variable income)
        mean_amount = sum(amounts) / len(amounts)
        amounts_similar = all(abs(amt - mean_amount) / mean_amount <= 0.10 for amt in amounts)
        
        if not amounts_similar:
            continue
        
        # Check for regular cadence
        if len(txs_sorted) >= 3:
            # Check if dates follow a pattern
            payroll_groups.append({
                'merchant': txs_sorted[0]['merchant'],
                'count': len(txs_sorted),
                'amounts': amounts,
                'dates': dates,
                'mean_amount': mean_amount
            })
        elif len(txs_sorted) == 2:
            # For 2 transactions, check if they're roughly weekly/bi-weekly/monthly apart
            days_between = (dates[1] - dates[0]).days
            if 7 <= days_between <= 35:  # Weekly to monthly range
                payroll_groups.append({
                    'merchant': txs_sorted[0]['merchant'],
                    'count': len(txs_sorted),
                    'amounts': amounts,
                    'dates': dates,
                    'mean_amount': mean_amount
                })
    
    return payroll_groups


def calculate_payment_frequency(dates: List[date]) -> str:
    """
    Calculate payment frequency from transaction dates.
    
    Args:
        dates: List of transaction dates (sorted)
        
    Returns:
        Frequency string: 'weekly', 'bi-weekly', 'monthly', 'irregular'
    """
    if len(dates) < 2:
        return 'irregular'
    
    sorted_dates = sorted(dates)
    gaps = []
    
    for i in range(len(sorted_dates) - 1):
        days_between = (sorted_dates[i + 1] - sorted_dates[i]).days
        gaps.append(days_between)
    
    if not gaps:
        return 'irregular'
    
    median_gap = sorted(gaps)[len(gaps) // 2]
    
    # Classify based on median gap
    if 5 <= median_gap <= 9:  # 7±2 days
        return 'weekly'
    elif 11 <= median_gap <= 17:  # 14±3 days
        return 'bi-weekly'
    elif 24 <= median_gap <= 33:  # 27-33 days
        return 'monthly'
    else:
        return 'irregular'


def calculate_payment_variability(amounts: List[float]) -> float:
    """
    Calculate payment variability as coefficient of variation.
    
    Args:
        amounts: List of payment amounts
        
    Returns:
        Coefficient of variation (std_dev / mean), or 0.0 if mean is 0
    """
    if not amounts or len(amounts) < 2:
        return 0.0
    
    mean = sum(amounts) / len(amounts)
    if mean == 0:
        return 0.0
    
    variance = sum((x - mean) ** 2 for x in amounts) / len(amounts)
    std_dev = variance ** 0.5
    
    return std_dev / mean


def calculate_median_pay_gap(dates: List[date]) -> float:
    """
    Calculate median days between paychecks.
    
    Args:
        dates: List of payment dates (sorted)
        
    Returns:
        Median days between payments
    """
    if len(dates) < 2:
        return 0.0
    
    sorted_dates = sorted(dates)
    gaps = []
    
    for i in range(len(sorted_dates) - 1):
        days_between = (sorted_dates[i + 1] - sorted_dates[i]).days
        gaps.append(days_between)
    
    if not gaps:
        return 0.0
    
    gaps_sorted = sorted(gaps)
    median = gaps_sorted[len(gaps_sorted) // 2]
    
    return float(median)


def detect_income_signals(user_id: int, window: str = '30d', conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Detect income stability signals for a user.
    
    Detects:
    - Payment frequency (weekly, bi-weekly, monthly, irregular)
    - Payment variability (coefficient of variation)
    - Cash-flow buffer (checking balance / average monthly expenses)
    - Median pay gap (median days between paychecks)
    
    Args:
        user_id: User ID
        window: Time window ('30d' or '180d')
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
        
        # Calculate date range based on window
        window_days = _get_window_days(window)
        window_start = TODAY - timedelta(days=window_days)
        
        # Get checking accounts for user
        cursor.execute("""
            SELECT a.id, a.account_id, a.current_balance
            FROM accounts a
            WHERE a.user_id = ?
            AND a.type = 'depository'
            AND a.subtype = 'checking'
        """, (user_id,))
        
        checking_accounts = cursor.fetchall()
        
        if not checking_accounts:
            # User has no checking account - skip gracefully
            return {'signals_stored': 0, 'payroll_detected': False}
        
        # Get total checking balance (sum across all checking accounts)
        total_checking_balance = sum(acc[2] for acc in checking_accounts)
        
        # Detect payroll transactions
        payroll_groups = detect_payroll_transactions(user_id, window_start, conn)
        
        # Convert dates to strings for JSON serialization
        serializable_payroll_groups = []
        for group in payroll_groups:
            serializable_group = {
                'merchant': group['merchant'],
                'count': group['count'],
                'amounts': group['amounts'],
                'dates': [d.isoformat() if isinstance(d, date) else str(d) for d in group['dates']],
                'mean_amount': group['mean_amount']
            }
            serializable_payroll_groups.append(serializable_group)
        
        # Calculate income signals
        signals_stored = 0
        metadata = {
            'payroll_groups': serializable_payroll_groups,
            'window_days': window_days
        }
        
        # Signal 1: Payment Frequency
        income_frequency = 'irregular'
        if payroll_groups:
            # Use the most frequent payroll group
            largest_group = max(payroll_groups, key=lambda x: x['count'])
            income_frequency = calculate_payment_frequency(largest_group['dates'])
        
        # Store frequency as string (we'll store it in metadata since value is numeric)
        store_signal(user_id, 'income_frequency', None, 
                    {**metadata, 'frequency': income_frequency}, window, conn)
        signals_stored += 1
        
        # Signal 2: Payment Variability
        income_variability = 0.0
        if payroll_groups:
            largest_group = max(payroll_groups, key=lambda x: x['count'])
            income_variability = calculate_payment_variability(largest_group['amounts'])
        
        store_signal(user_id, 'income_variability', round(income_variability, 4), metadata, window, conn)
        signals_stored += 1
        
        # Signal 3: Cash-Flow Buffer
        # Calculate average monthly expenses from all transactions in window
        cursor.execute("""
            SELECT SUM(ABS(t.amount))
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ?
            AND t.date >= ?
            AND t.amount < 0
            AND t.pending = 0
        """, (user_id, window_start))
        
        total_expenses_result = cursor.fetchone()
        total_expenses = total_expenses_result[0] if total_expenses_result[0] else 0
        
        # Average monthly expenses = total expenses / (window_days / 30)
        months_in_window = window_days / 30.0
        average_monthly_expenses = total_expenses / months_in_window if months_in_window > 0 else 0
        
        cash_flow_buffer = 0.0
        if average_monthly_expenses > 0:
            cash_flow_buffer = total_checking_balance / average_monthly_expenses
        
        signal_type = f'cash_flow_buffer_{window}'
        store_signal(user_id, signal_type, round(cash_flow_buffer, 2), metadata, window, conn)
        signals_stored += 1
        
        # Signal 4: Median Pay Gap
        median_pay_gap = 0.0
        if payroll_groups:
            # Combine all payroll dates
            all_dates = []
            for group in payroll_groups:
                all_dates.extend(group['dates'])
            median_pay_gap = calculate_median_pay_gap(all_dates)
        
        store_signal(user_id, 'median_pay_gap', round(median_pay_gap, 1), metadata, window, conn)
        signals_stored += 1
        
        return {
            'signals_stored': signals_stored,
            'payroll_detected': len(payroll_groups) > 0,
            'income_frequency': income_frequency,
            'income_variability': round(income_variability, 4),
            'cash_flow_buffer': round(cash_flow_buffer, 2),
            'median_pay_gap': round(median_pay_gap, 1)
        }
        
    finally:
        if close_conn:
            conn.close()


def detect_all_signals(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Run all signal detection for a user for both 30-day and 180-day windows.
    
    Args:
        user_id: User ID
        conn: Database connection (creates new if None)
        
    Returns:
        Dictionary with all detection results for both windows
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    try:
        results = {
            'user_id': user_id,
            'windows': {},
            'total_signals': 0
        }
        
        # Run detection for both windows
        for window in ['30d', '180d']:
            window_results = {
                'credit_signals': {},
                'subscription_signals': {},
                'savings_signals': {},
                'income_signals': {},
                'window_signals': 0
            }
            
            # Detect credit signals
            try:
                credit_results = detect_credit_signals(user_id, window, conn)
                window_results['credit_signals'] = credit_results
                window_results['window_signals'] += credit_results.get('signals_stored', 0)
            except Exception as e:
                window_results['credit_signals'] = {'error': str(e)}
            
            # Detect subscription signals
            try:
                subscription_results = detect_subscription_signals(user_id, window, conn)
                window_results['subscription_signals'] = subscription_results
                window_results['window_signals'] += subscription_results.get('signals_stored', 0)
            except Exception as e:
                window_results['subscription_signals'] = {'error': str(e)}
            
            # Detect savings signals
            try:
                savings_results = detect_savings_signals(user_id, window, conn)
                window_results['savings_signals'] = savings_results
                window_results['window_signals'] += savings_results.get('signals_stored', 0)
            except Exception as e:
                window_results['savings_signals'] = {'error': str(e)}
            
            # Detect income signals
            try:
                income_results = detect_income_signals(user_id, window, conn)
                window_results['income_signals'] = income_results
                window_results['window_signals'] += income_results.get('signals_stored', 0)
            except Exception as e:
                window_results['income_signals'] = {'error': str(e)}
            
            results['windows'][window] = window_results
            results['total_signals'] += window_results['window_signals']
        
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
            
            windows_data = result.get('windows', {})
            for window in ['30d', '180d']:
                if window in windows_data:
                    w_data = windows_data[window]
                    credit_info = w_data.get('credit_signals', {})
                    sub_info = w_data.get('subscription_signals', {})
                    savings_info = w_data.get('savings_signals', {})
                    income_info = w_data.get('income_signals', {})
                    
                    print(f"  {window}:")
                    print(f"    ✓ Credit: {credit_info.get('signals_stored', 0)} "
                          f"(max util: {credit_info.get('max_utilization', 0):.1f}%)")
                    print(f"    ✓ Subscriptions: {sub_info.get('signals_stored', 0)} "
                          f"(found: {sub_info.get('subscriptions_found', 0)})")
                    print(f"    ✓ Savings: {savings_info.get('signals_stored', 0)}")
                    print(f"    ✓ Income: {income_info.get('signals_stored', 0)}")
        
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

