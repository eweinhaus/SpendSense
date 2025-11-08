"""
User data helper functions for Phase 8A end-user application.
Reusable functions for aggregating user data across views.
"""

import json
from typing import Dict, List, Optional
from .database import get_db_connection


def get_user_persona_summary(user_id: int) -> Optional[Dict]:
    """Get user's persona with key insights."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT persona_type, criteria_matched, assigned_at
            FROM personas WHERE user_id = ?
        """, (user_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        persona_type, criteria_matched, assigned_at = row
        
        # Get persona descriptions
        persona_descriptions = {
            'high_utilization': {
                'name': 'High Utilization',
                'description': 'You have high credit card utilization, which can impact your credit score.',
                'insights': ['High credit utilization detected', 'Consider paying down balances']
            },
            'variable_income_budgeter': {
                'name': 'Variable Income Budgeter',
                'description': 'You have irregular income patterns and may benefit from budgeting strategies.',
                'insights': ['Variable income detected', 'Build cash buffer for stability']
            },
            'savings_builder': {
                'name': 'Savings Builder',
                'description': 'You\'re building savings effectively. Keep up the good work!',
                'insights': ['Positive savings growth', 'Maintain emergency fund']
            },
            'financial_newcomer': {
                'name': 'Financial Newcomer',
                'description': 'You\'re new to managing credit and finances. Educational resources can help.',
                'insights': ['Low credit utilization', 'Learning financial basics']
            },
            'subscription_heavy': {
                'name': 'Subscription-Heavy',
                'description': 'You have multiple recurring subscriptions. Review and optimize your spending.',
                'insights': ['Multiple subscriptions detected', 'Consider subscription management']
            },
            'neutral': {
                'name': 'Neutral',
                'description': 'Your financial patterns are balanced. Continue monitoring your finances.',
                'insights': ['Balanced financial profile', 'No major concerns detected']
            }
        }
        
        persona_info = persona_descriptions.get(persona_type, persona_descriptions['neutral'])
        
        return {
            'type': persona_type,
            'name': persona_info['name'],
            'description': persona_info['description'],
            'insights': persona_info['insights'],
            'criteria_matched': criteria_matched,
            'assigned_at': assigned_at
        }
    finally:
        conn.close()


def get_user_signal_summary(user_id: int) -> Dict:
    """Get aggregated signal data for user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get latest signals (prefer 30d window)
        cursor.execute("""
            SELECT signal_type, value, metadata, window
            FROM signals
            WHERE user_id = ?
            ORDER BY 
                CASE WHEN window = '30d' THEN 1 ELSE 2 END,
                signal_type
        """, (user_id,))
        
        signals = {}
        for row in cursor.fetchall():
            signal_type, value, metadata_json, window = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            # Use 30d window signals preferentially
            base_type = signal_type.replace('_30d', '').replace('_180d', '')
            if base_type not in signals or window == '30d':
                signals[base_type] = {
                    'value': value,
                    'metadata': metadata,
                    'window': window
                }
        
        # Extract key metrics
        result = {}
        
        # Credit signals
        if 'credit_utilization_max' in signals:
            result['credit_utilization_max'] = signals['credit_utilization_max']['value'] or 0
        if 'credit_utilization_avg' in signals:
            result['credit_utilization_avg'] = signals['credit_utilization_avg']['value'] or 0
        if 'credit_interest_charges' in signals:
            result['credit_interest_charges'] = signals['credit_interest_charges']['value'] or 0
        
        # Subscription signals
        if 'subscription_count' in signals:
            result['subscription_count'] = int(signals['subscription_count']['value'] or 0)
        if 'subscription_monthly_spend' in signals:
            result['subscription_monthly_spend'] = signals['subscription_monthly_spend']['value'] or 0
        
        # Savings signals
        if 'savings_net_inflow_30d' in signals:
            result['savings_net_inflow'] = signals['savings_net_inflow_30d']['value'] or 0
        if 'savings_growth_rate_30d' in signals:
            result['savings_growth_rate'] = signals['savings_growth_rate_30d']['value'] or 0
        if 'emergency_fund_coverage_30d' in signals:
            result['emergency_fund_coverage'] = signals['emergency_fund_coverage_30d']['value'] or 0
        
        # Income signals
        if 'income_variability' in signals:
            result['income_variability'] = signals['income_variability']['value'] or 0
        if 'cash_flow_buffer_30d' in signals:
            result['cash_flow_buffer'] = signals['cash_flow_buffer_30d']['value'] or 0
        if 'median_pay_gap' in signals:
            result['median_pay_gap'] = signals['median_pay_gap']['value'] or 0
        if 'income_frequency' in signals:
            metadata = signals['income_frequency'].get('metadata', {})
            result['income_frequency'] = metadata.get('frequency', 'irregular')
        
        return result
    finally:
        conn.close()


def get_user_account_summary(user_id: int) -> Dict:
    """Get account balances, types, and limits."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT type, subtype, SUM(current_balance) as total_balance, 
                   SUM(CASE WHEN "limit" IS NOT NULL THEN "limit" ELSE 0 END) as total_limit,
                   COUNT(*) as count
            FROM accounts
            WHERE user_id = ?
            GROUP BY type, subtype
        """, (user_id,))
        
        accounts_by_type = {}
        total_balance = 0
        total_credit_limit = 0
        
        for row in cursor.fetchall():
            acc_type, subtype, balance, limit, count = row
            balance = balance or 0
            limit = limit or 0
            
            key = f"{acc_type}_{subtype or 'default'}"
            accounts_by_type[key] = {
                'type': acc_type,
                'subtype': subtype,
                'balance': balance,
                'limit': limit,
                'count': count
            }
            
            total_balance += balance
            if acc_type == 'credit':
                total_credit_limit += limit
        
        # Get credit utilization
        cursor.execute("""
            SELECT SUM(current_balance) as total_balance, SUM("limit") as total_limit
            FROM accounts
            WHERE user_id = ? AND type = 'credit'
        """, (user_id,))
        
        credit_row = cursor.fetchone()
        credit_utilization = 0
        if credit_row and credit_row[0] and credit_row[1]:
            total_credit_balance = credit_row[0] or 0
            total_credit_limit = credit_row[1] or 0
            if total_credit_limit > 0:
                credit_utilization = (total_credit_balance / total_credit_limit) * 100
        
        return {
            'accounts_by_type': accounts_by_type,
            'total_balance': total_balance,
            'total_credit_limit': total_credit_limit,
            'credit_utilization': credit_utilization,
            'total_accounts': sum(acc['count'] for acc in accounts_by_type.values())
        }
    finally:
        conn.close()


def calculate_quick_stats(user_id: int) -> Dict:
    """Calculate quick stats: emergency fund, cash buffer, subscription spend, credit utilization."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get monthly expenses (approximate from last 30 days of transactions)
        cursor.execute("""
            SELECT SUM(ABS(amount)) as monthly_expenses
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? 
              AND t.date >= date('now', '-30 days')
              AND amount < 0
        """, (user_id,))
        
        expense_row = cursor.fetchone()
        monthly_expenses = expense_row[0] if expense_row and expense_row[0] else 0
        
        # Get savings balance
        cursor.execute("""
            SELECT SUM(current_balance) as savings_balance
            FROM accounts
            WHERE user_id = ? AND type IN ('depository', 'savings')
        """, (user_id,))
        
        savings_row = cursor.fetchone()
        savings_balance = savings_row[0] if savings_row and savings_row[0] else 0
        
        # Calculate emergency fund coverage (months)
        emergency_fund_months = 0
        if monthly_expenses > 0:
            emergency_fund_months = savings_balance / monthly_expenses
        
        # Get subscription monthly spend
        cursor.execute("""
            SELECT value FROM signals
            WHERE user_id = ? AND signal_type = 'subscription_monthly_spend'
            LIMIT 1
        """, (user_id,))
        
        sub_row = cursor.fetchone()
        subscription_spend = sub_row[0] if sub_row and sub_row[0] else 0
        
        # Get cash flow buffer
        cursor.execute("""
            SELECT value FROM signals
            WHERE user_id = ? AND signal_type = 'cash_flow_buffer_30d'
            LIMIT 1
        """, (user_id,))
        
        buffer_row = cursor.fetchone()
        cash_flow_buffer = buffer_row[0] if buffer_row and buffer_row[0] else 0
        
        # Get credit utilization
        cursor.execute("""
            SELECT value FROM signals
            WHERE user_id = ? AND signal_type = 'credit_utilization_max'
            LIMIT 1
        """, (user_id,))
        
        util_row = cursor.fetchone()
        credit_utilization = util_row[0] if util_row and util_row[0] else 0
        
        return {
            'emergency_fund_months': round(emergency_fund_months, 1),
            'emergency_fund_target_3mo': monthly_expenses * 3,
            'emergency_fund_target_6mo': monthly_expenses * 6,
            'monthly_expenses': monthly_expenses,
            'savings_balance': savings_balance,
            'subscription_spend': subscription_spend,
            'cash_flow_buffer': cash_flow_buffer,
            'credit_utilization': round(credit_utilization, 1)
        }
    finally:
        conn.close()


def get_user_transaction_insights(user_id: int, days: int = 30) -> Dict:
    """Get transaction insights: spending patterns, top merchants, spending by category."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Top merchants
        cursor.execute("""
            SELECT merchant_name, COUNT(*) as count, SUM(ABS(amount)) as total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? 
              AND t.date >= date('now', '-' || ? || ' days')
              AND amount < 0
              AND merchant_name IS NOT NULL
            GROUP BY merchant_name
            ORDER BY total DESC
            LIMIT 10
        """, (user_id, days))
        
        top_merchants = []
        for row in cursor.fetchall():
            merchant, count, total = row
            top_merchants.append({
                'merchant': merchant,
                'count': count,
                'total': total or 0
            })
        
        # Spending by category
        cursor.execute("""
            SELECT personal_finance_category, COUNT(*) as count, SUM(ABS(amount)) as total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? 
              AND t.date >= date('now', '-' || ? || ' days')
              AND amount < 0
              AND personal_finance_category IS NOT NULL
            GROUP BY personal_finance_category
            ORDER BY total DESC
        """, (user_id, days))
        
        spending_by_category = []
        for row in cursor.fetchall():
            category, count, total = row
            spending_by_category.append({
                'category': category,
                'count': count,
                'total': total or 0
            })
        
        # Monthly spending pattern (last 3 months)
        cursor.execute("""
            SELECT strftime('%Y-%m', t.date) as month, SUM(ABS(amount)) as total
            FROM transactions t
            JOIN accounts a ON t.account_id = a.id
            WHERE a.user_id = ? 
              AND t.date >= date('now', '-90 days')
              AND amount < 0
            GROUP BY month
            ORDER BY month
        """, (user_id,))
        
        monthly_pattern = []
        for row in cursor.fetchall():
            month, total = row
            monthly_pattern.append({
                'month': month,
                'total': total or 0
            })
        
        return {
            'top_merchants': top_merchants,
            'spending_by_category': spending_by_category,
            'monthly_pattern': monthly_pattern
        }
    finally:
        conn.close()




