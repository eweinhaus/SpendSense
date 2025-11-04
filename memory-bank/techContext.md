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

### Required (MVP + Phase 6B)
```
# Core dependencies
faker>=19.0.0

# Web framework (Phase 3)
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
gunicorn>=21.2.0
jinja2>=3.1.2
python-multipart>=0.0.6

# AI Integration (Phase 6B)
openai>=1.0.0  # OpenAI API for content generation

# Testing
pytest>=7.4.0
httpx>=0.25.0
```

### Optional
```
pandas>=2.0.0  # Data analysis (if needed)
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

**liabilities** (Phase 4)
- Primary key: `id`
- Foreign key: `account_id` → accounts
- Fields: `liability_type` ('mortgage' or 'student'), `interest_rate`, `next_payment_due_date`, `last_payment_amount`

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

# Generate data (75 users by default, configurable via NUM_USERS)
python3 -m spendsense.generate_data
# Or: NUM_USERS=60 python3 -m spendsense.generate_data

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

### File Structure (Phase 6B Complete ✅)
```
src/spendsense/
├── database.py               # SQLite setup ✅
├── generate_data.py          # Synthetic data generator ✅
├── detect_signals.py         # Signal detection ✅
├── personas.py               # Persona assignment ✅
├── recommendations.py        # Recommendation engine (72 items, AI integration) ✅
├── content_generator.py      # OpenAI API integration (Phase 6B) ✅
├── partner_offers.py         # Partner offers catalog (Phase 6B) ✅
├── rationales.py             # Rationale generation ✅
├── traces.py                 # Decision trace generation ✅
├── eligibility.py            # Eligibility checks ✅
├── tone_validator.py         # Tone validation (Phase 6) ✅
├── evaluation.py             # Evaluation harness (Phase 6) ✅
├── app.py                    # FastAPI app ✅
├── templates/                # Jinja2 templates ✅
│   ├── base.html
│   ├── dashboard.html
│   ├── user_detail.html      # Updated with partner offers (Phase 6B)
│   └── error.html
├── static/                   # CSS/JS ✅
│   ├── css/style.css
│   └── js/consent.js
├── tests/                    # Test suite (80+ tests) ✅
│   ├── test_content_generator.py # Phase 6B (10 tests)
│   ├── test_partner_offers.py    # Phase 6B (10 tests)
│   └── [other test files]
├── requirements.txt          # Dependencies (includes openai>=1.0.0) ✅
├── pytest.ini               # Test configuration ✅
├── spendsense.db             # SQLite database
└── [planning/, memory-bank/] # Documentation
```

## Technical Constraints

### MVP Constraints
- **Local only:** No external services (except potential API calls)
- **SQLite:** Single file, not scalable but sufficient for 50-100 users
- **75 users default:** Scalable data generation (configurable 50-100 range)
- **No authentication:** Operator view only, no user accounts
- **Static data:** Generate once, not real-time updates
- **Consent enforcement:** Hard requirement - recommendations blocked without consent

### Performance Requirements
- **Latency:** <5 seconds to generate recommendations per user
- **Page load:** <2 seconds for dashboard/detail pages
- **Database:** Handles 75-100 users efficiently (SQLite sufficient for this scale)

### Compatibility Requirements
- **Python 3.10+:** Modern Python features
- **Browser:** Chrome, Firefox, Safari (modern versions)
- **OS:** macOS, Linux, Windows (development)

## AI/LLM Integration

### Phase 6B (Current)
- **OpenAI API:** Integrated for personalized content generation
- **Content generation:** LLM generates personalized recommendations (3-5 per user)
- **Caching:** Aggressive caching by persona + signal combination (24-hour TTL)
- **Fallback:** Graceful fallback to templates if API fails or tone violations
- **Tone validation:** All AI-generated content validated using existing tone_validator
- **Rationale generation:** String formatting with data citations (from templates or AI)
- **Cost control:** Caching minimizes API calls, works without API key

### Environment Variables
- **OPENAI_API_KEY:** Required for AI content generation (optional - system works without it)
- Set via: `export OPENAI_API_KEY="your-key-here"`
- System gracefully degrades to templates if not set

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

### Production Deployment (Render.com) ✅
- **Platform:** Render.com (free tier available)
- **Build command:** `pip install -r requirements.txt`
- **Start command:** `gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT`
- **Configuration:** `render.yaml` file created for deployment
- **Environment variables:** Configured via API (PYTHONPATH, DATABASE_URL, DEBUG), OPENAI_API_KEY set manually
- **Database:** SQLite for demo (PostgreSQL migration available)
- **Static files:** Automatically served by Render
- **HTTPS:** Automatically provided by Render
- **Automated Deployment:** `scripts/deploy_render.py` script created using Render API
- **Service Details:**
  - Service ID: `srv-d44njmq4d50c73el4brg`
  - Service Name: `spendsense`
  - URL: https://spendsense-2e84.onrender.com
  - Dashboard: https://dashboard.render.com/web/srv-d44njmq4d50c73el4brg
  - Branch: `improve_mvp`
  - Region: Ohio
  - Plan: Starter
- **Status:** ✅ Service created successfully, initial deployment in progress

### Deployment Automation
- **Render API Script:** `scripts/deploy_render.py` - Automated service creation and deployment
- **Features:**
  - Checks for existing services
  - Creates new services via Render API
  - Configures environment variables
  - Triggers deployments
  - Uses Python's built-in `urllib` (no external dependencies)
- **Usage:** `python3 scripts/deploy_render.py`
- **API Key:** Set via `RENDER_API_KEY` environment variable or hardcoded in script

### Future Deployment Options
- **Database:** PostgreSQL (AWS RDS or Render PostgreSQL) - migration path prepared
- **Web server:** Production ASGI server (Gunicorn + uvicorn workers) ✅ Configured
- **Static files:** CDN or static file serving (Render handles automatically)
- **Environment variables:** Config management ✅ Configured (automated via API)
- **Docker:** Containerization for deployment (optional)

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
- **Phase 4:** ✅ 6+ additional tests (54+ total tests passing)
- **Phase 5:** ✅ 8+ additional tests (62+ total tests passing)
- **Phase 6:** ✅ 28+ additional tests (70+ total tests passing)
- **Phase 6B:** ✅ 24+ additional tests (80+ total tests passing)
- **Phase 7:** ✅ 13+ additional tests (90+ total tests passing)
- **Current:** ✅ 90+ tests (exceeds target of ≥15)
- **Full project:** ≥20 unit/integration tests (target exceeded by 4x)

### Test Types
- **Unit tests:** Signal detection, persona logic, rationale generation
- **Integration tests:** Full pipeline, API endpoints
- **Manual tests:** UI display, edge cases, demo flow

