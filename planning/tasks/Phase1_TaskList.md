# Phase 1: Data Pipeline - Task List

**Status:** Ready to Start  
**Estimated Time:** 10-14 hours  
**Dependencies:** None (foundation phase)

---

## High-Level Goals & Success Criteria

### Goals Overview

Phase 1 establishes the foundational data layer for SpendSense MVP. This phase accomplishes two main objectives:

1. **Data Foundation (Sub-Phase 1):** Create a Plaid-compatible SQLite database and populate it with realistic synthetic data for 5 diverse user profiles. Each user will have accounts, transactions (90 days), and credit card liability data that matches real-world financial patterns.

2. **Signal Detection (Sub-Phase 2):** Implement behavioral signal detection algorithms that analyze transaction and account data to identify:
   - **Credit Utilization Signals:** Calculate utilization percentages, detect high utilization flags (30%, 50%, 80%), identify overdue status, and track interest charges
   - **Subscription Patterns:** Detect recurring monthly subscriptions by matching merchant names, amounts (±$1 tolerance), and date spacing (30 days ±3 days)

### Success Criteria

#### Data Generation Success
- ✅ 5 users generated with diverse, realistic profiles:
  - User 1: High Utilization (single card, 75% utilization)
  - User 2: High Utilization (multiple cards, one overdue)
  - User 3: Subscription-Heavy (major services, ~$90/month)
  - User 4: Subscription-Heavy (many small services, ~$60/month)
  - User 5: Neutral/Healthy (low utilization, few subscriptions)
- ✅ All Plaid-compatible fields populated correctly
- ✅ 90 days of realistic transaction patterns
- ✅ All foreign key relationships intact
- ✅ No real PII (all synthetic via Faker)
- ✅ Deterministic generation (seed-based, reproducible)

#### Signal Detection Success
- ✅ Credit utilization calculated correctly for all users with credit cards
- ✅ All 8 credit signals stored per user (max, avg, count, interest, overdue, flags)
- ✅ Subscription patterns detected correctly (3+ occurrences, ±$1 amount, monthly cadence)
- ✅ All 4 subscription signals stored per user (count, monthly spend, merchants, share)
- ✅ Edge cases handled gracefully (no credit cards, no transactions, zero limits)
- ✅ Signals match expected values for demo users

#### Code Quality Success
- ✅ Database schema matches PRD specification exactly
- ✅ Code is well-commented and maintainable
- ✅ Error handling prevents crashes (division by zero, missing data, etc.)
- ✅ At least 3 tests passing (unit or integration)
- ✅ All deliverables present: `database.py`, `generate_data.py`, `detect_signals.py`

---

## Potential Pitfalls & Considerations

### 1. Subscription Detection Complexity ⚠️

**Issue:** Pattern matching for recurring subscriptions is deceptively complex. The algorithm must balance strictness (to avoid false positives) with flexibility (to catch real subscriptions).

**Potential Problems:**
- **Amount variations:** Real subscriptions may have slight price changes (e.g., Netflix $15.99 → $16.99)
- **Date spacing irregularities:** Monthly subscriptions might be 28-35 days apart, not exactly 30
- **Missing merchant names:** Some transactions may have null or generic merchant names
- **Multiple subscriptions to same merchant:** User might have multiple Netflix accounts

**Mitigation:**
- Start with strict rules (±$1 tolerance, 27-33 day window) as specified
- Test on known patterns first (Netflix, Spotify, etc.)
- Log edge cases for later refinement
- Consider adding metadata to signals for debugging

### 2. Data Generation Realism ⚠️

**Issue:** Synthetic data may not feel realistic enough, which could undermine the demo. Users need to see believable transaction patterns, merchant names, and amounts.

**Potential Problems:**
- Transaction amounts too random or unrealistic
- Merchant names don't match real-world patterns
- Transaction frequency doesn't match user profile
- Credit card balances don't align with utilization targets

**Mitigation:**
- Use Faker library for realistic merchant names
- Create transaction templates by category (coffee: $3-6, groceries: $50-150, etc.)
- Validate generated data matches user profile goals
- Manually review first generated user for realism

### 3. Division by Zero & Edge Cases ⚠️

**Issue:** Credit utilization calculation can fail if credit limit is 0 or missing. Signal detection may crash on users with no transactions or no credit cards.

**Potential Problems:**
- Division by zero when `limit = 0`
- Missing account data breaking queries
- Users with no credit cards causing errors
- Users with no transactions breaking subscription detection

**Mitigation:**
- Always check `limit > 0` before division
- Use try/except blocks around signal detection
- Return empty results gracefully (no signals, not errors)
- Test edge cases explicitly (no cards, no transactions, zero limits)

### 4. Database Schema Accuracy ⚠️

**Issue:** Plaid-compatible schema must match specification exactly. Wrong field names, types, or constraints will break downstream phases.

**Potential Problems:**
- Field name typos (e.g., `account_id` vs `accountId`)
- Missing required fields
- Wrong data types (TEXT vs REAL)
- Missing foreign key constraints
- Missing indexes (causing slow queries)

**Mitigation:**
- Copy schema directly from PRD
- Validate schema after creation (check table structure)
- Test foreign key constraints work
- Create indexes as specified

### 5. Deterministic Data Generation ⚠️

**Issue:** PRD requires deterministic generation (same seed = same data). This is critical for testing and reproducibility, but easy to break.

**Potential Problems:**
- Using system time or random state that's not seeded
- Database insert order affecting auto-increment IDs
- Faker not seeded properly
- Date calculations using current date instead of relative dates

**Mitigation:**
- Set random seed at start of generation
- Seed Faker with same seed
- Use relative dates (90 days ago, not absolute dates)
- Test that same seed produces identical data

### 6. Signal Storage & Metadata ⚠️

**Issue:** Signals table uses JSON metadata field. Need to ensure JSON is properly formatted and contains useful debugging info.

**Potential Problems:**
- JSON serialization errors
- Metadata missing critical information
- Hard to debug signal detection issues later

**Mitigation:**
- Use `json.dumps()` for consistent formatting
- Include merchant names, account IDs, dates in metadata
- Store enough info to regenerate/recalculate signals

### 7. Testing Coverage ⚠️

**Issue:** PRD requires ≥3 tests, but it's easy to write trivial tests that don't actually validate functionality.

**Potential Problems:**
- Tests that always pass
- Tests that don't catch real bugs
- Missing tests for edge cases

**Mitigation:**
- Test actual calculations (utilization = 75% when balance=$3750, limit=$5000)
- Test subscription detection with known patterns
- Test edge cases (zero limit, no transactions)
- Test database constraints (foreign keys)

---

## Detailed Task List

### Phase 1.1: Database Setup

#### Task 1.1.1: Create Database Module
**File:** `database.py`  
**Time:** 30-45 minutes  
**Description:** Create the database module with schema definition and connection management.

**Subtasks:**
- [ ] Create `database.py` file
- [ ] Implement `get_db_connection()` function (returns SQLite connection)
- [ ] Implement `init_database()` function (creates all tables)
- [ ] Add schema creation for `users` table (id, name, email, consent_given, created_at)
- [ ] Add schema creation for `accounts` table (all Plaid-compatible fields)
- [ ] Add schema creation for `transactions` table (all Plaid-compatible fields)
- [ ] Add schema creation for `credit_cards` table (liability data)
- [ ] Add schema creation for `signals` table (signal_type, value, metadata JSON, window, detected_at)
- [ ] Add all foreign key constraints
- [ ] Add all indexes (transactions_account, transactions_date, signals_user, accounts_user)
- [ ] Implement `validate_schema()` function (verifies schema matches PRD)
- [ ] Add error handling for database operations
- [ ] Add docstrings to all functions

**Acceptance Criteria:**
- Database file `spendsense.db` created successfully
- All 5 tables exist with correct structure
- Foreign keys enforced
- Indexes created
- Schema validation passes

**Testing:**
- [ ] Test table creation
- [ ] Test foreign key constraint (attempt insert invalid foreign key)
- [ ] Test index creation (verify indexes exist)

---

#### Task 1.1.2: Database Schema Validation
**File:** `database.py`  
**Time:** 15-20 minutes  
**Description:** Verify schema matches PRD specification exactly.

**Subtasks:**
- [ ] Create `validate_schema()` function
- [ ] Check all table names exist
- [ ] Check all column names match PRD
- [ ] Check all data types match PRD (TEXT, REAL, INTEGER, BOOLEAN, DATE, TIMESTAMP)
- [ ] Check all foreign keys defined
- [ ] Check all indexes created
- [ ] Print validation results (pass/fail for each check)

**Acceptance Criteria:**
- Validation function runs without errors
- All checks pass
- Clear output showing schema status

---

### Phase 1.2: Synthetic Data Generation

#### Task 1.2.1: Set Up Data Generation Module
**File:** `generate_data.py`  
**Time:** 20-30 minutes  
**Description:** Create the data generation module structure and dependencies.

**Subtasks:**
- [ ] Create `generate_data.py` file
- [ ] Import required libraries (faker, datetime, random, sqlite3)
- [ ] Set up Faker instance with seed
- [ ] Set up random seed (42, configurable)
- [ ] Create helper functions for date calculations
- [ ] Create base structure for user profile generation

**Acceptance Criteria:**
- File created with proper imports
- Seeds configured for deterministic generation
- Helper functions ready for use

---

#### Task 1.2.2: Implement User Generation
**File:** `generate_data.py`  
**Time:** 30-45 minutes  
**Description:** Generate synthetic users with realistic names and emails.

**Subtasks:**
- [ ] Implement `generate_user(user_profile)` function
- [ ] Use Faker to generate realistic name
- [ ] Use Faker to generate unique email
- [ ] Set `consent_given` to False (default)
- [ ] Insert user into database
- [ ] Return user ID
- [ ] Handle database errors gracefully

**Acceptance Criteria:**
- User created with valid name and email
- Email is unique (database constraint)
- User ID returned correctly
- Deterministic (same seed = same user)

**Testing:**
- [ ] Test user generation with seed
- [ ] Test email uniqueness constraint
- [ ] Verify deterministic generation

---

#### Task 1.2.3: Implement Account Generation
**File:** `generate_data.py`  
**Time:** 45-60 minutes  
**Description:** Generate Plaid-compatible accounts (checking and credit cards) for each user.

**Subtasks:**
- [ ] Implement `generate_accounts(user_id, profile)` function
- [ ] Generate checking account for all users:
  - Account ID format: "acc_XXXX" (random but deterministic)
  - Type: "depository"
  - Subtype: "checking"
  - Realistic balance based on profile
  - USD currency
- [ ] Generate credit card accounts based on profile:
  - User 1: 1 card ($5,000 limit, $3,750 balance)
  - User 2: 2 cards ($3,000/$2,100, $8,000/$6,500)
  - User 3: 1 card (low utilization)
  - User 4: 1 card (low utilization)
  - User 5: 1 card ($10,000 limit, $1,500 balance)
  - Account ID format: "acc_XXXX"
  - Type: "credit"
  - Subtype: "credit card"
  - Realistic limits and balances
  - USD currency
- [ ] Store account IDs for transaction generation
- [ ] Return list of account IDs

**Acceptance Criteria:**
- All users have checking account
- Credit cards match profile specifications
- Account IDs are unique and realistic
- Balances match utilization targets
- All Plaid fields populated

**Testing:**
- [ ] Test account generation for each user profile
- [ ] Verify account IDs are unique
- [ ] Verify balances match targets

---

#### Task 1.2.4: Implement Credit Card Liability Data Generation
**File:** `generate_data.py`  
**Time:** 30-45 minutes  
**Description:** Generate credit card liability data (APR, payments, overdue status).

**Subtasks:**
- [ ] Implement `generate_credit_card(account_id, profile)` function
- [ ] Generate realistic APR (15-25% range)
- [ ] Calculate minimum payment (typically 1-3% of balance)
- [ ] Set last payment amount (realistic based on balance)
- [ ] Set `is_overdue` based on profile:
  - User 2, Card 2: True (overdue)
  - All others: False
- [ ] Set `next_payment_due_date` (future date, 20-30 days out)
- [ ] Set `last_statement_balance` matching current balance
- [ ] Insert into `credit_cards` table
- [ ] Handle edge cases (no credit cards)

**Acceptance Criteria:**
- All credit cards have liability data
- APR in realistic range
- Overdue status matches profile
- Payment dates are in future
- Data relationships correct (account_id foreign key)

**Testing:**
- [ ] Test credit card generation for each profile
- [ ] Verify overdue status correct
- [ ] Verify foreign key constraint

---

#### Task 1.2.5: Implement Transaction Generation
**File:** `generate_data.py`  
**Time:** 90-120 minutes  
**Description:** Generate 90 days of realistic transactions for each account.

**Subtasks:**
- [ ] Implement `generate_transactions(account_id, profile)` function
- [ ] Generate 90 days of transactions (go back from today)
- [ ] Create transaction templates by category:
  - Daily: Coffee ($3-6), Gas ($30-50)
  - Weekly: Groceries ($50-150), Dining ($20-60)
  - Monthly: Utilities ($80-150), Subscriptions (see profile)
- [ ] For User 3 (Subscription-Heavy):
  - Netflix: $15.99/month (3 occurrences, 30 days apart)
  - Spotify: $9.99/month (3 occurrences)
  - Gym: $49.99/month (3 occurrences)
  - Amazon Prime: $14.99/month (3 occurrences)
- [ ] For User 4 (Subscription-Heavy):
  - 5+ different recurring merchants ($5-20 each)
  - 3 occurrences each, monthly cadence
- [ ] For other users:
  - Mix of transactions, few subscriptions
- [ ] Assign realistic merchant names (use Faker or hardcode: Netflix, Starbucks, etc.)
- [ ] Set `payment_channel` (online, in store, other)
- [ ] Set `personal_finance_category` (GENERAL_MERCHANDISE, FOOD_AND_DRINK, etc.)
- [ ] Mix of pending and settled transactions
- [ ] Ensure amounts are realistic for category
- [ ] Insert transactions with proper dates
- [ ] Handle negative amounts for credit card payments

**Acceptance Criteria:**
- 90 days of transactions generated
- Transaction patterns match user profiles
- Recurring subscriptions have correct cadence (30 days ±3)
- Merchant names are realistic
- All Plaid fields populated
- No future-dated transactions

**Testing:**
- [ ] Test transaction generation for each user
- [ ] Verify subscription cadence (check date spacing)
- [ ] Verify transaction amounts are realistic
- [ ] Verify no future dates

---

#### Task 1.2.6: Implement Profile-Based Generation Orchestration
**File:** `generate_data.py`  
**Time:** 30-45 minutes  
**Description:** Create main function that generates all 5 users with their specific profiles.

**Subtasks:**
- [ ] Define user profiles (5 profiles as specified in PRD)
- [ ] Implement `generate_all_users()` function
- [ ] For each profile:
  - Generate user
  - Generate accounts
  - Generate credit card liability data
  - Generate transactions
- [ ] Add progress logging
- [ ] Handle errors gracefully (continue on error, log issue)
- [ ] Return summary of generated data

**Acceptance Criteria:**
- All 5 users generated successfully
- Each user has complete data (accounts, cards, transactions)
- Summary shows generation results
- Deterministic (same seed = same data)

**Testing:**
- [ ] Test full generation pipeline
- [ ] Verify all 5 users created
- [ ] Verify data relationships intact
- [ ] Test deterministic generation (regenerate with same seed)

---

#### Task 1.2.7: Data Validation Script
**File:** `validate_data.py` (optional, or add to `generate_data.py`)  
**Time:** 30-45 minutes  
**Description:** Create script to validate generated data quality.

**Subtasks:**
- [ ] Create validation function
- [ ] Check all 5 users exist
- [ ] Check each user has checking account
- [ ] Check credit cards match profile targets
- [ ] Check utilization matches targets (User 1: 75%, User 2: 70%/81%, etc.)
- [ ] Check subscription transactions exist (User 3, User 4)
- [ ] Check transaction date ranges (last 90 days)
- [ ] Check no future-dated transactions
- [ ] Check foreign key relationships intact
- [ ] Print validation report

**Acceptance Criteria:**
- Validation script runs successfully
- All checks pass
- Clear report showing data quality

**Testing:**
- [ ] Run validation on generated data
- [ ] Verify all checks pass
- [ ] Test with intentionally bad data (should fail checks)

---

### Phase 1.3: Signal Detection

#### Task 1.3.1: Set Up Signal Detection Module
**File:** `detect_signals.py`  
**Time:** 20-30 minutes  
**Description:** Create the signal detection module structure.

**Subtasks:**
- [ ] Create `detect_signals.py` file
- [ ] Import required libraries (sqlite3, json, datetime)
- [ ] Import database connection function
- [ ] Create helper functions for date calculations
- [ ] Create base structure for signal detection

**Acceptance Criteria:**
- File created with proper imports
- Helper functions ready
- Database connection working

---

#### Task 1.3.2: Implement Credit Utilization Signal Detection
**File:** `detect_signals.py`  
**Time:** 90-120 minutes  
**Description:** Detect all credit utilization signals for a user.

**Subtasks:**
- [ ] Implement `detect_credit_signals(user_id)` function
- [ ] Query all credit card accounts for user
- [ ] For each card:
  - Get balance and limit
  - Check `limit > 0` (avoid division by zero)
  - Calculate utilization: `(balance / limit) * 100`
  - Handle negative balances (credit balance)
  - Check overdue status from `credit_cards` table
- [ ] Calculate aggregate signals:
  - `credit_utilization_max` (highest utilization)
  - `credit_utilization_avg` (average utilization)
  - `credit_card_count` (number of cards)
  - `credit_overdue` (boolean: any card overdue)
  - `credit_utilization_flag_30` (any card ≥30%)
  - `credit_utilization_flag_50` (any card ≥50%)
  - `credit_utilization_flag_80` (any card ≥80%)
- [ ] Calculate `credit_interest_charges` (if detectable from data)
- [ ] Create metadata JSON with card details
- [ ] Store each signal using `store_signal()` function
- [ ] Handle edge cases:
  - User with no credit cards → Skip gracefully
  - Zero credit limit → Skip utilization calculation
  - Missing balance data → Use 0 as fallback

**Acceptance Criteria:**
- All 8 credit signals detected and stored
- Utilization calculated correctly
- Flags set correctly (30%, 50%, 80%)
- Edge cases handled without errors
- Metadata contains useful debugging info

**Testing:**
- [ ] Test with User 1 (should detect 75% utilization)
- [ ] Test with User 2 (should detect 70% and 81%)
- [ ] Test with User 5 (should detect 15% utilization)
- [ ] Test edge case: user with no credit cards
- [ ] Test edge case: zero credit limit
- [ ] Verify flag values match expected

---

#### Task 1.3.3: Implement Subscription Pattern Detection
**File:** `detect_signals.py`  
**Time:** 120-150 minutes  
**Description:** Detect recurring subscription patterns from transactions.

**Subtasks:**
- [ ] Implement `detect_subscription_signals(user_id)` function
- [ ] Query all transactions for user in last 90 days
- [ ] Group transactions by merchant name (case-insensitive)
- [ ] For each merchant with ≥3 transactions:
  - Get all transaction amounts
  - Check amount similarity: `is_similar_amount(amounts, tolerance=1.0)`
    - All amounts within ±$1 of each other
  - Get all transaction dates
  - Check date spacing: `is_monthly_cadence(dates, days_range=(27, 33))`
    - Check if dates are approximately 30 days apart (±3 days)
    - Verify at least 3 occurrences
- [ ] For matched subscriptions:
  - Extract merchant name
  - Extract recurring amount
  - Count occurrences
- [ ] Calculate aggregate signals:
  - `subscription_count` (number of recurring merchants)
  - `subscription_monthly_spend` (sum of monthly recurring amounts)
  - `subscription_merchants` (JSON array of merchant names)
  - `subscription_share` (recurring spend / total spend in 30-day window)
- [ ] Calculate total spend in last 30 days
- [ ] Create metadata JSON with subscription details
- [ ] Store each signal using `store_signal()` function
- [ ] Handle edge cases:
  - User with no transactions → Skip gracefully
  - Merchant with <3 occurrences → Not considered recurring
  - Amounts vary by >$1 → Not considered recurring
  - Date spacing not monthly → Not considered recurring
  - Missing merchant names → Skip or use generic label

**Acceptance Criteria:**
- Subscription patterns detected correctly
- All 4 subscription signals stored
- User 3: Detects Netflix, Spotify, Gym, Amazon Prime
- User 4: Detects 5+ small subscriptions
- Other users: Few or no subscriptions detected
- Edge cases handled without errors

**Testing:**
- [ ] Test with User 3 (should detect 4 subscriptions)
- [ ] Test with User 4 (should detect 5+ subscriptions)
- [ ] Test with User 5 (should detect few/no subscriptions)
- [ ] Test edge case: user with no transactions
- [ ] Test edge case: merchant with only 2 occurrences (should not detect)
- [ ] Test edge case: amounts vary by $2 (should not detect)
- [ ] Test edge case: dates not monthly (should not detect)
- [ ] Verify subscription_share calculation

---

#### Task 1.3.4: Implement Signal Storage Helper
**File:** `detect_signals.py`  
**Time:** 20-30 minutes  
**Description:** Create helper function to store signals in database.

**Subtasks:**
- [ ] Implement `store_signal(user_id, signal_type, value, metadata, window='30d')` function
- [ ] Convert metadata dict to JSON string
- [ ] Insert signal into `signals` table
- [ ] Handle database errors gracefully
- [ ] Return signal ID

**Acceptance Criteria:**
- Signal stored successfully
- Metadata properly JSON-encoded
- Database errors handled gracefully

**Testing:**
- [ ] Test storing a signal
- [ ] Test with invalid metadata (should handle gracefully)
- [ ] Verify signal appears in database

---

#### Task 1.3.5: Implement Signal Detection Orchestration
**File:** `detect_signals.py`  
**Time:** 20-30 minutes  
**Description:** Create main function that runs all signal detection for a user.

**Subtasks:**
- [ ] Implement `detect_all_signals(user_id)` function
- [ ] Call `detect_credit_signals(user_id)`
- [ ] Call `detect_subscription_signals(user_id)`
- [ ] Add error handling (continue on error, log issue)
- [ ] Return summary of detected signals
- [ ] Create `detect_signals_for_all_users()` function
- [ ] Loop through all users and run detection
- [ ] Add progress logging

**Acceptance Criteria:**
- All signals detected for user
- Function runs without errors
- Summary shows detection results
- All users processed

**Testing:**
- [ ] Test signal detection for single user
- [ ] Test signal detection for all users
- [ ] Verify all signals stored in database

---

### Phase 1.4: Testing & Validation

#### Task 1.4.1: Create Unit Tests for Database
**File:** `test_database.py`  
**Time:** 30-45 minutes  
**Description:** Write unit tests for database schema and operations.

**Subtasks:**
- [ ] Create `test_database.py` file
- [ ] Test table creation
- [ ] Test foreign key constraints (attempt invalid insert)
- [ ] Test index creation (verify indexes exist)
- [ ] Test schema validation function
- [ ] Use pytest framework

**Acceptance Criteria:**
- At least 3 tests passing
- Tests cover critical functionality
- Tests are clear and maintainable

---

#### Task 1.4.2: Create Unit Tests for Signal Detection
**File:** `test_signals.py`  
**Time:** 45-60 minutes  
**Description:** Write unit tests for signal detection logic.

**Subtasks:**
- [ ] Create `test_signals.py` file
- [ ] Test credit utilization calculation:
  - Test with known values (balance=$3750, limit=$5000 → 75%)
  - Test division by zero protection (limit=0)
  - Test negative balance (credit balance)
- [ ] Test subscription pattern matching:
  - Test with known subscription pattern (3 transactions, same amount, 30 days apart)
  - Test with non-recurring pattern (varying amounts)
  - Test with insufficient occurrences (<3)
  - Test with irregular date spacing
- [ ] Test edge cases (no credit cards, no transactions)
- [ ] Use pytest framework

**Acceptance Criteria:**
- Tests cover critical calculations
- Edge cases tested
- Tests are clear and maintainable

---

#### Task 1.4.3: Integration Testing
**File:** `test_integration.py` (optional, or add to existing test files)  
**Time:** 30-45 minutes  
**Description:** Test full pipeline from data generation to signal detection.

**Subtasks:**
- [ ] Create integration test
- [ ] Generate test user with known profile
- [ ] Run signal detection
- [ ] Verify signals match expected values
- [ ] Verify data relationships intact
- [ ] Clean up test data after test

**Acceptance Criteria:**
- Full pipeline works end-to-end
- Signals match expected values
- No data corruption

---

#### Task 1.4.4: Manual Validation
**Time:** 30-45 minutes  
**Description:** Manually validate generated data and signals.

**Subtasks:**
- [ ] Review generated data for all 5 users
- [ ] Verify credit utilization matches targets:
  - User 1: 75%
  - User 2: 70% and 81%
  - User 5: 15%
- [ ] Verify subscriptions detected:
  - User 3: Netflix, Spotify, Gym, Amazon Prime
  - User 4: 5+ small subscriptions
- [ ] Check data quality (realistic merchant names, amounts, dates)
- [ ] Verify no errors in database
- [ ] Document any issues found

**Acceptance Criteria:**
- All manual checks pass
- Data looks realistic
- Signals are accurate
- Issues documented

---

### Phase 1.5: Documentation & Cleanup

#### Task 1.5.1: Code Documentation
**Time:** 30-45 minutes  
**Description:** Add comprehensive docstrings and comments to all code.

**Subtasks:**
- [ ] Add docstrings to all functions
- [ ] Add inline comments for complex logic
- [ ] Document function parameters and return values
- [ ] Document edge cases handled
- [ ] Document known limitations

**Acceptance Criteria:**
- All functions have docstrings
- Complex logic is commented
- Code is maintainable

---

#### Task 1.5.2: Create README for Phase 1
**File:** `README_Phase1.md` (optional)  
**Time:** 20-30 minutes  
**Description:** Document how to run Phase 1 components.

**Subtasks:**
- [ ] Document setup instructions
- [ ] Document how to generate data
- [ ] Document how to run signal detection
- [ ] Document how to run tests
- [ ] Document known limitations
- [ ] Document next steps (Phase 2)

**Acceptance Criteria:**
- Clear instructions for running Phase 1
- Known limitations documented
- Next steps clear

---

## Task Summary

**Total Tasks:** 25 main tasks  
**Estimated Time:** 10-14 hours

**Breakdown:**
- Database Setup: 45-65 minutes
- Data Generation: 4-5.5 hours
- Signal Detection: 3.5-5 hours
- Testing: 2-3 hours
- Documentation: 50-75 minutes

**Key Deliverables:**
1. `database.py` - Database schema and connection
2. `generate_data.py` - Synthetic data generator
3. `detect_signals.py` - Signal detection engine
4. `spendsense.db` - SQLite database with data
5. Test files - Unit and integration tests
6. Documentation - Code comments and README

---

## Next Steps After Phase 1

Once Phase 1 is complete, Phase 2 will use:
- `signals` table for persona assignment
- User data for recommendation generation
- Credit card data for rationale generation

Ensure all Phase 1 deliverables are working before moving to Phase 2.

