# SpendSense MVP - Phase 2: Intelligence Layer PRD
## Persona Assignment & Recommendation Engine

**Status:** Planning  
**Dependencies:** Phase 1 (Data Pipeline) - Requires signals table and user data  
**Deliverables:** Persona assignment system, recommendation engine, rationale generation, decision traces  
**Sub-Phases Covered:** Sub-Phase 3 (Persona Assignment) + Sub-Phase 4 (Recommendations)

---

## Overview

Phase 2 implements the intelligence layer that transforms detected signals into actionable insights. This phase includes Sub-Phase 3 (persona assignment logic) and Sub-Phase 4 (recommendation generation, data-driven rationale creation, and decision traceability for auditability).

## Goals

- Assign personas to users based on detected behavioral signals
- Generate 2-3 personalized recommendations per user
- Create data-driven rationales citing specific user data
- Store decision traces for full auditability
- Map recommendations to personas with appropriate content

## Non-Goals (Deferred)

- AI/LLM integration for content generation (hardcoded templates)
- Partner offer integration
- Advanced recommendation ranking algorithms
- Multi-persona assignment (user gets one primary persona)
- 180-day persona analysis

---

## Persona Assignment System

### Persona Definitions

**Persona 1: High Utilization**
- **Priority:** Highest (checked first)
- **Criteria (OR logic - match any):**
  - Any credit card utilization ≥50%
  - Interest charges > 0 (detected)
  - `is_overdue = true` on any credit card
- **Assignment Logic:**
  ```python
  if (max_utilization >= 50) or (interest_charges > 0) or (any_overdue):
      assign_persona(user_id, "high_utilization")
  ```
- **Focus Areas:** Reduce utilization, payment planning, autopay education

**Persona 2: Subscription-Heavy**
- **Priority:** Secondary (checked if High Utilization doesn't match)
- **Criteria (AND logic - match all):**
  - Recurring merchants ≥3
  - AND (monthly recurring spend ≥$50 OR subscription share ≥10%)
- **Assignment Logic:**
  ```python
  if (recurring_count >= 3) and ((monthly_spend >= 50) or (share >= 0.10)):
      assign_persona(user_id, "subscription_heavy")
  ```
- **Focus Areas:** Subscription audit, cancellation tips, bill alerts

**Persona 3: Neutral** (Fallback)
- **Priority:** Lowest (assigned if no other match)
- **Criteria:** Does not match High Utilization or Subscription-Heavy
- **Focus Areas:** General financial education

### Assignment Algorithm

```python
def assign_persona(user_id):
    signals = get_user_signals(user_id)
    
    # Check High Utilization (highest priority)
    if matches_high_utilization(signals):
        persona = "high_utilization"
        criteria = get_high_utilization_criteria(signals)
    
    # Check Subscription-Heavy (second priority)
    elif matches_subscription_heavy(signals):
        persona = "subscription_heavy"
        criteria = get_subscription_criteria(signals)
    
    # Fallback to Neutral
    else:
        persona = "neutral"
        criteria = "No matching persona criteria"
    
    # Store assignment
    store_persona_assignment(user_id, persona, criteria)
    return persona
```

### Priority Logic

**When user matches multiple personas:**
- Assign highest priority persona (High Utilization > Subscription-Heavy)
- Store both criteria matches in metadata for future use
- Document why this priority order was chosen

**When user matches no personas:**
- Assign "Neutral" persona
- Store "No matching criteria" in criteria_matched field
- Still generate generic recommendations

### Data Storage

**personas table:**
```sql
CREATE TABLE personas (
    user_id INTEGER PRIMARY KEY,
    persona_type TEXT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    criteria_matched TEXT,  -- JSON or text explaining why
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Example criteria_matched:**
- High Utilization: "Visa card ending in 4523 at 75% utilization, interest charges $87/month"
- Subscription-Heavy: "4 recurring merchants detected: Netflix, Spotify, Gym, Amazon Prime. Monthly spend: $90, Share: 12%"

---

## Recommendation Engine

### Content Templates

**File:** `recommendations.py` or `content_templates.json`

**High Utilization Templates:**

1. **"Reduce Credit Card Utilization"**
   - Title: "Strategies to Lower Your Credit Card Utilization"
   - Content: "High credit card utilization can negatively impact your credit score. Here are strategies to reduce it..."
   - Key Points:
     - Pay more than minimum
     - Consider balance transfer
     - Create payment plan
   - Target: Users with utilization ≥50%

2. **"Understanding Credit Scores"**
   - Title: "How Credit Utilization Affects Your Credit Score"
   - Content: "Credit utilization is a key factor in your credit score. Keeping it below 30% is ideal..."
   - Target: All High Utilization users

3. **"Set Up Autopay"**
   - Title: "Avoid Missed Payments with Autopay"
   - Content: "Setting up autopay ensures you never miss a payment and avoid late fees..."
   - Target: Users with overdue status or interest charges

**Subscription-Heavy Templates:**

1. **"Audit Your Subscriptions"**
   - Title: "Review Your Recurring Subscriptions"
   - Content: "You have multiple recurring subscriptions. Here's a checklist to review them..."
   - Key Points:
     - List all subscriptions
     - Identify unused services
     - Calculate total monthly cost
   - Target: Users with ≥3 recurring merchants

2. **"Negotiation Tips"**
   - Title: "How to Reduce Subscription Costs"
   - Content: "Many subscription services offer discounts or can be negotiated. Here's how..."
   - Target: Users with high subscription spend

3. **"Set Up Bill Alerts"**
   - Title: "Track Your Recurring Charges"
   - Content: "Set up alerts to track when subscriptions renew and how much they cost..."
   - Target: All Subscription-Heavy users

**Neutral Templates:**

1. **"Build Healthy Financial Habits"**
   - General financial education content
   - Target: Users without specific persona

### Recommendation Selection Logic

```python
def generate_recommendations(user_id):
    persona = get_user_persona(user_id)
    signals = get_user_signals(user_id)
    
    # Get templates for persona
    templates = get_templates_for_persona(persona)
    
    # Select 2-3 recommendations
    recommendations = []
    
    if persona == "high_utilization":
        # Always include "Reduce Utilization"
        recommendations.append(select_template("reduce_utilization", templates))
        
        # Include "Understanding Credit Scores"
        recommendations.append(select_template("credit_scores", templates))
        
        # Include "Set Up Autopay" if overdue or interest charges
        if signals.get("overdue") or signals.get("interest_charges"):
            recommendations.append(select_template("autopay", templates))
    
    elif persona == "subscription_heavy":
        # Always include "Audit Subscriptions"
        recommendations.append(select_template("audit_subscriptions", templates))
        
        # Include "Negotiation Tips" if high spend
        if signals.get("subscription_monthly_spend") >= 75:
            recommendations.append(select_template("negotiation", templates))
        
        # Include "Bill Alerts"
        recommendations.append(select_template("bill_alerts", templates))
    
    # Generate rationale for each
    for rec in recommendations:
        rec["rationale"] = generate_rationale(user_id, rec, signals)
        rec["decision_trace"] = generate_decision_trace(user_id, rec, persona)
    
    return recommendations
```

---

## Rationale Generation

### Rationale Format

**Structure:**
```
[Data-driven observation] + [Specific numbers] + [Actionable insight]
```

**Example (High Utilization):**
> "We noticed your Visa ending in 4523 is at 75% utilization ($3,750 of $5,000 limit). Bringing this below 30% could improve your credit score and reduce interest charges of $87/month."

**Example (Subscription-Heavy):**
> "You have 4 recurring subscriptions totaling $90/month, which represents 12% of your total spending. Reviewing and canceling unused services could save you money each month."

### Rationale Generation Logic

```python
def generate_rationale(user_id, recommendation, signals):
    persona = get_user_persona(user_id)
    
    if persona == "high_utilization":
        # Get credit card data
        card = get_highest_utilization_card(user_id)
        utilization = signals.get("credit_utilization_max")
        interest = signals.get("credit_interest_charges", 0)
        
        # Build rationale with fallbacks
        card_name = card.get("name", "credit card")
        last_4 = card.get("last_4", "XXXX")
        balance = card.get("balance", 0)
        limit = card.get("limit", 0)
        
        rationale = f"We noticed your {card_name} ending in {last_4} is at {utilization:.0f}% utilization "
        rationale += f"(${balance:.2f} of ${limit:.2f} limit). "
        
        if interest > 0:
            rationale += f"Bringing this below 30% could improve your credit score and reduce interest charges of ${interest:.2f}/month."
        else:
            rationale += "Bringing this below 30% could improve your credit score."
    
    elif persona == "subscription_heavy":
        count = signals.get("subscription_count", 0)
        monthly_spend = signals.get("subscription_monthly_spend", 0)
        share = signals.get("subscription_share", 0)
        
        rationale = f"You have {count} recurring subscriptions totaling ${monthly_spend:.2f}/month, "
        rationale += f"which represents {share:.0%} of your total spending. "
        rationale += "Reviewing and canceling unused services could save you money each month."
    
    # Add disclaimer
    rationale += "\n\n*This is educational content, not financial advice. Consult a licensed advisor for personalized guidance.*"
    
    return rationale
```

### Fallback Logic

**Missing Data Handling:**
- Missing card name → Use "credit card"
- Missing last 4 digits → Use "XXXX"
- Missing balance/limit → Use generic language
- Missing merchant names → Use "subscription services"

**Example Fallback:**
> "We noticed high credit card utilization. Bringing this below 30% could improve your credit score."

---

## Decision Traces

### Trace Structure

**Purpose:** Full auditability - explain why each recommendation was made

**Format:**
```
Recommended because:
1. [Signal] detected → [Value]
2. [Persona] assigned → [Criteria matched]
3. [Content] selected → [Reason]
4. [Rationale] generated → [Data cited]
```

**Example Trace:**
```
Recommended because:
1. credit_utilization_max detected → 75%
2. high_utilization persona assigned → Visa card at 75% utilization
3. "Reduce Credit Card Utilization" template selected → Matches persona focus
4. Rationale generated → Cited: Visa ending in 4523, $3,750 balance, $5,000 limit, $87 interest
```

### Decision Trace Storage

**decision_traces table:**
```sql
CREATE TABLE decision_traces (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    recommendation_id INTEGER NOT NULL,
    step INTEGER NOT NULL,
    reasoning TEXT NOT NULL,
    data_cited TEXT,  -- JSON of data points used
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
);
```

### Trace Generation Logic

```python
def generate_decision_trace(user_id, recommendation, persona):
    signals = get_user_signals(user_id)
    trace_steps = []
    
    # Step 1: Signal detection
    if persona == "high_utilization":
        trace_steps.append({
            "step": 1,
            "reasoning": f"credit_utilization_max detected → {signals.get('credit_utilization_max')}%",
            "data_cited": {"utilization": signals.get("credit_utilization_max")}
        })
    elif persona == "subscription_heavy":
        trace_steps.append({
            "step": 1,
            "reasoning": f"subscription_count detected → {signals.get('subscription_count')} recurring merchants",
            "data_cited": {"count": signals.get("subscription_count")}
        })
    
    # Step 2: Persona assignment
    trace_steps.append({
        "step": 2,
        "reasoning": f"{persona} persona assigned → {get_criteria_matched(user_id)}",
        "data_cited": {"persona": persona}
    })
    
    # Step 3: Recommendation selection
    trace_steps.append({
        "step": 3,
        "reasoning": f"'{recommendation['title']}' selected → Matches persona focus",
        "data_cited": {"recommendation_id": recommendation["id"]}
    })
    
    # Step 4: Rationale generation
    trace_steps.append({
        "step": 4,
        "reasoning": f"Rationale generated → Cited specific user data",
        "data_cited": get_rationale_data_cited(user_id, recommendation)
    })
    
    # Store traces
    for step in trace_steps:
        store_decision_trace(user_id, recommendation["id"], step)
    
    return trace_steps
```

---

## Implementation Details

### Persona Assignment

**File:** `personas.py`

**Functions:**
- `assign_persona(user_id)` - Main assignment function
- `matches_high_utilization(signals)` - Check High Utilization criteria
- `matches_subscription_heavy(signals)` - Check Subscription-Heavy criteria
- `get_criteria_matched(user_id, persona)` - Get criteria explanation
- `store_persona_assignment(user_id, persona, criteria)` - Store in database

### Recommendation Engine

**File:** `recommendations.py`

**Functions:**
- `generate_recommendations(user_id)` - Main generation function
- `get_templates_for_persona(persona)` - Get content templates
- `select_template(key, templates)` - Select specific template
- `store_recommendation(user_id, recommendation)` - Store in database

### Rationale Generation

**File:** `rationales.py`

**Functions:**
- `generate_rationale(user_id, recommendation, signals)` - Generate rationale
- `get_credit_card_data(user_id)` - Get card details for rationale
- `format_rationale(template, data)` - Format rationale with data
- `add_disclaimer(rationale)` - Append disclaimer

### Decision Traces

**File:** `traces.py`

**Functions:**
- `generate_decision_trace(user_id, recommendation, persona)` - Generate trace
- `store_decision_trace(user_id, rec_id, step)` - Store trace step
- `get_decision_trace(user_id, rec_id)` - Retrieve trace for display

---

## Testing Strategy

### Unit Tests

1. **Persona Assignment Tests:**
   - Test High Utilization matching (various scenarios)
   - Test Subscription-Heavy matching (various scenarios)
   - Test priority logic (multiple matches)
   - Test no-match scenario (Neutral assignment)
   - Test criteria matching storage

2. **Recommendation Generation Tests:**
   - Test template selection for each persona
   - Test recommendation count (2-3 per user)
   - Test recommendation-persona mapping

3. **Rationale Generation Tests:**
   - Test rationale with complete data
   - Test rationale with missing data (fallbacks)
   - Test disclaimer inclusion
   - Test data citation accuracy

4. **Decision Trace Tests:**
   - Test trace generation for each persona
   - Test trace step storage
   - Test trace retrieval

### Integration Tests

1. **Full Pipeline Test:**
   - Generate recommendations for all 5 users
   - Verify persona assignments
   - Verify recommendation quality
   - Verify decision traces stored

2. **Edge Case Tests:**
   - User with no signals
   - User matching multiple personas
   - User matching no personas
   - Missing data scenarios

---

## Success Criteria

### Persona Assignment
- [ ] All 5 users assigned appropriate personas
- [ ] Priority logic works correctly
- [ ] Criteria matched stored correctly
- [ ] Edge cases handled gracefully

### Recommendations
- [ ] 2-3 recommendations per user
- [ ] Recommendations match persona
- [ ] All recommendations have rationales
- [ ] Rationales cite specific data
- [ ] Disclaimers included on all recommendations

### Decision Traces
- [ ] Traces stored for all recommendations
- [ ] Traces explain decision path
- [ ] Traces cite data used
- [ ] Traces retrievable for display

### Code Quality
- [ ] Code is well-commented
- [ ] Error handling implemented
- [ ] Tests passing (≥3 tests minimum)
- [ ] Template system extensible

---

## Deliverables

1. **Persona Assignment:**
   - `personas.py` with assignment logic
   - Personas stored in database
   - Assignment tests

2. **Recommendation Engine:**
   - `recommendations.py` with generation logic
   - Content templates (JSON or Python dict)
   - Recommendations stored in database

3. **Rationale Generation:**
   - `rationales.py` with generation logic
   - Rationales stored with recommendations
   - Fallback handling

4. **Decision Traces:**
   - `traces.py` with trace generation
   - Traces stored in database
   - Trace retrieval for display

---

## Known Limitations

- Hardcoded content templates (no AI generation)
- One persona per user (no multi-persona)
- Simple recommendation selection (no ranking algorithm)
- Basic rationale generation (string templates)
- No A/B testing or personalization beyond persona

---

## Next Phase Dependencies

Phase 2 outputs required for Phase 3 (Interface & Guardrails):
- Personas assigned to all users (from Sub-Phase 3)
- Recommendations generated with rationales (from Sub-Phase 4)
- Decision traces stored for auditability (from Sub-Phase 4)

Phase 3 will use:
- Personas for UI display (Sub-Phase 5)
- Recommendations for user interface (Sub-Phase 5)
- Decision traces for operator view (Sub-Phase 5)
- All data for dashboard (Sub-Phase 5)
- Consent tracking (Sub-Phase 6)

---

## Timeline Estimate

- Persona assignment: 2-3 hours
- Recommendation engine: 3-4 hours
- Rationale generation: 2-3 hours
- Decision traces: 2-3 hours
- Testing: 2-3 hours
- **Total: 11-16 hours**

---

## Risk Mitigation

**Risk:** Rationale generation may break with missing data
- **Mitigation:** Comprehensive fallback logic, test all scenarios

**Risk:** Recommendations may not be relevant
- **Mitigation:** Manual review of templates, test on all users

**Risk:** Decision traces may be incomplete
- **Mitigation:** Trace every step, test trace retrieval

