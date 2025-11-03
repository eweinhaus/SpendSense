# SpendSense MVP - Product Requirements Document

## Overview

SpendSense MVP is a proof-of-concept system that analyzes transaction data to detect behavioral patterns, assign user personas, and deliver personalized financial education recommendations with clear rationales.

## Goals

- Demonstrate core signal detection capabilities
- Show persona assignment logic
- Generate personalized recommendations with data-driven rationales
- Build a functional operator view for demo purposes
- Create a solid foundation for full product development

## Non-Goals (Deferred to Full Release)

- Advanced AI/LLM integration for recommendations
- Multiple time windows (180-day analysis)
- Income stability detection
- All 5 personas
- Partner offer integration
- Advanced evaluation harness
- Production-ready deployment

## Target Users

**Primary:** Hiring managers and interviewers evaluating technical capabilities

**Secondary:** Future end-users (bank customers) and operators (bank staff)

## Core Features

### 1. Synthetic Data Generation

**Scope:**
- Generate 5 demo users with realistic financial profiles
- Include accounts (checking, savings, credit cards)
- Generate transactions with realistic patterns
- Include credit card liability data

**User Profiles:**
- User 1: High credit utilization (75%+), interest charges
- User 2: Multiple cards, one overdue
- User 3: Many subscriptions (Netflix, Spotify, gym, etc.)
- User 4: Heavy subscription spend (many small recurring charges)
- User 5: Neutral/healthy financial behavior (control case)

**Data Structure (Plaid-Compatible):**
- Users: id, name, email, consent_given, created_at
- Accounts: id, user_id, type, subtype, balance, available_balance, current_balance, limit, iso_currency_code, holder_category
- Transactions: id, account_id, date, amount, merchant_name, merchant_entity_id, payment_channel, personal_finance_category, pending
- Credit cards: account_id, apr, minimum_payment_amount, last_payment_amount, is_overdue, next_payment_due_date, last_statement_balance

**Success Criteria:**
- 5 users with diverse financial situations
- Realistic transaction patterns
- Data stored in SQLite

### 2. Behavioral Signal Detection

**Signals to Detect:**

**Credit Utilization:**
- Calculate per-card utilization (balance / limit) for each credit card
- Flag thresholds: ≥30%, ≥50%, ≥80%
- Track highest utilization card for user
- Detect interest charges (if present in transaction data)
- Identify overdue status (from credit_cards table)
- Simplified: Skip minimum-payment-only detection for MVP (requires transaction history analysis)

**Subscriptions:**
- Identify recurring merchants: ≥3 occurrences in 90-day window
- Pattern matching criteria:
  - Same merchant name (exact match)
  - Similar amount (±$1 tolerance)
  - Monthly cadence: 30 days ±3 days between occurrences
- Calculate monthly recurring spend (sum of recurring transaction amounts)
- Calculate subscription share of total spend (recurring spend / total spend in 30-day window)

**Time Window:**
- 30-day window only for MVP
- Skip 180-day analysis

**Success Criteria:**
- Accurate detection of credit utilization for all users
- Correct identification of recurring subscriptions
- Signals stored in database with clear values

### 3. Persona Assignment

**Personas (2 for MVP):**

**Persona 1: High Utilization**
- Criteria: Any card utilization ≥50% OR interest charges > 0 OR is_overdue = true
- Priority: Highest (checked first)
- Focus: Reduce utilization, payment planning, autopay education

**Persona 2: Subscription-Heavy**
- Criteria: ≥3 recurring merchants AND (monthly recurring spend ≥$50 OR subscription share ≥10%)
- Priority: Secondary
- Focus: Subscription audit, cancellation tips, bill alerts

**Assignment Logic:**
- Check High Utilization first (higher priority)
- If no match, check Subscription-Heavy
- If no match, assign "Neutral" or no persona
- One persona per user

**Success Criteria:**
- Clear assignment logic with documented priority
- All 5 users assigned appropriate personas
- Personas stored in database

### 4. Recommendation Engine

**Content:**
- 2-3 educational recommendations per user
- Mapped to assigned persona
- Hardcoded content templates (no AI for MVP)

**Rationale Generation:**
- Data-driven explanations citing specific numbers
- Format: "We noticed your [card_name] ending in [last_4] is at [utilization]% utilization ($[balance] of $[limit] limit)..."
- Plain language, no jargon
- Fallback templates if data is missing
- Include disclaimer on every recommendation: "This is educational content, not financial advice. Consult a licensed advisor for personalized guidance."

**Decision Traces:**
- Store decision trace for each recommendation
- Record: user_id, recommendation_id, reasoning steps, data cited
- Format: "Recommended because: [signal] detected → [persona] assigned → [content] matched"
- Display in operator view for auditability

**Content Templates:**

**High Utilization:**
- "Reduce Credit Card Utilization" - strategies to pay down debt
- "Understanding Credit Scores" - how utilization affects credit
- "Set Up Autopay" - avoid missed payments

**Subscription-Heavy:**
- "Audit Your Subscriptions" - checklist for reviewing recurring charges
- "Negotiation Tips" - how to reduce subscription costs
- "Set Up Bill Alerts" - track recurring charges

**Success Criteria:**
- 2-3 recommendations per user
- All recommendations include specific rationales
- Rationales cite actual user data
- Content mapped correctly to personas

### 5. Web Interface (Operator View)

**Technology:**
- FastAPI backend
- Jinja2 server-rendered templates
- Simple CSS styling (Bootstrap or custom)

**Pages:**

**Dashboard (/):**
- List all 5 users
- Show persona badges
- Quick stats (utilization %, subscription count)
- Links to user detail pages

**User Detail (/user/{id}):**
- User information
- Detected signals with values
- Assigned persona with criteria explanation
- Recommendations with rationales
- Decision traces (why recommendations were made)
- Consent toggle checkbox
- Disclaimer displayed on all recommendations

**API Endpoints:**
- `GET /` - Dashboard (HTML)
- `GET /user/{id}` - User detail (HTML)
- `POST /consent/{id}` - Toggle consent

**Success Criteria:**
- Clean, functional UI
- Easy navigation between users
- Clear display of signals and recommendations
- Working consent toggle

### 6. Guardrails (Basic)

**Consent Tracking:**
- Boolean flag per user
- Toggle via checkbox on user detail page
- Track consent status in database
- Display consent status clearly

**Eligibility Checks:**
- Don't recommend products user already has
- Example: Don't recommend HYSA if user has savings account
- Simple rule-based filtering

**Tone Guidelines:**
- No shaming language
- Empowering, educational tone
- Neutral, supportive phrasing

**Success Criteria:**
- Consent tracked per user
- Basic eligibility filtering works
- All content uses appropriate tone

## Technical Architecture

### Stack

**Backend:**
- Python 3.10+
- FastAPI (web framework)
- SQLite (database)
- Jinja2 (templating)

**Frontend:**
- Server-rendered HTML
- Bootstrap or simple CSS
- Minimal JavaScript

**Storage:**
- SQLite database (single file)
- JSON for content templates

### File Structure

```
spendsense/
├── app.py                    # Main FastAPI app + core logic
├── database.py               # SQLite setup & models
├── templates/
│   ├── dashboard.html        # User list
│   └── user_detail.html      # User profile
├── static/
│   └── style.css            # Styling
├── data/
│   └── spendsense.db        # SQLite database
├── requirements.txt
├── README.md
└── docs/
    └── decisions.md
```

### Database Schema

```sql
-- Core user data
users (id, name, email, consent_given, created_at)

-- Account information (Plaid-compatible)
accounts (
    id, user_id, account_id, 
    type, subtype, 
    available_balance, current_balance, limit,
    iso_currency_code, holder_category
)

-- Transaction data (Plaid-compatible)
transactions (
    id, account_id, date, amount,
    merchant_name, merchant_entity_id,
    payment_channel, personal_finance_category,
    pending
)

-- Credit card liability data
credit_cards (
    id, account_id,
    apr, minimum_payment_amount, last_payment_amount,
    is_overdue, next_payment_due_date, last_statement_balance
)

-- Detected behavioral signals
signals (
    id, user_id, signal_type, value, window, detected_at
)

-- Persona assignments
personas (
    user_id, persona_type, assigned_at, criteria_matched
)

-- Recommendations with rationales
recommendations (
    id, user_id, title, content, rationale, 
    persona_matched, created_at
)

-- Decision traces for auditability
decision_traces (
    id, user_id, recommendation_id, 
    step, reasoning, data_cited, created_at
)
```

## Development Sub-Phases

*Note: These sub-phases are organized into 3 main phases. See phase-specific PRDs for detailed implementation:*
- *Phase 1 (Data Pipeline): Sub-phases 1-2*
- *Phase 2 (Intelligence Layer): Sub-phases 3-4*
- *Phase 3 (Interface & Guardrails): Sub-phases 5-6*

### Sub-Phase 1: Data Foundation
- Set up SQLite database
- Create schema
- Generate 5 demo users with realistic data
- Validate data quality

### Sub-Phase 2: Signal Detection
- Implement credit utilization calculation
- Implement subscription detection
- Store signals in database
- Test on all 5 users

### Sub-Phase 3: Persona Assignment
- Implement High Utilization logic
- Implement Subscription-Heavy logic
- Handle priority and edge cases
- Assign personas to all users

### Sub-Phase 4: Recommendations
- Create content templates
- Implement rationale generation
- Map recommendations to personas
- Generate for all users

### Sub-Phase 5: Web Interface
- Set up FastAPI app
- Create dashboard page
- Create user detail page
- Add basic styling

### Sub-Phase 6: Guardrails & Polish
- Add consent tracking
- Implement eligibility checks
- Error handling
- Demo preparation

## Success Metrics

| Metric | Target |
|--------|--------|
| Users with assigned persona | 5/5 (100%) |
| Users with ≥3 detected behaviors | 5/5 (100%) |
| Users with ≥2 recommendations | 5/5 (100%) |
| Recommendations with rationales | 100% |
| Recommendations with decision traces | 100% |
| Signal detection accuracy | 100% (manual verification) |
| Page load time | <2 seconds |
| Code coverage (tests) | ≥5 key tests |

## Demo Strategy

### Demo Script (5-7 minutes)

**Setup (30 seconds):**
1. Start FastAPI server: `uvicorn app:app --reload`
2. Open browser to `http://localhost:8000`
3. Verify database is populated with 5 users

**Demo Flow:**

**1. Dashboard Overview (1 minute)**
- "Here are 5 synthetic users with diverse financial profiles"
- Point out persona badges showing different personas
- Highlight quick stats (utilization %, subscription counts)
- "Each user has been analyzed for behavioral signals"

**2. High Utilization User (2 minutes)**
- Click on User 1 (High Utilization)
- Show credit utilization signals:
  - "We detected 75% utilization on their Visa card"
  - "Interest charges of $87/month"
  - Point out specific data: balance, limit, utilization %
- Show persona assignment:
  - "This matches our High Utilization persona criteria"
  - Explain priority logic
- Show recommendations:
  - Read one rationale aloud: "We noticed your Visa ending in 4523 is at 75% utilization..."
  - Point out data-driven nature
  - Show decision trace explaining why this recommendation was made

**3. Subscription-Heavy User (2 minutes)**
- Navigate back, click User 3 (Subscription-Heavy)
- Show subscription signals:
  - "We detected 4 recurring merchants: Netflix, Spotify, Gym, etc."
  - "Monthly recurring spend of $85"
  - "Subscription share of 12% of total spend"
- Explain pattern matching:
  - "Same merchant, similar amount, monthly cadence"
- Show recommendations with subscription-focused content

**4. Consent & Guardrails (1 minute)**
- Toggle consent checkbox
- Explain: "Consent is tracked and required for recommendations"
- Show eligibility checks: "We don't recommend products they already have"

**5. Architecture Discussion (1-2 minutes)**
- "Modular, extensible architecture"
- "Clear, explainable logic - no black box"
- "Data-driven rationales citing specific numbers"
- "Compliance-aware with consent and eligibility guardrails"
- "Ready for AI integration when needed"
- "Scalable foundation for 50-100 users"

**Talking Points:**
- Transparency over sophistication
- User control over automation
- Education over sales
- Every recommendation has a clear, traceable rationale

## Known Limitations (MVP)

- Only 5 users (not 50-100)
- Only 2 personas (not 5)
- Hardcoded recommendations (no AI)
- 30-day window only (not 180-day)
- No income stability detection
- No savings growth analysis
- No partner offers
- No evaluation harness
- Simple subscription detection (may miss edge cases)
- No user authentication
- No production deployment

## Future Enhancements (Post-MVP)

See `planning/post_mvp_roadmap.md` for full list of features to implement for final submission.

## Compliance & Disclaimers

**Disclaimer on all recommendations:**
> "This is educational content, not financial advice. Consult a licensed advisor for personalized guidance."

**Data Privacy:**
- All data is synthetic (no real PII)
- Consent tracked and respected
- Clear data usage explanation

## Error Handling & Edge Cases

### Edge Cases to Handle

**Data Edge Cases:**
- User with no transactions → Show "Insufficient data" message, skip persona assignment
- User with no credit cards → Skip credit utilization signals, use other signals only
- Zero credit limit → Skip utilization calculation (division by zero protection)
- Missing merchant names → Use generic "Recurring Charge" label or merchant_entity_id
- Future-dated transactions → Filter out or flag for review
- Negative balances → Handle gracefully (show as negative, don't break calculations)

**Calculation Edge Cases:**
- Division by zero: Always check `limit > 0` before calculating utilization
- Empty time windows: If no transactions in 30-day window, show "No data available"
- Missing account data: Use fallback values or skip dependent signals

**Persona Assignment Edge Cases:**
- User matches multiple personas → Assign highest priority persona
- User matches no personas → Assign "Neutral" or show "No persona assigned"
- Missing required signals → Skip persona assignment, show "Insufficient data"

**Rationale Generation Edge Cases:**
- Missing card name → Use "credit card" as fallback
- Missing last 4 digits → Use "XXXX" or skip
- Missing balance/limit → Use generic language: "high utilization"
- Missing merchant names → Use "subscription services" as generic term

### Graceful Degradation Strategy

1. **Rationale Generation:**
   - Primary: Use specific data from user's account
   - Fallback: Use generic templates if data missing
   - Always include disclaimer regardless of data completeness

2. **Persona Assignment:**
   - Primary: Assign based on detected signals
   - Fallback: Assign "Neutral" if no criteria match
   - Never assign persona if required signals are missing

3. **Recommendations:**
   - Primary: Show persona-specific recommendations
   - Fallback: Show generic financial education content
   - Always show at least 1 recommendation per user

4. **Error Messages:**
   - User-friendly language: "We need more transaction data to provide personalized recommendations"
   - Technical details logged but not shown to users
   - Clear calls to action when possible

## Testing Strategy

### Test Coverage Requirements

**Critical Path Tests (Minimum 5):**

1. **Signal Detection Tests:**
   - Test credit utilization calculation with various balances/limits
   - Test subscription detection with known recurring patterns
   - Test edge cases: zero limit, missing data, no transactions

2. **Persona Assignment Tests:**
   - Test High Utilization criteria matching
   - Test Subscription-Heavy criteria matching
   - Test priority logic (multiple matches)
   - Test no-match scenario

3. **Rationale Generation Tests:**
   - Test with complete data
   - Test with missing data (fallbacks)
   - Test template formatting

4. **API Endpoint Tests:**
   - Test dashboard endpoint returns all users
   - Test user detail endpoint returns correct data
   - Test consent toggle updates database

5. **Data Validation Tests:**
   - Test synthetic data generation produces valid data
   - Test database schema constraints
   - Test data relationships (foreign keys)

### Test Approach

- **Unit Tests:** Test individual functions (signal detection, persona logic)
- **Integration Tests:** Test full pipeline (data → signals → personas → recommendations)
- **Manual Testing:** Verify UI displays correctly, check edge cases
- **Deterministic Testing:** Use seeds for random data generation

## Documentation Requirements

- README with setup instructions (one-command setup)
- Code comments for key logic (signal detection, persona assignment)
- Decision log explaining technical choices (why SQLite, why FastAPI, etc.)
- Known limitations documented
- Demo script prepared (see Demo Strategy section)
- API documentation (even if simple, document endpoints)
- Schema documentation with field descriptions

## Definition of Done

MVP is complete when:
- [ ] 5 users generated with realistic data (Plaid-compatible structure)
- [ ] All required Plaid fields included in schema
- [ ] Credit utilization detected correctly for all users
- [ ] Subscriptions detected correctly for all users (90-day pattern matching)
- [ ] Personas assigned correctly to all users with clear priority logic
- [ ] 2-3 recommendations per user with data-driven rationales
- [ ] Decision traces stored for all recommendations
- [ ] Web interface displays all data clearly
- [ ] Consent tracking works
- [ ] Basic eligibility checks implemented
- [ ] Error handling implemented for edge cases
- [ ] ≥5 tests passing (critical path coverage)
- [ ] README and documentation complete
- [ ] Demo script prepared and tested
- [ ] Code is clean and commented
- [ ] Known limitations documented
- [ ] Disclaimer displayed on all recommendations

