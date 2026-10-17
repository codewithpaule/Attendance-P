# Deployment Guide

This guide covers deploying the POMSOM attendance system to Vercel with Neon Postgres.

## Prerequisites

- Vercel account (Hobby plan)
- Neon account (Free plan)
- GitHub repository
- Custom domain (optional but recommended)
- Cloudflare account (for DNS management)

## Step 1: Set Up Neon Postgres

1. Create a new Neon project:
   - Go to https://neon.tech
   - Sign up or log in
   - Create a new project named "pomsom"
   - Choose a region (recommended: same as Vercel region)
   - Copy the connection string

2. Create a preview branch for development:
   - In Neon dashboard, create a branch "preview"
   - This will be used for preview deployments

3. Note the connection strings:
   - Pooled connection (DATABASE_URL): For the running app
   - Direct connection (DATABASE_URL_DIRECT): For migrations and backups

## Step 2: Configure Vercel

1. Connect your GitHub repository to Vercel:
   - Go to https://vercel.com
   - Sign up or log in
   - Click "Add New Project"
   - Import your GitHub repository

2. Configure environment variables:
   - Go to Settings > Environment Variables
   - Add all variables from `.env.example` (use production values)
   - Key variables:
     - `SECRET_KEY`: Generate with `openssl rand -hex 32`
     - `JOBS_SECRET`: Generate with `openssl rand -hex 32`
     - `DATABASE_URL`: Your Neon pooled connection string
     - `DATABASE_URL_DIRECT`: Your Neon direct connection string
     - `WEBAUTHN_RP_ID`: Your domain (e.g., pomsom.akili.com.ng)
     - `WEBAUTHN_RP_NAME`: "POMSOM"
     - `WEBACKN_ORIGIN`: https://pomsom.akili.com.ng
     - `IS_PREVIEW`: False for production, True for preview
     - `BACKUP_AGE_RECIPIENT`: Generate with `age-keygen` (see backup setup)
     - `RESEND_API_KEY`: Your Resend API key
     - `RESEND_FROM_EMAIL`: Your verified sender email

3. Configure preview environment:
   - Create a new environment named "preview"
   - Use the Neon preview branch connection string
   - Set `IS_PREVIEW=True`
   - WebAuthn will be disabled on preview deployments

## Step 3: Configure Domain and DNS

1. Add your custom domain in Vercel:
   - Go to Settings > Domains
   - Add your domain (e.g., pomsom.akili.com.ng)
   - Vercel will provide DNS records

2. Configure DNS in Cloudflare:
   - Log in to Cloudflare
   - Add your domain if not already added
   - Go to DNS settings
   - Add the records provided by Vercel as DNS-only (no proxying)
   - Important: DO NOT enable Cloudflare proxy (orange cloud)
   - This is required for WebAuthn to work correctly

3. Verify DNS propagation:
   - Use a tool like dig or nslookup to verify records
   - Wait for propagation (can take up to 48 hours)

## Step 4: Set Up GitHub Actions Secrets

1. Go to your GitHub repository > Settings > Secrets and variables > Actions

2. Add the following secrets:
   - `JOBS_SECRET`: Same as Vercel
   - `APP_URL`: Your production URL (e.g., https://pomsom.akili.com.ng)
   - `DATABASE_URL_DIRECT`: Same as Vercel
   - `BACKUP_AGE_RECIPIENT`: Your age public key (generate with `age-keygen`)

3. To generate age keys:
   ```bash
   age-keygen -o key.txt
   age-keygen -y key.txt > publickey.txt
   ```
   - Add the public key content to BACKUP_AGE_RECIPIENT
   - Keep the private key (key.txt) secure for restore operations

## Step 5: Run Initial Migration

1. Ensure the GitHub repository has `DATABASE_URL_DIRECT` and `SECRET_KEY` Actions secrets.
2. Manually trigger the `migrate` workflow from GitHub Actions using the branch containing the migration:
   - Go to GitHub Actions > migrate
   - Click "Run workflow"
   - The workflow uses the direct Neon connection and runs `migrate --fake-initial` so existing tables are recorded without being recreated.

3. Verify migration success:
   - Check the workflow logs
   - Ensure all migrations applied successfully

## Step 6: Create Database Cache Table

The app uses DatabaseCache for throttling. Create the cache table:

```bash
python manage.py createcachetable
```

Note: This only needs to be done once. In production, this can be done via a one-off script or manual SQL.

## Step 7: Verify Deployment

1. Check the health endpoint:
   - Visit https://pomsom.akili.com.ng/healthz
   - Should return `{"status": "ok"}`

2. Check the readiness endpoint:
   - Visit https://pomsom.akili.com.ng/readyz
   - Should return `{"status": "ok", "database": "connected"}`

3. Test the admin panel:
   - Visit https://pomsom.akili.com.ng/admin
   - Log in with your superuser account
   - Verify it loads correctly

4. Test static files:
   - Visit https://pomsom.akili.com.ng/static/css/ (should show directory listing or 404, but paths work)
   - Verify admin CSS/JS loads

## Step 8: Configure Jobs

The GitHub Actions workflows are already configured. They will:
- Evaluate attendance risk daily at 01:00 UTC
- Dispatch notifications hourly
- Purge location data Sundays at 03:00 UTC

To trigger jobs manually:
- Go to GitHub Actions > jobs
- Click "Run workflow" for the desired job

## Step 9: Set Up Resend for Email

1. Create a Resend account at https://resend.com
2. Verify your sender domain
3. Get your API key
4. Add `RESEND_API_KEY` to Vercel environment variables
5. Add `RESEND_FROM_EMAIL` with your verified sender email

## Step 10: Test End-to-End

1. Create test data via admin:
   - Create a term, room, course
   - Import students via CSV
   - Import enrollments

2. Test check-in flow:
   - Open a session as teacher
   - Scan QR as student
   - Verify check-in records correctly

3. Test job endpoints:
   - Trigger a job manually via GitHub Actions
   - Verify job execution in logs

## Migration Policy

All migrations must be backward compatible with the previous release:

- Use expand-then-contract pattern
- Never drop columns or tables in the same release
- Never rename columns or tables in the same release
- Document breaking changes in the next release

Example:
```
Release 1: Add new column with default value
Release 2: Populate column, make NOT NULL, remove default
Release 3: Drop column
```

## Rollback Procedure

If a deployment fails:

1. Roll back Vercel deployment:
   - Go to Vercel dashboard
   - Go to Deployments
   - Click "Rollback" on the failed deployment

2. If migrations were applied:
   - Manual rollback via migrate.yml using DATABASE_URL_DIRECT
   - Revert migration file in code
   - Redeploy

## Monitoring

- Vercel provides logs and metrics
- Check health endpoints regularly
- Monitor job execution in GitHub Actions
- Monitor Neon database usage (compute hours, storage)

## Troubleshooting

### Cold Start Latency
- First query after idle may be slow (Neon cold start)
- This is expected behavior
- Consider health check pings to keep database warm (not recommended for free tier)

### WebAuthn Not Working
- Verify WEBAUTHN_ORIGIN uses HTTPS
- Verify WEBAUTHN_RP_ID matches your domain
- Check Cloudflare DNS is in DNS-only mode (no proxy)
- Check browser console for WebAuthn errors

### Jobs Failing
- Check GitHub Actions logs
- Verify JOBS_SECRET matches between Vercel and GitHub
- Verify APP_URL is correct
- Check function duration limits (30s max)

### Database Connection Issues
- Verify DATABASE_URL is correct
- Check Neon project status (not suspended)
- Verify SSL mode is required
