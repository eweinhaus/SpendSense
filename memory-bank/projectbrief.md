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

### MVP Scope (Current Status)
- ✅ 50-100 synthetic users (75 default, configurable)
- ✅ 5 personas (High Utilization, Variable Income Budgeter, Savings Builder, Financial Newcomer, Subscription-Heavy, Neutral)
- ✅ Hardcoded recommendations (no AI) - templates for all 5 personas
- ✅ Both 30-day and 180-day windows implemented
- ✅ All signal types (credit, subscriptions, savings, income)
- ✅ Basic operator view with dual-window signal display
- ✅ SQLite database (local storage)
- ✅ Enhanced guardrails (eligibility, tone validation) - Phase 6 Complete
- ✅ Evaluation harness - Phase 6 Complete
- ✅ Operator view updates - Phase 6 Complete
- ✅ Comprehensive testing - Phase 6 Complete
- ✅ Documentation - Phase 6 Complete
- ✅ Deployment readiness - Phase 6 Complete
- ✅ Production deployment (Render.com) - Service created (srv-d44njmq4d50c73el4brg), automated script created, initial deployment in progress
- ⏳ End-user interface - Future phase

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
| Code Quality | Passing unit/integration tests | 70+ tests ✅ |
| Documentation | Schema and decision log clarity | Complete |

## Project Status

**Current Phase:** Phase 6 Complete - Production Readiness
**Timeline:** No strict deadline (individual/small team project)
**Approach:** Build MVP first as proof of concept, then expand to full requirements
**Completed:** Phases 1-6 (Data Pipeline, Intelligence Layer, Interface, Data Expansion, Intelligence Completion, Production Readiness)
**Next:** Production Deployment (Render.com) - Service created, automated script created, initial deployment in progress

## Core Principles

- **Transparency over sophistication:** Explainable logic, no black boxes
- **User control over automation:** Consent required, revocable
- **Education over sales:** Focus on financial education, not product promotion
- **Fairness built in:** Demographic parity checks, no harmful suggestions

## Technical Contact

**Bryce Harris** - bharris@peak6.com


