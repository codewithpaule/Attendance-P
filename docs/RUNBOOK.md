# Operations Runbook

This runbook covers common operational tasks and procedures for the Ofeeee attendance system.

## Neon Cold Start Behavior

Neon Postgres free tier suspends compute after 5 minutes of inactivity. When the first query arrives after suspension:

- The database takes longer to respond (cold start)
- This is expected behavior and not an error
- Subsequent queries are fast until the next idle period

**Impact:**
- First request after idle may timeout (health check, job execution)
- Jobs may fail on first attempt but succeed on retry

**Mitigation:**
- Jobs are scheduled with retry logic (GitHub Actions)
- Health endpoints have a 5s timeout for database checks
- Consider periodic health checks to keep database warm (not recommended for free tier due to compute-hour limits)

## Neon CU-Hour or Storage Quota Exhausted

**Symptoms:**
- Database connection failures
- "out of credits" errors in logs
- Failed queries or jobs

**Immediate Actions:**
1. Check Neon dashboard for quota status
2. If storage quota exhausted:
   - Clean up old data if possible
   - Run `purge_location_data` command to free space
3. If compute-hour quota exhausted:
   - Wait for monthly reset (free tier)
   - Consider upgrading to paid tier if this happens frequently

**Prevention:**
- Monitor Neon usage in dashboard
- Regular location data purges (configured via LOCATION_RETENTION_DAYS)
- Regular database cleanup

## Restoring from Backup into a Scratch Neon Branch

If you need to restore from a backup:

1. Download the backup artifact from GitHub Actions:
   - Go to Actions > backup
   - Download the latest artifact

2. Decrypt the backup:
   ```bash
   age -d -i backup.sql.age -o backup.sql
   ```

3. Create a scratch Neon branch:
   - In Neon dashboard, create a new branch "restore-YYYY-MM-DD"
   - Get the connection string for this branch

4. Restore the backup:
   ```bash
   psql "$DATABASE_URL" < backup.sql
   ```

5. Verify the restored data:
   - Connect to the scratch branch
   - Verify tables and data
   - Test critical functionality

6. If restore is successful:
   - Promote the scratch branch to main (careful - this replaces production!)
   - Or switch the app to use the new branch connection string

## Rotating JOBS_SECRET

To rotate the JOBS_SECRET (recommended periodically):

1. Generate a new secret:
   ```bash
   openssl rand -hex 32
   ```

2. Update Vercel environment variables:
   - Go to Vercel Settings > Environment Variables
   - Update JOBS_SECRET
   - Redeploy

3. Update GitHub Actions secrets:
   - Go to repository Settings > Secrets and variables > Actions
   - Update JOBS_SECRET
   - Test by triggering a job manually

4. Verify jobs work:
   - Trigger a job manually via GitHub Actions
   - Check logs for successful execution

## Rotating SECRET_KEY

Rotating SECRET_KEY requires care as it invalidates all sessions and user tokens:

1. Generate a new secret:
   ```bash
   openssl rand -hex 32
   ```

2. Update Vercel environment variables:
   - Go to Vercel Settings > Environment Variables
   - Update SECRET_KEY
   - Redeploy

3. Inform users:
   - All users will need to log in again
   - All passkeys will need to be re-registered
   - Send notification via email or other channels

4. Verify login flow works:
   - Test activation flow
   - Test passkey registration
   - Test login

## What to Do If the App is Down During Class

If the application becomes unavailable during a class:

1. Immediate communication:
   - Notify students and instructor via alternative channels
   - Switch to manual attendance (paper-based) if needed

2. Diagnose the issue:
   - Check Vercel status page
   - Check GitHub Actions logs for job failures
   - Check Neon dashboard for database issues

3. Common fixes:
   - Redeploy the latest version
   - Restart Vercel deployment
   - Check environment variables are correct
   - Verify Neon database is not suspended

4. If database is down:
   - Students cannot check in
   - Consider extending the check-in window after recovery
   - Manual attendance recording may be needed

5. Document the incident:
   - Record in AuditLog table what happened
   - Document for future prevention
   - Consider implementing fail-safes (e.g., offline mode)

## Warning: Do Not Add Keep-Alive Pings

**Do not add keep-alive pings to prevent Neon cold starts.**

**Reasons:**
- Free tier has compute-hour limits (500 hours/month)
- Keep-alive pings consume compute hours unnecessarily
- This would quickly exhaust the free tier quota
- Cold start latency is acceptable for our use case

**Alternatives:**
- Jobs run at regular intervals naturally keep database warm
- Health checks by users also warm the database
- If cold start latency becomes problematic, consider upgrading to paid tier

## Job Execution Failures

If a job fails:

1. Check the GitHub Actions logs for the specific job
2. Common causes:
   - Function timeout (30s limit exceeded)
   - Database connection issues
   - Job logic errors
   - JOBS_SECRET mismatch

3. Retry the job:
   - Go to GitHub Actions > jobs
   - Click "Run workflow" for the failed job
   - Jobs are idempotent, so retry is safe

4. If job consistently fails:
   - Check job implementation for efficiency
   - Consider breaking work into smaller chunks
   - Check database query performance
   - Verify time budget is sufficient

## Database Cache Throttling

The app uses DatabaseCache for throttling, which is shared across all Vercel instances:

- This ensures throttling works correctly even with multiple instances
- The cache table is created by `python manage.py createcachetable`
- Cache is cleared automatically by Django's cache framework

If throttling seems incorrect:
- Verify cache table exists and is being used
- Check for cache-related errors in logs
- Clear cache manually if needed: `python manage.py clearcache`

## WebAuthn Issues

If WebAuthn authentication fails:

1. Verify environment variables:
   - WEBAUTHN_RP_ID must match your domain exactly
   - WEBAUTHN_ORIGIN must use HTTPS
   - Both must be set in Vercel environment variables

2. Check Cloudflare DNS:
   - DNS records must be DNS-only (gray cloud)
   - Do not enable proxy (orange cloud)
   - Proxy interferes with WebAuthn

3. Check browser console:
   - Look for WebAuthn errors
   - Common error: "Site is not allowed to use WebAuthn"
   - This indicates domain mismatch

4. Preview deployments:
   - WebAuthn is disabled on preview deployments (different hostnames)
   - This is intentional - preview environments have different URLs
   - Use production environment for WebAuthn testing

## Email Delivery Issues

If emails are not being delivered:

1. Check Resend dashboard:
   - Verify API key is valid
   - Check sender domain is verified
   - Check daily email budget (100 emails/day free tier)

2. Check notification status:
   - Check Notification table in database
   - Look for PENDING notifications
   - Check last_error field

3. Check job execution:
   - Verify dispatch-notifications job is running hourly
   - Check GitHub Actions logs
   - Verify EMAIL_DAILY_BUDGET is not exhausted

4. Common issues:
   - Daily budget exhausted (emails left PENDING)
   - Invalid sender email
   - Resend API quota exceeded
   - Network issues

## Location Data Privacy

Location data is personal data under the Nigeria Data Protection Act:

- Collection: Only during check-in, never continuous
- Retention: LOCATION_RETENTION_DAYS (default 180 days)
- Never log coordinates in logs
- Coordinates are nullified after retention period while preserving distance_m

To manually purge location data:
```bash
python manage.py purge_location_data
```

This command nulls latitude and longitude older than LOCATION_RETENTION_DAYS while preserving distance_m for analysis.

## Security Incident Response

If a security incident is suspected:

1. Check AuditLog table for suspicious activity
2. Review JOBS_SECRET for potential compromise
3. Review SECRET_KEY for potential compromise
4. Rotate compromised secrets immediately
5. Notify affected users
6. Document the incident
7. Implement prevention measures

## Performance Issues

If the application is slow:

1. Check Vercel analytics for response times
2. Check Neon database query performance
3. Review slow queries in logs
4. Add database indexes if needed
5. Optimize expensive queries
6. Consider caching frequently accessed data

## Monitoring Checklist

Regular monitoring tasks:

- Daily: Check GitHub Actions job execution
- Daily: Check Vercel deployment logs
- Weekly: Check Neon compute-hour usage
- Weekly: Check Neon storage usage
- Weekly: Check backup artifacts in GitHub Actions
- Monthly: Review and rotate secrets (JOBS_SECRET, SECRET_KEY)
- Monthly: Review and update dependencies
