# POMSOM Attendance System

POMSOM records attendance for university classes. Students check in with a rotating QR code, their registered passkey, and a fresh location reading. The location is compared with the classroom point and radius saved for that course.

The application uses Django, Django REST Framework, SQLite for local development, and PostgreSQL on Neon in production. The web interface uses Django templates and JavaScript modules.

## What It Does

- Admins create terms, courses, users, and course enrollments.
- Teachers set the classroom point and allowed radius for each course, schedule class times, open check-in, and display a QR code.
- Students scan the QR code, share their current location, and confirm their registered passkey.
- The system records the check-in location with that attendance record. It does not save a permanent student profile location or track location continuously.
- Teachers view enrolled students and attendance status, inspect flag reasons, review flagged records, and finalize closed sessions.
- The teacher roster shows an attendance warning when attendance is below the configured threshold. The default is 80 percent after at least three completed sessions.

## Local Setup

### Requirements

- Python 3.12
- Git
- PowerShell on Windows, or a shell on macOS or Linux

Local development uses SQLite. PostgreSQL and Docker are not required for the basic local workflow.

### Install and Run on Windows

Run these commands from the repository directory in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python manage.py migrate
python create_local_admin.py
python manage.py runserver 127.0.0.1:8000
```

If PowerShell blocks virtual environment activation, run this once for your user account and activate again:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Open these local pages:

- App and login: http://127.0.0.1:8000/
- Django admin: http://127.0.0.1:8000/admin/
- API documentation: http://127.0.0.1:8000/api/v1/docs/

`create_local_admin.py` creates a local SQLite administrator with email `admin@pomsom.akili.com.ng` and password `Admin@1234` if one does not already exist. This script is for local development only. Change that password before using the local database with real user data. Do not run this script against production.

The local development settings use SQLite and default WebAuthn settings for localhost. Production secrets belong in the hosting provider's environment settings, not in source control.

### Verify the Installation

Open another terminal with the virtual environment activated and run:

```powershell
python manage.py check
pytest
ruff check .
```

`python manage.py check` verifies Django configuration. `pytest` runs the automated tests. `ruff check .` checks Python style and common errors.

## Initial Admin Setup

1. Sign in at `/admin/` with the local administrator account created above.
2. Under Academics, create a term with its start and end dates.
3. Under Accounts, create teacher accounts with email and full name. Saving an account sends an activation email when email delivery is configured.
4. Create student accounts with email, full name, and student number. A student number is required.
5. Under Academics, create courses and assign each course to its teacher and term.
6. Enroll students in courses by creating Enrollment records in Django admin.
7. Optionally create an Eligibility Policy. A course-specific policy takes priority over a global policy. Without either, the teacher roster uses the 80 percent default.
8. If an activation email does not arrive, select the pending account in Accounts and use the Resend activation email action. Email delivery requires valid Resend settings.

The admin interface does not currently provide CSV import screens. Create users, courses, and enrollments through the admin forms or use the documented API.

## Account Activation and Sign-In

1. Open the activation link from the account email or visit `/activate/`.
2. Enter the activation code and the account identity requested by the page.
3. Set a recovery password and register a passkey on the device or browser that will be used to sign in and check in.
4. Sign in at `/login/` with the account email and registered passkey.
5. Use the Log out button in the top account bar to end the browser session. Logout is a POST action, so opening `/logout/` directly in the address bar is not the logout procedure.

Passkeys are tied to the website domain and browser credential store. Use the same site and browser profile for activation, sign-in, and student check-in.

## Teacher Workflow

### Set the Classroom Location

1. Sign in with the teacher account.
2. Open `/teacher/classrooms/`.
3. Select the course.
4. Click the map to set the classroom point.
5. Set the allowed radius. This is the maximum distance used for check-in, not the GPS accuracy value.
6. Save the location. A classroom must be saved before scheduling a session for that course.

### Schedule and Open a Class

1. Open `/teacher/sessions/`.
2. Select the course and enter the class start and end date and time.
3. Schedule the class. Times use the configured application time zone, which defaults to `Africa/Lagos`.
4. Start check-in when the button becomes available. Check-in may open no earlier than 20 minutes before the scheduled start.
5. Display the live QR page on the classroom screen. The QR token refreshes regularly and expires after 15 seconds.
6. Close check-in early if needed. Before the scheduled end, a closed session can be reopened. The teacher can add up to 120 minutes; adding time to a closed session reopens it.

### View and Review Attendance

1. From the session list or live QR page, open Attendance roster.
2. The roster includes all students enrolled in the course, including students who have not checked in.
3. Review each student's status, check-in time, distance from the room, GPS accuracy, attendance percentage, and flag reasons.
4. For each flagged check-in, choose Approve present or Mark absent. Add a note when useful. The system records who reviewed it and when.
5. Close the session before finalizing. Resolve all flagged check-ins and pending spot checks first. Finalize attendance from the roster for a closed session.

### Attendance Warning Calculation

The roster calculates attendance as:

```text
present check-ins in completed sessions / number of completed sessions * 100
```

Only closed or finalized class sessions are included. A check-in contributes to the numerator when its final status is Present. A flagged check-in does not count as present until a teacher approves it. A completed class with no present check-in counts as not present.

The default warning threshold is 80 percent. The roster shows a warning after at least three completed sessions when attendance is below the threshold. A course-specific Eligibility Policy overrides the global policy. A global policy overrides the default.

The background attendance-risk evaluator and email notification dispatcher are not implemented. The warning described here appears on the teacher attendance roster. It does not currently send automatic email or in-app alerts.

## Student Workflow

1. Activate the account and register a passkey.
2. Sign in on the phone or browser with that passkey.
3. Open the teacher's live QR link or go to `/checkin/` and scan the displayed code with the camera. Pasting the QR link is also supported.
4. Allow location access when asked. Location is requested for this check-in only.
5. The browser checks the reading against the saved classroom point and radius. If outside the area, go to class and share the location again.
6. Confirm identity with the passkey registered to this student account.
7. Read the result. A successful check-in records the current location with that attendance record. A flagged check-in needs teacher review.

A newly registered passkey may be flagged for review during its first 24 hours. Other flag reasons include low GPS accuracy, a location near the radius boundary, repeated device signals, or repeated coordinates. Teachers can see the reasons on the roster.

Camera access requires HTTPS or localhost. If camera scanning is unavailable, check browser camera permission or paste the QR link. Location permission must also be allowed by the browser and device.

## Troubleshooting

### Student Cannot Sign In

- Confirm the account was activated.
- Use the same browser profile and site where the passkey was registered.
- Confirm the account has an active passkey under `/passkeys/` after signing in.

### Teacher Does Not See a Course

- Confirm the course is assigned to that teacher in Django admin.
- Open `/teacher/classrooms/` and save a classroom point and radius for the course before scheduling a session.

### QR Code Is Missing

- Confirm the class session is open and the teacher is viewing that session's QR page.
- Reload the page after the deployment containing the latest QR rendering code is active.
- Confirm the authenticated teacher owns the session.

### Student Check-In Is Flagged

- Open the session's Attendance roster to see the recorded reason.
- `New Credential` means the passkey was registered less than 24 hours before check-in.
- `Low Gps Accuracy` means the device location estimate is too imprecise.
- `Gps Borderline` means the location estimate is near the edge of the classroom radius.
- The teacher can approve the check-in as present or mark it absent after review.

### Classroom Page Shows a Database Column Error

Run the GitHub Actions `migrate` workflow using the branch containing the migration. The workflow requires `DATABASE_URL_DIRECT` and `SECRET_KEY` repository secrets. It uses `migrate --fake-initial` so existing tables are recorded and new migration operations are applied.

## Production Deployment

The production application runs on Vercel and uses Neon PostgreSQL. Configure production secrets in the hosting provider and GitHub Actions. Do not commit `.env` files or production credentials.

When a release includes database migrations:

1. Push the migration files to the deployment branch.
2. Run the GitHub Actions workflow named `migrate` from that branch.
3. Confirm the workflow succeeds before relying on code that queries the new columns.
4. Confirm the Vercel deployment uses the same branch and commit.

The migration workflow connects with the direct Neon database URL. `DATABASE_URL` used by the running app may be pooled and should not be used for schema migrations.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for Neon, Vercel, environment, and rollback details.

## Privacy and Security

- Location is requested only during student check-in, not continuously.
- Location coordinates are stored with the attendance record to support review and retention cleanup.
- QR tokens are short lived.
- Login, activation, and check-in identity verification use WebAuthn passkeys.
- Production must use HTTPS and environment-managed secrets.
- Do not log QR tokens, passkey assertions, activation codes, or student coordinates.


