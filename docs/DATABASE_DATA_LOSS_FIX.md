# Database Data Loss - Root Cause & Fix

## What Happened

Your data was lost because the database file was stored in an **ephemeral directory** that gets wiped on every Render deployment.

## Root Cause

### The Problem
1. **render.yaml** had: `DATABASE_URL=sqlite:////opt/render/project/spendsense.db`
2. On Render, `/opt/render/project/` is **ephemeral** - it gets wiped on every deployment
3. When Render redeployed after the PYTHONPATH fix, it wiped the directory and your database was lost

### Why This Happened
When I fixed the PYTHONPATH issue, the deployment triggered a fresh build. Render's ephemeral filesystem wiped everything in `/opt/render/project/` except the persistent disk.

## The Fix

Updated all database paths to use Render's **persistent disk** which survives deployments:

### 1. render.yaml
```yaml
envVars:
  - key: DATABASE_URL
    value: sqlite:////opt/render/project/persistent/spendsense.db
```

### 2. scripts/deploy_render.py
Updated to use persistent disk path in environment variables.

### 3. database.py (Already Correct)
The code already checks for persistent disk first:
```python
if os.getenv("RENDER"):
    persistent_dir = "/opt/render/project/persistent"
    if os.path.exists(persistent_dir):
        return os.path.join(persistent_dir, "spendsense.db")
```

## Important: Enable Persistent Disk on Render

**You must enable the persistent disk in Render dashboard:**

1. Go to your Render service dashboard
2. Navigate to **Settings** → **Disk**
3. Enable **Persistent Disk** (if not already enabled)
4. The persistent disk will be mounted at `/opt/render/project/persistent/`

**Without the persistent disk enabled, your database will still be lost on deployments!**

## How to Recover Your Data

Unfortunately, **the data is likely gone** if it was stored in the ephemeral directory. However:

### Option 1: Restore from Local Backup
If you have a local copy of `spendsense.db`:
1. Copy it to your local machine
2. Use the admin endpoint `/admin/populate-dev-data` to regenerate data
3. Or manually restore if you have a backup

### Option 2: Regenerate Data
Use the new admin endpoints to regenerate development data:
1. Go to `/admin/populate-dev-data` (requires operator auth)
2. Click "Populate Database"
3. This will generate users, signals, personas, and recommendations

### Option 3: Check Render Logs
Check if Render has any backup or if the database file still exists:
- Check Render service logs
- Look for database initialization messages
- Check if persistent disk was mounted

## Prevention

### Going Forward
1. ✅ **Always use persistent disk** for SQLite databases on Render
2. ✅ **Set DATABASE_URL** to point to persistent disk
3. ✅ **Enable persistent disk** in Render dashboard
4. ✅ **Consider PostgreSQL** for production (Render PostgreSQL is persistent by default)

### Best Practices
1. **For Production**: Use Render PostgreSQL (persistent by default)
2. **For Development**: Use persistent disk for SQLite
3. **Backup Strategy**: Regularly export data or use version control for seed data
4. **Monitoring**: Check database file size in logs to ensure it's persisting

## Next Steps

1. **Enable Persistent Disk** in Render dashboard (if not already)
2. **Deploy the fix** (updated render.yaml)
3. **Regenerate data** using `/admin/populate-dev-data` endpoint
4. **Verify persistence** by checking database after a test deployment

## Files Changed

- ✅ `render.yaml` - Updated DATABASE_URL to persistent disk
- ✅ `scripts/deploy_render.py` - Updated environment variable
- ✅ `docs/DATABASE_DATA_LOSS_FIX.md` - This documentation

## Status

⚠️ **Data Recovery**: Your previous data is likely lost if it was in ephemeral storage
✅ **Fix Applied**: Database now configured to use persistent disk
🔄 **Action Required**: Enable persistent disk in Render dashboard and regenerate data

