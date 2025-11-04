# SpendSense Technical Decisions

This document explains key technical decisions made during the development of SpendSense MVP and their rationale.

## Database Choice: SQLite vs PostgreSQL

**Decision:** Use SQLite for MVP, PostgreSQL for production

**Rationale:**
- SQLite requires no external dependencies or setup
- Perfect for local development and demonstration
- Code uses standard SQL that migrates easily to PostgreSQL
- Sufficient for 50-100 users (MVP scale)

**Trade-offs:**
- Not scalable to production (single-file, no concurrent writes)
- Limited performance at scale
- Migration path prepared with `db_config.py` abstraction

**Future Migration:**
- PostgreSQL migration guide available in `md_files/MIGRATION_GUIDE.md`
- Estimated effort: 7-11 hours

## Frontend: Server-Rendered vs SPA

**Decision:** Use server-rendered HTML with Jinja2 templates

**Rationale:**
- Faster to build for MVP (no build step, no JavaScript framework)
- Simpler deployment (static files handled automatically)
- Sufficient for operator view (not consumer-facing)

**Trade-offs:**
- Less interactive than SPA
- No real-time updates
- Acceptable for MVP operator dashboard

**Future Enhancement:**
- End-user interface could use React/Vue for better UX

## Recommendations: Template-Based vs AI

**Decision:** Use hardcoded content templates for MVP, OpenAI API for post-MVP

**Rationale:**
- No external API dependencies for MVP
- Faster iteration and testing
- More predictable and controllable output
- Can add AI later without breaking existing functionality

**Trade-offs:**
- Less personalized than AI-generated content
- Templates are fixed (need to update code for changes)
- AI integration added in Phase 6 with tone validation

**Future Enhancement:**
- OpenAI API integration for personalized recommendations
- Tone validation ensures content quality

## Persona Assignment: Single vs Multi-Persona

**Decision:** Assign one persona per user with priority logic

**Rationale:**
- Simpler logic, clearer for demo
- Priority system handles multiple matches (High Utilization > Variable Income > Savings Builder > Financial Newcomer > Subscription-Heavy > Neutral)
- Single persona makes recommendations more focused

**Trade-offs:**
- Users may match multiple personas, but priority handles this
- Could show multiple personas in future iterations

## Time Windows: 30-Day vs 180-Day

**Decision:** Implement both 30-day and 180-day windows (Phase 5)

**Rationale:**
- 30-day window provides recent behavioral patterns
- 180-day window provides longer-term trends
- Both windows enable comprehensive analysis
- Signals stored with window parameter for comparison

**Trade-offs:**
- More storage and computation required
- UI complexity increases (tabs/sections for both windows)
- Acceptable trade-off for comprehensive analysis

## Signal Detection: Pattern Matching vs ML

**Decision:** Use pattern matching for signal detection

**Rationale:**
- Transparent and explainable (not a black box)
- Easy to debug and adjust
- No ML model training required
- Sufficient accuracy for MVP use cases

**Trade-offs:**
- May miss edge cases (irregular patterns, varying merchant names)
- Manual tuning required for pattern rules
- ML could improve accuracy but reduce explainability

## Eligibility Checks: Basic vs Comprehensive

**Decision:** Start with basic account checks, expand to comprehensive in Phase 6

**Rationale:**
- MVP: Simple existing account checks sufficient
- Phase 6: Add income, credit score, product catalog, tone validation
- Progressive enhancement approach

**Trade-offs:**
- Basic checks may miss some edge cases
- Comprehensive checks add complexity
- Balance achieved through progressive implementation

## Testing Strategy: Unit + Integration

**Decision:** Comprehensive test suite with unit and integration tests

**Rationale:**
- Ensures code quality and reliability
- Catches regressions early
- Tests serve as documentation
- 62+ tests covering critical paths

**Trade-offs:**
- Requires maintenance as code evolves
- Some edge cases may not be covered
- Acceptable trade-off for quality assurance

## Deployment: Local vs Cloud

**Decision:** Local development for MVP, Render.com for production (Phase 6)

**Rationale:**
- Local development: Faster iteration, no deployment overhead
- Render.com: Easy deployment, free tier available, automatic HTTPS
- SQLite works for demo, PostgreSQL migration available

**Trade-offs:**
- SQLite file persistence on Render.com may need file storage
- Free tier has limitations
- Acceptable for demonstration purposes

## Architecture: Monolithic vs Microservices

**Decision:** Monolithic application structure

**Rationale:**
- Simpler for MVP scale (50-100 users)
- No service orchestration required
- Easier debugging and deployment
- Can refactor to microservices later if needed

**Trade-offs:**
- Not horizontally scalable
- All components in one process
- Acceptable for MVP demonstration

## Logging: Basic vs Comprehensive

**Decision:** Use Python logging module with basic configuration

**Rationale:**
- Simple and sufficient for MVP
- Logs eligibility failures and tone violations
- Can enhance with structured logging later

**Trade-offs:**
- No centralized log aggregation
- Basic format (could use JSON structured logs)
- Sufficient for MVP operator review

## Documentation: Minimal vs Comprehensive

**Decision:** Comprehensive documentation (Phase 6)

**Rationale:**
- Demonstrates professionalism
- Helps future maintenance
- Includes README, schema docs, decision log, API docs

**Trade-offs:**
- Requires maintenance as code evolves
- Takes time to write and update
- Worthwhile investment for project quality

