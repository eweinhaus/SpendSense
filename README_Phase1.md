# Phase 1: Data Pipeline - Documentation

## Overview

Phase 1 establishes the foundational data layer for SpendSense MVP. This phase includes:
1. **Database Setup:** SQLite database with Plaid-compatible schema
2. **Synthetic Data Generation:** 5 diverse user profiles with realistic financial data
3. **Signal Detection:** Credit utilization and subscription pattern detection

## Setup Instructions

### Prerequisites
- Python 3.10+ (tested with Python 3.9.6)
- pip package manager

### Installation

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

Required packages:
- `faker>=19.0.0` - For synthetic data generation
- `pytest>=7.4.0` - For running tests

### Database Initialization

Initialize the database schema:
```bash
python3 database.py
```

This will:
- Create `spendsense.db` SQLite database file
- Create all required tables (users, accounts, transactions, credit_cards, signals)
- Create indexes for performance
- Validate schema matches PRD specification

### Data Generation

Generate synthetic data for 5 demo users:
```bash
python3 generate_data.py
```

This will:
- Generate 5 users with diverse financial profiles
- Create checking and credit card accounts
- Generate 90 days of transaction history
- Create credit card liability data
- Output generation summary

**User Profiles:**
- **User 1:** High Utilization - Single Card (75% utilization)
- **User 2:** High Utilization - Multiple Cards (70%, 81% utilization, one overdue)
- **User 3:** Subscription-Heavy - Major Services (Netflix, Spotify, Gym, Amazon Prime)
- **User 4:** Subscription-Heavy - Many Small Services (5+ small subscriptions)
- **User 5:** Neutral/Healthy (15% utilization, few subscriptions)

### Signal Detection

Run signal detection on all users:
```bash
python3 detect_signals.py
```

This will:
- Detect credit utilization signals for all users with credit cards
- Detect subscription patterns from transaction history
- Store all signals in the database
- Output detection summary

**Credit Signals Detected (8 per user):**
- `credit_utilization_max` - Highest utilization across all cards
- `credit_utilization_avg` - Average utilization
- `credit_card_count` - Number of credit cards
- `credit_interest_charges` - Estimated monthly interest
- `credit_overdue` - Boolean: any card overdue
- `credit_utilization_flag_30` - Boolean: any card ≥30%
- `credit_utilization_flag_50` - Boolean: any card ≥50%
- `credit_utilization_flag_80` - Boolean: any card ≥80%

**Subscription Signals Detected (4 per user):**
- `subscription_count` - Number of recurring merchants
- `subscription_monthly_spend` - Sum of monthly recurring amounts
- `subscription_merchants` - JSON array of merchant names
- `subscription_share` - Subscription spend / total spend (30-day window)

## Testing

Run all tests:
```bash
python3 -m pytest test_database.py test_signals.py -v
```

**Test Coverage:**
- Database schema validation
- Foreign key constraints
- Index creation
- Credit utilization calculation
- Subscription pattern matching
- Edge cases (zero limits, no transactions, no credit cards)

**Test Results:**
- All 10 tests passing ✅
- Edge cases handled gracefully
- Division by zero protection verified

## File Structure

```
.
├── database.py           # Database schema and connection
├── generate_data.py      # Synthetic data generator
├── detect_signals.py     # Signal detection engine
├── test_database.py       # Database tests
├── test_signals.py        # Signal detection tests
├── requirements.txt      # Python dependencies
├── README_Phase1.md      # This file
└── spendsense.db         # SQLite database (generated)
```

## Database Schema

### Tables

**users**
- `id` (INTEGER PRIMARY KEY)
- `name` (TEXT)
- `email` (TEXT UNIQUE)
- `consent_given` (BOOLEAN)
- `created_at` (TIMESTAMP)

**accounts** (Plaid-compatible)
- `id` (INTEGER PRIMARY KEY)
- `user_id` (INTEGER FOREIGN KEY)
- `account_id` (TEXT UNIQUE)
- `type` (TEXT) - 'depository', 'credit'
- `subtype` (TEXT) - 'checking', 'credit card'
- `current_balance` (REAL)
- `limit` (REAL) - For credit cards
- `iso_currency_code` (TEXT)
- `holder_category` (TEXT)

**transactions** (Plaid-compatible)
- `id` (INTEGER PRIMARY KEY)
- `account_id` (INTEGER FOREIGN KEY)
- `date` (DATE)
- `amount` (REAL)
- `merchant_name` (TEXT)
- `payment_channel` (TEXT)
- `personal_finance_category` (TEXT)
- `pending` (BOOLEAN)

**credit_cards**
- `id` (INTEGER PRIMARY KEY)
- `account_id` (INTEGER FOREIGN KEY UNIQUE)
- `apr` (REAL)
- `minimum_payment_amount` (REAL)
- `is_overdue` (BOOLEAN)
- `next_payment_due_date` (DATE)
- `last_statement_balance` (REAL)

**signals**
- `id` (INTEGER PRIMARY KEY)
- `user_id` (INTEGER FOREIGN KEY)
- `signal_type` (TEXT)
- `value` (REAL)
- `metadata` (TEXT JSON)
- `window` (TEXT) - '30d' or '180d'
- `detected_at` (TIMESTAMP)

## Known Limitations

1. **Subscription Detection:**
   - Requires exactly 3+ occurrences with monthly cadence (27-33 days)
   - Amounts must be within ±$1 tolerance
   - May miss weekly subscriptions or irregular patterns
   - Some subscriptions may not be detected if date spacing is off due to random offsets

2. **Data Generation:**
   - Deterministic with seed=42, but random offsets in dates may cause slight variations
   - Transaction patterns are simplified (real-world patterns are more complex)
   - Credit card interest charges are estimated (not actual transaction-based)

3. **Signal Detection:**
   - Only 30-day window analysis (not 180-day)
   - Credit utilization calculated from current balance (not historical)
   - No income stability or savings growth detection

## Next Steps (Phase 2)

Phase 1 outputs required for Phase 2:
- ✅ Database with users, accounts, transactions, credit_cards
- ✅ Signals table populated with detected signals
- ✅ Validated data quality

Phase 2 will use:
- `signals` table for persona assignment
- User data for recommendation generation
- Credit card data for rationale generation

## Troubleshooting

### Database file not found
- Run `python3 database.py` to initialize the database

### Import errors
- Ensure all dependencies are installed: `pip install -r requirements.txt`

### Subscription detection not finding subscriptions
- Check that subscription transactions have exactly 3+ occurrences
- Verify dates are within 90-day window
- Check that amounts are within ±$1 tolerance
- Ensure date spacing is 27-33 days between occurrences

### Tests failing
- Ensure database is initialized: `python3 database.py`
- Check that test database files are not locked (delete `test_*.db` files if needed)

## Validation

After generating data and running signal detection, verify:

1. **Database:**
   ```bash
   python3 database.py  # Should show "Schema validation passed"
   ```

2. **Data Quality:**
   - Check that all 5 users exist
   - Verify credit utilization matches targets (User 1: 75%, User 2: 70%/81%, User 5: 15%)
   - Verify subscriptions detected (User 3: 3-4 subscriptions, User 4: 5+ subscriptions)

3. **Signals:**
   - Check signals table has 60+ signals (12 per user: 8 credit + 4 subscription)
   - Verify signal values are reasonable

## Success Criteria

✅ **All criteria met:**
- [x] 5 users generated with diverse profiles
- [x] All Plaid-compatible fields populated
- [x] 90 days of realistic transaction patterns
- [x] Credit utilization calculated correctly
- [x] Subscription patterns detected
- [x] All signals stored in database
- [x] Edge cases handled gracefully
- [x] Tests passing (10/10)
- [x] Schema validation passing
- [x] Deterministic generation (seed-based)

## Notes

- Database uses SQLite for simplicity (local file, no external dependencies)
- All data is synthetic (no real PII)
- Seed-based generation ensures reproducibility
- Foreign keys are enforced for data integrity
- Indexes improve query performance


