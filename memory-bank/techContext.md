# Technical Context

## Technology Stack

### Backend
- **Python 3.10+:** Core language
- **FastAPI:** Web framework (async, automatic OpenAPI docs, type hints)
- **SQLite:** Database (local, no external dependencies)
- **Jinja2:** Server-side templating
- **Faker:** Synthetic data generation (names, emails)

### Frontend
- **HTML5:** Structure
- **Bootstrap 5:** CSS framework (responsive, professional styling)
- **Minimal JavaScript:** Only for consent toggle (vanilla JS, no frameworks)

### Data Storage
- **SQLite:** Relational data (users, accounts, transactions, signals, personas, recommendations)
- **JSON:** Configuration files (content templates, configs)

### Development Tools
- **Git:** Version control
- **pytest:** Testing framework (implemented, 10 tests passing)
- **uvicorn:** ASGI server for FastAPI (for Phase 3)

## Key Libraries & Dependencies

### Required (MVP)
```
# Core dependencies
faker>=19.0.0

# Web framework (Phase 3)
fastapi>=0.104.0
uvicorn>=0.24.0
jinja2>=3.1.2
python-multipart>=0.0.6

# Testing
pytest>=7.4.0
httpx>=0.25.0
```

### Optional (Post-MVP)
```
google-generativeai>=0.3.0  # Gemini API (no OpenAI)
pandas>=2.0.0              # Data analysis (if needed)
```

## Database Schema

### Core Tables

**users**
- Primary key: `id`
- Fields: `name`, `email`, `consent_given`, `created_at`

**accounts** (Plaid-compatible)
- Primary key: `id`
- Foreign key: `user_id` → users
- Fields: `account_id`, `type`, `subtype`, `available_balance`, `current_balance`, `limit`, `iso_currency_code`, `holder_category`

**transactions** (Plaid-compatible)
- Primary key: `id`
- Foreign key: `account_id` → accounts
- Fields: `date`, `amount`, `merchant_name`, `merchant_entity_id`, `payment_channel`, `personal_finance_category`, `pending`

**credit_cards**
- Primary key: `id`
- Foreign key: `account_id` → accounts
- Fields: `apr`, `minimum_payment_amount`, `last_payment_amount`, `is_overdue`, `next_payment_due_date`, `last_statement_balance`

**signals**
- Primary key: `id`
- Foreign key: `user_id` → users
- Fields: `signal_type`, `value`, `metadata` (JSON), `window`, `detected_at`

**personas**
- Primary key: `user_id` → users
- Fields: `persona_type`, `assigned_at`, `criteria_matched`

**recommendations**
- Primary key: `id`
- Foreign key: `user_id` → users
- Fields: `title`, `content`, `rationale`, `persona_matched`, `created_at`

**decision_traces**
- Primary key: `id`
- Foreign keys: `user_id` → users, `recommendation_id` → recommendations
- Fields: `step`, `reasoning`, `data_cited` (JSON), `created_at`

## Development Setup

### Initial Setup
```bash
# Create virtual environment (optional)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 database.py

# Generate demo data
python3 generate_data.py

# Run signal detection
python3 detect_signals.py

# Run tests
python3 -m pytest tests/ -v

# Run development server (Phase 3)
PYTHONPATH=/path/to/SpendSense/src python3 -m uvicorn spendsense.app:app --reload --host 0.0.0.0 --port 8000

# Or from project root:
cd /path/to/SpendSense
PYTHONPATH=/path/to/SpendSense/src python3 -m uvicorn spendsense.app:app --reload
```

### File Structure (Current - Phase 2 Complete)
```
spendsense/
├── database.py               # SQLite setup & schema ✅
├── generate_data.py          # Synthetic data generator ✅
├── detect_signals.py         # Signal detection ✅
├── personas.py               # Persona assignment (Phase 2) ✅
├── recommendations.py        # Recommendation engine (Phase 2) ✅
├── rationales.py             # Rationale generation (Phase 2) ✅
├── traces.py                 # Decision trace generation (Phase 2) ✅
├── tests/                    # Test suite ✅
│   ├── __init__.py
│   ├── test_database.py     # 4 tests
│   ├── test_signals.py      # 6 tests
│   ├── test_personas.py     # 15 tests (Phase 2)
│   ├── test_recommendations.py # 12 tests (Phase 2)
│   └── test_integration.py  # 3 tests (Phase 2)
├── requirements.txt          # Dependencies (faker, pytest)
├── pytest.ini               # Test configuration ✅
├── quick_test.sh            # Manual test script ✅
├── spendsense.db             # SQLite database (generated)
└── [planning/, memory-bank/] # Documentation
```

### File Structure (Phase 3 Complete ✅)
```
src/spendsense/
├── database.py               # SQLite setup ✅
├── generate_data.py          # Synthetic data generator ✅
├── detect_signals.py         # Signal detection ✅
├── personas.py               # Persona assignment (Phase 2) ✅
├── recommendations.py        # Recommendation engine (Phase 2) ✅
├── rationales.py             # Rationale generation (Phase 2) ✅
├── traces.py                 # Decision trace generation (Phase 2) ✅
├── eligibility.py            # Eligibility checks (Phase 3) ✅
├── app.py                    # FastAPI app (Phase 3) ✅
├── templates/                # Jinja2 templates (Phase 3) ✅
│   ├── base.html
│   ├── dashboard.html
│   ├── user_detail.html
│   └── error.html
├── static/                   # CSS/JS (Phase 3) ✅
│   ├── css/style.css
│   └── js/consent.js
├── tests/                    # Test suite ✅
│   ├── __init__.py
│   ├── test_database.py      # 4 tests
│   ├── test_signals.py       # 6 tests
│   ├── test_personas.py      # 15 tests
│   ├── test_recommendations.py # 12 tests
│   ├── test_integration.py   # 3 tests
│   ├── test_app.py           # 6 tests (Phase 3)
│   └── test_eligibility.py  # 8 tests (Phase 3)
├── requirements.txt          # Dependencies ✅
├── pytest.ini               # Test configuration ✅
├── spendsense.db             # SQLite database (generated)
└── [planning/, memory-bank/] # Documentation
```

## Technical Constraints

### MVP Constraints
- **Local only:** No external services (except potential API calls)
- **SQLite:** Single file, not scalable but sufficient
- **5 users:** Limited data for demo
- **No authentication:** Operator view only, no user accounts
- **Static data:** Generate once, not real-time updates

### Performance Requirements
- **Latency:** <5 seconds to generate recommendations per user
- **Page load:** <2 seconds for dashboard/detail pages
- **Database:** Should handle 5 users easily (no optimization needed)

### Compatibility Requirements
- **Python 3.10+:** Modern Python features
- **Browser:** Chrome, Firefox, Safari (modern versions)
- **OS:** macOS, Linux, Windows (development)

## AI/LLM Integration

### MVP
- **No AI:** Hardcoded content templates
- **Rationale generation:** String formatting with data citations

### Post-MVP
- **Gemini API only:** Per project requirements (no OpenAI)
- **Content generation:** LLM for personalized recommendations
- **Rationale enhancement:** AI-generated explanations

## Security Considerations

### MVP (Minimal)
- **No real PII:** All synthetic data
- **Local storage:** SQLite database on local machine
- **No authentication:** Not needed for demo

### Future Considerations
- **Data encryption:** If storing real user data
- **Authentication:** If building end-user interface
- **API security:** Rate limiting, authentication tokens
- **Input validation:** Sanitize user inputs

## Deployment Considerations

### MVP (Local) ✅
- **Development server:** `PYTHONPATH=src python3 -m uvicorn spendsense.app:app --reload`
- **Database:** SQLite file (`spendsense.db`) in project root
- **Server URL:** http://localhost:8000
- **Dashboard:** http://localhost:8000/
- **User Details:** http://localhost:8000/user/{user_id}
- **No deployment:** Run locally for demo
- **Status:** ✅ Tested and working

### Future Deployment
- **Database:** PostgreSQL (AWS RDS) - migration path prepared
- **Web server:** Production ASGI server (Gunicorn + uvicorn workers)
- **Static files:** CDN or static file serving
- **Environment variables:** Config management
- **Docker:** Containerization for deployment

### Database Migration Strategy
- **Current:** SQLite for MVP (local, simple setup)
- **Target:** PostgreSQL (AWS RDS) for production
- **Migration Readiness:** ✅ Code uses standard SQL, parameterized queries
- **Abstraction Layer:** Created `db_config.py` for database-agnostic code
- **Migration Guide:** See `md_files/MIGRATION_GUIDE.md` for detailed instructions
- **Estimated Effort:** 7-11 hours for complete migration
- **Key Changes Needed:** AUTOINCREMENT → SERIAL, connection handling abstraction

## Known Technical Limitations

### MVP
- SQLite not suitable for production scale
- No caching layer
- No background job processing
- No real-time updates
- Limited error handling (basic)

### Future Improvements
- Add caching for frequently accessed data
- Background jobs for signal detection
- WebSocket for real-time updates
- Comprehensive error handling
- Logging and monitoring

## Testing Strategy

### Tools
- **pytest:** Unit and integration testing
- **Manual testing:** UI/UX validation
- **Data validation:** Verify synthetic data quality

### Test Coverage Goals
- **Phase 1:** ✅ 10 tests implemented and passing
- **Phase 2:** ✅ 30 additional tests (40 total tests passing)
- **Phase 3:** ✅ 8 additional tests (48 total tests passing)
- **MVP:** ✅ 48 tests (exceeds target of ≥15)
- **Full project:** ≥20 unit/integration tests (target exceeded)

### Test Types
- **Unit tests:** Signal detection, persona logic, rationale generation
- **Integration tests:** Full pipeline, API endpoints
- **Manual tests:** UI display, edge cases, demo flow

