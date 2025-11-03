#!/bin/bash

# Quick manual test script for SpendSense MVP

# Set PYTHONPATH to include src directory
export PYTHONPATH="$(pwd)/src:${PYTHONPATH}"

echo "=========================================="
echo "SpendSense Quick Manual Test"
echo "=========================================="
echo ""

# Check if database exists
if [ ! -f "spendsense.db" ]; then
    echo "⚠️  Database not found. Running initialization..."
    python3 -m spendsense.database
    echo ""
fi

# Test 1: Check database schema
echo "1️⃣  Database Schema Check"
python3 -m spendsense.database 2>&1 | grep -E "(✅|❌|Schema validation)" | tail -1
echo ""

# Test 2: Check data exists
echo "2️⃣  Data Check"
USERS=$(sqlite3 spendsense.db "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "0")
TRANS=$(sqlite3 spendsense.db "SELECT COUNT(*) FROM transactions;" 2>/dev/null || echo "0")
SIGNALS=$(sqlite3 spendsense.db "SELECT COUNT(*) FROM signals;" 2>/dev/null || echo "0")

if [ "$USERS" = "0" ]; then
    echo "   ⚠️  No users found. Run: python3 -m spendsense.generate_data"
else
    echo "   ✅ Users: $USERS"
fi

if [ "$TRANS" = "0" ]; then
    echo "   ⚠️  No transactions found. Run: python3 -m spendsense.generate_data"
else
    echo "   ✅ Transactions: $TRANS"
fi

if [ "$SIGNALS" = "0" ]; then
    echo "   ⚠️  No signals found. Run: python3 -m spendsense.detect_signals"
else
    echo "   ✅ Signals: $SIGNALS"
fi
echo ""

# Test 3: Check personas
echo "3️⃣  Persona Assignments"
PERSONAS=$(sqlite3 spendsense.db "SELECT COUNT(*) FROM personas;" 2>/dev/null || echo "0")
if [ "$PERSONAS" = "0" ]; then
    echo "   ⚠️  No personas assigned. Run: python3 -m spendsense.personas"
else
    echo "   ✅ Personas assigned: $PERSONAS"
    echo ""
    echo "   Persona distribution:"
    sqlite3 spendsense.db "SELECT persona_type, COUNT(*) as count FROM personas GROUP BY persona_type;" 2>/dev/null | while IFS='|' read -r persona count; do
        echo "      - $persona: $count"
    done
fi
echo ""

# Test 4: Check recommendations
echo "4️⃣  Recommendations"
RECS=$(sqlite3 spendsense.db "SELECT COUNT(*) FROM recommendations;" 2>/dev/null || echo "0")
if [ "$RECS" = "0" ]; then
    echo "   ⚠️  No recommendations found. Run: python3 -m spendsense.recommendations"
else
    echo "   ✅ Recommendations: $RECS"
    echo ""
    echo "   Recommendations per user:"
    sqlite3 spendsense.db "SELECT user_id, COUNT(*) as count FROM recommendations GROUP BY user_id ORDER BY user_id;" 2>/dev/null | while IFS='|' read -r user_id count; do
        echo "      - User $user_id: $count recommendations"
    done
fi
echo ""

# Test 5: Check decision traces
echo "5️⃣  Decision Traces"
TRACES=$(sqlite3 spendsense.db "SELECT COUNT(*) FROM decision_traces;" 2>/dev/null || echo "0")
if [ "$TRACES" = "0" ]; then
    echo "   ⚠️  No decision traces found. Run: python3 -m spendsense.recommendations"
else
    echo "   ✅ Decision traces: $TRACES"
    EXPECTED=$(($RECS * 4))
    if [ "$TRACES" = "$EXPECTED" ]; then
        echo "   ✅ All recommendations have 4 trace steps (as expected)"
    else
        echo "   ⚠️  Expected $EXPECTED traces ($RECS recommendations × 4 steps), found $TRACES"
    fi
fi
echo ""

# Test 6: Summary
echo "=========================================="
echo "📊 Summary"
echo "=========================================="
sqlite3 spendsense.db "
SELECT 
    'Users' as type, COUNT(*) as count FROM users
UNION ALL
SELECT 'Transactions', COUNT(*) FROM transactions
UNION ALL
SELECT 'Signals', COUNT(*) FROM signals
UNION ALL
SELECT 'Personas', COUNT(*) FROM personas
UNION ALL
SELECT 'Recommendations', COUNT(*) FROM recommendations
UNION ALL
SELECT 'Decision Traces', COUNT(*) FROM decision_traces;
" 2>/dev/null | while IFS='|' read -r type count; do
    printf "   %-20s %s\n" "$type:" "$count"
done

echo ""
echo "=========================================="
if [ "$PERSONAS" -gt 0 ] && [ "$RECS" -gt 0 ] && [ "$TRACES" -gt 0 ]; then
    echo "✅ All systems operational!"
else
    echo "⚠️  Some components missing. See warnings above."
fi
echo "=========================================="

