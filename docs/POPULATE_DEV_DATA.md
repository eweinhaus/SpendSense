# Populate Deployed App with Dev Data

This guide explains how to populate your deployed SpendSense application with development data.

## Methods

### Method 1: Admin Web Interface (Recommended)

1. **Access the Admin Page**
   - Navigate to: `https://your-app.onrender.com/admin/populate-dev-data`
   - You'll need to authenticate as an operator (see operator authentication in compliance module)

2. **Fill in the Form**
   - Enter the number of users to generate (default: 75)
   - Optionally check "Skip if users already exist" to avoid duplicates
   - Click "Populate Database"

3. **Wait for Completion**
   - The process will run the full data pipeline:
     - Generate users, accounts, transactions
     - Detect signals (30d and 180d windows)
     - Assign personas
     - Generate recommendations (for users with consent)
   - The page will automatically refresh after completion to show updated stats

### Method 2: API Endpoint (Programmatic)

You can also trigger data population via the API:

```bash
curl -X POST "https://your-app.onrender.com/admin/populate-dev-data" \
  -H "Cookie: operator_session=your_session_cookie" \
  -d "num_users=75" \
  -d "skip_existing=false"
```

**Response:**
```json
{
  "success": true,
  "message": "Dev data population completed",
  "summary": {
    "users_created": 75,
    "signals_detected": 1200,
    "personas_assigned": 75,
    "recommendations_generated": 225,
    "errors": []
  }
}
```

### Method 3: Render Shell (Alternative)

If you have access to Render Shell:

1. **Open Render Shell**
   - Go to your Render service dashboard
   - Click "Shell" tab (if available on your plan)

2. **Run the Script**
   ```bash
   cd /opt/render/project/src
   export PYTHONPATH=/opt/render/project/src/src
   python3 -m spendsense.populate_dev_data --num-users 75
   ```

### Method 4: Command Line (Local Development)

For local development:

```bash
# Set PYTHONPATH
export PYTHONPATH=src

# Run the script
python3 -m spendsense.populate_dev_data --num-users 75

# Or with options
python3 -m spendsense.populate_dev_data --num-users 100 --skip-existing
```

## What Gets Generated

The script runs the complete data pipeline:

1. **Users & Accounts**
   - Generates diverse user profiles
   - Creates accounts (checking, savings, credit cards, etc.)
   - Generates 90 days of transaction history

2. **Signals Detection**
   - Credit utilization signals
   - Subscription patterns
   - Savings signals
   - Income stability signals
   - All signals detected for both 30-day and 180-day windows

3. **Persona Assignment**
   - Assigns personas based on detected signals:
     - High Utilization
     - Variable Income Budgeter
     - Savings Builder
     - Financial Newcomer
     - Subscription-Heavy
     - Neutral

4. **Recommendations**
   - Generates personalized recommendations
   - Only for users with consent
   - Includes content from the 72-item catalog
   - Includes partner offers (if eligible)

## Configuration

### Environment Variables

- `NUM_USERS`: Default number of users to generate (default: 75)
- `DB_PATH`: Database file path (default: `spendsense.db`)

### Options

- `--num-users`: Number of users to generate (1-200)
- `--skip-existing`: Skip data generation if users already exist

## Troubleshooting

### Error: "No users found"
- The database may not be initialized
- Run database initialization first: `python3 -m spendsense.database`

### Error: "Module not found"
- Ensure `PYTHONPATH` is set correctly
- On Render: `PYTHONPATH=/opt/render/project/src/src`
- Locally: `PYTHONPATH=src`

### Error: "Database locked"
- Another process may be using the database
- Wait a few seconds and try again
- On Render, ensure only one instance is running

### Slow Performance
- Generating 75 users with full data can take 1-2 minutes
- Be patient, especially on free tier Render instances
- Consider generating fewer users for testing

## Security Notes

- The admin endpoint is protected by operator authentication
- Only authenticated operators can trigger data population
- In production, consider adding additional security (IP whitelist, rate limiting)

## Next Steps

After populating data:

1. **Verify Data**
   - Check the dashboard: `https://your-app.onrender.com/`
   - View user details to verify signals and personas
   - Check recommendations are generated

2. **Test Functionality**
   - Test consent toggling
   - Verify recommendations appear/disappear based on consent
   - Test end-user interface (if applicable)

3. **Monitor Performance**
   - Check Render logs for any errors
   - Monitor database size
   - Verify all endpoints are working

