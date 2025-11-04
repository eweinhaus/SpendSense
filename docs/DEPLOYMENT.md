# SpendSense Deployment Guide

This guide provides step-by-step instructions for deploying SpendSense to Render.com.

## Prerequisites

- GitHub account with SpendSense repository
- Render.com account (free tier available)
- OpenAI API key (if using OpenAI for recommendations)

## Render.com Setup

### Option A: Automated Deployment Script (Fastest)

A Python script has been created to automate the deployment process:

```bash
python3 scripts/deploy_render.py
```

This script will:
- Check if a service already exists
- Create a new service if needed
- Configure environment variables
- Trigger deployment

**Prerequisites:**
- Render API key set as `RENDER_API_KEY` environment variable or hardcoded in script
- GitHub repository connected to Render account

### Option B: Using render.yaml (Recommended for Blueprint)

If your repository has `render.yaml` in the root, Render will automatically detect it:

1. Go to [render.com](https://render.com)
2. Sign up for a free account
3. In Render dashboard, click "New" → "Blueprint"
4. Select "Connect GitHub"
5. Authorize Render to access your repositories
6. Select the SpendSense repository
7. Render will automatically detect `render.yaml` and configure the service
8. Review configuration and click "Apply"

### Option C: Manual Configuration

1. Go to [render.com](https://render.com)
2. Sign up for a free account
3. In Render dashboard, click "New" → "Web Service"
4. Select "Connect GitHub"
5. Authorize Render to access your repositories
6. Select the SpendSense repository
7. Choose the branch to deploy (e.g., `main` or `improve_mvp`)

### 4. Configure Web Service (if not using automated script or render.yaml)

**Basic Settings:**
- **Name**: `spendsense` (or your preferred name)
- **Environment**: `Python 3`
- **Region**: Choose closest to your users
- **Branch**: Select your branch (e.g., `main`)

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn -w 2 -k uvicorn.workers.UvicornWorker spendsense.app:app --bind 0.0.0.0:$PORT`

**Advanced Settings:**
- **Plan**: Free tier (or Starter if needed)
- **Auto-Deploy**: Yes (deploys on push to selected branch)

**Note:** If using `render.yaml`, these settings are automatically configured.

### 5. Configure Environment Variables

In the Render dashboard, go to "Environment" section and add:

```
PYTHONPATH=/opt/render/project/src
DATABASE_URL=sqlite:///spendsense.db
DEBUG=False
OPENAI_API_KEY=your_api_key_here
```

**Note**: 
- Replace `your_api_key_here` with your actual OpenAI API key
- For SQLite, the database file will be stored in the service directory
- For production, consider using Render PostgreSQL (requires migration)

### 6. Deploy

1. Click "Create Web Service"
2. Render will build and deploy your application
3. Monitor build logs for any errors
4. Once deployed, you'll get a public URL (e.g., `https://spendsense.onrender.com`)

## Post-Deployment Verification

### 1. Verify Application Access

1. Open your Render service URL in a browser
2. Verify dashboard loads: `https://your-app.onrender.com/`
3. Check for any errors in browser console

### 2. Verify Database

1. The application should initialize the database on first run
2. If using SQLite, ensure the file persists (check Render file system)
3. For production, consider migrating to Render PostgreSQL

### 3. Verify Endpoints

Test all endpoints:
- Dashboard: `GET /`
- User Detail: `GET /user/{user_id}`
- Consent Toggle: `POST /consent/{user_id}`
- API Docs: `GET /docs`

### 4. Verify Static Files

1. Check if CSS/JS files load correctly
2. Verify Bootstrap styling is applied
3. Check browser network tab for any 404s

### 5. Test Functionality

1. Navigate to dashboard
2. Click on a user to view details
3. Toggle consent checkbox
4. Verify recommendations generate/regenerate
5. Check signal display for both 30d and 180d windows

## Troubleshooting

### Build Failures

**Issue**: Build fails with dependency errors
**Solution**: 
- Check `requirements.txt` is up to date
- Verify Python version compatibility
- Check build logs for specific error messages

### Import Errors

**Issue**: `ModuleNotFoundError` or import errors
**Solution**:
- Verify `PYTHONPATH` environment variable is set correctly
- Check that `src/` directory structure is correct
- Ensure all imports use relative paths (`from .module import ...`)

### Database Issues

**Issue**: Database not accessible or not persisting
**Solution**:
- For SQLite: Check file permissions and persistence on Render
- Consider migrating to Render PostgreSQL for production
- Verify `DATABASE_URL` environment variable is correct

### Static Files Not Loading

**Issue**: CSS/JS files return 404
**Solution**:
- Verify `StaticFiles` mount in `app.py` is correct
- Check that static files are in `src/spendsense/static/`
- Verify Render handles static files automatically

### Performance Issues

**Issue**: Slow response times or timeouts
**Solution**:
- Check Render service logs for errors
- Verify database queries are optimized
- Consider upgrading to Starter plan if on free tier
- Profile application performance (see evaluation harness)

## Environment Configuration

### Development vs Production

**Development** (local):
- `DEBUG=True`
- `DATABASE_URL=sqlite:///spendsense.db`
- Local `.env` file for secrets

**Production** (Render.com):
- `DEBUG=False`
- `DATABASE_URL=sqlite:///spendsense.db` (or PostgreSQL URL)
- Environment variables set in Render dashboard

### Security Best Practices

1. **Never commit secrets**: Use `.env.example` as template, never commit `.env`
2. **Use environment variables**: Store API keys in Render environment variables
3. **Disable debug mode**: Set `DEBUG=False` in production
4. **HTTPS**: Render automatically provides HTTPS (verify certificate)

## Monitoring

### Render Dashboard

- **Metrics**: View CPU, memory, and request metrics
- **Logs**: Access application logs in real-time
- **Events**: View deployment events and errors

### Application Logs

Check logs for:
- Eligibility failures (logged when recommendations filtered)
- Tone validation violations (logged when prohibited phrases detected)
- Error messages and stack traces

## Database Migration (PostgreSQL)

For production, consider migrating from SQLite to PostgreSQL:

1. Create PostgreSQL database in Render dashboard
2. Update `DATABASE_URL` environment variable
3. Run migration script (see `md_files/MIGRATION_GUIDE.md`)
4. Verify data migration

## Continuous Deployment

Render automatically deploys on push to the selected branch:

1. Push changes to GitHub
2. Render detects changes
3. Builds new version
4. Deploys automatically
5. Previous version remains available for rollback

## Rollback

If deployment fails:

1. Go to Render dashboard
2. Navigate to "Events" tab
3. Find previous successful deployment
4. Click "Rollback" to revert

## Support

For issues:
1. Check Render service logs
2. Review application logs
3. Check GitHub issues
4. Refer to documentation in `docs/` directory

