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

### Add Additional Personas (Beyond 5)
**Current (MVP):** 5 personas (High Utilization, Variable Income Budgeter, Savings Builder, Financial Newcomer, Subscription-Heavy, Neutral)
**Target:** 6-10 total personas for more granular categorization

**Tasks:**
- [ ] Research and identify additional persona opportunities
  - [ ] Analyze user data patterns to identify distinct behavioral groups
  - [ ] Review financial wellness literature for common personas
  - [ ] Consider edge cases and unique financial situations
- [ ] Define new persona criteria (for each new persona)
  - [ ] Clear, measurable criteria based on behavioral signals
  - [ ] Document rationale for why this persona matters
  - [ ] Define primary educational focus areas
  - [ ] Map to relevant recommendation content
- [ ] Implement persona detection logic
  - [ ] Add detection functions to `personas.py`
  - [ ] Update priority logic to include new personas
  - [ ] Test persona assignment with diverse user data
- [ ] Create content templates
  - [ ] 10-15 educational content items per new persona
  - [ ] Variety: articles, calculators, checklists, templates
  - [ ] Persona-specific recommendations and guidance
- [ ] Update UI to display new personas
  - [ ] Add persona badges with appropriate colors
  - [ ] Update persona display in dashboard and user detail pages
  - [ ] Ensure all personas are visible and distinguishable

**Potential New Personas to Consider:**
- **Debt Consolidator**: High debt across multiple accounts, seeking consolidation strategies
- **Goal-Oriented Saver**: Active savings with specific goals (house, vacation, education)
- **Credit Builder**: Low credit utilization, building credit history (newcomer variant)
- **Balance Optimizer**: Moderate utilization, focused on optimization strategies
- **Income Maximizer**: High income, seeking investment and growth opportunities
- **Emergency Fund Builder**: Actively building emergency fund, not yet at target
- **Retirement Planner**: Focused on long-term retirement savings

**Complexity:** Medium-High
**Estimated effort:** 4-6 hours per persona (2-3 personas = 8-18 hours)

---

## 4. Recommendation Engine

### AI/LLM Integration
**Current (MVP):** Hardcoded content templates
**Target:** AI-generated personalized content

**Tasks:**
- [ ] Integrate OpenAI API for content generation
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

### UX/UI Polish & Visual Enhancement
**Current (MVP):** Basic Bootstrap 5 styling, functional but minimal visual appeal
**Target:** Modern, visually appealing, professional website with enhanced UX

**Tasks:**
- [ ] Design system and color palette
  - [ ] Define consistent color scheme (primary, secondary, accent colors)
  - [ ] Typography system (font families, sizes, weights)
  - [ ] Spacing and layout system (consistent margins, padding)
  - [ ] Component stylesheet (buttons, cards, badges, forms)
- [ ] Enhanced dashboard design
  - [ ] Card-based layout instead of table-only
  - [ ] Data visualization (charts for persona distribution, signal trends)
  - [ ] Quick stats cards (total users, personas breakdown, consent stats)
  - [ ] Better visual hierarchy and information architecture
- [ ] Enhanced user detail page
  - [ ] Modern layout with improved spacing
  - [ ] Better signal visualization (charts, progress bars, color-coded indicators)
  - [ ] Improved recommendation cards with better typography
  - [ ] Collapsible sections for better organization
  - [ ] Visual indicators for consent status, persona matches
- [ ] Component library
  - [ ] Consistent button styles (primary, secondary, danger, outline)
  - [ ] Form components (inputs, selects, checkboxes)
  - [ ] Alert/notification components (success, warning, error, info)
  - [ ] Loading states and spinners
  - [ ] Empty states with helpful messaging
- [ ] Interactive elements
  - [ ] Smooth transitions and animations
  - [ ] Hover effects on interactive elements
  - [ ] Toast notifications for actions (consent toggle, recommendations generated)
  - [ ] Tooltips for additional context
- [ ] Responsive design improvements
  - [ ] Mobile-first optimizations
  - [ ] Tablet layout adjustments
  - [ ] Breakpoint testing and refinement
- [ ] Accessibility enhancements
  - [ ] ARIA labels and roles
  - [ ] Keyboard navigation support
  - [ ] Focus indicators
  - [ ] Screen reader compatibility
  - [ ] Color contrast compliance (WCAG AA)
- [ ] Visual polish
  - [ ] Custom SVG icons (replace emoji/unicode where appropriate)
  - [ ] Consistent iconography throughout
  - [ ] Subtle shadows and depth
  - [ ] Professional imagery/illustrations (optional)
  - [ ] Consistent border radius and spacing

**Complexity:** Medium-High
**Estimated effort:** 8-12 hours

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

### Consent Enforcement (Required for MVP)
**Current (MVP):** Consent is tracked but not enforced
**Target:** Full enforcement per `directions.md` requirement: "No recommendations without consent"

**Critical Requirements:**
- [ ] Block recommendation generation if `consent_given = False`
  - Update `generate_recommendations()` in `recommendations.py`
  - Return empty list if no consent
- [ ] Block recommendation display in API endpoints
  - Update `get_recommendations_for_user()` in `app.py`
  - Return empty recommendations with appropriate message
- [ ] Update UI to show consent requirement
  - Display consent banner/message when consent not given
  - Hide recommendations section if no consent
  - Update `user_detail.html` template
- [ ] Add consent checks to recommendation retrieval
  - Ensure all recommendation endpoints check consent
  - Return user-friendly error messages
- [ ] Add tests for consent enforcement
  - Test that recommendations are blocked without consent
  - Test that recommendations appear after consent granted
  - Test consent revocation blocks future recommendations

**Complexity:** Low-Medium
**Estimated effort:** 2-3 hours
**Priority:** High (Required for MVP compliance)

### Enhanced Consent Management (Post-MVP)
**Current (MVP):** Basic consent tracking (boolean flag)
**Target:** Comprehensive consent management system

**Tasks:**
- [ ] Granular consent options (different data types)
  - Consent for transaction analysis
  - Consent for persona assignment
  - Consent for recommendation generation
  - Consent for partner offers
- [ ] Consent history tracking
  - Track consent changes over time
  - Store timestamps for grant/revocation
  - Track who changed consent (user vs operator)
- [ ] Revocation workflow
  - Immediate effect of revocation
  - Clear UI for revocation
  - Confirmation prompts
- [ ] Data deletion on consent revocation
  - Option to delete all user data when consent revoked
  - Option to anonymize data instead
  - Compliance with data retention policies
- [ ] Consent audit trail
  - Log all consent changes
  - Track consent status at time of recommendation generation
  - Store in `decision_traces` or separate audit table
- [ ] Block signal detection without consent (if required)
  - Update `detect_signals.py` to check consent
  - Prevent behavioral analysis without consent
- [ ] Block persona assignment without consent (if required)
  - Update `personas.py` to check consent
  - Prevent persona matching without consent
- [ ] Consent status display in operator view
  - Show consent status prominently
  - Highlight users without consent
  - Filter users by consent status

**Complexity:** Medium-High
**Estimated effort:** 4-6 hours
**Priority:** Medium (Enhanced features)

### Compliance Auditor Interface (Critical Compliance Only)
**Current (MVP):** No dedicated compliance interface
**Target:** Basic compliance auditor interface for regulatory oversight

**Regulatory Context:**
- GLBA (Gramm-Leach-Bliley Act) - Financial privacy, opt-out rights
- FCRA (Fair Credit Reporting Act) - Credit data, adverse action notices
- TDPSA (Texas Data Privacy and Security Act) - Data rights, consent management
- RFPA (Right to Financial Privacy Act) - Confidentiality of financial records

**Database Tables Needed:**
- [ ] `consent_audit_log` - Track consent history (grant/revoke with timestamps)
- [ ] `data_access_log` - Log all data access events (who, what, when, why)
- [ ] `compliance_violations` - Track compliance issues (consent violations, tone violations, eligibility failures)

**Critical Features:**
1. **Consent Audit Trail**
   - [ ] View consent history per user (grants, revocations, timestamps)
   - [ ] Identify users processed without valid consent
   - [ ] Consent status at time of recommendation generation
   - [ ] Export consent records for regulatory audits

2. **Data Access Logging**
   - [ ] Log all data access events (user, accessed_by, access_type, timestamp)
   - [ ] Filter by date range, user, access type
   - [ ] Export audit logs (CSV/JSON) for compliance reports
   - [ ] Identify unauthorized or suspicious access patterns

3. **Compliance Violations Dashboard**
   - [ ] View all compliance violations (consent, tone, eligibility)
   - [ ] Track violation severity and resolution status
   - [ ] Violation categories:
     - Consent violations (processing without consent)
     - Tone violations (shaming/judgmental language detected)
     - Eligibility failures (recommendations to ineligible users)
   - [ ] Resolution workflow (assign, track, document)

4. **Recommendation Compliance Review**
   - [ ] Verify each recommendation has:
     - ✅ Active consent at time of generation
     - ✅ Eligibility check performed
     - ✅ Required disclaimer present
     - ✅ Complete decision trace (4 steps)
     - ✅ Rationale cites specific data
   - [ ] Filter recommendations by compliance status
   - [ ] Export compliance reports

5. **Decision Trace Auditor**
   - [ ] View all decision traces (already stored in `decision_traces` table)
   - [ ] Verify trace completeness (all 4 steps present)
   - [ ] Validate traces cite actual data points
   - [ ] Export traces for regulatory audits

6. **Basic Regulatory Reporting**
   - [ ] Compliance summary report (consent coverage, violation rates)
   - [ ] Data access report (access logs)
   - [ ] Violation resolution report
   - [ ] Export formats: CSV, JSON for regulatory submissions

**Interface Requirements:**
- [ ] Compliance dashboard with overview metrics
- [ ] Consent audit log viewer
- [ ] Data access log viewer
- [ ] Violations dashboard
- [ ] Recommendation compliance review interface
- [ ] Export functionality for all audit data

**Non-Critical Features (Deferred):**
- Granular consent options (different data types)
- Advanced tone checking automation
- User data rights management (access/correction/deletion requests)
- GLBA opt-out management interface
- Data retention management
- Fairness/bias monitoring
- Advanced analytics and trends

**Complexity:** Medium
**Estimated effort:** 6-8 hours
**Priority:** High (Required for regulatory compliance)

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
- [ ] Consent enforcement tests
  - [ ] Recommendations blocked without consent
  - [ ] Recommendations generated after consent granted
  - [ ] Consent revocation blocks future recommendations
  - [ ] API endpoints respect consent status
  - [ ] UI displays consent requirements correctly

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
2. All 5 personas implemented (expandable to 6-10)
3. All signal types detected (credit, subscriptions, savings, income)
4. 30-day and 180-day windows
5. AI/LLM integration for recommendations
6. Partner offers with eligibility
7. **Consent enforcement** (block recommendations without consent)
8. Evaluation harness with metrics
9. ≥10 tests passing
10. Complete documentation

### Should Have (Important but not critical)
1. Enhanced operator view
2. **UX/UI polish & visual enhancement** (modern, professional appearance)
3. End-user interface
4. Comprehensive eligibility checks
5. Tone validation system
6. Decision traces
7. **Compliance auditor interface** (critical compliance features)
8. Performance optimization
9. Additional personas (beyond 5)

### Nice to Have (Bonus points)
1. Creative content formats
2. Advanced UI features
3. Fairness analysis
4. Interactive calculators
5. Gamification elements

---

## Estimated Total Effort (Post-MVP)

**Core Requirements:** 60-80 hours
**Compliance Interface:** 6-8 hours (added to core)
**UX/UI Polish:** 8-12 hours (added to core)
**Additional Personas:** 8-18 hours (2-3 personas)
**Nice-to-Haves:** 20-40 hours
**Total:** 102-158 hours

---

## Recommended Build Order (Post-MVP)

1. **Implement consent enforcement** (Required for MVP compliance) - 2-3 hours
2. **Expand data** (50-100 users, all account types) - 4-6 hours
3. **Database migration prep** (test PostgreSQL locally, update connection handling) - 2-3 hours
4. **Add savings & income signals** - 7-9 hours
5. **Add 180-day window** - 3-4 hours
6. **Implement remaining 3 personas** - 7-11 hours
7. **Integrate AI/LLM** (OpenAI) - 5-8 hours
8. **Add partner offers** - 4-6 hours
9. **Build evaluation harness** - 6-8 hours
10. **Expand test suite** (including consent enforcement tests) - 6-8 hours
11. **Refactor to modular structure** - 4-6 hours
12. **Enhanced operator view** - 4-6 hours
13. **UX/UI polish & visual enhancement** - 8-12 hours
14. **Build end-user interface** - 8-12 hours
15. **Build compliance auditor interface** (critical compliance features) - 6-8 hours
16. **Complete documentation** - 6-9 hours
17. **Enhanced consent management** (granular options, history, audit trail) - 4-6 hours
18. **Add additional personas** (2-3 new personas) - 8-18 hours
19. **AWS RDS setup & production migration** - 2-4 hours (when ready for production)
20. **Final polish & testing** - 4-6 hours

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

### Compliance (Critical Features)
- [ ] Consent audit log tracks all consent changes
- [ ] Data access logging captures all access events
- [ ] Compliance violations dashboard shows all issues
- [ ] Recommendation compliance review verifies all requirements
- [ ] Decision trace auditor validates trace completeness
- [ ] Regulatory reporting exports available (CSV/JSON)

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


