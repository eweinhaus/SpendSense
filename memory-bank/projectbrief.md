# SpendSense Project Brief

## Project Overview

SpendSense is a take-home assignment for a full-stack software engineer position. The project requires building an explainable, consent-aware system that detects behavioral patterns from transaction data (Plaid-style), assigns user personas, and delivers personalized financial education recommendations with clear guardrails around eligibility and tone.

## Core Challenge

Banks generate massive transaction data through Plaid integrations but struggle to turn it into actionable customer insights without crossing into regulated financial advice. The solution must be:
- **Explainable:** Every recommendation needs a clear rationale citing specific data points
- **Consent-aware:** Require explicit opt-in before processing data
- **Guardrails:** Prevent ineligible offers, enforce appropriate tone, include disclaimers
- **Auditable:** Full decision traces for oversight

## Project Scope

### MVP Scope (Current Focus)
- 5 synthetic users (not 50-100)
- 2 personas (High Utilization, Subscription-Heavy)
- Hardcoded recommendations (no AI)
- 30-day window only (not 180-day)
- Basic operator view (not end-user interface)
- SQLite database (local storage)

### Full Project Scope (Post-MVP)
- 50-100 synthetic users
- 5 personas (including custom persona)
- AI/LLM integration for recommendations (Gemini API only - no OpenAI)
- Both 30-day and 180-day windows
- All signal types (credit, subscriptions, savings, income)
- Partner offer integration
- Evaluation harness
- End-user interface

## Key Deliverables

1. **Synthetic Data Generator:** Plaid-compatible data for 50-100 users
2. **Feature Pipeline:** Signal detection for subscriptions, savings, credit, income patterns
3. **Persona System:** Assignment logic for 5 personas with prioritization
4. **Recommendation Engine:** Personalized education with plain-language rationales
5. **Guardrails:** Consent, eligibility, tone checks
6. **Operator View:** Oversight interface with decision traces
7. **Evaluation System:** Metrics harness with coverage, explainability, relevance, latency, fairness

## Success Criteria

| Category | Metric | Target |
|----------|--------|--------|
| Coverage | Users with assigned persona + ≥3 behaviors | 100% |
| Explainability | Recommendations with rationales | 100% |
| Latency | Time to generate recommendations per user | <5 seconds |
| Auditability | Recommendations with decision traces | 100% |
| Code Quality | Passing unit/integration tests | ≥10 tests |
| Documentation | Schema and decision log clarity | Complete |

## Project Status

**Current Phase:** Planning complete, ready to begin implementation
**Timeline:** No strict deadline (individual/small team project)
**Approach:** Build MVP first as proof of concept, then expand to full requirements

## Core Principles

- **Transparency over sophistication:** Explainable logic, no black boxes
- **User control over automation:** Consent required, revocable
- **Education over sales:** Focus on financial education, not product promotion
- **Fairness built in:** Demographic parity checks, no harmful suggestions

## Technical Contact

**Bryce Harris** - bharris@peak6.com

