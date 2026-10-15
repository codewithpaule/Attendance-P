# POMSOM - University Attendance System

A production-grade university attendance system that prevents students from signing in for absent classmates. A check-in is `PRESENT` only when all three conditions hold: a fresh QR code, passkey identity verification, and physical presence inside the classroom. Anything else becomes `FLAGGED` for teacher review.

## Features

- **Secure Check-in System**: Multi-factor verification using QR codes, WebAuthn passkeys, and geolocation
- **Fraud Detection**: Automatic flagging of suspicious check-ins (shared devices, duplicate coordinates, location anomalies)
- **Early Warning Alerts**: Alerts students and advisors when attendance approaches exam-eligibility thresholds
- **Role-Based Access**: Student, teacher, advisor, and admin roles with appropriate permissions
- **Audit Trail**: Comprehensive audit logging of all system actions
- **Mobile-First UI**: Server-rendered templates with progressive enhancement for mobile devices

## Architecture

This is a modular monolith Django application with clear bounded contexts:

- **core**: Cross-cutting concerns (clock, base model, exceptions, error handling, pagination, permission helpers)
- **accounts**: User identity, activation, passkeys, recovery
- **academics**: Terms, rooms, courses, enrollments, advisor assignments, eligibility policies
- **attendance**: Class sessions, QR tokens, check-ins, spot checks
- **alerts**: Risk assessment, notifications (outbox pattern)
- **audit**: Append-only audit log for all actions

Each Django app follows the same internal structure:
- `models.py`: Data and invariants only
- `selectors.py`: All read queries, always scoped to the acting user
- `services/`: All write use cases (transactional, audit logged)
- `domain/`: Pure Python algorithms, rules, enums, dataclasses
- `adapters/`: Wrappers around third parties (Resend, WebAuthn, signing)
- `api/`: DRF views, serializers, permissions, URLs
- `web/`: Template views, templates, static ES modules
- `tests/`: Mirrors the structure above

## Tech Stack

- **Backend**: Python 3.12, Django 5, Django REST Framework
- **Database**: PostgreSQL (Neon in production, SQLite in development)
- **Authentication**: WebAuthn (passkeys) with python-webauthn
- **Frontend**: Server-rendered Django templates with small ES modules (no SPA, no JS build step)
- **Testing**: pytest, pytest-django, factory_boy
- **Code Quality**: ruff, mypy with django-stubs, pre-commit
- **Deployment**: Vercel (Django function), Neon Postgres
- **Notifications**: Resend (email)

## Development Setup

### Prerequisites

- Python 3.12 or later
- PostgreSQL (for production) or SQLite (for development)
- Docker and Docker Compose (for local development)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd pomsome
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e .
```

4. Copy environment variables:
```bash
cp .env.example .env
```

5. Configure `.env` with your settings (see `.env.example` for reference)

6. Run migrations:
```bash
python manage.py migrate
```

7. Create a superuser:
```bash
python manage.py createsuperuser
```

8. Run the development server:
```bash
make run
# or
python manage.py runserver
```

### Docker Development

```bash
docker-compose up
```

## Testing

Run the full test suite:
```bash
make test
# or
pytest
```

Run with coverage:
```bash
pytest --cov=apps --cov-report=html
```

## Code Quality

Lint and format code:
```bash
make lint
# or
ruff check .
ruff format .
```

Type checking:
```bash
mypy config/
```

## Project Structure

```
pomsom/
├── apps/              # Django apps (bounded contexts)
│   ├── accounts/      # User identity, passkeys
│   ├── academics/     # Courses, enrollments, policies
│   ├── attendance/    # Sessions, check-ins, QR
│   ├── alerts/        # Risk assessment, notifications
│   ├── audit/         # Audit log
│   └── core/          # Cross-cutting concerns
├── config/            # Django settings
│   └── settings/      # Base, dev, prod, test
├── docs/              # Documentation
│   ├── SPEC.md        # Full product specification
│   └── adr/           # Architecture Decision Records
├── static/            # Static files (CSS, JS)
├── templates/         # Django templates
├── manage.py          # Django management script
├── pyproject.toml     # Project configuration
├── docker-compose.yml # Local development
├── Dockerfile         # Production image
├── Makefile           # Common commands
└── .github/           # GitHub Actions workflows
```

### Environment Variables

See `.env.example` for the complete list of required environment variables.

## Security

- Production HTTPS only with HSTS
- Secure and SameSite cookies
- CSRF protection
- Strict ALLOWED_HOSTS
- Secrets only from environment
- Admin on a non-default URL
- Structured JSON logging with request IDs
- Location data is collected only during check-in, never continuously
- Never log coordinates, tokens, assertions, or activation codes

## Privacy

Location data is personal data under the Nigeria Data Protection Act. The system:
- Collects location only during check-in
- Never tracks location continuously
- Shows a privacy notice to users
- Provides a `purge_location_data` command that nulls latitude and longitude older than `LOCATION_RETENTION_DAYS` (default 180) while preserving distance_m


