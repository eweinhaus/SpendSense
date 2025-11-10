# Quick Fix Guide - Data Loss Recovery

## ✅ What I've Done For You

1. **Fixed the database path** - Updated to use persistent disk
2. **Pushed changes to GitHub** - Render will auto-deploy
3. **Updated environment variables** - DATABASE_URL now points to persistent disk

## 🔧 What You Need to Do Now

### Step 1: Enable Persistent Disk (CRITICAL)

**Without this, your data will still be lost on each deployment!**

1. Go to: https://dashboard.render.com/web/srv-d44njmq4d50c73el4brg
2. Click **"Settings"** in the left sidebar
3. Scroll down to **"Disk"** section
4. Click **"Enable Persistent Disk"** or **"Add Disk"**
5. Set size to at least **1 GB** (free tier allows this)
6. Click **"Save"**

**The persistent disk will be mounted at `/opt/render/project/persistent/`**

### Step 2: Verify Deployment

1. Wait for Render to finish deploying (check the "Events" tab)
2. Visit: https://spendsense-2e84.onrender.com/
3. Check that the dashboard loads (it may be empty - that's OK)

### Step 3: Regenerate Your Data

You have **3 options** to regenerate data:

#### Option A: Use the Admin UI (Easiest)

1. Get your operator API key (set in Render environment variables as `OPERATOR_API_KEY`)
2. Visit: https://spendsense-2e84.onrender.com/admin/populate-dev-data
3. You'll need to authenticate with the API key (use browser dev tools or curl)
4. Fill in the form:
   - Number of users: `75` (or your preferred number)
   - Skip existing: Leave unchecked
5. Click **"Populate Database"**
6. Wait 1-2 minutes for data generation

#### Option B: Use the Helper Script (Recommended)

```bash
# Set your operator API key
export OPERATOR_API_KEY="your-operator-api-key-here"

# Run the script
python3 scripts/populate_render_data.py --num-users 75
```

#### Option C: Use curl/HTTPie

```bash
# Set your operator API key
export OPERATOR_API_KEY="your-operator-api-key-here"

# Populate data
curl -X POST https://spendsense-2e84.onrender.com/admin/populate-dev-data \
  -H "X-Operator-API-Key: $OPERATOR_API_KEY" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "num_users=75&skip_existing=false"
```

### Step 4: Verify Data Persists

1. After data is generated, check the dashboard
2. You should see users, personas, recommendations
3. **Test persistence**: Trigger a manual deployment in Render
4. After deployment completes, check dashboard again
5. **Data should still be there!** ✅

## 🚨 Important Notes

### Persistent Disk is Required

- **Without persistent disk**: Data will be lost on every deployment
- **With persistent disk**: Data survives deployments
- **Free tier**: Includes 1 GB persistent disk (sufficient for SQLite)

### Environment Variables

Make sure these are set in Render dashboard:
- ✅ `PYTHONPATH=/opt/render/project/src/src`
- ✅ `DATABASE_URL=sqlite:////opt/render/project/persistent/spendsense.db`
- ✅ `RENDER=true`
- ✅ `DEBUG=False`
- ✅ `OPERATOR_API_KEY=your-key-here` (for admin endpoints)

### Operator API Key

If you don't have an operator API key set:
1. Go to Render dashboard → Environment
2. Add: `OPERATOR_API_KEY` = `your-secret-key-here`
3. Use this key to authenticate admin endpoints

## 📊 Expected Results

After populating data, you should see:
- **75 users** (or your specified number)
- **~300+ signals** (30d and 180d windows)
- **75 personas** (one per user)
- **~225 recommendations** (3 per user with consent)

## 🐛 Troubleshooting

### "ModuleNotFoundError" Still Happening?

- Check that deployment completed successfully
- Verify PYTHONPATH is set correctly in Render dashboard
- Check build logs for errors

### Data Still Getting Lost?

- **Verify persistent disk is enabled** (Step 1 above)
- Check that DATABASE_URL points to `/opt/render/project/persistent/`
- Look in Render logs for database path messages

### Can't Access Admin Endpoints?

- Verify OPERATOR_API_KEY is set in Render environment
- Check that you're using the correct header: `X-Operator-API-Key`
- Try the helper script: `python3 scripts/populate_render_data.py`

### Service Won't Start?

- Check Render build logs
- Verify all environment variables are set
- Ensure persistent disk is enabled (service won't start if disk path doesn't exist)

## ✅ Success Checklist

- [ ] Persistent disk enabled in Render dashboard
- [ ] Environment variables updated (DATABASE_URL, PYTHONPATH)
- [ ] Deployment completed successfully
- [ ] Service is running (dashboard loads)
- [ ] Data populated (users visible on dashboard)
- [ ] Data persists after test deployment

## 📞 Need Help?

If you're still having issues:
1. Check Render service logs
2. Verify all environment variables
3. Test the admin endpoint with curl
4. Check that persistent disk is actually mounted

The fix is deployed - you just need to enable the persistent disk and regenerate your data!

