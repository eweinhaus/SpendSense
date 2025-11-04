# Product Context

## Why This Project Exists

Banks integrate with Plaid to access massive amounts of transaction data from their customers, but they struggle to transform this data into actionable, personalized insights without:
1. Crossing into regulated financial advice territory
2. Lacking explainability for why recommendations are made
3. Missing proper consent and guardrails
4. Failing to provide clear, educational value to customers

## Problem Statement

**Problem:** Financial institutions need to help customers improve their financial health through personalized education, but must do so in a way that is explainable, consent-aware, and compliant with regulations.

**Solution:** SpendSense provides a system that:
- Detects behavioral patterns from transaction data (subscriptions, credit utilization, savings, income stability)
- Assigns users to personas based on these patterns (5 personas with priority logic)
- Delivers personalized financial education recommendations
- Provides clear rationales citing specific data points
- Enforces comprehensive guardrails (consent, enhanced eligibility, tone validation)
- Maintains full auditability through decision traces
- Evaluates system performance through comprehensive metrics harness

## Target Audience

### Primary (MVP)
- **Hiring managers and interviewers:** Evaluating technical capabilities, problem-solving, and system design skills
- **Demo viewers:** Assessing the quality of the implementation and presentation

### Secondary (Full Product)
- **Bank customers:** End users who would receive personalized financial education
- **Bank operators:** Staff who oversee recommendations and ensure quality
- **Compliance officers:** Reviewing decision traces and ensuring guardrails are followed

## User Experience Goals

### MVP (Operator View)
- Clean, professional dashboard showing all users
- Clear display of signals, personas, and recommendations
- Easy navigation between users
- Decision traces accessible for auditability
- Consent toggle functionality

### Full Product (End Users)
- Personalized dashboard showing their financial insights
- Recommendation feed with educational content
- Clear explanations of why recommendations are relevant
- Consent management interface
- Interactive calculators and tools

## Key Value Propositions

1. **Explainability:** Every recommendation has a clear rationale citing specific data
2. **Compliance:** Built-in guardrails for consent, eligibility, and tone
3. **Personalization:** Recommendations tailored to detected behavioral patterns
4. **Education Focus:** Helps users understand their finances, not just sell products
5. **Auditability:** Full decision traces for oversight and compliance

## Success Metrics

- **Coverage:** ✅ 100% of users with assigned persona + ≥3 detected behaviors (Phase 6: verified via evaluation harness)
- **Explainability:** ✅ 100% of recommendations with plain-language rationales (Phase 6: verified via evaluation harness)
- **Relevance:** ✅ 100% persona-content fit (Phase 6: verified via evaluation harness)
- **Latency:** ✅ 0.007s average (target: <5s) (Phase 6: verified via evaluation harness)
- **Fairness:** ✅ Persona and recommendation distribution analysis (Phase 6: implemented)
- **Signal Detection:** ✅ All signal types (credit, subscriptions, savings, income) for both 30d and 180d windows
- **Persona Coverage:** ✅ 5 personas implemented with clear criteria and priority logic
- **Guardrails:** ✅ Enhanced eligibility checks (income, credit score, account exclusions, product catalog) + tone validation
- **Evaluation:** ✅ Comprehensive metrics harness with automated reporting

## Competitive Context

This is a take-home assignment, not a commercial product. However, the approach demonstrates:
- Understanding of financial data analysis
- Ability to build explainable AI systems
- Attention to compliance and guardrails
- Full-stack development capabilities
- System design and architecture skills

## Future Vision

If this were a production system, the vision would include:
- Real-time Plaid integration
- Advanced AI for content generation
- A/B testing for recommendation effectiveness
- Mobile app for end users
- Integration with bank systems
- Compliance reporting and analytics
- Scalability to millions of users



