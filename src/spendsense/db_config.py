"""
Database configuration and abstraction layer for SpendSense.
Supports SQLite (MVP) with easy migration path to PostgreSQL (production).

This module provides database-agnostic connection handling and query execution
to minimize changes needed when migrating from SQLite to PostgreSQL.
"""

import os
from typing import Optional, Union, Any
from enum import Enum


class DatabaseType(Enum):
    """Supported database types."""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"


# Database configuration from environment variables
DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()
DB_PATH = os.getenv("DB_PATH", "spendsense.db")  # SQLite path or PostgreSQL connection string
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "spendsense")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")


def get_database_type() -> DatabaseType:
    """Get the configured database type."""
    if DB_TYPE == "postgresql" or DB_TYPE == "postgres":
        return DatabaseType.POSTGRESQL
    return DatabaseType.SQLITE


def get_connection_string() -> str:
    """Get database connection string based on configured type."""
    db_type = get_database_type()
    
    if db_type == DatabaseType.POSTGRESQL:
        # PostgreSQL connection string
        if DB_PASSWORD:
            return f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        return f"postgresql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        # SQLite connection string (file path)
        return DB_PATH


def get_placeholder() -> str:
    """
    Get parameter placeholder for current database type.
    SQLite uses '?' while PostgreSQL uses '%s' (psycopg2) or '$1, $2' (asyncpg).
    
    Returns:
        Placeholder string for parameterized queries
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "%s"  # psycopg2 style
    return "?"  # SQLite style


def convert_placeholders(query: str) -> str:
    """
    Convert SQLite placeholders (?) to PostgreSQL placeholders (%s).
    
    This allows us to write queries once and convert them at runtime.
    
    Args:
        query: SQL query with placeholders
        
    Returns:
        Query with appropriate placeholders for current database
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        # Convert ? to %s for psycopg2
        return query.replace("?", "%s")
    return query  # Keep ? for SQLite


def get_auto_increment_syntax() -> str:
    """
    Get auto-increment syntax for current database type.
    
    SQLite: INTEGER PRIMARY KEY AUTOINCREMENT
    PostgreSQL: SERIAL PRIMARY KEY or BIGSERIAL PRIMARY KEY
    
    Returns:
        Auto-increment syntax string
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "SERIAL PRIMARY KEY"
    return "INTEGER PRIMARY KEY AUTOINCREMENT"


def get_boolean_type() -> str:
    """
    Get boolean type syntax for current database.
    Both SQLite and PostgreSQL support BOOLEAN, but defaults differ.
    
    Returns:
        Boolean type syntax
    """
    return "BOOLEAN"  # Both support this


def get_text_type() -> str:
    """
    Get text type syntax. 
    PostgreSQL prefers VARCHAR with length, SQLite uses TEXT.
    
    For migration: Use TEXT in SQLite, VARCHAR(255) in PostgreSQL.
    
    Returns:
        Text type syntax
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "VARCHAR(255)"  # PostgreSQL prefers VARCHAR
    return "TEXT"  # SQLite uses TEXT


def get_real_type() -> str:
    """
    Get numeric type for financial data.
    SQLite uses REAL, PostgreSQL prefers NUMERIC or DECIMAL for financial data.
    
    Returns:
        Numeric type syntax
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "NUMERIC(10, 2)"  # PostgreSQL: NUMERIC for financial data
    return "REAL"  # SQLite uses REAL


def get_timestamp_type() -> str:
    """
    Get timestamp type syntax.
    
    Returns:
        Timestamp type syntax
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    return "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"  # Both support this


def get_foreign_key_enable_sql() -> Optional[str]:
    """
    Get SQL to enable foreign key constraints.
    SQLite requires PRAGMA, PostgreSQL has them enabled by default.
    
    Returns:
        SQL statement or None
    """
    db_type = get_database_type()
    if db_type == DatabaseType.SQLITE:
        return "PRAGMA foreign_keys = ON"
    return None  # PostgreSQL has foreign keys enabled by default


def get_schema_query_table() -> str:
    """
    Get table name for schema introspection queries.
    SQLite: sqlite_master
    PostgreSQL: information_schema.tables
    
    Returns:
        SQL query fragment for table listing
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "information_schema.tables"
    return "sqlite_master"


def get_schema_query_filter() -> str:
    """
    Get filter for schema introspection to exclude system tables.
    
    Returns:
        SQL WHERE clause fragment
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return "table_schema = 'public'"
    return "type='table' AND name NOT LIKE 'sqlite_%'"


def get_table_info_query(table_name: str) -> str:
    """
    Get query to fetch table column information.
    
    Args:
        table_name: Name of table
        
    Returns:
        SQL query string
    """
    db_type = get_database_type()
    if db_type == DatabaseType.POSTGRESQL:
        return f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            ORDER BY ordinal_position
        """
    return f"PRAGMA table_info({table_name})"


# Migration readiness checklist
MIGRATION_READINESS = {
    "schema_types": {
        "status": "needs_work",
        "issues": [
            "AUTOINCREMENT needs to be SERIAL for PostgreSQL",
            "TEXT should be VARCHAR(255) for PostgreSQL",
            "REAL should be NUMERIC(10,2) for financial data in PostgreSQL"
        ]
    },
    "connection_abstraction": {
        "status": "in_progress",
        "notes": "Creating abstraction layer (this file)"
    },
    "parameterized_queries": {
        "status": "good",
        "notes": "Using ? placeholders - can convert to %s for PostgreSQL"
    },
    "foreign_keys": {
        "status": "good",
        "notes": "Using standard FOREIGN KEY syntax compatible with both"
    },
    "indexes": {
        "status": "good",
        "notes": "Using standard CREATE INDEX syntax compatible with both"
    },
    "date_handling": {
        "status": "good",
        "notes": "Using DATE and TIMESTAMP types compatible with both"
    },
    "json_storage": {
        "status": "good",
        "notes": "Storing JSON as TEXT in SQLite, can use JSONB in PostgreSQL"
    }
}

