# SpendSense Database Schema

## Overview

SpendSense uses a SQLite database with a Plaid-compatible schema. The database stores user data, accounts, transactions, detected signals, persona assignments, recommendations, and decision traces.

## Entity Relationship Diagram

```mermaid
erDiagram
    users ||--o{ accounts : has
    users ||--o| personas : assigned
    users ||--o{ signals : has
    users ||--o{ recommendations : receives
    accounts ||--o{ transactions : contains
    accounts ||--o| credit_cards : "has (if credit)"
    accounts ||--o| liabilities : "has (if mortgage/student)"
    recommendations ||--o{ decision_traces : has
    
    users {
        int id PK
        string name
        string email UK
        bool consent_given
        timestamp created_at
    }
    
    accounts {
        int id PK
        int user_id FK
        string account_id UK
        string type
        string subtype
        float available_balance
        float current_balance
        float limit
        string iso_currency_code
        string holder_category
    }
    
    transactions {
        int id PK
        int account_id FK
        date date
        float amount
        string merchant_name
        string merchant_entity_id
        string payment_channel
        string personal_finance_category
        bool pending
    }
    
    credit_cards {
        int id PK
        int account_id FK UK
        float apr
        float minimum_payment_amount
        float last_payment_amount
        bool is_overdue
        date next_payment_due_date
        float last_statement_balance
    }
    
    liabilities {
        int id PK
        int account_id FK UK
        string liability_type
        float interest_rate
        date next_payment_due_date
        float last_payment_amount
    }
    
    signals {
        int id PK
        int user_id FK
        string signal_type
        float value
        json metadata
        string window
        timestamp detected_at
    }
    
    personas {
        int user_id PK FK
        string persona_type
        string criteria_matched
        timestamp assigned_at
    }
    
    recommendations {
        int id PK
        int user_id FK
        string title
        string content
        string rationale
        string persona_matched
        timestamp created_at
    }
    
    decision_traces {
        int id PK
        int user_id FK
        int recommendation_id FK
        int step
        string reasoning
        json data_cited
        timestamp created_at
    }
```

## Table Descriptions

### users

Stores user information and consent status.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| name | TEXT | User's full name |
| email | TEXT | User's email (unique) |
| consent_given | BOOLEAN | Whether user has given consent for data processing |
| created_at | TIMESTAMP | Account creation timestamp |

**Indexes:**
- Primary key on `id`
- Unique constraint on `email`

### accounts

Stores account information (Plaid-compatible). Supports checking, savings, credit cards, money market, HSA, mortgages, and student loans.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| user_id | INTEGER | Foreign key to users.id |
| account_id | TEXT | Unique account identifier |
| type | TEXT | Account type (depository, credit, loan) |
| subtype | TEXT | Account subtype (checking, savings, credit card, etc.) |
| available_balance | REAL | Available balance |
| current_balance | REAL | Current balance |
| limit | REAL | Credit limit (for credit cards) |
| iso_currency_code | TEXT | Currency code (default: USD) |
| holder_category | TEXT | Account holder category (default: consumer) |

**Indexes:**
- Primary key on `id`
- Unique constraint on `account_id`
- Foreign key on `user_id` → users.id

### transactions

Stores transaction history (Plaid-compatible).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| account_id | INTEGER | Foreign key to accounts.id |
| date | DATE | Transaction date |
| amount | REAL | Transaction amount (negative for debits, positive for credits) |
| merchant_name | TEXT | Merchant name |
| merchant_entity_id | TEXT | Merchant entity identifier |
| payment_channel | TEXT | Payment channel (online, in store, etc.) |
| personal_finance_category | TEXT | Personal finance category |
| pending | BOOLEAN | Whether transaction is pending |

**Indexes:**
- Primary key on `id`
- Foreign key on `account_id` → accounts.id
- Index on `date` for time-based queries

### credit_cards

Stores credit card liability data.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| account_id | INTEGER | Foreign key to accounts.id (unique) |
| apr | REAL | Annual percentage rate |
| minimum_payment_amount | REAL | Minimum payment due |
| last_payment_amount | REAL | Last payment amount |
| is_overdue | BOOLEAN | Whether payment is overdue |
| next_payment_due_date | DATE | Next payment due date |
| last_statement_balance | REAL | Last statement balance |

**Indexes:**
- Primary key on `id`
- Foreign key on `account_id` → accounts.id (unique)

### liabilities

Stores mortgage and student loan liability data (Phase 4).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| account_id | INTEGER | Foreign key to accounts.id (unique) |
| liability_type | TEXT | Type: 'mortgage' or 'student' |
| interest_rate | REAL | Interest rate |
| next_payment_due_date | DATE | Next payment due date |
| last_payment_amount | REAL | Last payment amount |

**Indexes:**
- Primary key on `id`
- Foreign key on `account_id` → accounts.id (unique)

### signals

Stores detected behavioral signals. Supports both 30-day and 180-day windows (Phase 5).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| user_id | INTEGER | Foreign key to users.id |
| signal_type | TEXT | Signal type (credit_utilization_max, subscription_count, etc.) |
| value | REAL | Signal value |
| metadata | JSON | Additional signal metadata (stored as JSON string) |
| window | TEXT | Time window ('30d' or '180d') |
| detected_at | TIMESTAMP | Detection timestamp |

**Indexes:**
- Primary key on `id`
- Foreign key on `user_id` → users.id
- Index on `(user_id, signal_type, window)` for efficient lookups

**Signal Types:**
- Credit: `credit_utilization_max`, `credit_utilization_avg`, `credit_card_count`, `credit_interest_charges`, `credit_overdue`, flags (30, 50, 80%)
- Subscriptions: `subscription_count`, `subscription_monthly_spend`, `subscription_merchants`, `subscription_share`
- Savings: `savings_net_inflow_30d`, `savings_net_inflow_180d`, `savings_growth_rate_30d`, `savings_growth_rate_180d`, `emergency_fund_coverage_30d`, `emergency_fund_coverage_180d`
- Income: `income_frequency`, `income_variability`, `cash_flow_buffer_30d`, `cash_flow_buffer_180d`, `median_pay_gap`

### personas

Stores persona assignments for users.

| Column | Type | Description |
|--------|------|-------------|
| user_id | INTEGER | Primary key, foreign key to users.id |
| persona_type | TEXT | Persona type (high_utilization, variable_income_budgeter, savings_builder, financial_newcomer, subscription_heavy, neutral) |
| criteria_matched | TEXT | Criteria that matched for this persona |
| assigned_at | TIMESTAMP | Assignment timestamp |

**Indexes:**
- Primary key on `user_id` → users.id (one persona per user)

### recommendations

Stores generated recommendations with content and rationales.

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| user_id | INTEGER | Foreign key to users.id |
| title | TEXT | Recommendation title |
| content | TEXT | Recommendation content |
| rationale | TEXT | Data-driven rationale |
| persona_matched | TEXT | Persona that triggered this recommendation |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes:**
- Primary key on `id`
- Foreign key on `user_id` → users.id

### decision_traces

Stores 4-step decision traces for each recommendation (auditability).

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key, auto-increment |
| user_id | INTEGER | Foreign key to users.id |
| recommendation_id | INTEGER | Foreign key to recommendations.id |
| step | INTEGER | Step number (1-4) |
| reasoning | TEXT | Reasoning for this step |
| data_cited | JSON | Data cited in this step (stored as JSON string) |
| created_at | TIMESTAMP | Creation timestamp |

**Indexes:**
- Primary key on `id`
- Foreign key on `user_id` → users.id
- Foreign key on `recommendation_id` → recommendations.id
- Index on `(recommendation_id, step)` for efficient lookups

**Decision Trace Steps:**
1. Signal Detected
2. Persona Assigned
3. Recommendation Selected
4. Rationale Generated

## Migration Notes

This schema is designed for SQLite (MVP) but uses standard SQL syntax that will migrate easily to PostgreSQL (production):

- `AUTOINCREMENT` → `SERIAL` in PostgreSQL
- `TEXT` → `VARCHAR(255)` in PostgreSQL (optional optimization)
- `REAL` → `NUMERIC(10,2)` in PostgreSQL (for financial precision)
- Parameterized queries use `?` (SQLite) - easily converted to `%s` (PostgreSQL)

See `md_files/MIGRATION_GUIDE.md` for detailed migration instructions.

