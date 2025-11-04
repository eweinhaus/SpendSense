# System Patterns

## Architecture Overview

SpendSense follows a modular, layered architecture designed for explainability and auditability.

### High-Level Architecture

```
┌─────────────────────────────────────────┐
│         Operator View (FastAPI)          │
│      Server-rendered HTML templates       │
└────────────────┬──────────────────────────┘
                 │
┌────────────────┴──────────────────────────┐
│         Business Logic Layer              │
│  ┌──────────┐  ┌──────────┐  ┌─────────┐│
│  │  Ingest  │→ │ Features  │→ │Personas ││
│  └──────────┘  └──────────┘  └─────────┘│
│       │              │             │      │
│       └──────────────┴─────────────┘     │
│                    │                       │
│  ┌─────────────────┴──────────────────┐  │
│  │     Recommendation Engine          │  │
│  │  - Content Templates               │  │
│  │  - Rationale Generation            │  │
│  │  - Decision Traces                 │  │
│  └─────────────────┬──────────────────┘  │
│                    │                       │
│  ┌─────────────────┴──────────────────┐  │
│  │     Guardrails System              │  │
│  │  - Consent Tracking                │  │
│  │  - Eligibility Checks              │  │
│  └─────────────────┬──────────────────┘  │
└────────────────────┼──────────────────────┘
                     │
┌────────────────────┴──────────────────────┐
│         Data Layer (SQLite)              │
│  - users, accounts, transactions        │
│  - credit_cards, liabilities, signals   │
│  - personas, recommendations, traces    │
└─────────────────────────────────────────┘
```

## Design Patterns

### 1. Modular Pipeline Pattern

**Purpose:** Clear separation of concerns, testable components

**Structure:**
```
Data Generation → Signal Detection → Persona Assignment → Recommendation Generation → Guardrails → Display
```

**Benefits:**
- Each phase can be tested independently
- Easy to add new signal types or personas
- Clear data flow

### 2. Template-Based Recommendations

**Purpose:** Consistency, easy iteration, no AI dependency for MVP

**Structure:**
- Content templates stored as JSON or Python dicts
- Persona-to-template mapping
- Rationale generation uses string formatting with data citations

**Benefits:**
- No external API dependencies for MVP
- Easy to modify content
- Predictable output

### 3. Decision Trace Pattern

**Purpose:** Full auditability, explainability

**Structure:**
```
Step 1: Signal Detected → [data]
Step 2: Persona Assigned → [criteria]
Step 3: Recommendation Selected → [reason]
Step 4: Rationale Generated → [data cited]
```

**Benefits:**
- Every recommendation is traceable
- Compliance and oversight enabled
- Debugging made easier

### 3a. AI Integration Pattern (Phase 6B)

**Purpose:** Personalized content generation with graceful fallback

**Structure:**
```
1. Check cache (persona + signal combination)
2. If cache miss:
   - Build prompt with user context
   - Call OpenAI API
   - Validate tone on response
   - Cache valid responses
3. If API fails or tone violation:
   - Fallback to templates
4. Always ensure content quality
```

**Benefits:**
- Personalized content when available
- Graceful degradation (works without API key)
- Cost control through aggressive caching
- Quality assurance through tone validation
- Backward compatible (templates always work)

### 3b. Partner Offers Pattern (Phase 6B)

**Purpose:** Eligible partner offers with data-driven rationales

**Structure:**
```
1. Check offer eligibility (utilization, accounts, persona)
2. Use existing eligibility system for comprehensive checks
3. Generate rationale with specific user data
4. Select 1-3 most relevant offers
5. Display with disclaimers
```

**Benefits:**
- Reuses existing eligibility infrastructure
- Data-driven rationales increase relevance
- Clear disclaimers ensure transparency
- Flexible catalog (easy to add new offers)

### 4. Graceful Degradation Pattern

**Purpose:** Handle missing data without breaking

**Structure:**
- Primary: Use specific user data
- Fallback: Use generic templates if data missing
- Always: Include disclaimer

**Benefits:**
- System doesn't break on edge cases
- Still provides value even with incomplete data
- Better user experience

### 5. Consent Enforcement Pattern

**Purpose:** Compliance and user control

**Structure:**
```
User → Consent Check → Generate Recommendations → Display
              ↓
        No Consent → Block Generation → Show Banner
```

**Implementation:**
- `has_consent()` helper function checks consent status
- Recommendations blocked at generation time (not just display)
- API endpoints respect consent status
- UI shows clear consent requirement banner
- Automatic regeneration when consent granted
- Automatic cleanup when consent revoked

**Benefits:**
- Compliance with data protection requirements
- User control over recommendations
- Clean separation of concerns
- Prevents duplicate recommendations

## Data Flow Patterns

### Signal Detection Flow

```
1. Query transactions/accounts for user (for specified window)
2. Group by merchant (subscriptions) or calculate ratios (credit, savings, income)
3. Apply pattern matching rules (payroll detection, subscription patterns)
4. Store signals in database with metadata and window parameter
5. Repeat for both 30d and 180d windows (via detect_all_signals())
```

### Persona Assignment Flow

```
1. Query signals for user (all windows)
2. Check High Utilization criteria (highest priority)
3. If no match, check Variable Income Budgeter criteria
4. If no match, check Savings Builder criteria
5. If no match, check Financial Newcomer criteria
6. If no match, check Subscription-Heavy criteria
7. If no match, assign Neutral
8. Store persona with criteria explanation
```

### Recommendation Generation Flow (Phase 6B Updated)

```
1. Check user consent (if no consent, return empty list)
2. Get user persona
3. Try OpenAI generation (if API key available):
   - Build prompt with user context
   - Check cache first
   - Call OpenAI API
   - Validate tone on generated content
   - Fallback to templates if API fails or tone violations
4. If no AI content, use expanded content catalog (72 items):
   - Select from articles, calculators, checklists, templates
   - Prioritize by persona match and signal relevance
5. Generate rationale citing user data
6. Generate decision trace
7. Apply eligibility filters
8. Store recommendations
```

## Code Organization Patterns

### Current Structure (Phase 7 Complete)

```
spendsense/
├── database.py         # SQLite setup & schema (Phase 4: liabilities table)
├── generate_data.py     # Synthetic data generator (Phase 4: scaled to 75 users)
├── detect_signals.py   # Signal detection engine (Phase 5: savings, income, dual-window) ✅
├── personas.py         # Persona assignment (Phase 2, Phase 5: 3 new personas) ✅
├── recommendations.py  # Recommendation engine (Phase 2, Phase 4: consent, Phase 5: new templates, Phase 6B: AI integration, 72 items) ✅
├── content_generator.py # OpenAI API integration (Phase 6B: new) ✅
├── partner_offers.py   # Partner offers catalog (Phase 6B: new) ✅
├── rationales.py       # Rationale generation (Phase 2) ✅
├── traces.py           # Decision trace generation (Phase 2) ✅
├── eligibility.py      # Eligibility checks (Phase 3, Phase 4: consent, Phase 6: enhanced) ✅
├── tone_validator.py   # Tone validation (Phase 6: new) ✅
├── evaluation.py       # Evaluation harness (Phase 6: new) ✅
├── app.py              # FastAPI app (Phase 3, Phase 4: consent, Phase 5: dual-window signals, Phase 6B: partner offers, Phase 7: enhanced persona display) ✅
├── scripts/
│   ├── deploy_render.py      # Automated Render deployment script (Phase 6: new) ✅
│   └── test_operator_view.py # Manual testing automation script (Phase 7: new) ✅
├── templates/          # Jinja2 templates (Phase 3, Phase 4: consent, Phase 5: dual-window tabs, Phase 6: persona badges, Phase 6B: partner offers, Phase 7: enhanced decision traces) ✅
├── static/             # CSS/JS (Phase 3, Phase 4: auto-reload) ✅
├── tests/              # Test suite (90+ tests)
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_signals.py (Phase 5: updated for windows)
│   ├── test_personas.py
│   ├── test_recommendations.py (Phase 6B: AI integration, content catalog tests)
│   ├── test_integration.py (Phase 5: updated for windows)
│   ├── test_app.py           # Phase 3 ✅
│   ├── test_eligibility.py   # Phase 3, Phase 4, Phase 6: enhanced ✅
│   ├── test_tone.py          # Phase 6: new ✅
│   ├── test_evaluation.py    # Phase 6: new ✅
│   ├── test_content_generator.py # Phase 6B: new ✅
│   ├── test_partner_offers.py    # Phase 6B: new ✅
│   ├── test_phase4.py         # Phase 4 ✅
│   ├── test_phase5.py         # Phase 5 ✅
│   └── test_phase7.py         # Phase 7: new (13 tests) ✅
├── requirements.txt    # Python dependencies (Phase 6B: openai>=1.0.0)
├── pytest.ini         # Test configuration
├── spendsense.db       # SQLite database (79 users, 238 accounts, 10 liabilities)
└── [planning/, memory-bank/]  # Documentation
```

### Signal Types (Phase 6 Complete)

**Credit Signals:**
- `credit_utilization_max`, `credit_utilization_avg`, `credit_card_count`
- `credit_interest_charges`, `credit_overdue`
- `credit_utilization_flag_30`, `credit_utilization_flag_50`, `credit_utilization_flag_80`
- All stored with window parameter (30d/180d)

**Subscription Signals:**
- `subscription_count`, `subscription_monthly_spend`, `subscription_merchants`, `subscription_share`
- All stored with window parameter (30d/180d)

**Savings Signals (Phase 5):**
- `savings_net_inflow_30d` / `savings_net_inflow_180d`
- `savings_growth_rate_30d` / `savings_growth_rate_180d`
- `emergency_fund_coverage_30d` / `emergency_fund_coverage_180d`

**Income Signals (Phase 5):**
- `income_frequency` (stored in metadata, not value)
- `income_variability`
- `cash_flow_buffer_30d` / `cash_flow_buffer_180d`
- `median_pay_gap` (not window-specific)

### Persona System (Phase 6 Complete)

**Priority Order:**
1. High Utilization (highest priority)
2. Variable Income Budgeter
3. Savings Builder
4. Financial Newcomer
5. Subscription-Heavy
6. Neutral (fallback)

**Persona Detection:**
- Uses `get_signal_value()` helper to extract window-specific signals
- Prefers 30d window signals for persona assignment
- Falls back to 180d or base signal type if 30d not available

### Guardrails System (Phase 6 Complete)

**Enhanced Eligibility Checks:**
- Product catalog with eligibility rules (income, credit score, account exclusions)
- Income estimation from payroll transactions
- Credit score checks (placeholder, allows by default if not available)
- Comprehensive account exclusion checks
- Harmful product blacklist
- Eligibility failure logging

**Tone Validation:**
- Prohibited phrases detection (shaming language)
- Keyword-based validation (fast, simple)
- Violation logging for operator review
- Integrated into recommendation generation flow

**Evaluation Harness:**
- Coverage metrics (persona + ≥3 behaviors)
- Explainability metrics (rationales)
- Relevance metrics (persona-content fit)
- Latency metrics (generation time)
- Fairness metrics (distribution analysis)
- Automated report generation (JSON, CSV, Markdown)

### Target Structure (Phase 6 Complete)

```
spendsense/
├── database.py         # SQLite setup
├── generate_data.py    # Synthetic data generator
├── detect_signals.py   # Signal detection
├── personas.py         # Persona assignment (Phase 2)
├── recommendations.py  # Recommendation engine (Phase 2)
├── app.py              # Main FastAPI app (Phase 3)
├── templates/          # Jinja2 templates (Phase 3)
├── static/             # CSS/JS (Phase 3)
├── tests/              # Test suite
└── spendsense.db       # Database file
```

### Post-MVP Structure (Modular)

```
spendsense/
├── app/
│   ├── main.py         # FastAPI app
│   ├── ingest/         # Data generation
│   ├── features/       # Signal detection
│   ├── personas/       # Persona assignment
│   ├── recommend/     # Recommendation engine
│   ├── guardrails/     # Consent, eligibility
│   └── models/         # Database models
├── templates/
├── static/
└── data/
```

## Key Architectural Decisions

### 1. SQLite for MVP
**Decision:** Use SQLite instead of PostgreSQL/Firebase  
**Rationale:** Local, no external dependencies, simple setup, sufficient for MVP  
**Trade-off:** Not scalable, but acceptable for demo

### 2. Server-Rendered UI
**Decision:** Jinja2 templates instead of React  
**Rationale:** Faster to build, simpler deployment, no build step  
**Trade-off:** Less interactive, but sufficient for operator view

### 3. Hardcoded Recommendations (with Tone Validation)
**Decision:** Templates instead of AI for MVP, with tone validation in Phase 6  
**Rationale:** No external API dependencies, faster iteration, more predictable  
**Trade-off:** Less personalized, but can add AI later  
**Phase 6:** Added tone validation to ensure content quality, integrated into generation flow

### 4. Single Persona Assignment (Priority-Based)
**Decision:** One persona per user with priority logic (5 personas total)  
**Rationale:** Simpler logic, clearer for demo, priority ensures consistent assignment  
**Priority Order:** High Utilization → Variable Income → Savings Builder → Financial Newcomer → Subscription-Heavy → Neutral  
**Trade-off:** Users may match multiple personas, but priority handles this correctly

### 5. Dual-Window Analysis (Phase 5)
**Decision:** Implement both 30-day and 180-day windows  
**Rationale:** Provides short-term and long-term insights, matches full requirements  
**Trade-off:** 2x signal storage and computation, but provides comprehensive analysis  
**Status:** ✅ Implemented in Phase 5

### 6. Enhanced Guardrails (Phase 6)
**Decision:** Comprehensive eligibility checks and tone validation  
**Rationale:** Ensures appropriate recommendations, prevents harmful content  
**Trade-off:** Adds complexity, but critical for production readiness  
**Status:** ✅ Implemented in Phase 6

### 7. Evaluation Harness (Phase 6)
**Decision:** Comprehensive metrics system for system evaluation  
**Rationale:** Required for requirements compliance, enables quality assurance  
**Trade-off:** Adds overhead, but provides critical insights  
**Status:** ✅ Implemented in Phase 6

### 8. Automated Deployment (Phase 6)
**Decision:** Automated Render.com deployment via Python script using Render API  
**Rationale:** Reduces manual setup, enables programmatic deployment, faster iteration  
**Trade-off:** Requires API key management, but provides significant automation  
**Status:** ✅ Implemented in Phase 6 (scripts/deploy_render.py)
**Service Details:** 
- Service ID: srv-d44njmq4d50c73el4brg
- URL: https://spendsense-2e84.onrender.com
- Dashboard: https://dashboard.render.com/web/srv-d44njmq4d50c73el4brg

### 9. AI-Powered Recommendations (Phase 6B)
**Decision:** OpenAI API integration with aggressive caching and template fallback  
**Rationale:** Personalized content enhances user value, fallback ensures reliability  
**Trade-off:** Adds API costs and latency, but provides better personalization  
**Status:** ✅ Implemented in Phase 6B (content_generator.py)
**Features:**
- Caching by persona + signal combination (24-hour TTL)
- Tone validation on all AI-generated content
- Automatic fallback to templates on API failure
- Works without API key (graceful degradation)

### 10. Expanded Content Catalog (Phase 6B)
**Decision:** Expand from 3 to 72 items with variety (articles, calculators, checklists, templates)  
**Rationale:** Provides comprehensive educational resources, variety improves engagement  
**Trade-off:** More content to maintain, but significantly better user experience  
**Status:** ✅ Implemented in Phase 6B (recommendations.py)
**Distribution:**
- High Utilization: 13 items
- Variable Income Budgeter: 13 items
- Savings Builder: 13 items
- Financial Newcomer: 12 items
- Subscription-Heavy: 11 items
- Neutral: 10 items
- Total: 72 items

### 11. Partner Offers System (Phase 6B)
**Decision:** Eligibility-based partner offers with data-driven rationales  
**Rationale:** Provides relevant financial products while maintaining compliance  
**Trade-off:** Adds complexity, but enhances user value and potential revenue  
**Status:** ✅ Implemented in Phase 6B (partner_offers.py)
**Offer Types:**
- Balance Transfer Credit Cards
- High-Yield Savings Accounts (HYSA)
- Budgeting Apps
- Subscription Management Tools

## Extension Points

### Easy to Add
- New signal types (savings, income) ✅ Added in Phase 5
- New personas ✅ Added 3 in Phase 5
- New recommendation templates ✅ Added 9 in Phase 5
- Additional eligibility rules ✅ Enhanced in Phase 6
- Additional time windows (e.g., 90d, 365d)
- Additional prohibited phrases (tone validation) ✅ Extensible in Phase 6

### Requires Refactoring
- AI/LLM integration (tone validation ready, OpenAI integration ready)
- Partner offers (eligibility system ready)
- End-user interface
- Real-time data updates

## Testing Patterns

### Unit Tests
- Test signal detection with known data
- Test persona assignment logic
- Test rationale generation
- Test eligibility checks

### Integration Tests
- Test full pipeline (data → signals → personas → recommendations)
- Test API endpoints
- Test database operations

### Manual Tests
- Verify UI displays correctly
- Check edge cases (no data, missing fields)
- Validate demo flow

