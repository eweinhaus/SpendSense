"""
Database module for SpendSense MVP.
Creates SQLite database with Plaid-compatible schema.

Migration Note: This module is designed for SQLite (MVP) but uses standard SQL
syntax that will migrate easily to PostgreSQL (production). Key considerations:
- AUTOINCREMENT → SERIAL in PostgreSQL
- TEXT → VARCHAR(255) in PostgreSQL (optional, for better compatibility)
- REAL → NUMERIC(10,2) in PostgreSQL (for financial precision)
- Parameterized queries use '?' (SQLite) - easily converted to '%s' (PostgreSQL)

See md_files/MIGRATION_GUIDE.md for detailed migration instructions.
"""

import sqlite3
from typing import Optional
from datetime import datetime


def get_db_connection(db_path: str = "spendsense.db") -> sqlite3.Connection:
    """
    Get SQLite database connection with foreign keys enabled.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        SQLite connection object
    """
    conn = sqlite3.connect(db_path)
    # Enable foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(db_path: str = "spendsense.db") -> None:
    """
    Initialize database with all tables and indexes.
    Creates database file if it doesn't exist.
    
    Args:
        db_path: Path to SQLite database file
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Create users table
    # Migration Note: AUTOINCREMENT → SERIAL in PostgreSQL
    # Migration Note: TEXT → VARCHAR(255) in PostgreSQL (optional optimization)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            consent_given BOOLEAN DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create accounts table (Plaid-compatible)
    # Migration Note: REAL → NUMERIC(10,2) in PostgreSQL for financial precision
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            account_id TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL,
            subtype TEXT,
            available_balance REAL,
            current_balance REAL NOT NULL,
            "limit" REAL,
            iso_currency_code TEXT DEFAULT 'USD',
            holder_category TEXT DEFAULT 'consumer',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create transactions table (Plaid-compatible)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            date DATE NOT NULL,
            amount REAL NOT NULL,
            merchant_name TEXT,
            merchant_entity_id TEXT,
            payment_channel TEXT,
            personal_finance_category TEXT,
            pending BOOLEAN DEFAULT 0,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)
    
    # Create credit_cards table (Liability data)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS credit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL UNIQUE,
            apr REAL,
            minimum_payment_amount REAL,
            last_payment_amount REAL,
            is_overdue BOOLEAN DEFAULT 0,
            next_payment_due_date DATE,
            last_statement_balance REAL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)
    
    # Create signals table (Detected behavioral signals)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS signals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            signal_type TEXT NOT NULL,
            value REAL,
            metadata TEXT,
            window TEXT DEFAULT '30d',
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create personas table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS personas (
            user_id INTEGER PRIMARY KEY,
            persona_type TEXT NOT NULL,
            assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            criteria_matched TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create recommendations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            rationale TEXT NOT NULL,
            persona_matched TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create decision_traces table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_traces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recommendation_id INTEGER NOT NULL,
            step INTEGER NOT NULL,
            reasoning TEXT NOT NULL,
            data_cited TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
        )
    """)
    
    # Create liabilities table (for mortgages and student loans)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS liabilities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            liability_type TEXT NOT NULL,
            interest_rate REAL,
            next_payment_due_date DATE,
            last_payment_amount REAL,
            FOREIGN KEY (account_id) REFERENCES accounts(id)
        )
    """)
    
    # Create indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_account 
        ON transactions(account_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_transactions_date 
        ON transactions(date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_user 
        ON signals(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_accounts_user 
        ON accounts(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_recommendations_user 
        ON recommendations(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_traces_user 
        ON decision_traces(user_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_decision_traces_recommendation 
        ON decision_traces(recommendation_id)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_liabilities_account 
        ON liabilities(account_id)
    """)
    
    conn.commit()
    conn.close()


def validate_schema(db_path: str = "spendsense.db") -> bool:
    """
    Validate that database schema matches PRD specification.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if schema is valid, False otherwise
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Expected tables and their columns
    expected_schema = {
        'users': ['id', 'name', 'email', 'consent_given', 'created_at'],
        'accounts': ['id', 'user_id', 'account_id', 'type', 'subtype', 
                     'available_balance', 'current_balance', 'limit', 
                     'iso_currency_code', 'holder_category'],
        'transactions': ['id', 'account_id', 'date', 'amount', 'merchant_name',
                        'merchant_entity_id', 'payment_channel', 
                        'personal_finance_category', 'pending'],
        'credit_cards': ['id', 'account_id', 'apr', 'minimum_payment_amount',
                        'last_payment_amount', 'is_overdue', 
                        'next_payment_due_date', 'last_statement_balance'],
        'signals': ['id', 'user_id', 'signal_type', 'value', 'metadata',
                   'window', 'detected_at'],
        'personas': ['user_id', 'persona_type', 'assigned_at', 'criteria_matched'],
        'recommendations': ['id', 'user_id', 'title', 'content', 'rationale',
                          'persona_matched', 'created_at'],
        'decision_traces': ['id', 'user_id', 'recommendation_id', 'step',
                           'reasoning', 'data_cited', 'created_at'],
        'liabilities': ['id', 'account_id', 'liability_type', 'interest_rate',
                       'next_payment_due_date', 'last_payment_amount']
    }
    
    # Check all tables exist
    # Migration Note: sqlite_master → information_schema.tables in PostgreSQL
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
    """)
    existing_tables = {row[0] for row in cursor.fetchall()}
    
    if set(expected_schema.keys()) != existing_tables:
        missing = set(expected_schema.keys()) - existing_tables
        extra = existing_tables - set(expected_schema.keys())
        print(f"❌ Schema validation failed:")
        if missing:
            print(f"   Missing tables: {missing}")
        if extra:
            print(f"   Extra tables: {extra}")
        conn.close()
        return False
    
    # Check columns for each table
    # Migration Note: PRAGMA table_info → information_schema.columns in PostgreSQL
    all_valid = True
    for table_name, expected_columns in expected_schema.items():
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        if set(expected_columns) != existing_columns:
            missing = set(expected_columns) - existing_columns
            extra = existing_columns - set(expected_columns)
            print(f"❌ Table '{table_name}' validation failed:")
            if missing:
                print(f"   Missing columns: {missing}")
            if extra:
                print(f"   Extra columns: {extra}")
            all_valid = False
    
    # Check indexes
    expected_indexes = [
        'idx_transactions_account',
        'idx_transactions_date',
        'idx_signals_user',
        'idx_accounts_user',
        'idx_recommendations_user',
        'idx_decision_traces_user',
        'idx_decision_traces_recommendation',
        'idx_liabilities_account'
    ]
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='index' AND name NOT LIKE 'sqlite_%'
    """)
    existing_indexes = {row[0] for row in cursor.fetchall()}
    
    for idx_name in expected_indexes:
        if idx_name not in existing_indexes:
            print(f"❌ Missing index: {idx_name}")
            all_valid = False
    
    if all_valid:
        print("✅ Schema validation passed - all tables, columns, and indexes present")
    else:
        print("❌ Schema validation failed - see errors above")
    
    conn.close()
    return all_valid


if __name__ == "__main__":
    """Initialize database and validate schema."""
    print("Initializing database...")
    init_database()
    print("Database initialized successfully.")
    print("\nValidating schema...")
    validate_schema()

