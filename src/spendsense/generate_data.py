"""
Synthetic data generation for SpendSense MVP.
Generates 5 diverse user profiles with realistic financial data.
"""

import sqlite3
import random
import json
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


def days_ago(n: int) -> date:
    """Get date n days ago from today."""
    return TODAY - timedelta(days=n)


def generate_user(user_profile: dict, conn: sqlite3.Connection) -> int:
    """
    Generate a single user with synthetic name and email.
    
    Args:
        user_profile: Dictionary with user profile information
        conn: Database connection
        
    Returns:
        User ID of created user
    """
    cursor = conn.cursor()
    
    name = fake.name()
    email = fake.unique.email()
    
    cursor.execute("""
        INSERT INTO users (name, email, consent_given)
        VALUES (?, ?, ?)
    """, (name, email, False))
    
    user_id = cursor.lastrowid
    conn.commit()
    
    return user_id


def generate_accounts(user_id: int, profile: dict, conn: sqlite3.Connection) -> dict:
    """
    Generate accounts (checking and credit cards) for a user.
    
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
        'credit_cards': []
    }
    
    # Generate checking account for all users
    checking_account_id = f"acc_{random.randint(1000, 9999)}"
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
    
    # Generate credit cards based on profile
    credit_cards = profile.get('credit_cards', [])
    for card_spec in credit_cards:
        card_account_id = f"acc_{random.randint(1000, 9999)}"
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


def generate_all_users(conn: sqlite3.Connection) -> dict:
    """
    Generate all 5 user profiles with complete data.
    
    Args:
        conn: Database connection
        
    Returns:
        Summary dictionary with generation results
    """
    # Define user profiles
    profiles = [
        {
            'name': 'User 1: High Utilization - Single Card',
            'checking_balance': 2500.0,
            'credit_cards': [
                {
                    'limit': 5000.0,
                    'balance': 3750.0,  # 75% utilization
                    'apr': 22.0,
                    'is_overdue': False
                }
            ],
            'subscriptions': []
        },
        {
            'name': 'User 2: High Utilization - Multiple Cards',
            'checking_balance': 1800.0,
            'credit_cards': [
                {
                    'limit': 3000.0,
                    'balance': 2100.0,  # 70% utilization
                    'apr': 20.0,
                    'is_overdue': False
                },
                {
                    'limit': 8000.0,
                    'balance': 6500.0,  # 81% utilization
                    'apr': 24.0,
                    'is_overdue': True  # Overdue
                }
            ],
            'subscriptions': []
        },
        {
            'name': 'User 3: Subscription-Heavy - Major Services',
            'checking_balance': 3200.0,
            'credit_cards': [
                {
                    'limit': 10000.0,
                    'balance': 1200.0,  # 12% utilization (low)
                    'apr': 18.0,
                    'is_overdue': False
                }
            ],
            'subscriptions': [
                {'merchant': 'Netflix', 'amount': 15.99},
                {'merchant': 'Spotify', 'amount': 9.99},
                {'merchant': 'Gym Membership', 'amount': 49.99},
                {'merchant': 'Amazon Prime', 'amount': 14.99}
            ]
        },
        {
            'name': 'User 4: Subscription-Heavy - Many Small Services',
            'checking_balance': 2800.0,
            'credit_cards': [
                {
                    'limit': 8000.0,
                    'balance': 1500.0,  # 18.75% utilization (low)
                    'apr': 19.0,
                    'is_overdue': False
                }
            ],
            'subscriptions': [
                {'merchant': 'Hulu', 'amount': 7.99},
                {'merchant': 'Disney+', 'amount': 10.99},
                {'merchant': 'Adobe Creative Cloud', 'amount': 22.99},
                {'merchant': 'Microsoft 365', 'amount': 6.99},
                {'merchant': 'Dropbox', 'amount': 9.99},
                {'merchant': 'Apple iCloud', 'amount': 2.99}
            ]
        },
        {
            'name': 'User 5: Neutral/Healthy',
            'checking_balance': 4500.0,
            'credit_cards': [
                {
                    'limit': 10000.0,
                    'balance': 1500.0,  # 15% utilization (healthy)
                    'apr': 16.0,
                    'is_overdue': False
                }
            ],
            'subscriptions': [
                {'merchant': 'Netflix', 'amount': 15.99}  # Just one subscription
            ]
        }
    ]
    
    summary = {
        'users_created': 0,
        'errors': []
    }
    
    for i, profile in enumerate(profiles, 1):
        try:
            print(f"Generating {profile['name']}...")
            
            # Generate user
            user_id = generate_user(profile, conn)
            
            # Generate accounts
            accounts_info = generate_accounts(user_id, profile, conn)
            
            # Generate credit card liability data
            for card_info in accounts_info['credit_cards']:
                card_spec = next(
                    (c for c in profile['credit_cards'] 
                     if c['limit'] == card_info['limit']), 
                    None
                )
                if card_spec:
                    generate_credit_card(card_info['db_id'], card_spec, conn)
            
            # Generate transactions
            # Checking account transactions
            generate_transactions(
                accounts_info['checking']['db_id'], 
                'checking', 
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
            print(f"  ✓ User {i} created successfully")
            
        except Exception as e:
            error_msg = f"Error generating user {i}: {str(e)}"
            print(f"  ✗ {error_msg}")
            summary['errors'].append(error_msg)
    
    return summary


if __name__ == "__main__":
    """Generate all synthetic data."""
    print("=" * 60)
    print("SpendSense - Synthetic Data Generation")
    print("=" * 60)
    print()
    
    conn = get_db_connection()
    
    print("Generating 5 user profiles...")
    print()
    
    summary = generate_all_users(conn)
    
    print()
    print("=" * 60)
    print("Generation Summary:")
    print(f"  Users created: {summary['users_created']}/5")
    if summary['errors']:
        print(f"  Errors: {len(summary['errors'])}")
        for error in summary['errors']:
            print(f"    - {error}")
    else:
        print("  ✓ All users generated successfully!")
    print("=" * 60)
    
    conn.close()

