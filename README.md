# POMSOM - University Attendance System

A production-grade university attendance system that prevents students from signing in for absent classmates. A check-in is `PRESENT` only when all three conditions hold: a fresh QR code, passkey identity verification, and physical presence inside the classroom. Anything else becomes `FLAGGED` for teacher review.

## 🌐 Live Deployment

**Production URL:** https://pomsom.akili.com.ng

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

7. Create admin account:
```bash
python create_admin.py
```
This creates:
- Email: admin@pomsom.akili.com.ng
- Password: Admin@1234
- Role: ADMIN

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

**Local Development:**
- **Local URL:** http://localhost:8000
- **Login Page:** http://localhost:8000/login/
- **Admin Panel:** http://localhost:8000/admin/
- **API Documentation:** http://localhost:8000/api/v1/docs/

## 📖 User Guide

### Access URLs

- **Live Production:** https://pomsom.akili.com.ng
- **Login Page:** https://pomsom.akili.com.ng/login/
- **Admin Panel:** https://pomsom.akili.com.ng/admin/
- **API Documentation:** https://pomsom.akili.com.ng/api/v1/docs/

### User Roles & Flows

#### 1. Admin Flow

**Access:** https://pomsom.akili.com.ng/admin/

**Setup Steps:**
1. Create admin account (done locally with `python manage.py createsuperuser`)
2. Access Django Admin panel
3. Configure initial data:
   - Create academic terms (e.g., 2024/2025 First Semester)
   - Add rooms/buildings (e.g., Room 101, Lecture Hall A)
   - Create courses (e.g., CSC 101, MTH 201)
   - Import students via CSV (email, student_id, full_name)
   - Import teachers via CSV (email, full_name)
   - Import advisors via CSV (email, full_name)
   - Create enrollments (link students to courses)
   - Assign advisors to students

**Admin Responsibilities:**
- Manage users (students, teachers, advisors)
- Configure attendance policies (minimum attendance % for exam eligibility)
- Review flagged check-ins
- Monitor system health via audit logs
- Export attendance reports

#### 2. Teacher Flow

**Login:** https://pomsom.akili.com.ng/login/

**Teacher Account Setup:**
1. Admin creates teacher account via CSV import or Admin panel
2. Teacher receives activation code via email
3. Teacher visits https://pomsom.akili.com.ng/activate/
4. Teacher enters activation code
5. Teacher sets password (for recovery)
6. Teacher registers passkey (fingerprint/Face ID on phone)
7. Account activated and ready!

**Daily Class Session:**
1. Log in with passkey at https://pomsom.akili.com.ng/login/
2. Navigate to "My Sessions" or create new session
3. Select course and room
4. Open session for check-ins
5. Display QR code on projector screen
6. Monitor student check-ins in real-time
7. Close session after class
8. Review flagged check-ins (suspicious activity)
9. Finalize attendance (approve/reject flagged entries)

**Teacher Dashboard:**
- View upcoming sessions
- See active session QR code
- Monitor live check-ins
- Review flagged check-ins
- Approve/reject suspicious entries
- View attendance reports per course

#### 3. Student Flow

**Account Activation:**
1. Receive activation code via email (sent by admin)
2. Visit https://pomsom.akili.com.ng/activate/
3. Enter activation code
4. Create password (for recovery)
5. Register passkey (recommended: use phone fingerprint or security key)
6. Registration complete!

**Daily Check-in Process:**
1. Open https://pomsom.akili.com.ng on phone browser
2. Log in with passkey (fingerprint/Face ID)
3. See today's scheduled classes
4. When teacher displays QR code:
   - Allow camera access
   - Scan QR code displayed in classroom
   - Wait for location verification (GPS)
   - Wait for passkey verification
   - See check-in status (PRESENT or FLAGGED)
5. If FLAGGED: Report to teacher for manual review

**Student Dashboard:**
- View class schedule
- Check attendance history
- See attendance percentage per course
- Receive early warning alerts (if attendance drops below threshold)
- Manage passkeys (add/remove devices)

#### 4. Advisor Flow

**Login:** https://pomsom.akili.com.ng/login/

**Advisor Dashboard:**
- View assigned students
- Monitor attendance across all courses
- Identify at-risk students (low attendance)
- Receive early warning alerts
- Contact students with attendance issues
- Generate attendance reports for academic review

### Check-in Decision Flow

```
Student scans QR code
         ↓
Is QR code fresh (within 20 seconds)?
         ↓ NO → FLAGGED (stale code)
         ↓ YES
Is passkey valid and registered to student?
         ↓ NO → FLAGGED (invalid passkey)
         ↓ YES
Is student physically in classroom (geolocation)?
         ↓ NO → FLAGGED (outside classroom)
         ↓ YES
Is there suspicious activity?
         ↓ YES → FLAGGED (possible fraud)
         ↓ NO
    → PRESENT ✓
```

### Fraud Detection Rules

A check-in is automatically FLAGGED if:
- QR code is expired (> 20 seconds old)
- Passkey not registered to the student
- Location outside classroom radius (> 100m accuracy threshold)
- Multiple check-ins from same device for different students
- Coordinates identical to another recent check-in (possible device sharing)
- Network burst pattern (rapid successive check-ins)
- New passkey used within 24 hours of registration

All FLAGGED check-ins require **manual teacher review** before finalizing.

### Initial Setup Checklist

**First-time Admin Setup:**

1. **Create Admin Account**
   ```bash
   python create_admin.py
   ```
   This creates an admin account with:
   - Email: admin@pomsom.akili.com.ng
   - Password: Admin@1234
   - Role: ADMIN

   **IMPORTANT:** Change this password after first login!

2. **Access Admin Panel**
   - Visit: https://pomsom.akili.com.ng/admin/
   - Log in with admin credentials

3. **Configure Academic Structure**
   - Go to "Academics" section
   - Add Terms (e.g., "2024/2025 First Semester")
   - Add Rooms (e.g., "Room 101", "Lecture Hall A")
   - Add Courses (e.g., "CSC 101 - Introduction to Computer Science")

4. **Import Users**
   - Prepare CSV files for students, teachers, advisors
   - Format: `email,student_id,full_name` (for students)
   - Format: `email,full_name` (for teachers/advisors)
   - Use Admin panel import function

5. **Create Enrollments**
   - Link students to their courses
   - Assign advisors to students

6. **Configure Policies**
   - Set minimum attendance percentage for exam eligibility (default: 75%)
   - Configure location retention period (default: 180 days)

7. **Test the System**
   - Create a test student account
   - Activate the account
   - Register a passkey
   - Test QR code check-in flow
   - Verify attendance tracking

### CSV Import Format

**Students CSV:**
```csv
email,student_id,full_name
student1@university.edu,STU001,John Doe
student2@university.edu,STU002,Jane Smith
```

**Teachers CSV:**
```csv
email,full_name
teacher1@university.edu,Dr. Alan Turing
teacher2@university.edu,Prof. Grace Hopper
```

**Advisors CSV:**
```csv
email,full_name
advisor1@university.edu,Dr. Margaret Hamilton
advisor2@university.edu,Prof. Katherine Johnson
```

**Enrollments CSV:**
```csv
student_email,course_code
student1@university.edu,CSC101
student1@university.edu,MTH201
student2@university.edu,CSC101
```

### Troubleshooting

**Student can't log in:**
- Check if account is activated
- Verify passkey is registered
- Try password recovery option

**QR code not scanning:**
- Ensure QR code is displayed clearly
- Check camera permissions
- Update browser to latest version

**Location verification failing:**
- Enable GPS/location services on phone
- Ensure you're physically in the classroom
- Check if building has GPS signal

**Check-in showing FLAGGED:**
- Check if QR code was stale (scan faster next time)
- Verify you're using your own passkey
- Ensure you're within classroom boundaries
- Contact teacher for manual review



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

## Future Enhancements

- **Map Interface for Classroom Locations**: Visual map to pin classroom locations and draw radius circles instead of manual coordinate entry
- **Push Notifications**: Real-time alerts for students when check-in is about to open
- **Offline Mode**: Allow check-in queuing when internet is poor, sync when reconnected
- **Multi-Language Support**: Support for local languages
- **Advanced Analytics**: Attendance trends, heatmaps, and predictive analytics
- **Mobile App**: Native mobile apps for better camera performance and background location

## Privacy

Location data is personal data under the Nigeria Data Protection Act. The system:
- Collects location only during check-in
- Never tracks location continuously
- Shows a privacy notice to users
- Provides a `purge_location_data` command that nulls latitude and longitude older than `LOCATION_RETENTION_DAYS` (default 180) while preserving distance_m


Location data is personal data under the Nigeria Data Protection Act. The system:
- Collects location only during check-in
- Never tracks location continuously
- Shows a privacy notice to users
- Provides a `purge_location_data` command that nulls latitude and longitude older than `LOCATION_RETENTION_DAYS` (default 180) while preserving distance_m


