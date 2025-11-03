"""
Unit tests for database module.
"""

import sqlite3
import os
import sys
import pytest

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import init_database, validate_schema, get_db_connection


@pytest.fixture
def test_db():
    """Create a test database for each test."""
    test_db_path = "test_spendsense.db"
    # Remove test database if it exists
    if os.path.exists(test_db_path):
        os.remove(test_db_path)
    
    # Initialize test database
    init_database(test_db_path)
    
    yield test_db_path
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


def test_table_creation(test_db):
    """Test that all tables are created."""
    conn = get_db_connection(test_db)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    
    tables = {row[0] for row in cursor.fetchall()}
    
    expected_tables = {'users', 'accounts', 'transactions', 'credit_cards', 'signals'}
    assert tables == expected_tables, f"Expected tables {expected_tables}, got {tables}"
    
    conn.close()


def test_foreign_key_constraint(test_db):
    """Test that foreign key constraints are enforced."""
    conn = get_db_connection(test_db)
    cursor = conn.cursor()
    
    # Try to insert account with invalid user_id
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute("""
            INSERT INTO accounts (
                user_id, account_id, type, current_balance
            ) VALUES (?, ?, ?, ?)
        """, (999, "acc_test", "depository", 1000.0))
        conn.commit()
    
    conn.close()


def test_index_creation(test_db):
    """Test that indexes are created."""
    conn = get_db_connection(test_db)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name NOT LIKE 'sqlite_%'
    """)
    
    indexes = {row[0] for row in cursor.fetchall()}
    
    expected_indexes = {
        'idx_transactions_account',
        'idx_transactions_date',
        'idx_signals_user',
        'idx_accounts_user'
    }
    
    assert expected_indexes.issubset(indexes), f"Missing indexes: {expected_indexes - indexes}"
    
    conn.close()


def test_schema_validation(test_db):
    """Test that schema validation passes."""
    assert validate_schema(test_db) == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

