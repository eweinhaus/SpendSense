# SpendSense MVP

SpendSense is a proof-of-concept system that analyzes transaction data to detect behavioral patterns, assign user personas, and deliver personalized financial education recommendations with clear rationales.

## Overview

SpendSense MVP demonstrates:
- **Signal Detection**: Identifies credit utilization patterns and recurring subscriptions from transaction data
- **Persona Assignment**: Categorizes users based on detected behavioral patterns
- **Personalized Recommendations**: Generates educational recommendations with data-driven rationales
- **Explainability**: Every recommendation includes a clear rationale and decision trace
- **Guardrails**: Consent tracking and eligibility checks to ensure appropriate recommendations

## Features

### Core Capabilities
- **Credit Utilization Detection**: Calculates utilization percentages and flags high-risk patterns
- **Subscription Pattern Detection**: Identifies recurring merchants using pattern matching (same merchant, similar amount, monthly cadence)
- **Persona System**: Assigns users to personas (High Utilization, Subscription-Heavy, Neutral) based on detected signals
- **Recommendation Engine**: Generates 2-3 personalized recommendations per user with data-driven rationales
- **Decision Traces**: Stores complete audit trail for each recommendation (4-step trace)
- **Web Interface**: Operator dashboard to view users, signals, personas, and recommendations
- **Consent Management**: Tracks and manages user consent for data processing
- **Eligibility Checks**: Filters recommendations based on user's existing accounts

### Technical Stack
- **Backend**: Python 3.10+, FastAPI
- **Database**: SQLite (Plaid-compatible schema)
- **Frontend**: Server-rendered HTML with Jinja2 templates, Bootstrap 5
- **Testing**: pytest with comprehensive test coverage

## Quick Start

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Installation

1. **Clone the repository** (if not already done):
```bash
git clone <repository-url>
cd SpendSense
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Initialize the database**:
```bash
PYTHONPATH=src python3 -m spendsense.database
```

This creates the SQLite database (`spendsense.db`) with all required tables and indexes.

4. **Generate synthetic data**:
```bash
PYTHONPATH=src python3 -m spendsense.generate_data
```

This generates 5 users with diverse financial profiles:
- User 1: High Utilization (75% credit utilization)
- User 2: High Utilization with Multiple Cards (one overdue)
- User 3: Subscription-Heavy (major services)
- User 4: Subscription-Heavy (many small subscriptions)
- User 5: Neutral/Healthy financial behavior

5. **Detect signals**:
```bash
PYTHONPATH=src python3 -m spendsense.detect_signals
```

This analyzes transactions and accounts to detect behavioral signals (credit utilization, subscriptions).

6. **Assign personas**:
```bash
PYTHONPATH=src python3 -c "from spendsense.personas import assign_personas_for_all_users; assign_personas_for_all_users()"
```

7. **Generate recommendations**:
```bash
PYTHONPATH=src python3 -c "from spendsense.recommendations import generate_recommendations_for_all_users; generate_recommendations_for_all_users()"
```

8. **Start the web server**:
```bash
PYTHONPATH=src python3 -m uvicorn spendsense.app:app --reload --host 0.0.0.0 --port 8000
```

9. **Open in browser**:
Navigate to `http://localhost:8000` to view the operator dashboard.

## Project Structure

```
SpendSense/
├── src/
│   └── spendsense/          # Main application code
│       ├── app.py            # FastAPI application
│       ├── database.py       # Database setup and connection
│       ├── generate_data.py  # Synthetic data generator
│       ├── detect_signals.py # Signal detection engine
│       ├── personas.py       # Persona assignment logic
│       ├── recommendations.py # Recommendation engine
│       ├── rationales.py     # Rationale generation
│       ├── traces.py         # Decision trace generation
│       ├── eligibility.py    # Eligibility checks
│       ├── templates/        # Jinja2 HTML templates
│       └── static/           # CSS and JavaScript files
├── tests/                    # Test suite
├── planning/                 # PRDs and planning documents
├── memory-bank/              # Project documentation
├── md_files/                 # Additional documentation
├── requirements.txt          # Python dependencies
├── pytest.ini               # Test configuration
└── spendsense.db            # SQLite database (generated)
```

## Usage

### Running Tests

Run all tests:
```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

Run specific test files:
```bash
PYTHONPATH=src python3 -m pytest tests/test_signals.py -v
PYTHONPATH=src python3 -m pytest tests/test_personas.py -v
PYTHONPATH=src python3 -m pytest tests/test_app.py -v
```

### Web Interface

Once the server is running, you can:

1. **View Dashboard**: `http://localhost:8000/`
   - Lists all users with persona badges
   - Shows quick stats (utilization %, subscription count)
   - Links to individual user detail pages

2. **View User Details**: `http://localhost:8000/user/{user_id}`
   - User information and consent status
   - Detected signals with values
   - Assigned persona with criteria
   - Recommendations with rationales
   - Decision traces (expandable)

3. **Toggle Consent**: Click the consent checkbox on user detail page to update consent status

### Regenerating Data

To regenerate all data from scratch:
```bash
# Remove existing database (optional)
rm spendsense.db

# Recreate database
PYTHONPATH=src python3 -m spendsense.database

# Generate data
PYTHONPATH=src python3 -m spendsense.generate_data

# Run full pipeline
PYTHONPATH=src python3 -m spendsense.detect_signals
PYTHONPATH=src python3 -c "from spendsense.personas import assign_personas_for_all_users; assign_personas_for_all_users()"
PYTHONPATH=src python3 -c "from spendsense.recommendations import generate_recommendations_for_all_users; generate_recommendations_for_all_users()"
```

## Architecture

### Data Flow

```
Synthetic Data Generation
    ↓
Signal Detection (Credit Utilization, Subscriptions)
    ↓
Persona Assignment (High Utilization, Subscription-Heavy, Neutral)
    ↓
Recommendation Generation (with Rationales)
    ↓
Eligibility Filtering
    ↓
Web Interface Display
```

### Key Components

**Signal Detection** (`detect_signals.py`):
- Credit utilization: Calculates per-card and max utilization percentages
- Subscriptions: Pattern matching (same merchant, similar amount, monthly cadence)
- Stores signals in database with metadata

**Persona Assignment** (`personas.py`):
- High Utilization: Matches users with ≥50% utilization, interest charges, or overdue cards
- Subscription-Heavy: Matches users with ≥3 recurring merchants and high subscription spend
- Priority logic: High Utilization checked first, then Subscription-Heavy, then Neutral fallback

**Recommendations** (`recommendations.py`):
- Content templates mapped to personas
- Generates 2-3 recommendations per user
- Includes data-driven rationales citing specific user data
- Stores decision traces for auditability

**Guardrails** (`eligibility.py`):
- Filters recommendations based on existing accounts
- Prevents recommending products user already has
- Checks product requirements (e.g., checking account for HYSA)

## Database Schema

The system uses SQLite with a Plaid-compatible schema:

- **users**: User information and consent status
- **accounts**: Account details (checking, savings, credit cards)
- **transactions**: Transaction history with merchant information
- **credit_cards**: Credit card liability data (APR, payments, overdue status)
- **signals**: Detected behavioral signals with values and metadata
- **personas**: Persona assignments with criteria matched
- **recommendations**: Recommendations with content and rationales
- **decision_traces**: 4-step decision traces for each recommendation

## Testing

The test suite includes:
- **Unit Tests**: Signal detection, persona logic, rationale generation, eligibility checks
- **Integration Tests**: Full pipeline from data generation to recommendations
- **API Tests**: FastAPI endpoints (dashboard, user detail, consent toggle)

**Test Coverage**: 51+ tests covering critical paths and edge cases.

## Phase 6 Features (Production Readiness)

### Enhanced Guardrails
- **Comprehensive Eligibility Checks**: Income requirements, credit score checks (if available), account exclusions, product catalog
- **Tone Validation**: Automated detection of prohibited shaming language in generated content
- **Eligibility Logging**: All eligibility failures logged for operator review

### Evaluation Harness
- **Coverage Metrics**: % of users with assigned persona + ≥3 behaviors (target: 100%)
- **Explainability Metrics**: % of recommendations with rationales (target: 100%)
- **Relevance Metrics**: Persona-content fit scoring
- **Latency Metrics**: Time to generate recommendations per user (target: <5 seconds)
- **Fairness Metrics**: Persona and recommendation distribution analysis
- **Automated Reports**: JSON, CSV, and Markdown summary reports

### Operator View Enhancements
- **Dual-Window Display**: Both 30-day and 180-day signal windows with tabs
- **Organized Signal Display**: All signal types (credit, subscriptions, savings, income) organized by category
- **Complete Persona Display**: All 5 personas displayed with color-coded badges

### Testing & Documentation
- **Comprehensive Test Suite**: 70+ tests covering all new features
- **Complete Documentation**: README, schema docs, decision log, API docs
- **Deployment Ready**: Environment configuration and deployment documentation

## Known Limitations (MVP)

- SQLite database (not suitable for production scale, but sufficient for demo)
- No real-time updates (data pre-generated)
- No user authentication (operator view only)
- Simple subscription detection (may miss edge cases with irregular patterns)
- Credit score not tracked (eligibility checks allow by default)
- Income estimation from payroll transactions (may not be 100% accurate)

## Evaluation Harness

Run the evaluation harness to generate metrics:

```bash
PYTHONPATH=src python3 -m spendsense.evaluation
```

This generates:
- Coverage metrics (persona + ≥3 behaviors)
- Explainability metrics (rationales)
- Relevance metrics (persona-content fit)
- Latency metrics (generation time)
- Fairness metrics (distribution analysis)

Reports are saved to `metrics/` directory in JSON, CSV, and Markdown formats.

## Deployment

### Production Deployment (Render.com)

See `docs/DEPLOYMENT.md` for detailed deployment instructions.

**Quick Steps:**
1. Create Render.com account and connect GitHub repository
2. Create Web Service with:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT`
3. Set environment variables (see `.env.example`)
4. Deploy and verify

### Environment Variables

Create a `.env` file (see `.env.example` for template):

```
OPENAI_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///spendsense.db
DEBUG=False
```

## Future Enhancements

See `planning/post_mvp_roadmap.md` for planned features:
- ✅ Scale to 50-100 users (Phase 4)
- ✅ Add more personas (Phase 5)
- ✅ AI/LLM integration (Phase 6)
- ✅ 180-day analysis window (Phase 5)
- ✅ Partner offer integration (Phase 6)
- ✅ Evaluation harness (Phase 6)
- ⏳ End-user interface (Future phase)

## Documentation

- **PRD**: `planning/PRD_MVP.md` - Complete product requirements
- **Phase PRDs**: `planning/PRDs/` - Detailed phase-specific requirements
- **Architecture**: `planning/architecture.mmd` - System architecture diagram
- **Schema Documentation**: `docs/schema.md` - Database schema with ER diagrams
- **Decision Log**: `docs/decisions.md` - Key technical decisions and rationale
- **Deployment Guide**: `docs/DEPLOYMENT.md` - Production deployment instructions
- **Memory Bank**: `memory-bank/` - Project documentation and context
- **Testing Guide**: `md_files/MANUAL_TESTING_GUIDE.md` - Manual testing procedures
- **API Documentation**: Available at `/docs` endpoint when server is running (FastAPI auto-generated)

## License

This project is a proof-of-concept demonstration system.

## Support

For questions or issues, please refer to the documentation in the `planning/` and `memory-bank/` directories.

