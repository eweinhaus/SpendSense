"""
Tests for data ingestion module (CSV/JSON ingestion).
"""

import pytest
import os
import json
import sqlite3
from datetime import date
from spendsense.data_ingest import (
    get_nested_value,
    parse_date,
    validate_user_data,
    validate_account_data,
    validate_transaction_data,
    validate_credit_card_data,
    validate_liability_data,
    map_plaid_account_to_schema,
    map_plaid_transaction_to_schema,
    map_plaid_credit_card_to_schema,
    map_plaid_liability_to_schema,
    resolve_account_id,
    ingest_json,
    ingest_csv
)
from spendsense.database import init_database, get_db_connection


@pytest.fixture
def test_db():
    """Create a test database for ingestion tests."""
    test_db_path = "test_ingest.db"
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    init_database(test_db_path)
    conn = get_db_connection(test_db_path)
    
    yield test_db_path, conn
    
    conn.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


# ============================================================================
# Helper Function Tests
# ============================================================================

def test_get_nested_value():
    """Test nested value extraction."""
    data = {
        'balances': {
            'available': 1000.0,
            'current': 2000.0
        },
        'category': {
            'primary': 'FOOD',
            'detailed': 'RESTAURANTS'
        }
    }
    
    assert get_nested_value(data, 'balances.available') == 1000.0
    assert get_nested_value(data, 'balances.current') == 2000.0
    assert get_nested_value(data, 'category.primary') == 'FOOD'
    assert get_nested_value(data, 'balances.nonexistent', default=0) == 0
    assert get_nested_value(data, 'nonexistent.path', default=None) is None


def test_get_nested_value_array():
    """Test nested value extraction with arrays."""
    data = {
        'aprs': [
            {'percentage': 22.0},
            {'percentage': 18.0}
        ]
    }
    
    # Note: Array access not fully implemented in get_nested_value
    # This test verifies current behavior
    assert get_nested_value(data, 'aprs') == [{'percentage': 22.0}, {'percentage': 18.0}]


def test_parse_date():
    """Test date parsing."""
    # ISO format
    assert parse_date('2024-01-15') == date(2024, 1, 15)
    assert parse_date('2024-12-31') == date(2024, 12, 31)
    
    # Invalid formats
    assert parse_date('invalid') is None
    assert parse_date('') is None
    assert parse_date(None) is None
    
    # Other formats (if implemented)
    assert parse_date('01/15/2024') == date(2024, 1, 15) or parse_date('01/15/2024') is None


# ============================================================================
# Validation Tests
# ============================================================================

def test_validate_user_data():
    """Test user data validation."""
    # Valid user
    valid_user = {'name': 'John Doe', 'email': 'john@example.com'}
    is_valid, errors = validate_user_data(valid_user)
    assert is_valid
    assert len(errors) == 0
    
    # Missing name
    invalid_user = {'email': 'john@example.com'}
    is_valid, errors = validate_user_data(invalid_user)
    assert not is_valid
    assert 'name' in str(errors[0])
    
    # Missing email
    invalid_user = {'name': 'John Doe'}
    is_valid, errors = validate_user_data(invalid_user)
    assert not is_valid
    assert 'email' in str(errors[0])
    
    # Invalid email
    invalid_user = {'name': 'John Doe', 'email': 'not-an-email'}
    is_valid, errors = validate_user_data(invalid_user)
    assert not is_valid
    assert 'email' in str(errors[0])


def test_validate_account_data():
    """Test account data validation."""
    # Valid account
    valid_account = {
        'account_id': 'acc_001',
        'user_id': 1,
        'type': 'depository',
        'current_balance': 1000.0
    }
    is_valid, errors = validate_account_data(valid_account)
    assert is_valid
    assert len(errors) == 0
    
    # Missing account_id
    invalid_account = {
        'user_id': 1,
        'type': 'depository',
        'current_balance': 1000.0
    }
    is_valid, errors = validate_account_data(invalid_account)
    assert not is_valid
    assert 'account_id' in str(errors[0])
    
    # Invalid type
    invalid_account = {
        'account_id': 'acc_001',
        'user_id': 1,
        'type': 'invalid',
        'current_balance': 1000.0
    }
    is_valid, errors = validate_account_data(invalid_account)
    assert not is_valid
    assert 'type' in str(errors[0])
    
    # Missing current_balance
    invalid_account = {
        'account_id': 'acc_001',
        'user_id': 1,
        'type': 'depository'
    }
    is_valid, errors = validate_account_data(invalid_account)
    assert not is_valid
    assert 'current_balance' in str(errors[0])


def test_validate_transaction_data():
    """Test transaction data validation."""
    # Valid transaction
    valid_tx = {
        'account_id': 'acc_001',
        'date': '2024-01-15',
        'amount': -50.0
    }
    is_valid, errors = validate_transaction_data(valid_tx)
    assert is_valid
    assert len(errors) == 0
    
    # Missing account_id
    invalid_tx = {
        'date': '2024-01-15',
        'amount': -50.0
    }
    is_valid, errors = validate_transaction_data(invalid_tx)
    assert not is_valid
    assert 'account_id' in str(errors[0])
    
    # Invalid date
    invalid_tx = {
        'account_id': 'acc_001',
        'date': 'invalid-date',
        'amount': -50.0
    }
    is_valid, errors = validate_transaction_data(invalid_tx)
    assert not is_valid
    assert 'date' in str(errors[0])
    
    # Missing amount
    invalid_tx = {
        'account_id': 'acc_001',
        'date': '2024-01-15'
    }
    is_valid, errors = validate_transaction_data(invalid_tx)
    assert not is_valid
    assert 'amount' in str(errors[0])


def test_validate_credit_card_data():
    """Test credit card data validation."""
    # Valid credit card
    valid_cc = {'account_id': 'acc_001', 'apr': 22.0}
    is_valid, errors = validate_credit_card_data(valid_cc)
    assert is_valid
    assert len(errors) == 0
    
    # Missing account_id
    invalid_cc = {'apr': 22.0}
    is_valid, errors = validate_credit_card_data(invalid_cc)
    assert not is_valid
    assert 'account_id' in str(errors[0])
    
    # Invalid APR
    invalid_cc = {'account_id': 'acc_001', 'apr': 150.0}
    is_valid, errors = validate_credit_card_data(invalid_cc)
    assert not is_valid
    assert 'APR' in str(errors[0])


def test_validate_liability_data():
    """Test liability data validation."""
    # Valid liability
    valid_liability = {'account_id': 'acc_001', 'liability_type': 'mortgage'}
    is_valid, errors = validate_liability_data(valid_liability)
    assert is_valid
    assert len(errors) == 0
    
    # Missing account_id
    invalid_liability = {'liability_type': 'mortgage'}
    is_valid, errors = validate_liability_data(invalid_liability)
    assert not is_valid
    assert 'account_id' in str(errors[0])
    
    # Invalid liability_type
    invalid_liability = {'account_id': 'acc_001', 'liability_type': 'invalid'}
    is_valid, errors = validate_liability_data(invalid_liability)
    assert not is_valid
    assert 'liability_type' in str(errors[0])


# ============================================================================
# Mapping Tests
# ============================================================================

def test_map_plaid_account_to_schema():
    """Test account field mapping."""
    # Plaid format with nested balances
    plaid_account = {
        'account_id': 'acc_001',
        'user_id': 1,
        'type': 'depository',
        'subtype': 'checking',
        'balances': {
            'available': 1000.0,
            'current': 2000.0
        },
        'iso_currency_code': 'USD',
        'holder_category': 'consumer'
    }
    
    mapped = map_plaid_account_to_schema(plaid_account)
    assert mapped['account_id'] == 'acc_001'
    assert mapped['available_balance'] == 1000.0
    assert mapped['current_balance'] == 2000.0
    assert mapped['iso_currency_code'] == 'USD'
    
    # Flat format
    flat_account = {
        'account_id': 'acc_002',
        'user_id': 1,
        'type': 'credit',
        'subtype': 'credit card',
        'current_balance': 1500.0,
        'limit': 5000.0
    }
    
    mapped = map_plaid_account_to_schema(flat_account)
    assert mapped['current_balance'] == 1500.0
    assert mapped['limit'] == 5000.0
    assert mapped['iso_currency_code'] == 'USD'  # Default
    assert mapped['holder_category'] == 'consumer'  # Default


def test_map_plaid_transaction_to_schema():
    """Test transaction field mapping."""
    # Plaid format with nested category
    plaid_tx = {
        'account_id': 'acc_001',
        'date': '2024-01-15',
        'amount': -50.0,
        'merchant_name': 'Coffee Shop',
        'payment_channel': 'in store',
        'personal_finance_category': {
            'primary': 'FOOD_AND_DRINK',
            'detailed': 'RESTAURANTS'
        },
        'pending': False
    }
    
    mapped = map_plaid_transaction_to_schema(plaid_tx)
    assert mapped['account_id'] == 'acc_001'
    assert mapped['date'] == date(2024, 1, 15)
    assert mapped['amount'] == -50.0
    assert mapped['merchant_name'] == 'Coffee Shop'
    assert mapped['personal_finance_category'] == 'FOOD_AND_DRINK'
    
    # Flat format
    flat_tx = {
        'account_id': 'acc_002',
        'date': '2024-01-20',
        'amount': 2500.0,
        'merchant_name': 'PAYROLL',
        'personal_finance_category': 'INCOME'
    }
    
    mapped = map_plaid_transaction_to_schema(flat_tx)
    assert mapped['date'] == date(2024, 1, 20)
    assert mapped['amount'] == 2500.0
    assert mapped['personal_finance_category'] == 'INCOME'
    assert mapped['pending'] is False  # Default


def test_map_plaid_credit_card_to_schema():
    """Test credit card field mapping."""
    plaid_cc = {
        'account_id': 'acc_001',
        'apr': 22.0,
        'minimum_payment_amount': 50.0,
        'last_payment_amount': 200.0,
        'is_overdue': False,
        'next_payment_due_date': '2024-02-15',
        'last_statement_balance': 2000.0
    }
    
    mapped = map_plaid_credit_card_to_schema(plaid_cc)
    assert mapped['account_id'] == 'acc_001'
    assert mapped['apr'] == 22.0
    assert mapped['minimum_payment_amount'] == 50.0
    assert mapped['next_payment_due_date'] == date(2024, 2, 15)


def test_map_plaid_liability_to_schema():
    """Test liability field mapping."""
    plaid_liability = {
        'account_id': 'acc_001',
        'liability_type': 'mortgage',
        'interest_rate': 3.5,
        'next_payment_due_date': '2024-02-01',
        'last_payment_amount': 1500.0
    }
    
    mapped = map_plaid_liability_to_schema(plaid_liability)
    assert mapped['account_id'] == 'acc_001'
    assert mapped['liability_type'] == 'mortgage'
    assert mapped['interest_rate'] == 3.5
    assert mapped['next_payment_due_date'] == date(2024, 2, 1)


def test_resolve_account_id():
    """Test account ID resolution."""
    account_map = {
        'acc_001': 1,
        'acc_002': 2,
        'acc_003': 3
    }
    
    assert resolve_account_id('acc_001', account_map) == 1
    assert resolve_account_id('acc_002', account_map) == 2
    assert resolve_account_id('acc_nonexistent', account_map) is None


# ============================================================================
# Integration Tests
# ============================================================================

def test_ingest_json_complete(test_db):
    """Test complete JSON ingestion."""
    test_db_path, conn = test_db
    
    # Create sample JSON file
    json_data = {
        'users': [
            {
                'user_id': 'user_test_001',
                'name': 'Test User',
                'email': 'test@example.com',
                'consent_given': True,
                'accounts': [
                    {
                        'account_id': 'acc_test_001',
                        'type': 'depository',
                        'subtype': 'checking',
                        'balances': {
                            'available': 1000.0,
                            'current': 1000.0
                        },
                        'transactions': [
                            {
                                'account_id': 'acc_test_001',
                                'date': '2024-01-15',
                                'amount': -50.0,
                                'merchant_name': 'Test Merchant',
                                'payment_channel': 'other'
                            }
                        ]
                    }
                ]
            }
        ]
    }
    
    json_file = 'test_sample.json'
    with open(json_file, 'w') as f:
        json.dump(json_data, f)
    
    try:
        # Ingest JSON
        summary = ingest_json(json_file, conn)
        
        # Verify summary
        assert summary['success']
        assert summary['users_created'] == 1
        assert summary['accounts_created'] == 1
        assert summary['transactions_created'] == 1
        
        # Verify data in database
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'test@example.com'")
        assert cursor.fetchone()[0] == 1
        
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE account_id = 'acc_test_001'")
        assert cursor.fetchone()[0] == 1
        
        cursor.execute("SELECT COUNT(*) FROM transactions")
        assert cursor.fetchone()[0] == 1
    
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)


def test_ingest_json_missing_fields(test_db):
    """Test JSON ingestion with missing optional fields."""
    test_db_path, conn = test_db
    
    json_data = {
        'users': [
            {
                'name': 'Test User',
                'email': 'test2@example.com',
                'accounts': [
                    {
                        'account_id': 'acc_test_002',
                        'type': 'depository',
                        'current_balance': 1000.0  # Flat format, no nested balances
                    }
                ]
            }
        ]
    }
    
    json_file = 'test_sample2.json'
    with open(json_file, 'w') as f:
        json.dump(json_data, f)
    
    try:
        summary = ingest_json(json_file, conn)
        assert summary['success']
        assert summary['users_created'] == 1
        assert summary['accounts_created'] == 1
    
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)


def test_ingest_json_duplicate_account_id(test_db):
    """Test JSON ingestion handles duplicate account_ids."""
    test_db_path, conn = test_db
    
    # First ingestion
    json_data = {
        'users': [
            {
                'name': 'Test User 1',
                'email': 'test3@example.com',
                'accounts': [
                    {
                        'account_id': 'acc_duplicate',
                        'type': 'depository',
                        'current_balance': 1000.0
                    }
                ]
            }
        ]
    }
    
    json_file = 'test_duplicate.json'
    with open(json_file, 'w') as f:
        json.dump(json_data, f)
    
    try:
        summary1 = ingest_json(json_file, conn)
        assert summary1['success']
        assert summary1['accounts_created'] == 1
        
        # Second ingestion (duplicate)
        summary2 = ingest_json(json_file, conn)
        # Should handle gracefully (skip or warn)
        assert 'acc_duplicate' in str(summary2['warnings']) or summary2['accounts_created'] == 0
    
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)


def test_ingest_csv_complete(test_db):
    """Test complete CSV ingestion."""
    test_db_path, conn = test_db
    
    # Create sample CSV files
    users_file = 'test_users.csv'
    accounts_file = 'test_accounts.csv'
    transactions_file = 'test_transactions.csv'
    
    with open(users_file, 'w') as f:
        f.write('user_id,name,email,consent_given\n')
        f.write('user_csv_001,CSV User,csv@example.com,true\n')
    
    with open(accounts_file, 'w') as f:
        f.write('account_id,user_id,type,subtype,current_balance,iso_currency_code\n')
        f.write('acc_csv_001,user_csv_001,depository,checking,2000.00,USD\n')
    
    with open(transactions_file, 'w') as f:
        f.write('account_id,date,amount,merchant_name\n')
        f.write('acc_csv_001,2024-01-15,-100.00,Test Merchant\n')
    
    try:
        summary = ingest_csv(users_file, accounts_file, transactions_file, None, None, conn)
        
        assert summary['success']
        assert summary['users_created'] == 1
        assert summary['accounts_created'] == 1
        assert summary['transactions_created'] == 1
        
        # Verify data
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = 'csv@example.com'")
        assert cursor.fetchone()[0] == 1
        
        cursor.execute("SELECT COUNT(*) FROM accounts WHERE account_id = 'acc_csv_001'")
        assert cursor.fetchone()[0] == 1
    
    finally:
        for f in [users_file, accounts_file, transactions_file]:
            if os.path.exists(f):
                os.remove(f)


def test_ingest_csv_missing_optional_files(test_db):
    """Test CSV ingestion with missing optional files."""
    test_db_path, conn = test_db
    
    users_file = 'test_users2.csv'
    accounts_file = 'test_accounts2.csv'
    
    with open(users_file, 'w') as f:
        f.write('user_id,name,email\n')
        f.write('user_csv_002,CSV User 2,csv2@example.com\n')
    
    with open(accounts_file, 'w') as f:
        f.write('account_id,user_id,type,current_balance\n')
        f.write('acc_csv_002,user_csv_002,depository,3000.00\n')
    
    try:
        # No transactions file provided
        summary = ingest_csv(users_file, accounts_file, None, None, None, conn)
        
        assert summary['success']
        assert summary['users_created'] == 1
        assert summary['accounts_created'] == 1
        assert summary['transactions_created'] == 0
    
    finally:
        for f in [users_file, accounts_file]:
            if os.path.exists(f):
                os.remove(f)


def test_ingest_csv_foreign_key_errors(test_db):
    """Test CSV ingestion handles foreign key errors."""
    test_db_path, conn = test_db
    
    users_file = 'test_users3.csv'
    accounts_file = 'test_accounts3.csv'
    transactions_file = 'test_transactions3.csv'
    
    with open(users_file, 'w') as f:
        f.write('user_id,name,email\n')
        f.write('user_csv_003,CSV User 3,csv3@example.com\n')
    
    with open(accounts_file, 'w') as f:
        f.write('account_id,user_id,type,current_balance\n')
        f.write('acc_csv_003,user_csv_003,depository,4000.00\n')
    
    with open(transactions_file, 'w') as f:
        f.write('account_id,date,amount\n')
        f.write('acc_nonexistent,2024-01-15,-50.00\n')  # Account doesn't exist
    
    try:
        summary = ingest_csv(users_file, accounts_file, transactions_file, None, None, conn)
        
        # Should have errors for missing account
        assert len(summary['errors']) > 0
        assert 'acc_nonexistent' in str(summary['errors'][0])
        assert summary['transactions_created'] == 0
    
    finally:
        for f in [users_file, accounts_file, transactions_file]:
            if os.path.exists(f):
                os.remove(f)


def test_ingest_transaction_safety(test_db):
    """Test transaction rollback on errors."""
    test_db_path, conn = test_db
    
    # This test verifies that errors in one user don't affect others
    json_data = {
        'users': [
            {
                'name': 'Valid User',
                'email': 'valid@example.com',
                'accounts': [
                    {
                        'account_id': 'acc_valid',
                        'type': 'depository',
                        'current_balance': 1000.0
                    }
                ]
            },
            {
                'name': 'Invalid User',  # Missing email
                'accounts': [
                    {
                        'account_id': 'acc_invalid',
                        'type': 'depository',
                        'current_balance': 2000.0
                    }
                ]
            },
            {
                'name': 'Another Valid User',
                'email': 'valid2@example.com',
                'accounts': [
                    {
                        'account_id': 'acc_valid2',
                        'type': 'depository',
                        'current_balance': 3000.0
                    }
                ]
            }
        ]
    }
    
    json_file = 'test_transaction_safety.json'
    with open(json_file, 'w') as f:
        json.dump(json_data, f)
    
    try:
        summary = ingest_json(json_file, conn)
        
        # Should have processed valid users
        assert summary['users_created'] >= 2  # At least 2 valid users
        # Should have errors for invalid user
        assert len(summary['errors']) > 0 or len(summary['warnings']) > 0
    
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)

