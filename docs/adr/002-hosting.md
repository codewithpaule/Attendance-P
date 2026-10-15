# ADR-002: Hosting on Vercel with Neon

## Status
Accepted

## Context

We need to deploy the university attendance system to production with the following requirements:
- Django application with PostgreSQL database
- Scheduled jobs (evaluate attendance risk, dispatch notifications, purge location data)
- Database backups
- Manual migration workflow
- Cost-effective solution suitable for a university deployment
- Must support WebAuthn for secure authentication
- Must handle multiple phones/passkeys per student
- Must comply with Nigeria Data Protection Act for location data

## Decision

We deploy the Django application as a single Vercel Function (Hobby plan) with Neon Postgres (Free plan) as the database.

### Platform Selection

**Vercel:**
- Serverless platform optimized for Django
- Automatic HTTPS, CDN, and edge caching
- Built-in CI/CD with git-based deployments
- Separate preview environments
- Hobby plan provides sufficient resources for our use case
- Limitation: No background processes, 10s function duration (configurable to 60s), ephemeral instances

**Neon Postgres:**
- Serverless PostgreSQL with automatic scaling
- Free tier provides 3 projects with auto-suspend after 5 idle minutes
- Transaction pooling support for serverless workloads
- Branching for preview environments
- Limitation: 6-hour restore window, cold start after suspend

### Architecture Constraints

**Vercel Function Constraints:**
- Single WSGI entrypoint via pyproject.toml [tool.vercel]
- No background processes or long-running work
- No persistent disk storage
- Function duration limit: configured to 30s in vercel.json
- Instances are ephemeral and run in parallel
- Request body size limits (process uploads in memory, enforce 2MB max)

**Neon Constraints:**
- Free compute suspends after 5 idle minutes
- First query after cold start is slow
- Restore window is only 6 hours
- Transaction pooling (DATABASE_URL) requires specific settings:
  - sslmode=require
  - CONN_MAX_AGE=0
  - DISABLE_SERVER_SIDE_CURSORS=True
  - Short connect timeout to tolerate cold starts
- Direct connection (DATABASE_URL_DIRECT) needed for migrations and backups

**Scheduling Constraint:**
- Vercel Hobby cron is once per day (insufficient for hourly dispatch-notifications)
- Solution: GitHub Actions workflows with schedule triggers calling secured job endpoints

### Job Design

Instead of background processes or Vercel Cron, we use a job endpoint pattern:

**Job Model (ops.models.JobRun):**
- name, status (RUNNING, SUCCEEDED, FAILED)
- started_at, finished_at, lease_expires_at
- stats (JSON field for job metrics)
- Partial unique constraint: only one RUNNING row per job name
- Expired leases are marked FAILED before new claim (crashed run recovery)

**Job Registry (ops.registry):**
- Apps register jobs with register(name, fn) in apps/<app>/jobs.py
- Loaded from AppConfig.ready (ops never imports other apps)
- Function signature: fn(deadline: datetime) -> dict of stats
- Jobs must stop cleanly before deadline, be idempotent, and resume safely

**Job Endpoint:**
- POST /internal/jobs/<name>/
- Auth: Authorization: Bearer <JOBS_SECRET> with hmac.compare_digest
- Returns 404 for invalid auth (does not reveal route)
- CSRF exempt only on this view
- Throttled
- Every call is audit logged
- Returns JSON stats

**Job Implementation:**
- evaluate-attendance-risk: Daily at 01:00 UTC
- dispatch-notifications: Hourly (respects email budget and time budget)
- purge-location-data: Sundays at 03:00 UTC
- Existing management commands become thin wrappers for local use

### Database and Settings

**Connection Handling:**
- DATABASE_URL: Pooled Neon connection for the running app (transaction pooling)
- DATABASE_URL_DIRECT: Direct connection for migrations and backups only
- DatabaseCache for throttling (shared across instances via database)
- Sessions remain database-backed

**Production Settings:**
- DEBUG=False, ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS from env
- Secure cookies, SameSite Lax
- SECURE_PROXY_SSL_HEADER from X-Forwarded-Proto
- SECURE_SSL_REDIRECT with health endpoints exempt
- HSTS configurable (short value first, document how to raise)
- WebAuthn settings from env, fail fast at startup if missing or invalid
- WebAuthn disabled with clear message on preview deployments

**Client IP Detection:**
- core/net.get_client_ip(request) helper
- When BEHIND_VERCEL=True: reads Vercel's non-spoofable header (X-Vercel-IP-Address)
- Otherwise: REMOTE_ADDR
- Used in audit logs, check-in network_ip, throttles
- Unit tests for both modes

**Health Endpoints:**
- /healthz: Liveness only (no database)
- /readyz: Readiness check with database (5s timeout)
- Both exempt from SSL redirect

**Logging:**
- JSON logs to stdout
- Never log coordinates, tokens, assertions, or activation codes
- Vercel logs are short-lived, so security events must live in AuditLog table

### Migrations

**Manual Workflow:**
- GitHub Actions workflow (migrate.yml, workflow_dispatch)
- Uses DATABASE_URL_DIRECT
- Never runs at Vercel build time
- Never runs at app start

**Migration Policy:**
- Every migration must be backward compatible with the previous release
- Expand then contract pattern
- No drops or renames in the same release
- Documented in docs/DEPLOYMENT.md
- CI check flags destructive operations

### Security Headers

**vercel.json Headers:**
- Strict-Transport-Security
- X-Content-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: allows geolocation and publickey-credentials-get for self

### Static Files

- Follow Vercel's Django guide
- collectstatic during build
- Verify admin and app CSS/JS load in production

### Environment Separation

- Production and Preview environments are separate
- Preview uses Neon preview branch (never reaches production database)
- WebAuthn disabled on preview (preview deployments have different hostnames)

### Backup Strategy

**GitHub Actions workflow (backup.yml):**
- Weekly pg_dump (client version matching Neon server)
- Over DATABASE_URL_DIRECT
- Encrypted with age using BACKUP_AGE_RECIPIENT
- Uploaded as artifact with 30 days retention
- Never store unencrypted dump anywhere

## Consequences

### Positive
- Cost-effective: Vercel Hobby + Neon Free tier
- Automatic HTTPS and CDN
- Git-based deployment with preview environments
- Automatic scaling without server management
- Clear separation of concerns (ops app for jobs)
- Idempotent jobs that can be retried safely
- Job lease mechanism prevents concurrent runs and handles crashes
- Backup workflow provides disaster recovery

### Negative
- Vercel function duration limit (30s) requires careful job design
- Neon cold start after 5 idle minutes adds latency to first query
- No background processes (everything must be request/response)
- Preview deployments cannot use WebAuthn (different hostnames)
- Job scheduling depends on GitHub Actions (not Vercel Cron)
- Ephemeral instances prevent in-memory caching, throttling, or locks
- 6-hour Neon restore window requires frequent backups

### Mitigations
- Jobs designed to finish well within 30s time budget
- DatabaseCache for shared state across instances
- WebAuthn disabled on preview with clear message
- Weekly backups with 30-day retention
- Jobs are idempotent and can be retried safely
- Job lease mechanism handles crashed runs
- Documentation for cold start behavior and recovery procedures

## Alternatives Considered

1. **Traditional VPS (DigitalOcean, AWS EC2)**: More control but requires server management, scaling, and security patching. Rejected due to operational overhead.

2. **Kubernetes**: Overkill for our scale and team size. Rejected due to complexity.

3. **Heroku**: Similar to Vercel but more expensive and declining support for free tier. Rejected.

4. **Vercel Cron**: Once per day limit insufficient for hourly dispatch-notifications. Rejected in favor of GitHub Actions.

5. **Cloudflare Workers**: No Django support, would require major rewrite. Rejected.

## References

- Vercel Django guide: https://vercel.com/docs/frameworks/django
- Neon transaction pooling: https://neon.tech/docs/internals/connection-pooling
- Vercel headers: https://vercel.com/docs/concepts/headers/
- SPEC.md (full product specification)
- ADR-001 (modular monolith architecture)
