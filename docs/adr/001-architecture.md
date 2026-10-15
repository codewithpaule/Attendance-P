# ADR-001: Modular Monolith Architecture

## Status
Accepted

## Context
We are building a university attendance system with the following requirements:
- Students check in to class using their own phones with QR codes and passkeys
- System must detect fraudulent check-ins (buddy punching, location spoofing)
- Multiple roles: student, teacher, advisor, admin
- Early warning alerts for attendance thresholds
- Nigeria Data Protection Act compliance for location data
- Deployment target: Render web service with Neon/Supabase Postgres

Given these requirements, we need an architecture that:
- Is easy to deploy and operate (no microservices complexity)
- Maintains clear boundaries between domains
- Supports future extraction of bounded contexts if needed
- Enforces dependency discipline to prevent coupling
- Provides testability and maintainability

## Decision
We adopt a modular monolith architecture with the following structure:

### Bounded Contexts (Django Apps)
1. **core**: Cross-cutting concerns (clock, base model, exceptions, error handling, pagination, permission helpers)
2. **accounts**: User identity, activation, passkeys, recovery
3. **academics**: Terms, rooms, courses, enrollments, advisor assignments, eligibility policies
4. **attendance**: Class sessions, QR tokens, check-ins, spot checks
5. **alerts**: Risk assessment, notifications (outbox pattern)
6. **audit**: Append-only audit log for all actions

### Internal App Structure
Each bounded context follows the same internal layout:
- `models.py`: Data and invariants only (constraints, enums, small validators)
- `selectors.py`: All read queries, always scoped to the acting user
- `services/`: All write use cases. Plain arguments (never request objects), transaction.atomic, one audit entry, return domain result
- `domain/`: Pure Python, NO Django imports. Algorithms, rules, enums, dataclasses
- `adapters/`: Wrappers around third parties (Resend, WebAuthn, signing). Interface is a typing.Protocol defined by the consumer
- `api/`: DRF views, input/output serializers, permissions, urls. Thin: validate, call ONE service or selector, serialize
- `web/`: Template views, templates, static ES modules. Same thin rule
- `tests/`: Mirrors the structure above

### Dependency Rules
Dependencies point inward only. Never import around the rules:
- api, web -> services, selectors -> domain, models
- attendance -> academics -> accounts -> core
- alerts -> attendance, academics, accounts
- audit is used only through audit.services.record()

Cross-app access goes through the other app's selectors or services only. No direct model imports across apps.

### Business Logic Placement
- No business logic in views, serializers, templates, signals, or model methods
- Models only protect their own invariants (constraints, enums, small validators)
- One responsibility per function and module
- Pure domain logic lives in domain/ (no Django imports)
- Write orchestration lives in services/ (transactional, audit logged)
- Read queries live in selectors/ (actor-scoped)

### Time Handling
All time comes from core.clock.now() (injected), never datetime.now(). This enables testability and consistent UTC handling with Africa/Lagos display.

### Testing Strategy
- Domain: Table-driven unit tests for pure functions (geo, decision, risk, state machine)
- Services: Database tests for every use case (including edge cases)
- API: Permission matrix test per role and endpoint
- Jobs: Cooldown, dedupe, daily email budget, digest grouping, retry limits
- Coverage floor: 90% on domain and services

### Technology Stack
- Python 3.12
- Django 5
- Django REST Framework
- PostgreSQL
- Server-rendered templates with small ES modules (no SPA, no JS build step)
- drf-spectacular for OpenAPI schema
- pytest, pytest-django, factory_boy for testing
- ruff, mypy with django-stubs for linting and type checking
- pre-commit for git hooks
- Docker Compose for local development (web + postgres)
- gunicorn, whitenoise for production

### Deployment
- Render web service
- Neon or Supabase Postgres
- Two cron jobs: evaluate_attendance_risk and dispatch_notifications
- DATABASE_URL from environment
- HTTPS only, HSTS, secure cookies, CSRF protection

## Consequences
### Positive
- Clear separation of concerns
- Easy to reason about and maintain
- Testable domain logic without Django dependencies
- Deployable as a single artifact
- Future extraction of bounded contexts is straightforward
- Enforced dependency discipline prevents architectural erosion

### Negative
- More files than a typical Django project (but each file has a single responsibility)
- Slightly more boilerplate for cross-app calls (must go through selectors/services)
- Not a microservices architecture (but we don't need that scale yet)

### Mitigations
- Use IDE file nesting to reduce visual clutter
- Document cross-app interfaces in docstrings
- Keep service/selector functions focused and well-named
- Regular architecture reviews (ADR updates)

## Alternatives Considered
1. **Standard Django monolith**: Would lead to God models, unclear boundaries, and hard-to-test code. Rejected.
2. **Microservices**: Too much operational complexity for our current scale and team size. Rejected.
3. **Clean Architecture layers over Django**: Would add unnecessary abstraction and fight Django's patterns. Rejected.

## References
- SPEC.md (full product specification)
- Domain-Driven Design by Eric Evans
- Modular Monolith: A Software Architecture Pattern by Kamil Grzybek
