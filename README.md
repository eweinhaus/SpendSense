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

4. **Generate or ingest data**:

   **Option A: Generate synthetic data** (default):
   ```bash
   PYTHONPATH=src python3 -m spendsense.generate_data
   ```
   
   This generates 75 users (configurable via `NUM_USERS` env var) with diverse financial profiles.

   **Option B: Ingest from CSV/JSON files**:
   ```bash
   # JSON ingestion (nested structure)
   PYTHONPATH=src python3 -m spendsense.data_ingest --format json --file data/sample_users.json
   
   # CSV ingestion (separate files)
   PYTHONPATH=src python3 -m spendsense.data_ingest --format csv \
     --users data/sample_users.csv \
     --accounts data/sample_accounts.csv \
     --transactions data/sample_transactions.csv \
     --credit-cards data/sample_credit_cards.csv \
     --liabilities data/sample_liabilities.csv
   ```
   
   Sample data files are provided in the `data/` directory. See [Data Ingestion](#data-ingestion-from-csvjson) section below for details.

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

10. **Access End-User Interface (Phase 8A)**:
Navigate to `http://localhost:8000/login` to log in as an end user. Use any user's email address or user ID from the operator dashboard to log in (demo mode - no password required).

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

**Test Coverage**: 120+ tests covering critical paths and edge cases (Phase 1: 10, Phase 2: 30, Phase 3: 8, Phase 4: 6+, Phase 5: 8+, Phase 6: 28+, Phase 7: 13+, Phase 8A: 20+, Phase 8B: 25+, Phase 8C: 14+, Data Ingestion: 20+).

## Data Ingestion from CSV/JSON

SpendSense supports ingesting Plaid-compatible data from JSON or CSV files, in addition to synthetic data generation.

### Supported Formats

**JSON Format** (Nested Structure):
- Single JSON file with users, each containing nested accounts, transactions, credit cards, and liabilities
- Plaid-compatible field names with nested structures (e.g., `balances.available`, `personal_finance_category.primary`)
- Example: `data/sample_users.json`

**CSV Format** (Separate Files):
- Multiple CSV files: `users.csv`, `accounts.csv`, `transactions.csv`, `credit_cards.csv`, `liabilities.csv`
- Headers match Plaid field names
- Foreign key relationships via `account_id` (for transactions) and `user_id` (for accounts)
- Example files: `data/sample_*.csv`

### Usage

**JSON Ingestion:**
```bash
PYTHONPATH=src python3 -m spendsense.data_ingest --format json --file data/sample_users.json
```

**CSV Ingestion:**
```bash
PYTHONPATH=src python3 -m spendsense.data_ingest --format csv \
  --users data/sample_users.csv \
  --accounts data/sample_accounts.csv \
  --transactions data/sample_transactions.csv \
  --credit-cards data/sample_credit_cards.csv \
  --liabilities data/sample_liabilities.csv
```

**Custom Database Path:**
```bash
PYTHONPATH=src python3 -m spendsense.data_ingest --format json --file data.json --db-path custom.db
```

### Field Mapping

The ingestion system automatically maps Plaid-compatible fields to the database schema:

- **Nested Values**: `balances.available` → `available_balance`, `balances.current` → `current_balance`
- **Date Formats**: ISO format (YYYY-MM-DD) preferred, with fallback parsing
- **Optional Fields**: Missing optional fields use defaults (e.g., `iso_currency_code` defaults to 'USD')
- **Foreign Keys**: Account IDs are resolved automatically (Plaid `account_id` strings → database integer IDs)

### Error Handling

- **Validation**: All required fields are validated before insertion
- **Transaction Safety**: Each user (JSON) or file (CSV) is processed in a transaction (rollback on errors)
- **Error Reporting**: Detailed error messages with file/row information for debugging
- **Duplicate Handling**: Duplicate emails or account_ids are skipped with warnings

### Sample Data

Sample data files are provided in the `data/` directory:
- `sample_users.json` - Complete JSON example with nested structure
- `sample_users.csv`, `sample_accounts.csv`, etc. - CSV examples

See `md_files/CSV_JSON_INGESTION_DESIGN.md` for detailed field mappings and format specifications.

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

### Operator View Enhancements (Phase 7)
- **Dual-Window Display**: Both 30-day and 180-day signal windows with tabs
- **Organized Signal Display**: All signal types (credit, subscriptions, savings, income) organized by category
- **Complete Persona Display**: All 5 personas displayed with color-coded badges
- **Enhanced Decision Traces**: Formatted decision traces with all 4 steps clearly displayed, expandable data citations
- **Window-Based Persona Rationale**: Shows which signals and windows contributed to persona assignment

### Testing & Documentation (Phase 7)
- **Comprehensive Test Suite**: 90+ tests covering all new features, edge cases, and integration paths
- **Complete Documentation**: README, schema docs, decision log, API docs, limitations
- **Deployment Ready**: Environment configuration and deployment documentation
- **Production Verified**: Render.com deployment with full verification

### End-User Application (Phase 8A)
- **User Authentication**: Session-based authentication with email/user ID login, logout functionality
- **Personalized Dashboard**: User-specific dashboard showing persona, key signals, quick stats, recommendation preview, consent banner
- **Recommendation Feed**: Full recommendation feed with education items, partner offers, feedback functionality, consent enforcement
- **Financial Profile**: Detailed profile with all signals organized by category, 30d/180d window toggle, account summary, transaction insights
- **Consent Management**: User-facing consent interface with status display, explanation, toggle functionality, immediate effect on recommendations
- **Interactive Calculators**: Three financial calculators:
  - Emergency Fund Calculator (3-6 months coverage)
  - Debt Paydown Calculator (amortization schedule)
  - Savings Goal Calculator (monthly savings needed)
- **Protected Routes**: All user routes (`/portal/*`) require authentication, operator routes remain public
- **Test Coverage**: 100+ total tests (Phase 8A: 20+ new tests including unit, integration, and Playwright E2E tests)

### Compliance & Audit Interface (Phase 8B)
- **Consent Audit Log**: Complete audit trail of all consent changes with timestamps, actions, and who made changes
- **Compliance Dashboard**: Real-time compliance metrics (consent coverage, violations, failures, recommendation compliance)
- **Recommendation Compliance Review**: 5-point compliance checking per recommendation:
  1. Active Consent at generation time
  2. Eligibility Check performed
  3. Required Disclaimer present
  4. Complete Decision Trace (all 4 steps)
  5. Rationale Cites Data
- **Regulatory Reporting**: Exportable reports (CSV/JSON/Markdown) for regulatory submissions:
  - Consent audit reports
  - Recommendation compliance reports
  - Compliance summary reports
- **Operator Authentication**: Simple API key authentication for compliance routes
- **Recent Issues Detection**: Automatic identification of compliance issues (missing disclaimers, etc.)

## Known Limitations (MVP)

### Technical Limitations
- **SQLite Database**: Not suitable for production scale (single-file, limited concurrent writes). Sufficient for demo with 50-100 users. PostgreSQL migration path available.
- **No Real-Time Updates**: Data is pre-generated. No live transaction streaming or real-time signal detection.
- **Simple Authentication**: Demo-grade session-based authentication (no password hashing, email/user ID lookup only). Production would require OAuth, MFA, etc.
- **Simple Subscription Detection**: Pattern matching may miss edge cases with irregular patterns or varying merchant names.
- **Credit Score Not Tracked**: Credit score checks are placeholder (allows by default if not available). Real implementation would require credit score integration.
- **Income Estimation**: Income estimated from payroll transactions. May not be 100% accurate for all income types.

### Functional Limitations
- **Fixed Content Catalog**: Content templates are hardcoded. AI-generated content available but requires API key.
- **Single Persona Assignment**: One persona per user (priority-based). Multiple personas could provide richer insights.
- **Limited Signal Types**: Focus on credit, subscriptions, savings, and income signals. Additional signal types could be added.
- **No Historical Analysis**: No time-series analysis or trend detection beyond 180-day window.
- **No A/B Testing**: No built-in experimentation framework for recommendation effectiveness.

### Scalability Considerations
- **Single-Process Architecture**: Monolithic application. Not horizontally scalable without refactoring.
- **No Caching Layer**: No Redis or similar caching for frequently accessed data.
- **No Background Jobs**: Signal detection and recommendation generation run synchronously.
- **File Storage**: SQLite database file on filesystem. Render.com free tier may have limitations.

### Future Enhancements
See `planning/post_mvp_roadmap.md` for planned features:
- PostgreSQL migration for production scale
- Real-time data streaming integration
- End-user interface with authentication
- Advanced analytics and reporting
- Machine learning for signal detection
- A/B testing framework

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
- ✅ End-user interface (Phase 8A)

## Documentation

- **PRD**: `planning/PRD_MVP.md` - Complete product requirements
- **Phase PRDs**: `planning/PRDs/` - Detailed phase-specific requirements
- **Architecture**: `planning/architecture.mmd` - System architecture diagram
- **Schema Documentation**: `docs/schema.md` - Database schema with ER diagrams
- **Decision Log**: `docs/decisions.md` - Key technical decisions and rationale
- **Deployment Guide**: `docs/DEPLOYMENT.md` - Production deployment instructions
- **Memory Bank**: `memory-bank/` - Project documentation and context
- **Testing Guide**: `md_files/MANUAL_TESTING_GUIDE.md` - Manual testing procedures
- **API Documentation**: Available at `/docs` endpoint when server is running (FastAPI auto-generated OpenAPI/Swagger docs)

## License

This project is a proof-of-concept demonstration system.

## Support

For questions or issues, please refer to the documentation in the `planning/` and `memory-bank/` directories.

