"""
Synthetic data generation for SpendSense Phase 4.
Generates 50-100 diverse user profiles with realistic financial data.
Supports all Plaid account types including money market, HSA, mortgages, and student loans.
"""

import sqlite3
import random
import json
import os
from datetime import date, timedelta
from faker import Faker
from .database import get_db_connection


# Set seed for deterministic generation
SEED = 42
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)

# Today's date (for relative date calculations)
TODAY = date.today()

# Configuration: Number of users to generate (50-100, default 75)
NUM_USERS = int(os.getenv('NUM_USERS', 75))


def days_ago(n: int) -> date:
    """Get date n days ago from today."""
    return TODAY - timedelta(days=n)


def generate_user(user_profile: dict, conn: sqlite3.Connection) -> int:
    """
    Generate a single user with synthetic name and email.
    
    Args:
        user_profile: Dictionary with user profile information (can include 'name' and 'email')
        conn: Database connection
        
    Returns:
        User ID of created user
    """
    cursor = conn.cursor()
    
    # Use provided name/email or generate new ones
    name = user_profile.get('name', fake.name())
    email = user_profile.get('email', fake.unique.email())
    
    try:
        cursor.execute("""
            INSERT INTO users (name, email, consent_given)
            VALUES (?, ?, ?)
        """, (name, email, False))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        if not user_id or user_id == 0:
            raise ValueError(f"Failed to insert user - lastrowid is {user_id}")
        
        return user_id
    except sqlite3.IntegrityError as e:
        conn.rollback()
        raise ValueError(f"Database constraint error: {str(e)}")
    except Exception as e:
        conn.rollback()
        raise ValueError(f"Error inserting user: {str(e)}")


def generate_accounts(user_id: int, profile: dict, conn: sqlite3.Connection) -> dict:
    """
    Generate accounts for a user (checking, savings, credit cards, money market, HSA, mortgages, student loans).
    
    Args:
        user_id: User ID
        profile: User profile dictionary with account specifications
        conn: Database connection
        
    Returns:
        Dictionary with account IDs and metadata
    """
    cursor = conn.cursor()
    accounts_info = {
        'checking': None,
        'savings': None,
        'money_market': None,
        'hsa': None,
        'credit_cards': [],
        'mortgages': [],
        'student_loans': []
    }
    
    # Helper to generate unique account_id
    def get_unique_account_id():
        import time
        import uuid
        max_attempts = 20
        for attempt in range(max_attempts):
            # Use UUID for guaranteed uniqueness
            unique_suffix = str(uuid.uuid4())[:12].replace('-', '')
            account_id = f"acc_{int(time.time() * 1000000)}_{unique_suffix}"
            cursor.execute("SELECT id FROM accounts WHERE account_id = ?", (account_id,))
            if not cursor.fetchone():
                return account_id
        # Final fallback: timestamp + UUID + random
        return f"acc_{int(time.time() * 1000000)}_{uuid.uuid4().hex[:12]}_{random.randint(100000, 999999)}"
    
    # Generate checking account for all users
    checking_account_id = get_unique_account_id()
    checking_balance = profile.get('checking_balance', random.uniform(500, 5000))
    
    cursor.execute("""
        INSERT INTO accounts (
            user_id, account_id, type, subtype, available_balance,
            current_balance, iso_currency_code, holder_category
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, checking_account_id, 'depository', 'checking',
        checking_balance, checking_balance, 'USD', 'consumer'
    ))
    
    checking_db_id = cursor.lastrowid
    accounts_info['checking'] = {
        'account_id': checking_account_id,
        'db_id': checking_db_id
    }
    
    # Generate savings account (if specified in profile)
    if profile.get('savings_balance') is not None:
        savings_account_id = get_unique_account_id()
        savings_balance = profile.get('savings_balance', random.uniform(1000, 10000))
        
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, available_balance,
                current_balance, iso_currency_code, holder_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, savings_account_id, 'depository', 'savings',
            savings_balance, savings_balance, 'USD', 'consumer'
        ))
        
        savings_db_id = cursor.lastrowid
        accounts_info['savings'] = {
            'account_id': savings_account_id,
            'db_id': savings_db_id
        }
    
    # Generate money market account (if specified)
    if profile.get('money_market_balance') is not None:
        mm_account_id = get_unique_account_id()
        mm_balance = profile.get('money_market_balance', random.uniform(5000, 50000))
        
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, available_balance,
                current_balance, iso_currency_code, holder_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, mm_account_id, 'depository', 'money market',
            mm_balance, mm_balance, 'USD', 'consumer'
        ))
        
        mm_db_id = cursor.lastrowid
        accounts_info['money_market'] = {
            'account_id': mm_account_id,
            'db_id': mm_db_id
        }
    
    # Generate HSA account (if specified)
    if profile.get('hsa_balance') is not None:
        hsa_account_id = get_unique_account_id()
        hsa_balance = profile.get('hsa_balance', random.uniform(1000, 10000))
        
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, available_balance,
                current_balance, iso_currency_code, holder_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, hsa_account_id, 'depository', 'hsa',
            hsa_balance, hsa_balance, 'USD', 'consumer'
        ))
        
        hsa_db_id = cursor.lastrowid
        accounts_info['hsa'] = {
            'account_id': hsa_account_id,
            'db_id': hsa_db_id
        }
    
    # Generate credit cards based on profile
    credit_cards = profile.get('credit_cards', [])
    for card_spec in credit_cards:
        card_account_id = get_unique_account_id()
        limit = card_spec['limit']
        balance = card_spec['balance']
        utilization = (balance / limit) * 100 if limit > 0 else 0
        
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, available_balance,
                current_balance, "limit", iso_currency_code, holder_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, card_account_id, 'credit', 'credit card',
            limit - balance, balance, limit, 'USD', 'consumer'
        ))
        
        card_db_id = cursor.lastrowid
        accounts_info['credit_cards'].append({
            'account_id': card_account_id,
            'db_id': card_db_id,
            'limit': limit,
            'balance': balance,
            'utilization': utilization
        })
    
    # Generate mortgages (if specified)
    mortgages = profile.get('mortgages', [])
    for mortgage_spec in mortgages:
        mortgage_account_id = get_unique_account_id()
        balance = mortgage_spec.get('balance', random.uniform(100000, 500000))
        
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, available_balance,
                current_balance, iso_currency_code, holder_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, mortgage_account_id, 'liability', 'mortgage',
            0, balance, 'USD', 'consumer'
        ))
        
        mortgage_db_id = cursor.lastrowid
        accounts_info['mortgages'].append({
            'account_id': mortgage_account_id,
            'db_id': mortgage_db_id,
            'spec': mortgage_spec
        })
    
    # Generate student loans (if specified)
    student_loans = profile.get('student_loans', [])
    for loan_spec in student_loans:
        loan_account_id = get_unique_account_id()
        balance = loan_spec.get('balance', random.uniform(10000, 100000))
        
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, subtype, available_balance,
                current_balance, iso_currency_code, holder_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, loan_account_id, 'liability', 'student',
            0, balance, 'USD', 'consumer'
        ))
        
        loan_db_id = cursor.lastrowid
        accounts_info['student_loans'].append({
            'account_id': loan_account_id,
            'db_id': loan_db_id,
            'spec': loan_spec
        })
    
    conn.commit()
    return accounts_info


def generate_credit_card(account_id: int, card_spec: dict, conn: sqlite3.Connection) -> None:
    """
    Generate credit card liability data.
    
    Args:
        account_id: Database account ID
        card_spec: Credit card specification from profile
        conn: Database connection
    """
    cursor = conn.cursor()
    
    balance = card_spec['balance']
    limit = card_spec['limit']
    
    # Realistic APR (15-25%)
    apr = card_spec.get('apr', random.uniform(15.0, 25.0))
    
    # Minimum payment (typically 1-3% of balance)
    minimum_payment = card_spec.get('minimum_payment', balance * 0.02)
    
    # Last payment amount (realistic based on balance)
    last_payment = card_spec.get('last_payment', max(100, balance * 0.1))
    
    # Overdue status
    is_overdue = card_spec.get('is_overdue', False)
    
    # Next payment due date (20-30 days in future)
    next_due_date = TODAY + timedelta(days=random.randint(20, 30))
    
    # Last statement balance matches current balance
    last_statement_balance = balance
    
    cursor.execute("""
        INSERT INTO credit_cards (
            account_id, apr, minimum_payment_amount, last_payment_amount,
            is_overdue, next_payment_due_date, last_statement_balance
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        account_id, apr, minimum_payment, last_payment,
        is_overdue, next_due_date, last_statement_balance
    ))
    
    conn.commit()


def generate_liability(account_id: int, liability_type: str, liability_spec: dict, 
                       conn: sqlite3.Connection) -> None:
    """
    Generate liability data for mortgages or student loans.
    
    Args:
        account_id: Database account ID
        liability_type: 'mortgage' or 'student'
        liability_spec: Liability specification from profile
        conn: Database connection
    """
    cursor = conn.cursor()
    
    # Interest rate (mortgages: 3-6%, student loans: 3-8%)
    if liability_type == 'mortgage':
        interest_rate = liability_spec.get('interest_rate', random.uniform(3.0, 6.0))
        last_payment = liability_spec.get('last_payment_amount', random.uniform(1000, 3000))
    else:  # student loan
        interest_rate = liability_spec.get('interest_rate', random.uniform(3.0, 8.0))
        last_payment = liability_spec.get('last_payment_amount', random.uniform(100, 500))
    
    # Next payment due date (15-30 days in future)
    next_due_date = TODAY + timedelta(days=random.randint(15, 30))
    
    cursor.execute("""
        INSERT INTO liabilities (
            account_id, liability_type, interest_rate,
            next_payment_due_date, last_payment_amount
        ) VALUES (?, ?, ?, ?, ?)
    """, (
        account_id, liability_type, interest_rate,
        next_due_date, last_payment
    ))
    
    conn.commit()


def generate_transactions(account_id: int, account_type: str, profile: dict, 
                          conn: sqlite3.Connection) -> None:
    """
    Generate 90 days of transactions for an account.
    
    Args:
        account_id: Database account ID
        account_type: 'checking' or 'credit'
        profile: User profile dictionary
        conn: Database connection
    """
    cursor = conn.cursor()
    
    # Transaction templates by category
    templates = {
        'coffee': {'amount_range': (3.0, 6.0), 'frequency': 'daily', 
                   'merchants': ['Starbucks', 'Dunkin', 'Local Coffee Shop']},
        'gas': {'amount_range': (30.0, 50.0), 'frequency': 'weekly',
                'merchants': ['Shell', 'BP', 'Exxon', 'Chevron']},
        'groceries': {'amount_range': (50.0, 150.0), 'frequency': 'weekly',
                      'merchants': ['Walmart', 'Target', 'Kroger', 'Whole Foods']},
        'dining': {'amount_range': (20.0, 60.0), 'frequency': 'weekly',
                   'merchants': ['Chipotle', 'McDonald\'s', 'Olive Garden', 'Local Restaurant']},
        'utilities': {'amount_range': (80.0, 150.0), 'frequency': 'monthly',
                      'merchants': ['Electric Company', 'Gas Company', 'Water Utility']},
    }
    
    transactions = []
    
    # Generate daily transactions (coffee)
    if account_type == 'credit':
        for i in range(90):
            if random.random() < 0.7:  # 70% chance of coffee transaction
                date_val = days_ago(90 - i)
                merchant = random.choice(templates['coffee']['merchants'])
                amount = round(random.uniform(*templates['coffee']['amount_range']), 2)
                transactions.append({
                    'date': date_val,
                    'amount': amount,
                    'merchant': merchant,
                    'category': 'FOOD_AND_DRINK',
                    'channel': random.choice(['in store', 'other'])
                })
    
    # Generate weekly transactions (gas, groceries, dining)
    for i in range(0, 90, 7):
        if random.random() < 0.8:  # Weekly gas
            date_val = days_ago(90 - i + random.randint(0, 6))
            merchant = random.choice(templates['gas']['merchants'])
            amount = round(random.uniform(*templates['gas']['amount_range']), 2)
            transactions.append({
                'date': date_val,
                'amount': amount,
                'merchant': merchant,
                'category': 'GENERAL_MERCHANDISE',
                'channel': 'in store'
            })
        
        if random.random() < 0.9:  # Weekly groceries
            date_val = days_ago(90 - i + random.randint(0, 6))
            merchant = random.choice(templates['groceries']['merchants'])
            amount = round(random.uniform(*templates['groceries']['amount_range']), 2)
            transactions.append({
                'date': date_val,
                'amount': amount,
                'merchant': merchant,
                'category': 'GENERAL_MERCHANDISE',
                'channel': random.choice(['in store', 'online'])
            })
        
        if random.random() < 0.6:  # Weekly dining
            date_val = days_ago(90 - i + random.randint(0, 6))
            merchant = random.choice(templates['dining']['merchants'])
            amount = round(random.uniform(*templates['dining']['amount_range']), 2)
            transactions.append({
                'date': date_val,
                'amount': amount,
                'merchant': merchant,
                'category': 'FOOD_AND_DRINK',
                'channel': random.choice(['in store', 'online'])
            })
    
    # Generate monthly transactions (utilities)
    for i in range(0, 90, 30):
        date_val = days_ago(90 - i + random.randint(0, 29))
        merchant = random.choice(templates['utilities']['merchants'])
        amount = round(random.uniform(*templates['utilities']['amount_range']), 2)
        transactions.append({
            'date': date_val,
            'amount': amount,
            'merchant': merchant,
            'category': 'GENERAL_SERVICES',
            'channel': 'online'
        })
    
    # Add profile-specific subscriptions (only for checking accounts)
    if account_type == 'checking':
        subscriptions = profile.get('subscriptions', [])
        for sub in subscriptions:
            merchant = sub['merchant']
            amount = sub['amount']
            # Generate exactly 3 occurrences, approximately 30 days apart
            # Start from ~85 days ago (to ensure within 90-day window), then ~55, then ~25
            # Ensure spacing stays within 27-33 day range for detection
            for occurrence in range(3):
                # Calculate base date (85, 55, 25 days ago) to ensure within 90-day window
                base_days = 85 - (occurrence * 30)
                # Add small random offset (±1 day) for realism, but keep within range
                offset = random.randint(-1, 1)
                date_val = days_ago(base_days + offset)
                transactions.append({
                    'date': date_val,
                    'amount': amount,
                    'merchant': merchant,
                    'category': 'GENERAL_SERVICES',
                    'channel': 'online'
                })
    
    # Add credit card payments (negative amounts for credit accounts)
    if account_type == 'credit':
        for i in range(0, 90, 30):
            date_val = days_ago(90 - i + random.randint(0, 5))
            payment_amount = round(random.uniform(100, 500), 2)
            transactions.append({
                'date': date_val,
                'amount': -payment_amount,  # Negative for payments
                'merchant': 'Credit Card Payment',
                'category': 'TRANSFER_OUT',
                'channel': 'online'
            })
    
    # Insert transactions
    for tx in transactions:
        cursor.execute("""
            INSERT INTO transactions (
                account_id, date, amount, merchant_name, payment_channel,
                personal_finance_category, pending
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            account_id, tx['date'], tx['amount'], tx['merchant'],
            tx['channel'], tx['category'], random.random() < 0.1  # 10% pending
        ))
    
    conn.commit()


def generate_high_utilization_profile() -> dict:
    """Generate a high utilization user profile."""
    num_cards = random.choice([1, 2])
    credit_cards = []
    
    for _ in range(num_cards):
        limit = random.uniform(3000, 10000)
        utilization = random.uniform(0.65, 0.85)  # High utilization
        balance = limit * utilization
        credit_cards.append({
            'limit': round(limit, 2),
            'balance': round(balance, 2),
            'apr': random.uniform(18.0, 25.0),
            'is_overdue': random.random() < 0.2  # 20% chance overdue
        })
    
    return {
        'checking_balance': random.uniform(500, 3000),
        'savings_balance': random.uniform(0, 2000) if random.random() < 0.5 else None,
        'credit_cards': credit_cards,
        'subscriptions': []
    }


def generate_variable_income_profile() -> dict:
    """Generate a variable income budgeter profile."""
    return {
        'checking_balance': random.uniform(200, 1500),
        'savings_balance': random.uniform(500, 3000) if random.random() < 0.7 else None,
        'credit_cards': [{
            'limit': random.uniform(2000, 8000),
            'balance': random.uniform(300, 1500),  # Low-medium utilization
            'apr': random.uniform(15.0, 22.0),
            'is_overdue': False
        }],
        'subscriptions': random.sample([
            {'merchant': 'Netflix', 'amount': 15.99},
            {'merchant': 'Spotify', 'amount': 9.99},
            {'merchant': 'Gym Membership', 'amount': 49.99},
        ], k=random.randint(1, 3))
    }


def generate_subscription_heavy_profile() -> dict:
    """Generate a subscription-heavy user profile."""
    subscriptions = random.sample([
        {'merchant': 'Netflix', 'amount': 15.99},
        {'merchant': 'Spotify', 'amount': 9.99},
        {'merchant': 'Hulu', 'amount': 7.99},
        {'merchant': 'Disney+', 'amount': 10.99},
        {'merchant': 'Amazon Prime', 'amount': 14.99},
        {'merchant': 'Gym Membership', 'amount': 49.99},
        {'merchant': 'Adobe Creative Cloud', 'amount': 22.99},
        {'merchant': 'Microsoft 365', 'amount': 6.99},
        {'merchant': 'Dropbox', 'amount': 9.99},
        {'merchant': 'Apple iCloud', 'amount': 2.99},
        {'merchant': 'YouTube Premium', 'amount': 11.99},
        {'merchant': 'Apple Music', 'amount': 9.99},
    ], k=random.randint(4, 8))
    
    return {
        'checking_balance': random.uniform(1000, 5000),
        'savings_balance': random.uniform(1000, 5000) if random.random() < 0.6 else None,
        'credit_cards': [{
            'limit': random.uniform(5000, 15000),
            'balance': random.uniform(500, 2000),  # Low utilization
            'apr': random.uniform(15.0, 20.0),
            'is_overdue': False
        }],
        'subscriptions': subscriptions
    }


def generate_savings_builder_profile() -> dict:
    """Generate a savings builder profile."""
    # Some users have savings, money market, or HSA accounts
    has_savings = random.random() < 0.8
    has_money_market = random.random() < 0.3
    has_hsa = random.random() < 0.2
    
    profile = {
        'checking_balance': random.uniform(2000, 8000),
        'savings_balance': random.uniform(3000, 20000) if has_savings else None,
        'money_market_balance': random.uniform(10000, 50000) if has_money_market else None,
        'hsa_balance': random.uniform(2000, 15000) if has_hsa else None,
        'credit_cards': [{
            'limit': random.uniform(5000, 15000),
            'balance': random.uniform(200, 1500),  # Low utilization
            'apr': random.uniform(14.0, 19.0),
            'is_overdue': False
        }],
        'subscriptions': random.sample([
            {'merchant': 'Netflix', 'amount': 15.99},
            {'merchant': 'Spotify', 'amount': 9.99},
        ], k=random.randint(0, 2))
    }
    
    # Some savings builders have mortgages
    if random.random() < 0.4:
        profile['mortgages'] = [{
            'balance': random.uniform(150000, 400000),
            'interest_rate': random.uniform(3.0, 6.0),
            'last_payment_amount': random.uniform(1200, 2500)
        }]
    
    return profile


def generate_custom_persona_profile() -> dict:
    """Generate a custom persona profile (mix of characteristics)."""
    profile = {
        'checking_balance': random.uniform(1000, 6000),
        'savings_balance': random.uniform(1000, 10000) if random.random() < 0.6 else None,
        'credit_cards': [],
        'subscriptions': []
    }
    
    # Random number of credit cards
    num_cards = random.randint(1, 3)
    for _ in range(num_cards):
        limit = random.uniform(2000, 12000)
        utilization = random.uniform(0.1, 0.6)
        profile['credit_cards'].append({
            'limit': round(limit, 2),
            'balance': round(limit * utilization, 2),
            'apr': random.uniform(15.0, 23.0),
            'is_overdue': random.random() < 0.1
        })
    
    # Random subscriptions
    available_subs = [
        {'merchant': 'Netflix', 'amount': 15.99},
        {'merchant': 'Spotify', 'amount': 9.99},
        {'merchant': 'Gym Membership', 'amount': 49.99},
        {'merchant': 'Amazon Prime', 'amount': 14.99},
    ]
    profile['subscriptions'] = random.sample(available_subs, k=random.randint(0, 3))
    
    # Some have student loans
    if random.random() < 0.3:
        profile['student_loans'] = [{
            'balance': random.uniform(15000, 80000),
            'interest_rate': random.uniform(3.0, 7.0),
            'last_payment_amount': random.uniform(150, 400)
        }]
    
    return profile


def generate_neutral_profile() -> dict:
    """Generate a neutral/healthy profile."""
    return {
        'checking_balance': random.uniform(2000, 7000),
        'savings_balance': random.uniform(2000, 15000) if random.random() < 0.7 else None,
        'credit_cards': [{
            'limit': random.uniform(5000, 15000),
            'balance': random.uniform(500, 3000),  # Low-medium utilization (10-20%)
            'apr': random.uniform(14.0, 19.0),
            'is_overdue': False
        }],
        'subscriptions': random.sample([
            {'merchant': 'Netflix', 'amount': 15.99},
            {'merchant': 'Spotify', 'amount': 9.99},
        ], k=random.randint(1, 2))
    }


def generate_all_users(conn: sqlite3.Connection) -> dict:
    """
    Generate 50-100 user profiles with complete data based on persona distribution.
    
    Args:
        conn: Database connection
        
    Returns:
        Summary dictionary with generation results
    """
    # Calculate user distribution based on NUM_USERS
    # Target distribution per PRD:
    # ~20 High Utilization (Persona 1)
    # ~15 Variable Income Budgeter (Persona 2)
    # ~20 Subscription-Heavy (Persona 3)
    # ~15 Savings Builder (Persona 4)
    # ~10 Custom Persona (Persona 5)
    # ~20 Neutral/Healthy (may overlap)
    
    total = NUM_USERS
    high_util = max(1, int(total * 0.27))  # ~20/75
    var_income = max(1, int(total * 0.20))  # ~15/75
    sub_heavy = max(1, int(total * 0.27))  # ~20/75
    savings_builder = max(1, int(total * 0.20))  # ~15/75
    custom_persona = max(1, int(total * 0.13))  # ~10/75
    neutral = total - high_util - var_income - sub_heavy - savings_builder - custom_persona
    
    profile_generators = [
        ('high_utilization', generate_high_utilization_profile, high_util),
        ('variable_income', generate_variable_income_profile, var_income),
        ('subscription_heavy', generate_subscription_heavy_profile, sub_heavy),
        ('savings_builder', generate_savings_builder_profile, savings_builder),
        ('custom_persona', generate_custom_persona_profile, custom_persona),
        ('neutral', generate_neutral_profile, neutral),
    ]
    
    summary = {
        'users_created': 0,
        'errors': [],
        'by_persona': {}
    }
    
    user_num = 0
    for persona_type, generator_func, count in profile_generators:
        summary['by_persona'][persona_type] = 0
        for _ in range(count):
            user_num += 1
            try:
                if user_num % 10 == 0:
                    print(f"Generating user {user_num}/{total}...")
                
                # Generate profile
                profile = generator_func()
                profile['persona_type'] = persona_type
                
                # Generate user
                user_id = generate_user(profile, conn)
                
                # Generate accounts
                accounts_info = generate_accounts(user_id, profile, conn)
                
                # Generate credit card liability data
                for card_info in accounts_info['credit_cards']:
                    # Find matching card spec
                    card_spec = None
                    for card_spec_item in profile['credit_cards']:
                        if abs(card_spec_item['limit'] - card_info['limit']) < 0.01:
                            card_spec = card_spec_item
                            break
                    if not card_spec and profile['credit_cards']:
                        card_spec = profile['credit_cards'][0]
                    
                    if card_spec:
                        generate_credit_card(card_info['db_id'], card_spec, conn)
                
                # Generate liability data for mortgages
                for mortgage_info in accounts_info['mortgages']:
                    mortgage_spec = mortgage_info.get('spec', {})
                    generate_liability(mortgage_info['db_id'], 'mortgage', mortgage_spec, conn)
                
                # Generate liability data for student loans
                for loan_info in accounts_info['student_loans']:
                    loan_spec = loan_info.get('spec', {})
                    generate_liability(loan_info['db_id'], 'student', loan_spec, conn)
                
                # Generate transactions
                # Checking account transactions
                if accounts_info['checking']:
                    generate_transactions(
                        accounts_info['checking']['db_id'], 
                        'checking', 
                        profile, 
                        conn
                    )
                
                # Savings account transactions (if exists)
                if accounts_info.get('savings'):
                    generate_transactions(
                        accounts_info['savings']['db_id'],
                        'checking',  # Use same transaction pattern
                        profile,
                        conn
                    )
                
                # Credit card transactions
                for card_info in accounts_info['credit_cards']:
                    generate_transactions(
                        card_info['db_id'], 
                        'credit', 
                        profile, 
                        conn
                    )
                
                summary['users_created'] += 1
                summary['by_persona'][persona_type] += 1
                
            except Exception as e:
                error_msg = f"Error generating user {user_num} ({persona_type}): {str(e)}"
                print(f"  ✗ {error_msg}")
                summary['errors'].append(error_msg)
    
    return summary


if __name__ == "__main__":
    """Generate all synthetic data."""
    print("=" * 60)
    print("SpendSense - Synthetic Data Generation (Phase 4)")
    print("=" * 60)
    print()
    
    conn = get_db_connection()
    
    print(f"Generating {NUM_USERS} user profiles...")
    print()
    
    summary = generate_all_users(conn)
    
    print()
    print("=" * 60)
    print("Generation Summary:")
    print(f"  Users created: {summary['users_created']}/{NUM_USERS}")
    if summary.get('by_persona'):
        print("\n  Distribution by persona:")
        for persona, count in summary['by_persona'].items():
            print(f"    {persona}: {count}")
    if summary['errors']:
        print(f"\n  Errors: {len(summary['errors'])}")
        for error in summary['errors'][:10]:  # Show first 10 errors
            print(f"    - {error}")
        if len(summary['errors']) > 10:
            print(f"    ... and {len(summary['errors']) - 10} more errors")
    else:
        print("  ✓ All users generated successfully!")
    print("=" * 60)
    
    conn.close()

