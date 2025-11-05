"""
Data ingestion module for SpendSense.
Supports ingesting Plaid-compatible data from JSON or CSV files.
"""

import json
import csv
import sqlite3
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Any
from .database import get_db_connection, get_db_path


# ============================================================================
# Helper Functions
# ============================================================================

def get_nested_value(data: Dict, path: str, default: Any = None) -> Any:
    """
    Extract nested value from dictionary using dot notation.
    
    Args:
        data: Dictionary to extract from
        path: Dot-separated path (e.g., 'balances.available')
        default: Default value if path not found
        
    Returns:
        Extracted value or default
    """
    keys = path.split('.')
    value = data
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        elif isinstance(value, list) and len(value) > 0:
            # Handle array access like 'aprs[0].percentage'
            if '[' in key and ']' in key:
                array_key, index_str = key.split('[')
                index = int(index_str.rstrip(']'))
                if array_key in data:
                    value = data[array_key]
                    if isinstance(value, list) and 0 <= index < len(value):
                        value = value[index]
                    else:
                        return default
                else:
                    return default
            else:
                return default
        else:
            return default
    return value if value is not None else default


def parse_date(date_str: str) -> Optional[date]:
    """
    Parse date string in ISO format (YYYY-MM-DD).
    
    Args:
        date_str: Date string to parse
        
    Returns:
        date object or None if invalid
    """
    if not date_str or not isinstance(date_str, str):
        return None
    
    try:
        # Try ISO format first (YYYY-MM-DD)
        return datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
    except ValueError:
        # Try other common formats
        formats = ['%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d']
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None


# ============================================================================
# Validation Functions
# ============================================================================

def validate_user_data(user_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate user data.
    
    Args:
        user_data: User dictionary with fields
        
    Returns:
        (is_valid, [error_messages])
    """
    errors = []
    
    if not user_data.get('name'):
        errors.append("Missing required field: 'name'")
    
    if not user_data.get('email'):
        errors.append("Missing required field: 'email'")
    elif '@' not in str(user_data.get('email', '')):
        errors.append("Invalid email format")
    
    return (len(errors) == 0, errors)


def validate_account_data(account_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate account data.
    
    Args:
        account_data: Account dictionary with fields
        
    Returns:
        (is_valid, [error_messages])
    """
    errors = []
    
    if not account_data.get('account_id'):
        errors.append("Missing required field: 'account_id'")
    
    if 'user_id' not in account_data:
        errors.append("Missing required field: 'user_id'")
    
    if not account_data.get('type'):
        errors.append("Missing required field: 'type'")
    elif account_data['type'] not in ['depository', 'credit', 'liability']:
        errors.append(f"Invalid account type: {account_data['type']}. Must be 'depository', 'credit', or 'liability'")
    
    # Check current_balance (can be in balances.current or current_balance)
    current_balance = get_nested_value(account_data, 'balances.current') or account_data.get('current_balance')
    if current_balance is None:
        errors.append("Missing required field: 'current_balance' or 'balances.current'")
    else:
        try:
            float(current_balance)
        except (ValueError, TypeError):
            errors.append(f"Invalid current_balance: {current_balance}. Must be numeric")
    
    return (len(errors) == 0, errors)


def validate_transaction_data(tx_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate transaction data.
    
    Args:
        tx_data: Transaction dictionary with fields
        
    Returns:
        (is_valid, [error_messages])
    """
    errors = []
    
    if not tx_data.get('account_id'):
        errors.append("Missing required field: 'account_id'")
    
    if not tx_data.get('date'):
        errors.append("Missing required field: 'date'")
    else:
        parsed_date = parse_date(tx_data['date'])
        if parsed_date is None:
            errors.append(f"Invalid date format: {tx_data['date']}. Expected YYYY-MM-DD")
    
    if 'amount' not in tx_data or tx_data.get('amount') is None:
        errors.append("Missing required field: 'amount'")
    else:
        try:
            float(tx_data['amount'])
        except (ValueError, TypeError):
            errors.append(f"Invalid amount: {tx_data['amount']}. Must be numeric")
    
    return (len(errors) == 0, errors)


def validate_credit_card_data(cc_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate credit card data.
    
    Args:
        cc_data: Credit card dictionary with fields
        
    Returns:
        (is_valid, [error_messages])
    """
    errors = []
    
    if not cc_data.get('account_id'):
        errors.append("Missing required field: 'account_id'")
    
    # Validate APR if present
    apr = cc_data.get('apr') or get_nested_value(cc_data, 'aprs[0].percentage')
    if apr is not None:
        try:
            apr_float = float(apr)
            if apr_float < 0 or apr_float > 100:
                errors.append(f"Invalid APR: {apr_float}. Must be between 0 and 100")
        except (ValueError, TypeError):
            errors.append(f"Invalid APR: {apr}. Must be numeric")
    
    return (len(errors) == 0, errors)


def validate_liability_data(liability_data: Dict) -> Tuple[bool, List[str]]:
    """
    Validate liability data.
    
    Args:
        liability_data: Liability dictionary with fields
        
    Returns:
        (is_valid, [error_messages])
    """
    errors = []
    
    if not liability_data.get('account_id'):
        errors.append("Missing required field: 'account_id'")
    
    liability_type = liability_data.get('liability_type') or liability_data.get('type')
    if not liability_type:
        errors.append("Missing required field: 'liability_type' or 'type'")
    elif liability_type not in ['mortgage', 'student']:
        errors.append(f"Invalid liability_type: {liability_type}. Must be 'mortgage' or 'student'")
    
    return (len(errors) == 0, errors)


# ============================================================================
# Field Mapping Functions
# ============================================================================

def map_plaid_account_to_schema(plaid_account: Dict) -> Dict:
    """
    Map Plaid account format to our database schema.
    
    Args:
        plaid_account: Plaid account dictionary
        
    Returns:
        Mapped account dictionary for database insertion
    """
    # Extract nested values
    available_balance = get_nested_value(plaid_account, 'balances.available')
    current_balance = get_nested_value(plaid_account, 'balances.current') or plaid_account.get('current_balance')
    limit = get_nested_value(plaid_account, 'balances.limit') or plaid_account.get('limit')
    
    # Build mapped account
    mapped = {
        'account_id': plaid_account.get('account_id'),
        'user_id': plaid_account.get('user_id'),  # Will be resolved later
        'type': plaid_account.get('type'),
        'subtype': plaid_account.get('subtype'),
        'available_balance': float(available_balance) if available_balance is not None else None,
        'current_balance': float(current_balance) if current_balance is not None else 0.0,
        'limit': float(limit) if limit is not None else None,
        'iso_currency_code': plaid_account.get('iso_currency_code', 'USD'),
        'holder_category': plaid_account.get('holder_category', 'consumer')
    }
    
    return mapped


def map_plaid_transaction_to_schema(plaid_transaction: Dict) -> Dict:
    """
    Map Plaid transaction format to our database schema.
    
    Args:
        plaid_transaction: Plaid transaction dictionary
        
    Returns:
        Mapped transaction dictionary for database insertion
    """
    # Extract nested category
    category = get_nested_value(plaid_transaction, 'personal_finance_category.primary') or \
               plaid_transaction.get('personal_finance_category')
    
    # Parse date
    tx_date = parse_date(plaid_transaction.get('date', ''))
    if tx_date is None and plaid_transaction.get('date'):
        # Fallback: try to use as-is if parsing failed (will be caught by validation)
        tx_date = plaid_transaction.get('date')
    
    mapped = {
        'account_id': plaid_transaction.get('account_id'),  # Will be resolved to DB ID
        'date': tx_date,
        'amount': float(plaid_transaction.get('amount', 0)),
        'merchant_name': plaid_transaction.get('merchant_name'),
        'merchant_entity_id': plaid_transaction.get('merchant_entity_id'),
        'payment_channel': plaid_transaction.get('payment_channel', 'other'),
        'personal_finance_category': category,
        'pending': bool(plaid_transaction.get('pending', False))
    }
    
    return mapped


def map_plaid_credit_card_to_schema(plaid_cc: Dict) -> Dict:
    """
    Map Plaid credit card format to our database schema.
    
    Args:
        plaid_cc: Plaid credit card dictionary
        
    Returns:
        Mapped credit card dictionary for database insertion
    """
    # Handle APR (can be direct or nested in array)
    apr = plaid_cc.get('apr')
    if apr is None:
        apr = get_nested_value(plaid_cc, 'aprs[0].percentage')
    
    # Parse date
    next_due_date = None
    if plaid_cc.get('next_payment_due_date'):
        next_due_date = parse_date(plaid_cc['next_payment_due_date'])
    
    mapped = {
        'account_id': plaid_cc.get('account_id'),  # Will be resolved to DB ID
        'apr': float(apr) if apr is not None else None,
        'minimum_payment_amount': float(plaid_cc['minimum_payment_amount']) if plaid_cc.get('minimum_payment_amount') is not None else None,
        'last_payment_amount': float(plaid_cc['last_payment_amount']) if plaid_cc.get('last_payment_amount') is not None else None,
        'is_overdue': bool(plaid_cc.get('is_overdue', False)),
        'next_payment_due_date': next_due_date,
        'last_statement_balance': float(plaid_cc['last_statement_balance']) if plaid_cc.get('last_statement_balance') is not None else None
    }
    
    return mapped


def map_plaid_liability_to_schema(plaid_liability: Dict) -> Dict:
    """
    Map Plaid liability format to our database schema.
    
    Args:
        plaid_liability: Plaid liability dictionary
        
    Returns:
        Mapped liability dictionary for database insertion
    """
    # Parse date
    next_due_date = None
    if plaid_liability.get('next_payment_due_date'):
        next_due_date = parse_date(plaid_liability['next_payment_due_date'])
    
    liability_type = plaid_liability.get('liability_type') or plaid_liability.get('type')
    
    mapped = {
        'account_id': plaid_liability.get('account_id'),  # Will be resolved to DB ID
        'liability_type': liability_type,
        'interest_rate': float(plaid_liability['interest_rate']) if plaid_liability.get('interest_rate') is not None else None,
        'next_payment_due_date': next_due_date,
        'last_payment_amount': float(plaid_liability['last_payment_amount']) if plaid_liability.get('last_payment_amount') is not None else None
    }
    
    return mapped


# ============================================================================
# Account ID Resolution
# ============================================================================

def resolve_account_id(plaid_account_id: str, account_map: Dict[str, int]) -> Optional[int]:
    """
    Resolve Plaid account_id to database account ID.
    
    Args:
        plaid_account_id: Plaid account ID string
        account_map: Mapping dictionary {plaid_account_id: db_account_id}
        
    Returns:
        Database account ID or None if not found
    """
    return account_map.get(plaid_account_id)


# ============================================================================
# JSON Ingestion
# ============================================================================

def ingest_json(file_path: str, conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Ingest data from JSON file with nested structure.
    
    Args:
        file_path: Path to JSON file
        conn: Database connection (creates new if None)
        
    Returns:
        Summary dictionary with counts and errors
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    summary = {
        'success': True,
        'users_created': 0,
        'accounts_created': 0,
        'transactions_created': 0,
        'credit_cards_created': 0,
        'liabilities_created': 0,
        'errors': [],
        'warnings': []
    }
    
    try:
        # Load JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        if 'users' not in data:
            summary['success'] = False
            summary['errors'].append({
                'type': 'structure',
                'message': 'JSON file must have "users" array at root level'
            })
            return summary
        
        users = data['users']
        if not isinstance(users, list):
            summary['success'] = False
            summary['errors'].append({
                'type': 'structure',
                'message': '"users" must be an array'
            })
            return summary
        
        cursor = conn.cursor()
        
        # Process each user
        for user_idx, user_data in enumerate(users):
            user_errors = []
            
            try:
                # Validate user data
                is_valid, validation_errors = validate_user_data(user_data)
                if not is_valid:
                    user_errors.extend([{'type': 'validation', 'message': e} for e in validation_errors])
                    summary['errors'].append({
                        'type': 'user',
                        'index': user_idx,
                        'user_id': user_data.get('user_id', 'unknown'),
                        'errors': user_errors
                    })
                    continue
                
                # Start transaction for this user
                conn.execute('BEGIN TRANSACTION')
                
                try:
                    # Insert user
                    name = user_data.get('name')
                    email = user_data.get('email')
                    consent_given = bool(user_data.get('consent_given', False))
                    
                    # Check for duplicate email
                    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                    existing = cursor.fetchone()
                    if existing:
                        summary['warnings'].append(f"User with email {email} already exists, skipping")
                        conn.execute('ROLLBACK')
                        continue
                    
                    cursor.execute("""
                        INSERT INTO users (name, email, consent_given)
                        VALUES (?, ?, ?)
                    """, (name, email, consent_given))
                    
                    user_id = cursor.lastrowid
                    summary['users_created'] += 1
                    
                    # Build account map for this user
                    account_map = {}
                    
                    # Process accounts
                    accounts = user_data.get('accounts', [])
                    for account_data in accounts:
                        # Add user_id to account_data for validation
                        account_data['user_id'] = user_id
                        
                        # Validate account data
                        is_valid, validation_errors = validate_account_data(account_data)
                        if not is_valid:
                            user_errors.extend([{'type': 'validation', 'message': e} for e in validation_errors])
                            continue
                        
                        # Map Plaid → schema
                        mapped_account = map_plaid_account_to_schema(account_data)
                        mapped_account['user_id'] = user_id
                        plaid_account_id = mapped_account['account_id']
                        
                        # Check for duplicate account_id
                        cursor.execute("SELECT id FROM accounts WHERE account_id = ?", (plaid_account_id,))
                        existing = cursor.fetchone()
                        if existing:
                            summary['warnings'].append(f"Account {plaid_account_id} already exists, skipping")
                            account_map[plaid_account_id] = existing[0]
                            continue
                        
                        # Insert account
                        cursor.execute("""
                            INSERT INTO accounts (
                                user_id, account_id, type, subtype, available_balance,
                                current_balance, "limit", iso_currency_code, holder_category
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            mapped_account['user_id'],
                            mapped_account['account_id'],
                            mapped_account['type'],
                            mapped_account['subtype'],
                            mapped_account['available_balance'],
                            mapped_account['current_balance'],
                            mapped_account['limit'],
                            mapped_account['iso_currency_code'],
                            mapped_account['holder_category']
                        ))
                        
                        db_account_id = cursor.lastrowid
                        account_map[plaid_account_id] = db_account_id
                        summary['accounts_created'] += 1
                        
                        # Process transactions for this account
                        transactions = account_data.get('transactions', [])
                        for tx_data in transactions:
                            # Validate transaction
                            is_valid, validation_errors = validate_transaction_data(tx_data)
                            if not is_valid:
                                user_errors.extend([{'type': 'validation', 'message': e} for e in validation_errors])
                                continue
                            
                            # Map Plaid → schema
                            mapped_tx = map_plaid_transaction_to_schema(tx_data)
                            db_account_id_for_tx = resolve_account_id(tx_data['account_id'], account_map)
                            
                            if db_account_id_for_tx is None:
                                user_errors.append({
                                    'type': 'foreign_key',
                                    'message': f"Account {tx_data['account_id']} not found for transaction"
                                })
                                continue
                            
                            mapped_tx['account_id'] = db_account_id_for_tx
                            
                            # Insert transaction
                            cursor.execute("""
                                INSERT INTO transactions (
                                    account_id, date, amount, merchant_name, merchant_entity_id,
                                    payment_channel, personal_finance_category, pending
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """, (
                                mapped_tx['account_id'],
                                mapped_tx['date'],
                                mapped_tx['amount'],
                                mapped_tx['merchant_name'],
                                mapped_tx['merchant_entity_id'],
                                mapped_tx['payment_channel'],
                                mapped_tx['personal_finance_category'],
                                mapped_tx['pending']
                            ))
                            summary['transactions_created'] += 1
                        
                        # Process credit card data for this account
                        credit_card_data = account_data.get('credit_card')
                        if credit_card_data:
                            credit_card_data['account_id'] = plaid_account_id
                            is_valid, validation_errors = validate_credit_card_data(credit_card_data)
                            if not is_valid:
                                user_errors.extend([{'type': 'validation', 'message': e} for e in validation_errors])
                            else:
                                mapped_cc = map_plaid_credit_card_to_schema(credit_card_data)
                                db_account_id_for_cc = resolve_account_id(credit_card_data['account_id'], account_map)
                                
                                if db_account_id_for_cc is None:
                                    user_errors.append({
                                        'type': 'foreign_key',
                                        'message': f"Account {credit_card_data['account_id']} not found for credit card"
                                    })
                                else:
                                    mapped_cc['account_id'] = db_account_id_for_cc
                                    
                                    # Insert credit card
                                    cursor.execute("""
                                        INSERT INTO credit_cards (
                                            account_id, apr, minimum_payment_amount, last_payment_amount,
                                            is_overdue, next_payment_due_date, last_statement_balance
                                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                                    """, (
                                        mapped_cc['account_id'],
                                        mapped_cc['apr'],
                                        mapped_cc['minimum_payment_amount'],
                                        mapped_cc['last_payment_amount'],
                                        mapped_cc['is_overdue'],
                                        mapped_cc['next_payment_due_date'],
                                        mapped_cc['last_statement_balance']
                                    ))
                                    summary['credit_cards_created'] += 1
                        
                        # Process liability data for this account
                        liability_data = account_data.get('liability')
                        if liability_data:
                            liability_data['account_id'] = plaid_account_id
                            # Infer liability_type from account subtype if not provided
                            if 'liability_type' not in liability_data and 'type' not in liability_data:
                                if account_data.get('subtype') == 'mortgage':
                                    liability_data['liability_type'] = 'mortgage'
                                elif account_data.get('subtype') == 'student':
                                    liability_data['liability_type'] = 'student'
                            
                            is_valid, validation_errors = validate_liability_data(liability_data)
                            if not is_valid:
                                user_errors.extend([{'type': 'validation', 'message': e} for e in validation_errors])
                            else:
                                mapped_liability = map_plaid_liability_to_schema(liability_data)
                                db_account_id_for_liability = resolve_account_id(liability_data['account_id'], account_map)
                                
                                if db_account_id_for_liability is None:
                                    user_errors.append({
                                        'type': 'foreign_key',
                                        'message': f"Account {liability_data['account_id']} not found for liability"
                                    })
                                else:
                                    mapped_liability['account_id'] = db_account_id_for_liability
                                    
                                    # Insert liability
                                    cursor.execute("""
                                        INSERT INTO liabilities (
                                            account_id, liability_type, interest_rate,
                                            next_payment_due_date, last_payment_amount
                                        ) VALUES (?, ?, ?, ?, ?)
                                    """, (
                                        mapped_liability['account_id'],
                                        mapped_liability['liability_type'],
                                        mapped_liability['interest_rate'],
                                        mapped_liability['next_payment_due_date'],
                                        mapped_liability['last_payment_amount']
                                    ))
                                    summary['liabilities_created'] += 1
                    
                    # Commit transaction for this user
                    conn.commit()
                    
                    if user_errors:
                        summary['warnings'].append(f"User {user_id} ingested with {len(user_errors)} warnings")
                
                except Exception as e:
                    conn.rollback()
                    summary['errors'].append({
                        'type': 'insertion',
                        'user_index': user_idx,
                        'user_id': user_data.get('user_id', 'unknown'),
                        'message': str(e)
                    })
                    summary['success'] = False
            
            except Exception as e:
                summary['errors'].append({
                    'type': 'processing',
                    'user_index': user_idx,
                    'message': str(e)
                })
                summary['success'] = False
        
        return summary
    
    except FileNotFoundError:
        summary['success'] = False
        summary['errors'].append({
            'type': 'file',
            'message': f'File not found: {file_path}'
        })
        return summary
    except json.JSONDecodeError as e:
        summary['success'] = False
        summary['errors'].append({
            'type': 'json',
            'message': f'Invalid JSON: {str(e)}'
        })
        return summary
    finally:
        if close_conn:
            conn.close()


# ============================================================================
# CSV Ingestion
# ============================================================================

def ingest_csv(users_file: str, accounts_file: str, 
               transactions_file: Optional[str] = None,
               credit_cards_file: Optional[str] = None,
               liabilities_file: Optional[str] = None,
               conn: Optional[sqlite3.Connection] = None) -> Dict:
    """
    Ingest data from CSV files.
    
    Args:
        users_file: Path to users.csv
        accounts_file: Path to accounts.csv
        transactions_file: Optional path to transactions.csv
        credit_cards_file: Optional path to credit_cards.csv
        liabilities_file: Optional path to liabilities.csv
        conn: Database connection (creates new if None)
        
    Returns:
        Summary dictionary with counts and errors
    """
    if conn is None:
        conn = get_db_connection()
        close_conn = True
    else:
        close_conn = False
    
    summary = {
        'success': True,
        'users_created': 0,
        'accounts_created': 0,
        'transactions_created': 0,
        'credit_cards_created': 0,
        'liabilities_created': 0,
        'errors': [],
        'warnings': []
    }
    
    cursor = conn.cursor()
    
    try:
        # Step 1: Load and insert users
        user_map = {}  # {plaid_user_id: db_user_id}
        
        try:
            with open(users_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                conn.execute('BEGIN TRANSACTION')
                
                for row_idx, row in enumerate(reader):
                    is_valid, validation_errors = validate_user_data(row)
                    if not is_valid:
                        summary['errors'].append({
                            'type': 'validation',
                            'file': 'users.csv',
                            'row': row_idx + 1,
                            'errors': validation_errors
                        })
                        continue
                    
                    email = row.get('email')
                    # Check for duplicate
                    cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
                    existing = cursor.fetchone()
                    if existing:
                        summary['warnings'].append(f"User with email {email} already exists, skipping")
                        plaid_user_id = row.get('user_id') or row.get('id')
                        if plaid_user_id:
                            user_map[plaid_user_id] = existing[0]
                        continue
                    
                    name = row.get('name')
                    consent_given = bool(row.get('consent_given', False))
                    
                    cursor.execute("""
                        INSERT INTO users (name, email, consent_given)
                        VALUES (?, ?, ?)
                    """, (name, email, consent_given))
                    
                    db_user_id = cursor.lastrowid
                    plaid_user_id = row.get('user_id') or row.get('id')
                    if plaid_user_id:
                        user_map[plaid_user_id] = db_user_id
                    summary['users_created'] += 1
                
                conn.commit()
        
        except FileNotFoundError:
            summary['success'] = False
            summary['errors'].append({
                'type': 'file',
                'message': f'File not found: {users_file}'
            })
            return summary
        except Exception as e:
            conn.rollback()
            summary['success'] = False
            summary['errors'].append({
                'type': 'processing',
                'file': 'users.csv',
                'message': str(e)
            })
            return summary
        
        # Step 2: Load and insert accounts
        account_map = {}  # {plaid_account_id: db_account_id}
        
        try:
            with open(accounts_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                conn.execute('BEGIN TRANSACTION')
                
                for row_idx, row in enumerate(reader):
                    # Resolve user_id
                    plaid_user_id = row.get('user_id')
                    if not plaid_user_id:
                        summary['errors'].append({
                            'type': 'validation',
                            'file': 'accounts.csv',
                            'row': row_idx + 1,
                            'errors': ['Missing user_id']
                        })
                        continue
                    
                    db_user_id = user_map.get(plaid_user_id)
                    if db_user_id is None:
                        summary['errors'].append({
                            'type': 'foreign_key',
                            'file': 'accounts.csv',
                            'row': row_idx + 1,
                            'message': f'User {plaid_user_id} not found'
                        })
                        continue
                    
                    row['user_id'] = db_user_id  # Add resolved user_id
                    
                    # Validate account data
                    is_valid, validation_errors = validate_account_data(row)
                    if not is_valid:
                        summary['errors'].append({
                            'type': 'validation',
                            'file': 'accounts.csv',
                            'row': row_idx + 1,
                            'errors': validation_errors
                        })
                        continue
                    
                    # Map to schema (handle both flat and nested formats)
                    mapped_account = map_plaid_account_to_schema(row)
                    plaid_account_id = mapped_account['account_id']
                    
                    # Check for duplicate
                    cursor.execute("SELECT id FROM accounts WHERE account_id = ?", (plaid_account_id,))
                    existing = cursor.fetchone()
                    if existing:
                        summary['warnings'].append(f"Account {plaid_account_id} already exists, skipping")
                        account_map[plaid_account_id] = existing[0]
                        continue
                    
                    # Insert account
                    cursor.execute("""
                        INSERT INTO accounts (
                            user_id, account_id, type, subtype, available_balance,
                            current_balance, "limit", iso_currency_code, holder_category
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        mapped_account['user_id'],
                        mapped_account['account_id'],
                        mapped_account['type'],
                        mapped_account['subtype'],
                        mapped_account['available_balance'],
                        mapped_account['current_balance'],
                        mapped_account['limit'],
                        mapped_account['iso_currency_code'],
                        mapped_account['holder_category']
                    ))
                    
                    db_account_id = cursor.lastrowid
                    account_map[plaid_account_id] = db_account_id
                    summary['accounts_created'] += 1
                
                conn.commit()
        
        except FileNotFoundError:
            summary['success'] = False
            summary['errors'].append({
                'type': 'file',
                'message': f'File not found: {accounts_file}'
            })
            return summary
        except Exception as e:
            conn.rollback()
            summary['success'] = False
            summary['errors'].append({
                'type': 'processing',
                'file': 'accounts.csv',
                'message': str(e)
            })
            return summary
        
        # Step 3: Load and insert transactions (if provided)
        if transactions_file:
            try:
                with open(transactions_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    conn.execute('BEGIN TRANSACTION')
                    
                    for row_idx, row in enumerate(reader):
                        is_valid, validation_errors = validate_transaction_data(row)
                        if not is_valid:
                            summary['errors'].append({
                                'type': 'validation',
                                'file': 'transactions.csv',
                                'row': row_idx + 1,
                                'errors': validation_errors
                            })
                            continue
                        
                        plaid_account_id = row.get('account_id')
                        db_account_id = resolve_account_id(plaid_account_id, account_map)
                        
                        if db_account_id is None:
                            summary['errors'].append({
                                'type': 'foreign_key',
                                'file': 'transactions.csv',
                                'row': row_idx + 1,
                                'message': f'Account {plaid_account_id} not found'
                            })
                            continue
                        
                        # Map to schema
                        mapped_tx = map_plaid_transaction_to_schema(row)
                        mapped_tx['account_id'] = db_account_id
                        
                        # Insert transaction
                        cursor.execute("""
                            INSERT INTO transactions (
                                account_id, date, amount, merchant_name, merchant_entity_id,
                                payment_channel, personal_finance_category, pending
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            mapped_tx['account_id'],
                            mapped_tx['date'],
                            mapped_tx['amount'],
                            mapped_tx['merchant_name'],
                            mapped_tx['merchant_entity_id'],
                            mapped_tx['payment_channel'],
                            mapped_tx['personal_finance_category'],
                            mapped_tx['pending']
                        ))
                        summary['transactions_created'] += 1
                    
                    conn.commit()
            
            except FileNotFoundError:
                summary['warnings'].append(f'Transactions file not found: {transactions_file}')
            except Exception as e:
                conn.rollback()
                summary['errors'].append({
                    'type': 'processing',
                    'file': 'transactions.csv',
                    'message': str(e)
                })
        
        # Step 4: Load and insert credit cards (if provided)
        if credit_cards_file:
            try:
                with open(credit_cards_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    conn.execute('BEGIN TRANSACTION')
                    
                    for row_idx, row in enumerate(reader):
                        is_valid, validation_errors = validate_credit_card_data(row)
                        if not is_valid:
                            summary['errors'].append({
                                'type': 'validation',
                                'file': 'credit_cards.csv',
                                'row': row_idx + 1,
                                'errors': validation_errors
                            })
                            continue
                        
                        plaid_account_id = row.get('account_id')
                        db_account_id = resolve_account_id(plaid_account_id, account_map)
                        
                        if db_account_id is None:
                            summary['errors'].append({
                                'type': 'foreign_key',
                                'file': 'credit_cards.csv',
                                'row': row_idx + 1,
                                'message': f'Account {plaid_account_id} not found'
                            })
                            continue
                        
                        # Map to schema
                        mapped_cc = map_plaid_credit_card_to_schema(row)
                        mapped_cc['account_id'] = db_account_id
                        
                        # Insert credit card
                        cursor.execute("""
                            INSERT INTO credit_cards (
                                account_id, apr, minimum_payment_amount, last_payment_amount,
                                is_overdue, next_payment_due_date, last_statement_balance
                            ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            mapped_cc['account_id'],
                            mapped_cc['apr'],
                            mapped_cc['minimum_payment_amount'],
                            mapped_cc['last_payment_amount'],
                            mapped_cc['is_overdue'],
                            mapped_cc['next_payment_due_date'],
                            mapped_cc['last_statement_balance']
                        ))
                        summary['credit_cards_created'] += 1
                    
                    conn.commit()
            
            except FileNotFoundError:
                summary['warnings'].append(f'Credit cards file not found: {credit_cards_file}')
            except Exception as e:
                conn.rollback()
                summary['errors'].append({
                    'type': 'processing',
                    'file': 'credit_cards.csv',
                    'message': str(e)
                })
        
        # Step 5: Load and insert liabilities (if provided)
        if liabilities_file:
            try:
                with open(liabilities_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    conn.execute('BEGIN TRANSACTION')
                    
                    for row_idx, row in enumerate(reader):
                        is_valid, validation_errors = validate_liability_data(row)
                        if not is_valid:
                            summary['errors'].append({
                                'type': 'validation',
                                'file': 'liabilities.csv',
                                'row': row_idx + 1,
                                'errors': validation_errors
                            })
                            continue
                        
                        plaid_account_id = row.get('account_id')
                        db_account_id = resolve_account_id(plaid_account_id, account_map)
                        
                        if db_account_id is None:
                            summary['errors'].append({
                                'type': 'foreign_key',
                                'file': 'liabilities.csv',
                                'row': row_idx + 1,
                                'message': f'Account {plaid_account_id} not found'
                            })
                            continue
                        
                        # Map to schema
                        mapped_liability = map_plaid_liability_to_schema(row)
                        mapped_liability['account_id'] = db_account_id
                        
                        # Insert liability
                        cursor.execute("""
                            INSERT INTO liabilities (
                                account_id, liability_type, interest_rate,
                                next_payment_due_date, last_payment_amount
                            ) VALUES (?, ?, ?, ?, ?)
                        """, (
                            mapped_liability['account_id'],
                            mapped_liability['liability_type'],
                            mapped_liability['interest_rate'],
                            mapped_liability['next_payment_due_date'],
                            mapped_liability['last_payment_amount']
                        ))
                        summary['liabilities_created'] += 1
                    
                    conn.commit()
            
            except FileNotFoundError:
                summary['warnings'].append(f'Liabilities file not found: {liabilities_file}')
            except Exception as e:
                conn.rollback()
                summary['errors'].append({
                    'type': 'processing',
                    'file': 'liabilities.csv',
                    'message': str(e)
                })
        
        return summary
    
    finally:
        if close_conn:
            conn.close()


# ============================================================================
# Command-Line Interface
# ============================================================================

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(
        description='Ingest Plaid-compatible data from JSON or CSV files'
    )
    parser.add_argument(
        '--format',
        required=True,
        choices=['json', 'csv'],
        help='Input format: json or csv'
    )
    parser.add_argument(
        '--file',
        help='Path to JSON file (required for JSON format)'
    )
    parser.add_argument(
        '--users',
        help='Path to users.csv (required for CSV format)'
    )
    parser.add_argument(
        '--accounts',
        help='Path to accounts.csv (required for CSV format)'
    )
    parser.add_argument(
        '--transactions',
        help='Path to transactions.csv (optional for CSV format)'
    )
    parser.add_argument(
        '--credit-cards',
        dest='credit_cards',
        help='Path to credit_cards.csv (optional for CSV format)'
    )
    parser.add_argument(
        '--liabilities',
        help='Path to liabilities.csv (optional for CSV format)'
    )
    parser.add_argument(
        '--db-path',
        help='Path to database file (defaults to spendsense.db)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.format == 'json':
        if not args.file:
            print("Error: --file is required for JSON format", file=sys.stderr)
            sys.exit(1)
    elif args.format == 'csv':
        if not args.users or not args.accounts:
            print("Error: --users and --accounts are required for CSV format", file=sys.stderr)
            sys.exit(1)
    
    # Get database connection
    if args.db_path:
        import os
        os.environ['DB_PATH'] = args.db_path
    
    conn = get_db_connection()
    
    print("=" * 60)
    print("SpendSense - Data Ingestion")
    print("=" * 60)
    print()
    
    # Run ingestion
    if args.format == 'json':
        print(f"Ingesting JSON file: {args.file}")
        summary = ingest_json(args.file, conn)
    else:
        print(f"Ingesting CSV files:")
        print(f"  Users: {args.users}")
        print(f"  Accounts: {args.accounts}")
        if args.transactions:
            print(f"  Transactions: {args.transactions}")
        if args.credit_cards:
            print(f"  Credit Cards: {args.credit_cards}")
        if args.liabilities:
            print(f"  Liabilities: {args.liabilities}")
        summary = ingest_csv(
            args.users,
            args.accounts,
            args.transactions,
            args.credit_cards,
            args.liabilities,
            conn
        )
    
    print()
    print("=" * 60)
    print("Ingestion Summary:")
    print("=" * 60)
    print(f"  Success: {summary['success']}")
    print(f"  Users created: {summary['users_created']}")
    print(f"  Accounts created: {summary['accounts_created']}")
    print(f"  Transactions created: {summary['transactions_created']}")
    print(f"  Credit cards created: {summary['credit_cards_created']}")
    print(f"  Liabilities created: {summary['liabilities_created']}")
    
    if summary['warnings']:
        print()
        print(f"  Warnings ({len(summary['warnings'])}):")
        for warning in summary['warnings'][:10]:  # Show first 10
            print(f"    - {warning}")
        if len(summary['warnings']) > 10:
            print(f"    ... and {len(summary['warnings']) - 10} more warnings")
    
    if summary['errors']:
        print()
        print(f"  Errors ({len(summary['errors'])}):")
        for error in summary['errors'][:10]:  # Show first 10
            if isinstance(error, dict):
                msg = error.get('message', str(error))
                print(f"    - {msg}")
            else:
                print(f"    - {error}")
        if len(summary['errors']) > 10:
            print(f"    ... and {len(summary['errors']) - 10} more errors")
    
    print("=" * 60)
    
    conn.close()
    
    # Exit with error code if ingestion failed
    if not summary['success'] or summary['errors']:
        sys.exit(1)

