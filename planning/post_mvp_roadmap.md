# SpendSense Post-MVP Roadmap
## Features & Improvements for Final Submission

This document outlines everything needed to go from MVP to full submission based on the original requirements in `directions.md`.

---

## 1. Data & Scale

### Expand Synthetic Data
**Current (MVP):** 5 users
**Target:** 50-100 users

**Tasks:**
- [ ] Enhance data generator to create 50-100 diverse users
- [ ] Include demographic diversity (if tracking fairness metrics)
- [ ] Add more account types: money market, HSA, mortgages, student loans
- [ ] Generate more realistic transaction patterns (seasonal, irregular income, etc.)
- [ ] Add mortgage and student loan liability data
- [ ] Ensure diverse financial situations across income levels

**Complexity:** Medium
**Estimated effort:** 2-3 hours

### Add Missing Account Types
**Current (MVP):** Checking, savings, credit cards
**Target:** All Plaid account types

**Tasks:**
- [ ] Money market accounts
- [ ] HSA (Health Savings Account)
- [ ] Mortgages with interest rates and payment schedules
- [ ] Student loans with interest rates and payment schedules
- [ ] Exclude business accounts (holder_category filter)

**Complexity:** Low-Medium
**Estimated effort:** 2-3 hours

---

## 1.5. Database Migration to PostgreSQL (AWS RDS)

### Migrate from SQLite to PostgreSQL
**Current (MVP):** SQLite (local file-based database)
**Target:** PostgreSQL on AWS RDS (production-ready, scalable)

**Migration Status:**
- ✅ Database abstraction layer created (`db_config.py`)
- ✅ Migration guide documented (`md_files/MIGRATION_GUIDE.md`)
- ✅ Migration readiness assessment completed
- ✅ Code uses standard SQL (compatible with PostgreSQL)
- ✅ All queries use parameterized placeholders

**Tasks:**
- [ ] Update `get_db_connection()` to support both SQLite and PostgreSQL
- [ ] Create PostgreSQL schema file (convert AUTOINCREMENT → SERIAL, REAL → NUMERIC)
- [ ] Test schema creation with local PostgreSQL instance
- [ ] Update schema validation queries (sqlite_master → information_schema)
- [ ] Test all queries with PostgreSQL
- [ ] Create data migration script (SQLite → PostgreSQL)
- [ ] Set up AWS RDS PostgreSQL instance
- [ ] Configure security groups and networking
- [ ] Migrate production data
- [ ] Update application configuration (environment variables)
- [ ] Test production deployment
- [ ] Set up automated backups on RDS
- [ ] Document production connection strings and credentials management

**Key Changes:**
- `INTEGER PRIMARY KEY AUTOINCREMENT` → `SERIAL PRIMARY KEY`
- `TEXT` → `VARCHAR(255)` (optional optimization)
- `REAL` → `NUMERIC(10,2)` (for financial precision)
- `?` placeholders → `%s` (psycopg2 style)
- `sqlite_master` → `information_schema.tables`
- Connection handling: `sqlite3` → `psycopg2`

**Benefits:**
- Scalability to handle 50-100+ users efficiently
- Better performance for complex analytical queries
- Production-ready with automated backups and high availability
- Better support for financial data precision (NUMERIC vs REAL)
- Advanced SQL features (window functions, JSONB, etc.)

**Complexity:** Medium
**Estimated effort:** 7-11 hours (preparation done, implementation remaining)

**Resources:**
- Migration guide: `md_files/MIGRATION_GUIDE.md`
- Migration readiness: `md_files/MIGRATION_READINESS.md`
- Database abstraction: `db_config.py`

**Note:** Migration can be done incrementally - test with PostgreSQL locally before production migration.

---

## 2. Behavioral Signal Detection

### Add Missing Signals

#### Savings Signals (Not in MVP)
**Tasks:**
- [ ] Net inflow to savings-like accounts (savings, money market, cash management, HSA)
- [ ] Savings growth rate calculation
- [ ] Emergency fund coverage = `savings balance / average monthly expenses`
- [ ] Track over 30-day and 180-day windows

**Complexity:** Medium
**Estimated effort:** 3-4 hours

#### Income Stability Signals (Not in MVP)
**Tasks:**
- [ ] Payroll ACH detection (identify payroll transactions)
- [ ] Payment frequency detection (weekly, bi-weekly, monthly)
- [ ] Payment variability calculation (standard deviation)
- [ ] Cash-flow buffer in months = `checking balance / average monthly expenses`
- [ ] Median pay gap calculation

**Complexity:** Medium-High
**Estimated effort:** 4-5 hours

### Add 180-Day Window Analysis
**Current (MVP):** 30-day window only
**Target:** Both 30-day and 180-day windows

**Tasks:**
- [ ] Refactor signal detection to support multiple time windows
- [ ] Calculate all signals for both 30d and 180d windows
- [ ] Store window parameter in signals table
- [ ] Update persona assignment to consider both windows
- [ ] Display both short-term and long-term trends in UI

**Complexity:** Medium
**Estimated effort:** 3-4 hours

---

## 3. Persona System

### Add Remaining 3 Personas
**Current (MVP):** 2 personas (High Utilization, Subscription-Heavy)
**Target:** 5 personas

#### Persona 3: Variable Income Budgeter
**Tasks:**
- [ ] Define criteria: Median pay gap > 45 days AND cash-flow buffer < 1 month
- [ ] Implement detection logic
- [ ] Create content templates
- [ ] Document focus: Percent-based budgets, emergency fund basics, smoothing strategies

**Complexity:** Medium
**Estimated effort:** 2-3 hours

#### Persona 4: Savings Builder
**Tasks:**
- [ ] Define criteria: Savings growth rate ≥2% over window OR net savings inflow ≥$200/month, AND all card utilizations < 30%
- [ ] Implement detection logic
- [ ] Create content templates
- [ ] Document focus: Goal setting, automation, APY optimization (HYSA/CD basics)

**Complexity:** Medium
**Estimated effort:** 2-3 hours

#### Persona 5: Custom Persona (Design Your Own)
**Tasks:**
- [ ] Research and define a meaningful 5th persona
- [ ] Document clear criteria based on behavioral signals
- [ ] Write rationale for why this persona matters
- [ ] Define primary educational focus
- [ ] Implement detection logic
- [ ] Create content templates
- [ ] Document prioritization logic if multiple personas match

**Complexity:** Medium-High
**Estimated effort:** 3-5 hours

### Implement Multi-Persona Prioritization
**Tasks:**
- [ ] Define clear priority order when user matches multiple personas
- [ ] Document prioritization logic
- [ ] Handle edge cases (no match, all match)
- [ ] Consider showing secondary personas in UI

**Complexity:** Low-Medium
**Estimated effort:** 1-2 hours

---

## 4. Recommendation Engine

### AI/LLM Integration
**Current (MVP):** Hardcoded content templates
**Target:** AI-generated personalized content

**Tasks:**
- [ ] Integrate Gemini API for content generation (per memory: no OpenAI)
- [ ] Create prompts for generating educational content
- [ ] Implement rationale generation with LLM
- [ ] Add fallback to templates if API fails
- [ ] Cache generated content to minimize API calls
- [ ] Implement content quality checks

**Complexity:** High
**Estimated effort:** 5-8 hours

### Partner Offers
**Current (MVP):** Education content only
**Target:** 1-3 partner offers per user with eligibility checks

**Tasks:**
- [ ] Define partner offer catalog (balance transfer cards, HYSA, budgeting apps, subscription tools)
- [ ] Implement eligibility checking logic:
  - Minimum income requirements
  - Credit requirements
  - Existing account filters
  - Avoid harmful products (no payday loans)
- [ ] Map offers to personas
- [ ] Generate offer recommendations with rationales
- [ ] Add offer display in UI

**Complexity:** Medium-High
**Estimated effort:** 4-6 hours

### Expand Content Catalog
**Tasks:**
- [ ] Create 10-15 educational content items per persona
- [ ] Add variety: articles, calculators, checklists, templates
- [ ] Include images/infographics (optional)
- [ ] Add video content links (optional)
- [ ] Implement content ranking/selection logic

**Complexity:** Medium (mostly content creation)
**Estimated effort:** 4-6 hours

---

## 5. User Experience

### End-User Interface (Not in MVP)
**Current (MVP):** Operator view only
**Target:** User-facing experience

**Options:**
- [ ] Web app with personalized dashboard
- [ ] Email preview templates
- [ ] Chat interface for Q&A
- [ ] Content feed (social media style)
- [ ] Mobile app mockup (Figma/screenshots acceptable)

**Choose one and implement:**
- [ ] User authentication (simple, no production security needed)
- [ ] Personalized dashboard showing user's persona
- [ ] Recommendation feed
- [ ] Interactive calculators (emergency fund, debt paydown)
- [ ] Consent management interface

**Complexity:** High
**Estimated effort:** 8-12 hours

### Enhanced Operator View
**Tasks:**
- [ ] Add filtering and search functionality
- [ ] Show both 30d and 180d persona assignments
- [ ] Display decision traces (why this recommendation was made)
- [ ] Implement approve/override functionality
- [ ] Add flag for review feature
- [ ] Add bulk operations
- [ ] Export functionality (CSV/JSON)

**Complexity:** Medium
**Estimated effort:** 4-6 hours

---

## 6. Guardrails & Compliance

### Enhanced Eligibility Checks
**Current (MVP):** Basic filtering
**Target:** Comprehensive eligibility system

**Tasks:**
- [ ] Minimum income requirements per product
- [ ] Credit score requirements (if tracking credit data)
- [ ] Existing account checks (comprehensive)
- [ ] Geographic eligibility (if relevant)
- [ ] Age requirements
- [ ] Harmful product blacklist

**Complexity:** Medium
**Estimated effort:** 3-4 hours

### Tone Validation System
**Current (MVP):** Manual review
**Target:** Automated tone checking

**Tasks:**
- [ ] Create list of prohibited phrases (shaming language)
- [ ] Implement tone checker (keyword-based or LLM-based)
- [ ] Validate all generated content
- [ ] Flag content for manual review if needed
- [ ] Document tone guidelines

**Complexity:** Medium
**Estimated effort:** 3-4 hours

### Enhanced Consent Management
**Tasks:**
- [ ] Granular consent options (different data types)
- [ ] Consent history tracking
- [ ] Revocation workflow
- [ ] Data deletion on consent revocation
- [ ] Consent audit trail

**Complexity:** Medium
**Estimated effort:** 2-3 hours

---

## 7. Evaluation & Metrics

### Build Evaluation Harness
**Current (MVP):** Manual testing
**Target:** Automated evaluation system

**Metrics to Implement:**

#### Coverage
- [ ] % of users with assigned persona
- [ ] % of users with ≥3 detected behaviors
- [ ] Target: 100%

#### Explainability
- [ ] % of recommendations with plain-language rationales
- [ ] Rationale quality scoring (manual or automated)
- [ ] Target: 100%

#### Relevance
- [ ] Manual review scoring system
- [ ] Education-persona fit scoring
- [ ] User feedback simulation

#### Latency
- [ ] Time to generate recommendations per user
- [ ] Target: <5 seconds
- [ ] Performance profiling

#### Fairness
- [ ] Demographic parity check (if tracking demographics)
- [ ] Persona distribution analysis
- [ ] Recommendation distribution analysis

**Tasks:**
- [ ] Build evaluation script
- [ ] Generate metrics JSON/CSV
- [ ] Create summary report (1-2 pages)
- [ ] Generate per-user decision traces
- [ ] Add visualization (charts/graphs)

**Complexity:** High
**Estimated effort:** 6-8 hours

---

## 8. Testing & Quality

### Comprehensive Test Suite
**Current (MVP):** 5 basic tests
**Target:** ≥10 unit/integration tests

**Test Coverage:**
- [ ] Data generation tests
- [ ] Signal detection tests (edge cases)
  - [ ] Zero balance/limit
  - [ ] Missing data
  - [ ] Date edge cases
- [ ] Persona assignment tests
  - [ ] Single match
  - [ ] Multiple matches (priority)
  - [ ] No match
- [ ] Recommendation generation tests
- [ ] Eligibility filter tests
- [ ] API endpoint tests
- [ ] Rationale generation tests
- [ ] Consent tracking tests

**Complexity:** Medium-High
**Estimated effort:** 6-8 hours

### Edge Case Handling
**Tasks:**
- [ ] User with no transactions
- [ ] User with no credit cards
- [ ] User with no accounts
- [ ] Missing merchant names
- [ ] Pending transactions
- [ ] Negative balances
- [ ] Zero credit limits
- [ ] Future-dated transactions
- [ ] Duplicate transactions

**Complexity:** Medium
**Estimated effort:** 3-4 hours

---

## 9. Documentation

### Technical Documentation
**Tasks:**
- [ ] Comprehensive README with:
  - [ ] Setup instructions (one-command setup)
  - [ ] Usage guide
  - [ ] API documentation
  - [ ] Architecture overview
  - [ ] Testing instructions
- [ ] Decision log in `/docs` explaining:
  - [ ] Why 5 personas were chosen
  - [ ] Signal detection methodology
  - [ ] Persona prioritization logic
  - [ ] Technology choices
  - [ ] Trade-offs made
- [ ] Schema documentation with ER diagrams
- [ ] Code comments for complex logic
- [ ] API documentation (OpenAPI/Swagger)

**Complexity:** Medium
**Estimated effort:** 4-6 hours

### Limitations & Future Work
**Tasks:**
- [ ] Document explicit limitations
- [ ] Known issues and bugs
- [ ] Future enhancement ideas
- [ ] Scalability considerations
- [ ] Security considerations

**Complexity:** Low
**Estimated effort:** 1-2 hours

---

## 10. Submission Requirements

### Technical Writeup (1-2 pages)
**Tasks:**
- [ ] Project overview
- [ ] Technical approach
- [ ] Key decisions and trade-offs
- [ ] Results and metrics
- [ ] Challenges and solutions
- [ ] Future improvements

**Complexity:** Low-Medium
**Estimated effort:** 2-3 hours

### AI Tools Documentation
**Tasks:**
- [ ] Document all AI tools used (Cursor, ChatGPT, etc.)
- [ ] Document prompts used for content generation
- [ ] Document LLM integration approach
- [ ] Explain AI vs. rules-based decisions

**Complexity:** Low
**Estimated effort:** 1 hour

### Demo Video or Presentation
**Tasks:**
- [ ] Record demo video (5-10 minutes) showing:
  - [ ] Data ingestion
  - [ ] Signal detection
  - [ ] Persona assignment
  - [ ] Recommendations with rationales
  - [ ] Operator view
  - [ ] Guardrails in action
- [ ] Prepare live presentation slides
- [ ] Create demo script
- [ ] Prepare for Q&A

**Complexity:** Medium
**Estimated effort:** 3-4 hours

### Performance Metrics & Benchmarks
**Tasks:**
- [ ] Run evaluation harness
- [ ] Generate metrics report
- [ ] Create visualizations
- [ ] Document performance characteristics
- [ ] Compare against success criteria

**Complexity:** Low (if harness built)
**Estimated effort:** 1-2 hours

### Test Cases & Validation Results
**Tasks:**
- [ ] Document all test cases
- [ ] Show test results
- [ ] Include edge case handling
- [ ] Demonstrate deterministic behavior

**Complexity:** Low
**Estimated effort:** 1-2 hours

### Data Model/Schema Documentation
**Tasks:**
- [ ] Create ER diagram
- [ ] Document all tables and relationships
- [ ] Document data types and constraints
- [ ] Include sample data

**Complexity:** Low-Medium
**Estimated effort:** 2-3 hours

---

## 11. Code Quality & Best Practices

### Refactoring
**Tasks:**
- [ ] Extract single file into modular structure
- [ ] Separate concerns (ingest, features, personas, recommend, guardrails)
- [ ] Create proper module structure
- [ ] Add type hints throughout
- [ ] Remove code duplication

**Complexity:** Medium
**Estimated effort:** 4-6 hours

### Configuration Management
**Tasks:**
- [ ] Move hardcoded values to config files
- [ ] Create config.json or config.py
- [ ] Environment variable support (database type, connection strings)
- [ ] Separate dev/prod configs
- [ ] Use `db_config.py` for database configuration
- [ ] Secure credential management (AWS Secrets Manager or environment variables)

**Complexity:** Low
**Estimated effort:** 1-2 hours

### Logging & Monitoring
**Tasks:**
- [ ] Add structured logging
- [ ] Log key decisions (persona assignment, recommendation selection)
- [ ] Performance logging
- [ ] Error logging with context

**Complexity:** Low-Medium
**Estimated effort:** 2-3 hours

### Deterministic Behavior
**Tasks:**
- [ ] Use seeds for all randomness
- [ ] Ensure reproducible results
- [ ] Document seed usage
- [ ] Test reproducibility

**Complexity:** Low
**Estimated effort:** 1 hour

---

## 12. Optional Enhancements (Nice to Have)

### Creative Formats
- [ ] Generated images/infographics for recommendations
- [ ] Short video content links
- [ ] Interactive calculators (React components)
- [ ] Gamified savings challenges
- [ ] Progress tracking

**Complexity:** High
**Estimated effort:** Variable (8-20 hours)

### Advanced Features
- [ ] Multi-language support
- [ ] Accessibility (WCAG compliance)
- [ ] Dark mode
- [ ] Export user reports (PDF)
- [ ] Email notification system
- [ ] Webhook integrations

**Complexity:** High
**Estimated effort:** Variable (10-30 hours)

---

## Priority Matrix

### Must Have (Critical for Submission)
1. 50-100 users with diverse data
2. All 5 personas implemented
3. All signal types detected (credit, subscriptions, savings, income)
4. 30-day and 180-day windows
5. AI/LLM integration for recommendations
6. Partner offers with eligibility
7. Evaluation harness with metrics
8. ≥10 tests passing
9. Complete documentation
10. Demo video/presentation

### Should Have (Important but not critical)
1. Enhanced operator view
2. End-user interface
3. Comprehensive eligibility checks
4. Tone validation system
5. Decision traces
6. Performance optimization

### Nice to Have (Bonus points)
1. Creative content formats
2. Advanced UI features
3. Fairness analysis
4. Interactive calculators
5. Gamification elements

---

## Estimated Total Effort (Post-MVP)

**Core Requirements:** 60-80 hours
**Nice-to-Haves:** 20-40 hours
**Total:** 80-120 hours

---

## Recommended Build Order (Post-MVP)

1. **Expand data** (50-100 users, all account types) - 4-6 hours
2. **Database migration prep** (test PostgreSQL locally, update connection handling) - 2-3 hours
3. **Add savings & income signals** - 7-9 hours
4. **Add 180-day window** - 3-4 hours
5. **Implement remaining 3 personas** - 7-11 hours
6. **Integrate AI/LLM** (Gemini) - 5-8 hours
7. **Add partner offers** - 4-6 hours
8. **Build evaluation harness** - 6-8 hours
9. **Expand test suite** - 6-8 hours
10. **Refactor to modular structure** - 4-6 hours
11. **Enhanced operator view** - 4-6 hours
12. **Build end-user interface** - 8-12 hours
13. **Complete documentation** - 6-9 hours
14. **AWS RDS setup & production migration** - 2-4 hours (when ready for production)
15. **Create demo video** - 3-4 hours
16. **Final polish & testing** - 4-6 hours

**Note:** Database migration can happen anytime after MVP is complete. The abstraction layer is already in place, so migration can be done incrementally without blocking other features.

---

## Success Criteria Checklist

From `directions.md` requirements:

### Coverage
- [ ] 100% of users with assigned persona + ≥3 behaviors

### Explainability
- [ ] 100% of recommendations with rationales

### Latency
- [ ] <5 seconds to generate recommendations per user

### Auditability
- [ ] 100% of recommendations with decision traces

### Code Quality
- [ ] ≥10 passing unit/integration tests
- [ ] One-command setup
- [ ] Clear modular structure
- [ ] Deterministic behavior

### Documentation
- [ ] Complete schema documentation
- [ ] Decision log with key choices
- [ ] Explicit limitations documented
- [ ] Standard disclaimer included

### Guardrails
- [ ] All personas have clear, documented criteria
- [ ] Guardrails prevent ineligible offers
- [ ] Tone checks enforce "no shaming" language
- [ ] Consent tracked and enforced

### Operator View
- [ ] Shows all signals
- [ ] Can override recommendations
- [ ] Displays decision traces

### Evaluation
- [ ] Report includes fairness analysis
- [ ] Metrics JSON/CSV generated
- [ ] Summary report (1-2 pages)

### System
- [ ] Runs locally without external dependencies (except API calls)
- [ ] All data is synthetic (no real PII)
- [ ] Database migration path documented and tested
- [ ] PostgreSQL compatibility verified (if migrating)

---

## Notes & Reminders

- Keep `directions.md` as the source of truth
- Refer to this document when building post-MVP features
- Update this document if requirements change
- Track progress with checkboxes
- Document any deviations from plan
- Focus on explainability over sophistication
- Transparency > complexity
- User control > automation
- Education > sales
- Build systems people can trust

---

## Contact for Questions

**Bryce Harris** - bharris@peak6.com


