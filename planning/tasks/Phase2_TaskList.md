# Phase 2 Task List – Intelligence Layer

> **Context:** Implements Sub-Phase 3 (Persona Assignment) and Sub-Phase 4 (Recommendations) of the MVP as defined in `planning/PRDs/PRD_Phase2_Intelligence.md`.
>
> **Goal:** Assign personas to all users, generate 2-3 personalized recommendations each (with rationales and decision traces), store everything in SQLite, and ship with ≥8 passing tests.

---

## Legend
| ID | Status | Est. hrs | Owner | Description |
|----|--------|---------|-------|-------------|
| ⏳ | pending |         |       | Not started |
| 🚧 | in_progress |     |       | In progress |
| ✅ | completed |       |       | Finished |

---

## Sub-Phase 3 – Persona Assignment

| ID | Status | Est. hrs | Description | Acceptance Criteria |
|----|--------|---------|-------------|---------------------|
| P-1 | ⏳ | 0.5 | Create `personas.py` module skeleton | File exists, imports pass |
| P-2 | ⏳ | 1 | Implement `matches_high_utilization(signals)` | Returns True/False per spec with unit tests |
| P-3 | ⏳ | 1 | Implement `matches_subscription_heavy(signals)` | Returns True/False per spec with unit tests |
| P-4 | ⏳ | 0.5 | Implement priority logic in `assign_persona(user_id)` | Correct persona chosen when multiple match |
| P-5 | ⏳ | 0.25 | Implement Neutral fallback in `assign_persona` | Neutral assigned when no criteria match |
| P-6 | ⏳ | 0.5 | Implement `store_persona_assignment()` DB insert | Row appears in `personas` table |
| P-7 | ⏳ | 0.25 | Add `get_criteria_matched()` helper | Returns human-readable explanation |
| P-8 | ⏳ | 1 | Unit tests: all persona logic cases (≥5) | All tests pass |

### Subtotal Sub-Phase 3: **5 hrs**

---

## Sub-Phase 4 – Recommendation Generation

| ID | Status | Est. hrs | Description | Acceptance Criteria |
|----|--------|---------|-------------|---------------------|
| R-1 | ⏳ | 0.5 | Create `recommendations.py` module skeleton | File exists, imports pass |
| R-2 | ⏳ | 0.75 | Define content templates JSON/dict | Contains 3 templates per persona & neutral |
| R-3 | ⏳ | 0.5 | Implement `get_templates_for_persona()` | Returns correct list |
| R-4 | ⏳ | 1 | Implement `select_template()` & selection rules | Always picks required templates per spec |
| R-5 | ⏳ | 1 | Implement `generate_rationale()` in `rationales.py` | Generates string with fallback logic |
| R-6 | ⏳ | 1 | Implement `generate_decision_trace()` in `traces.py` | Stores 4-step trace in DB |
| R-7 | ⏳ | 0.5 | Implement `store_recommendation()` DB insert | Row appears in `recommendations` table |
| R-8 | ⏳ | 1.5 | Integration function `generate_recommendations(user_id)` | Produces 2-3 recs with rationale & traces |
| R-9 | ⏳ | 1.25 | Unit tests: recommendation selection & rationale (≥6) | All tests pass |
| R-10 | ⏳ | 0.5 | Unit tests: decision trace generation & storage | All tests pass |

### Subtotal Sub-Phase 4: **8 hrs**

---

## Testing & Quality Assurance

| ID | Status | Est. hrs | Description | Acceptance Criteria |
|----|--------|---------|-------------|---------------------|
| T-1 | ⏳ | 0.25 | Configure `pytest` & CI step (optional) | `pytest` command runs |
| T-2 | ⏳ | 0.5 | Full pipeline integration test (signals→persona→recs) | All assertions pass |
| T-3 | ⏳ | 0.5 | Edge case tests (no data, multiple personas, missing fields) | All pass |

### Subtotal Testing: **1.25 hrs**

---

## Documentation & Cleanup

| ID | Status | Est. hrs | Description | Acceptance Criteria |
|----|--------|---------|-------------|---------------------|
| D-1 | ⏳ | 0.25 | Update `progress.md` percentages & notes | Reflect accurate state |
| D-2 | ⏳ | 0.25 | Add docstrings & comments to new modules | Pylint/docstring checker clean |
| D-3 | ⏳ | 0.25 | Update architecture diagram (optional) | Mermaid diagram includes Phase 2 boxes |

### Subtotal Docs: **0.75 hrs**

---

## Phase 2 Summary
* **Total Estimated Time:** **≈15 hrs** (aligns with PRD estimate 11-16 hrs)
* **Success Criteria:**
  * All 5 users assigned personas (High Utilization, Subscription-Heavy, or Neutral)
  * 2-3 recommendations per user with rationales & disclaimers
  * Decision traces stored and retrievable
  * ≥8 new unit tests + 1 integration test passing
  * Code lint-clean & documented

---

*Last updated: <!-- DATE_PLACEHOLDER -->*

