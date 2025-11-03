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
│  - credit_cards, signals, personas       │
│  - recommendations, decision_traces     │
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

## Data Flow Patterns

### Signal Detection Flow

```
1. Query transactions/accounts for user
2. Group by merchant (subscriptions) or calculate ratios (credit)
3. Apply pattern matching rules
4. Store signals in database with metadata
```

### Persona Assignment Flow

```
1. Query signals for user
2. Check High Utilization criteria (highest priority)
3. If no match, check Subscription-Heavy criteria
4. If no match, assign Neutral
5. Store persona with criteria explanation
```

### Recommendation Generation Flow

```
1. Get user persona
2. Get content templates for persona
3. Select 2-3 recommendations
4. Generate rationale citing user data
5. Generate decision trace
6. Apply eligibility filters
7. Store recommendations
```

## Code Organization Patterns

### Current Structure (Phase 2 Complete)

```
spendsense/
├── database.py         # SQLite setup & schema
├── generate_data.py     # Synthetic data generator
├── detect_signals.py   # Signal detection engine
├── personas.py         # Persona assignment (Phase 2) ✅
├── recommendations.py  # Recommendation engine (Phase 2) ✅
├── rationales.py       # Rationale generation (Phase 2) ✅
├── traces.py           # Decision trace generation (Phase 2) ✅
├── tests/              # Test suite
│   ├── __init__.py
│   ├── test_database.py
│   ├── test_signals.py
│   ├── test_personas.py      # Phase 2 ✅
│   ├── test_recommendations.py # Phase 2 ✅
│   └── test_integration.py    # Phase 2 ✅
├── requirements.txt    # Python dependencies
├── pytest.ini         # Test configuration
├── spendsense.db       # SQLite database
└── [planning/, memory-bank/]  # Documentation
```

### Target MVP Structure (Phase 3)

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

### 3. Hardcoded Recommendations
**Decision:** Templates instead of AI for MVP  
**Rationale:** No external API dependencies, faster iteration, more predictable  
**Trade-off:** Less personalized, but can add AI later

### 4. Single Persona Assignment
**Decision:** One persona per user with priority logic  
**Rationale:** Simpler logic, clearer for demo  
**Trade-off:** Users may match multiple personas, but priority handles this

### 5. 30-Day Window Only
**Decision:** Skip 180-day analysis for MVP  
**Rationale:** Faster to build, sufficient for proof of concept  
**Trade-off:** Less comprehensive, but can add later

## Extension Points

### Easy to Add
- New signal types (savings, income)
- New personas
- New recommendation templates
- Additional eligibility rules

### Requires Refactoring
- AI/LLM integration
- Partner offers
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

