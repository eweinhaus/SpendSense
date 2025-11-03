# SpendSense MVP - Phase 3: User Interface & Guardrails PRD
## Web Interface, Consent Tracking & Eligibility Checks

**Status:** Planning  
**Dependencies:** Phase 1 (Data Pipeline), Phase 2 (Intelligence Layer)  
**Deliverables:** FastAPI web application, operator dashboard, user detail pages, consent tracking, eligibility checks  
**Sub-Phases Covered:** Sub-Phase 5 (Web Interface) + Sub-Phase 6 (Guardrails & Polish)

---

## Overview

Phase 3 implements the user-facing interface and compliance guardrails. This phase includes Sub-Phase 5 (FastAPI web application with server-rendered templates and operator dashboard) and Sub-Phase 6 (consent tracking, eligibility filtering, error handling, and demo preparation).

## Goals

- Build functional operator view (dashboard + user detail pages)
- Implement consent tracking with toggle functionality
- Implement basic eligibility checks for recommendations
- Display all data clearly: signals, personas, recommendations, decision traces
- Ensure error handling and graceful degradation
- Create demo-ready interface

## Non-Goals (Deferred)

- End-user facing interface (operator view only for MVP)
- User authentication/authorization
- Advanced filtering and search
- Approve/override functionality (display only)
- Real-time updates (static data for MVP)
- Mobile-responsive design (desktop focus)

---

## Web Application Architecture

### Technology Stack

**Backend:**
- FastAPI (Python web framework)
- Jinja2 (server-side templating)
- SQLite (database - from Phase 1, Sub-Phase 1)

**Frontend:**
- HTML5 with Jinja2 templates
- Bootstrap 5 (CSS framework)
- Minimal JavaScript (only for consent toggle)

**File Structure:**
```
spendsense/
├── app.py                 # FastAPI application
├── database.py            # Database connection (from Phase 1, Sub-Phase 1)
├── templates/
│   ├── base.html          # Base template with layout
│   ├── dashboard.html     # User list page
│   └── user_detail.html   # User profile page
├── static/
│   ├── css/
│   │   └── style.css      # Custom styles (minimal)
│   └── js/
│       └── consent.js     # Consent toggle (minimal)
└── data/
    └── spendsense.db      # SQLite database
```

---

## API Endpoints

### Dashboard Endpoint

**Route:** `GET /`

**Purpose:** Display list of all users with quick stats

**Response:** HTML page (server-rendered)

**Data Required:**
- All users from database
- Persona assignments for each user
- Quick stats (utilization %, subscription count)

**Template:** `templates/dashboard.html`

### User Detail Endpoint

**Route:** `GET /user/{user_id}`

**Purpose:** Display detailed user profile with signals, persona, recommendations

**Response:** HTML page (server-rendered)

**Data Required:**
- User information
- All signals for user
- Persona assignment with criteria
- All recommendations with rationales
- Decision traces for recommendations
- Consent status

**Template:** `templates/user_detail.html`

### Consent Toggle Endpoint

**Route:** `POST /consent/{user_id}`

**Purpose:** Toggle consent status for user

**Request Body:**
```json
{
    "consent": true  // or false
}
```

**Response:**
```json
{
    "success": true,
    "consent_given": true
}
```

**Action:** Updates `users.consent_given` in database

---

## UI Components

### Dashboard Page

**Layout:**
- Header: "SpendSense MVP - Operator Dashboard"
- User list table with columns:
  - User ID
  - Name
  - Email
  - Persona (badge)
  - Quick Stats (utilization %, subscription count)
  - Actions (View Details link)

**Design:**
- Clean, professional layout
- Bootstrap table styling
- Persona badges (color-coded):
  - High Utilization: Red/Orange badge
  - Subscription-Heavy: Blue badge
  - Neutral: Gray badge
- Responsive table (horizontal scroll on mobile)

**Quick Stats:**
- Credit Utilization: "75%" or "N/A" if no cards
- Subscriptions: "4 recurring" or "0" if none

### User Detail Page

**Layout Sections:**

1. **User Information:**
   - Name, Email
   - Consent status (checkbox + label)
   - Last updated timestamp

2. **Detected Signals:**
   - Credit Utilization section:
     - Highest utilization card
     - Utilization percentage
     - Interest charges (if any)
     - Overdue status
   - Subscription section:
     - Number of recurring merchants
     - List of merchant names
     - Monthly recurring spend
     - Subscription share

3. **Persona Assignment:**
   - Persona badge
   - Criteria matched (explanation)
   - Assignment timestamp

4. **Recommendations:**
   - List of 2-3 recommendations
   - Each recommendation card shows:
     - Title
     - Content (brief)
     - Rationale (full text with data citations)
     - Disclaimer
   - Decision trace button (expandable)

5. **Decision Traces:**
   - Expandable section for each recommendation
   - Shows step-by-step decision path
   - Data cited for each step

**Design:**
- Card-based layout
- Clear section separation
- Bootstrap cards for recommendations
- Expandable decision traces (JavaScript)
- Clear visual hierarchy

---

## Consent Tracking

### Consent Status

**Database Field:** `users.consent_given` (BOOLEAN)

**Default:** `false` (no consent by default)

**Display:**
- Checkbox on user detail page
- Label: "User has given consent for data processing"
- Visual indicator: ✓ or ✗

### Consent Toggle

**Implementation:**
- JavaScript function to handle toggle
- AJAX POST to `/consent/{user_id}`
- Update checkbox state
- Show success/error message

**Code:**
```javascript
function toggleConsent(userId) {
    const checkbox = document.getElementById('consent-checkbox');
    const consent = checkbox.checked;
    
    fetch(`/consent/${userId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({consent: consent})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Show success message
        } else {
            // Revert checkbox, show error
            checkbox.checked = !consent;
        }
    });
}
```

### Consent Enforcement

**Logic:**
- Recommendations should check consent status
- If `consent_given = false`, show message: "Consent required for personalized recommendations"
- Still show general educational content (not personalized)

**Implementation:**
```python
def get_recommendations(user_id):
    user = get_user(user_id)
    if not user.consent_given:
        return get_generic_recommendations()  # Non-personalized
    return get_personalized_recommendations(user_id)  # From Phase 2, Sub-Phase 4
```

---

## Eligibility Checks

### Eligibility Rules

**Rule 1: Don't Recommend Products User Already Has**
- If user has savings account → Don't recommend HYSA
- If user has credit card → Don't recommend new credit card (unless balance transfer)
- Simple check: Query accounts table for existing products

**Rule 2: Basic Product Requirements** (MVP - Simplified)
- For HYSA recommendation: User must have checking account (to transfer funds)
- For credit card recommendation: User must have income (inferred from transactions)
- Skip complex credit score checks for MVP

**Implementation:**
```python
def check_eligibility(user_id, recommendation):
    # Get user's existing accounts
    accounts = get_user_accounts(user_id)
    account_types = [acc.type for acc in accounts]
    
    # Rule 1: Don't recommend what they have
    if recommendation.product_type == "savings_account":
        if "savings" in account_types:
            return False, "User already has savings account"
    
    if recommendation.product_type == "credit_card":
        if "credit" in account_types and recommendation.type != "balance_transfer":
            return False, "User already has credit card"
    
    # Rule 2: Basic requirements
    if recommendation.product_type == "savings_account":
        if "checking" not in account_types:
            return False, "User needs checking account to transfer funds"
    
    return True, "Eligible"
```

### Eligibility Filtering

**Apply to Recommendations:**
- Filter recommendations before displaying
- Show only eligible recommendations
- Optionally show why others were filtered (in operator view)

**Display:**
- Show eligibility status in operator view
- For MVP: Just filter out ineligible recommendations
- Don't show "filtered" recommendations to keep UI clean

---

## Error Handling

### Error Scenarios

**1. User Not Found:**
- Route: `/user/{user_id}` where user_id doesn't exist
- Response: 404 error page
- Message: "User not found"

**2. Missing Data:**
- User with no signals → Show "Insufficient data" message
- User with no recommendations → Show "No recommendations available"
- Handle gracefully, don't crash

**3. Database Errors:**
- Connection errors → Show error message
- Query errors → Log and show user-friendly message

**4. Missing Signals:**
- No credit signals → Skip credit section, show subscription section
- No subscription signals → Skip subscription section, show credit section
- Both missing → Show "No signals detected"

### Error Page Template

**File:** `templates/error.html`

**Display:**
- Error message
- Error code (404, 500, etc.)
- Link back to dashboard
- Contact info (if applicable)

### Graceful Degradation

**Missing Data Handling:**
- Missing card name → Show "Credit Card" (generic)
- Missing merchant names → Show "Recurring Charge" (generic)
- Missing balances → Show "N/A" or skip calculation
- Missing recommendations → Show generic financial education

**Example:**
```python
def get_user_signals_display(user_id):
    signals = get_user_signals(user_id)
    
    # Handle missing credit signals
    if not signals.get("credit_utilization_max"):
        return {
            "credit": None,
            "subscription": signals.get("subscription_data")
        }
    
    # Handle missing subscription signals
    if not signals.get("subscription_count"):
        return {
            "credit": signals.get("credit_data"),
            "subscription": None
        }
    
    return signals
```

---

## Implementation Details

### FastAPI Application

**File:** `app.py`

**Structure:**
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    # Get all users with personas
    users = get_all_users_with_personas()
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "users": users
    })

@app.get("/user/{user_id}", response_class=HTMLResponse)
def user_detail(request: Request, user_id: int):
    # Get user data
    user = get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all data
    signals = get_user_signals(user_id)
    persona = get_user_persona(user_id)
    recommendations = get_user_recommendations(user_id)
    traces = get_decision_traces(user_id)
    
    return templates.TemplateResponse("user_detail.html", {
        "request": request,
        "user": user,
        "signals": signals,
        "persona": persona,
        "recommendations": recommendations,
        "traces": traces
    })

@app.post("/consent/{user_id}")
def toggle_consent(user_id: int, consent_data: dict):
    # Update consent status
    success = update_consent(user_id, consent_data["consent"])
    if success:
        return {"success": True, "consent_given": consent_data["consent"]}
    return {"success": False}
```

### Templates

**Base Template:** `templates/base.html`
- HTML structure
- Bootstrap CSS includes
- Navigation (if needed)
- Footer

**Dashboard Template:** `templates/dashboard.html`
- Extends base.html
- User list table
- Links to user detail pages

**User Detail Template:** `templates/user_detail.html`
- Extends base.html
- All sections (signals, persona, recommendations)
- Consent checkbox
- Decision traces (expandable)

### Static Files

**CSS:** `static/css/style.css`
- Minimal custom styling
- Override Bootstrap if needed
- Card styling for recommendations

**JavaScript:** `static/js/consent.js`
- Consent toggle function
- AJAX request handling
- Error handling

---

## Testing Strategy

### Unit Tests

1. **API Endpoint Tests:**
   - Test dashboard endpoint returns HTML
   - Test user detail endpoint with valid user_id
   - Test user detail endpoint with invalid user_id (404)
   - Test consent toggle endpoint

2. **Template Tests:**
   - Test template rendering with sample data
   - Test template with missing data (graceful degradation)
   - Test template with empty data

3. **Eligibility Tests:**
   - Test eligibility checks with various account types
   - Test filtering logic

### Integration Tests

1. **Full Page Load Tests:**
   - Load dashboard, verify all users displayed
   - Load user detail, verify all sections displayed
   - Test consent toggle updates database

2. **Error Handling Tests:**
   - Test 404 for invalid user_id
   - Test graceful degradation with missing data
   - Test database error handling

### Manual Testing

1. **UI/UX Testing:**
   - Verify all data displays correctly
   - Verify layout is clean and professional
   - Verify links work correctly
   - Verify consent toggle works

2. **Browser Testing:**
   - Test in Chrome, Firefox, Safari
   - Verify responsive design (if implemented)
   - Verify JavaScript works

---

## Success Criteria

### Web Interface
- [ ] Dashboard displays all 5 users
- [ ] User detail pages show all data correctly
- [ ] Recommendations display with rationales
- [ ] Decision traces are accessible
- [ ] UI is clean and professional
- [ ] All links work correctly

### Consent Tracking
- [ ] Consent checkbox displays current status
- [ ] Consent toggle updates database
- [ ] Consent enforcement works (if implemented)
- [ ] Consent status persists across page loads

### Eligibility Checks
- [ ] Eligibility checks filter recommendations
- [ ] Ineligible recommendations not shown
- [ ] Checks work for all account types

### Error Handling
- [ ] 404 errors handled gracefully
- [ ] Missing data handled gracefully
- [ ] Database errors handled gracefully
- [ ] No crashes on edge cases

### Code Quality
- [ ] Code is well-commented
- [ ] Templates are clean and maintainable
- [ ] Tests passing (≥2 tests minimum)
- [ ] Demo-ready

---

## Deliverables

1. **FastAPI Application:**
   - `app.py` with all endpoints
   - Working web server
   - Error handling

2. **Templates:**
   - `base.html` with layout
   - `dashboard.html` with user list
   - `user_detail.html` with full user profile
   - `error.html` for error pages

3. **Static Files:**
   - `style.css` with custom styles
   - `consent.js` with toggle functionality

4. **Functionality:**
   - Consent tracking working
   - Eligibility checks implemented
   - Error handling comprehensive

---

## Known Limitations

- No user authentication (operator view only)
- No approve/override functionality
- No advanced filtering or search
- No real-time updates
- Desktop-focused (not fully mobile-responsive)
- Basic eligibility checks (no complex credit scoring)
- Static data (no live Plaid connection)

---

## Demo Preparation

### Demo Checklist

- [ ] All 5 users have data
- [ ] All users have personas assigned
- [ ] All users have recommendations
- [ ] Dashboard loads correctly
- [ ] User detail pages load correctly
- [ ] Consent toggle works
- [ ] Decision traces display
- [ ] No errors in console
- [ ] UI looks professional

### Demo Flow

1. Start server: `uvicorn app:app --reload`
2. Open `http://localhost:8000`
3. Show dashboard with 5 users
4. Click User 1 → Show detail page
5. Demonstrate consent toggle
6. Show decision traces
7. Navigate to User 3 → Show different persona
8. Explain architecture and extensibility

---

## Timeline Estimate

- FastAPI setup: 1-2 hours
- Dashboard page: 2-3 hours
- User detail page: 3-4 hours
- Consent tracking: 1-2 hours
- Eligibility checks: 2-3 hours
- Error handling: 2-3 hours
- Styling and polish: 2-3 hours
- Testing: 2-3 hours
- **Total: 15-23 hours**

---

## Risk Mitigation

**Risk:** UI may not display data correctly
- **Mitigation:** Test with all user types, handle missing data gracefully

**Risk:** Consent toggle may not work
- **Mitigation:** Test AJAX requests, handle errors, verify database updates

**Risk:** Eligibility checks may be too restrictive
- **Mitigation:** Start with simple rules, test on all users, adjust as needed

**Risk:** Demo may have errors
- **Mitigation:** Test all scenarios, prepare fallback data, practice demo flow

