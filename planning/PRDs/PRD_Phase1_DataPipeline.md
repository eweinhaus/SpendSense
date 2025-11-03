# SpendSense MVP - Phase 1: Data Pipeline PRD
## Data Foundation & Signal Detection

**Status:** Planning  
**Dependencies:** None (foundation phase)  
**Deliverables:** Database schema, synthetic data generator, signal detection engine  
**Sub-Phases Covered:** Sub-Phase 1 (Data Foundation) + Sub-Phase 2 (Signal Detection)

---

## Overview

Phase 1 establishes the data foundation for SpendSense MVP. This phase includes Sub-Phase 1 (database setup and synthetic data generation matching Plaid's structure) and Sub-Phase 2 (core behavioral signal detection for credit utilization and subscriptions).

## Goals

- Create SQLite database with Plaid-compatible schema
- Generate 5 diverse synthetic users with realistic financial profiles
- Implement credit utilization signal detection
- Implement subscription pattern detection
- Store all signals in database for downstream processing
- Validate data quality and signal accuracy

## Non-Goals (Deferred)

- Income stability detection
- Savings growth analysis
- 180-day time window analysis
- Advanced pattern matching (fuzzy matching, ML-based detection)
- Real-time data ingestion from Plaid

---

## Database Schema

### Core Tables

**users**
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    consent_given BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**accounts** (Plaid-compatible)
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    account_id TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,  -- 'depository', 'credit', etc.
    subtype TEXT,  -- 'checking', 'savings', 'credit card', etc.
    available_balance REAL,
    current_balance REAL NOT NULL,
    limit REAL,  -- For credit cards
    iso_currency_code TEXT DEFAULT 'USD',
    holder_category TEXT DEFAULT 'consumer',  -- Exclude 'business'
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**transactions** (Plaid-compatible)
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    date DATE NOT NULL,
    amount REAL NOT NULL,
    merchant_name TEXT,
    merchant_entity_id TEXT,
    payment_channel TEXT,  -- 'online', 'in store', 'other'
    personal_finance_category TEXT,  -- 'GENERAL_MERCHANDISE', etc.
    pending BOOLEAN DEFAULT 0,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

**credit_cards** (Liability data)
```sql
CREATE TABLE credit_cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL UNIQUE,
    apr REAL,  -- Annual percentage rate
    minimum_payment_amount REAL,
    last_payment_amount REAL,
    is_overdue BOOLEAN DEFAULT 0,
    next_payment_due_date DATE,
    last_statement_balance REAL,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

**signals** (Detected behavioral signals)
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    signal_type TEXT NOT NULL,  -- 'credit_utilization', 'subscription_recurring', etc.
    value REAL,
    metadata TEXT,  -- JSON for additional signal data
    window TEXT DEFAULT '30d',  -- '30d' or '180d'
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Indexes

```sql
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_signals_user ON signals(user_id);
CREATE INDEX idx_accounts_user ON accounts(user_id);
```

---

## Synthetic Data Generation

### User Profiles (5 Users)

**User 1: High Utilization - Single Card**
- 1 credit card: $5,000 limit, $3,750 balance (75% utilization)
- Interest charges: $87/month
- Not overdue
- Mix of transactions (groceries, dining, gas)
- Goal: Clear High Utilization persona match

**User 2: High Utilization - Multiple Cards**
- 2 credit cards:
  - Card 1: $3,000 limit, $2,100 balance (70% utilization)
  - Card 2: $8,000 limit, $6,500 balance (81% utilization), overdue
- Interest charges on both
- Mix of transactions
- Goal: High Utilization with multiple cards, one overdue

**User 3: Subscription-Heavy - Major Services**
- 1 checking account
- 1 credit card (low utilization)
- Recurring subscriptions:
  - Netflix: $15.99/month (3 occurrences)
  - Spotify: $9.99/month (3 occurrences)
  - Gym: $49.99/month (3 occurrences)
  - Amazon Prime: $14.99/month (3 occurrences)
- Monthly recurring spend: ~$90
- Total monthly spend: ~$750
- Subscription share: ~12%
- Goal: Clear Subscription-Heavy persona match

**User 4: Subscription-Heavy - Many Small Services**
- 1 checking account
- 1 credit card (low utilization)
- Many small recurring charges:
  - Various streaming services: $5-10 each
  - Software subscriptions: $10-20 each
  - At least 5 different recurring merchants
  - Monthly recurring spend: ~$60
  - Total monthly spend: ~$600
  - Subscription share: ~10%
- Goal: Subscription-Heavy with many small subscriptions

**User 5: Neutral/Healthy**
- 1 checking account with healthy balance
- 1 credit card: $10,000 limit, $1,500 balance (15% utilization)
- No interest charges
- Not overdue
- Mix of transactions, few subscriptions
- Goal: Does not match either persona (control case)

### Data Generation Requirements

**Accounts:**
- Each user has 1 checking account
- Users 1, 2, 5 have 1-2 credit cards
- Users 3, 4 have 1 credit card (low utilization)
- Realistic account IDs (format: "acc_XXXX")
- Realistic balances based on user profile

**Transactions:**
- Generate 90 days of transaction history
- Realistic transaction patterns:
  - Daily: Coffee, gas, groceries
  - Weekly: Dining, entertainment
  - Monthly: Recurring subscriptions, utilities
- Realistic amounts based on category
- Mix of pending and settled transactions
- Realistic merchant names (Netflix, Starbucks, etc.)
- Include `payment_channel` and `personal_finance_category`

**Credit Cards:**
- Realistic APRs (15-25%)
- Realistic limits ($3,000-$10,000)
- Set balances based on utilization target
- Set `is_overdue` based on user profile
- Set `next_payment_due_date` (future dates)
- Set `last_statement_balance` matching current balance

**Data Quality:**
- No real PII (use Faker library for names/emails)
- All amounts in USD
- All dates within last 90 days
- No future-dated transactions (except payment due dates)
- Consistent data relationships (foreign keys)

---

## Signal Detection

### Credit Utilization Signals

**Calculation:**
```python
utilization = (balance / limit) * 100 if limit > 0 else 0
```

**Signals to Store:**
1. `credit_utilization_max` - Highest utilization across all cards
2. `credit_utilization_avg` - Average utilization across all cards
3. `credit_card_count` - Number of credit cards
4. `credit_interest_charges` - Monthly interest charges (if detectable)
5. `credit_overdue` - Boolean: any card overdue
6. `credit_utilization_flag_30` - Boolean: any card ≥30%
7. `credit_utilization_flag_50` - Boolean: any card ≥50%
8. `credit_utilization_flag_80` - Boolean: any card ≥80%

**Detection Logic:**
1. Query all credit card accounts for user
2. For each card:
   - Calculate utilization (balance / limit)
   - Check if limit > 0 (avoid division by zero)
   - Flag thresholds (30%, 50%, 80%)
3. Store highest utilization card details
4. Check overdue status from credit_cards table
5. Store all signals in signals table

**Edge Cases:**
- User with no credit cards → Skip credit signals
- Zero credit limit → Skip utilization calculation
- Missing balance data → Use 0 as fallback
- Negative balance → Handle gracefully (credit balance)

### Subscription Detection Signals

**Pattern Matching Criteria:**
1. Same merchant name (exact match, case-insensitive)
2. Similar amount (±$1 tolerance)
3. Monthly cadence: 30 days ±3 days between occurrences
4. At least 3 occurrences in 90-day window

**Detection Algorithm:**
```python
def detect_subscriptions(user_id, window_days=90):
    # Get all transactions in window
    transactions = get_transactions(user_id, window_days)
    
    # Group by merchant
    by_merchant = group_by_merchant(transactions)
    
    # For each merchant with ≥3 transactions:
    recurring = []
    for merchant, txs in by_merchant.items():
        if len(txs) >= 3:
            # Check amount similarity
            amounts = [tx.amount for tx in txs]
            if is_similar_amount(amounts, tolerance=1.0):
                # Check date spacing (monthly cadence)
                if is_monthly_cadence(txs, days_range=(27, 33)):
                    recurring.append({
                        'merchant': merchant,
                        'count': len(txs),
                        'amount': amounts[0],
                        'monthly_spend': amounts[0]
                    })
    
    return recurring
```

**Signals to Store:**
1. `subscription_count` - Number of recurring merchants
2. `subscription_monthly_spend` - Sum of monthly recurring amounts
3. `subscription_merchants` - JSON array of merchant names
4. `subscription_share` - Subscription spend / total spend (30-day window)

**Detection Logic:**
1. Query transactions for user in last 90 days
2. Group transactions by merchant name
3. For merchants with ≥3 transactions:
   - Check amount similarity (±$1)
   - Check date spacing (30 days ±3)
4. Calculate monthly recurring spend (sum of recurring amounts)
5. Calculate subscription share (recurring / total in 30-day window)
6. Store signals in signals table

**Edge Cases:**
- User with no transactions → Skip subscription signals
- Merchant with <3 occurrences → Not considered recurring
- Amounts vary by >$1 → Not considered recurring
- Date spacing not monthly → Not considered recurring
- Missing merchant names → Skip or use generic label

---

## Implementation Details

### Database Setup

**File:** `database.py`

**Functions:**
- `init_database()` - Create all tables and indexes
- `get_db_connection()` - Get SQLite connection
- `validate_schema()` - Verify schema matches requirements

**Seeding:**
- Use deterministic seed for reproducible data
- Seed: 42 (configurable)

### Data Generation

**File:** `generate_data.py`

**Functions:**
- `generate_user(user_profile)` - Generate single user with all data
- `generate_accounts(user_id, profile)` - Generate accounts for user
- `generate_transactions(account_id, profile)` - Generate transactions
- `generate_credit_card(account_id, profile)` - Generate credit card data
- `generate_all_users()` - Generate all 5 users

**Dependencies:**
- `faker` library for names/emails
- `datetime` for date manipulation
- `random` with seed for deterministic generation

### Signal Detection

**File:** `detect_signals.py`

**Functions:**
- `detect_credit_signals(user_id)` - Detect all credit utilization signals
- `detect_subscription_signals(user_id)` - Detect subscription patterns
- `store_signal(user_id, signal_type, value, metadata)` - Store in database
- `detect_all_signals(user_id)` - Run all signal detection

**Dependencies:**
- Database connection
- Date calculations for time windows

---

## Testing Strategy

### Unit Tests

1. **Database Schema Tests:**
   - Test table creation
   - Test foreign key constraints
   - Test index creation
   - Test data types

2. **Data Generation Tests:**
   - Test user generation creates valid data
   - Test account generation with correct relationships
   - Test transaction generation with realistic patterns
   - Test credit card generation with correct utilization
   - Test deterministic generation (same seed = same data)

3. **Signal Detection Tests:**
   - Test credit utilization calculation (various balances/limits)
   - Test division by zero protection
   - Test subscription pattern matching (known patterns)
   - Test subscription detection with edge cases
   - Test signal storage in database

### Integration Tests

1. **Full Pipeline Test:**
   - Generate 5 users
   - Run signal detection
   - Verify signals stored correctly
   - Verify data relationships intact

2. **Edge Case Tests:**
   - User with no credit cards
   - User with no transactions
   - User with zero credit limit
   - User with missing merchant names

### Manual Validation

1. **Data Quality Check:**
   - Verify all 5 users generated
   - Verify realistic transaction patterns
   - Verify credit utilization matches targets
   - Verify subscriptions detected correctly

2. **Signal Accuracy Check:**
   - Verify credit utilization calculations
   - Verify subscription merchants identified
   - Verify signal values stored correctly

---

## Success Criteria

### Data Generation
- [ ] 5 users generated with diverse profiles
- [ ] All Plaid-compatible fields populated
- [ ] Realistic transaction patterns (90 days)
- [ ] Data relationships correct (foreign keys)
- [ ] No real PII (all synthetic)

### Signal Detection
- [ ] Credit utilization calculated correctly for all users
- [ ] Subscription patterns detected correctly
- [ ] All signals stored in database
- [ ] Edge cases handled gracefully
- [ ] Signals match expected values for demo users

### Code Quality
- [ ] Database schema matches specification
- [ ] Code is well-commented
- [ ] Error handling implemented
- [ ] Tests passing (≥3 tests minimum)
- [ ] Deterministic generation (seed-based)

---

## Deliverables

1. **Database Schema:**
   - `database.py` with schema definition
   - SQLite database file (`spendsense.db`)
   - Schema documentation

2. **Data Generator:**
   - `generate_data.py` with generation functions
   - Generated data for 5 users
   - Data validation script

3. **Signal Detection:**
   - `detect_signals.py` with detection logic
   - Signals stored in database
   - Signal detection tests

4. **Documentation:**
   - Code comments
   - Test results
   - Known limitations

---

## Known Limitations

- Only 30-day window (not 180-day)
- Simple subscription pattern matching (exact merchant name, no fuzzy matching)
- No income stability detection
- No savings growth analysis
- No minimum-payment-only detection (requires transaction history analysis)
- Subscription detection may miss edge cases (weekly subscriptions, irregular amounts)

---

## Next Phase Dependencies

Phase 1 outputs required for Phase 2 (Intelligence Layer):
- Database with users, accounts, transactions, credit_cards
- Signals table populated with detected signals
- Validated data quality

Phase 2 will use:
- `signals` table for persona assignment (Sub-Phase 3)
- User data for recommendation generation (Sub-Phase 4)
- Credit card data for rationale generation (Sub-Phase 4)

---

## Timeline Estimate

- Database setup: 1-2 hours
- Data generation: 3-4 hours
- Signal detection: 4-5 hours
- Testing: 2-3 hours
- **Total: 10-14 hours**

---

## Risk Mitigation

**Risk:** Subscription detection may miss patterns
- **Mitigation:** Start with strict rules, test on known patterns

**Risk:** Data generation may not be realistic
- **Mitigation:** Use Faker library, validate against real patterns

**Risk:** Division by zero errors
- **Mitigation:** Always check `limit > 0` before calculation

**Risk:** Signal detection may be slow
- **Mitigation:** Use indexes, optimize queries, test on 5 users first

