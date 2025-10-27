#!/bin/bash
# Test script to verify Reflex app compiles without errors

set -e

LOG_FILE="reflex_test.log"
PID_FILE="reflex_test.pid"

echo "🧪 Testing Reflex app compilation..."
echo "======================================"
echo ""

# Clean up any previous test artifacts
rm -f "$LOG_FILE" "$PID_FILE"

# Start Reflex in the background and capture output
echo "Starting Reflex..."

# Use existing venv if available, otherwise let uv create one
if [ -d ".venv" ]; then
    echo "Using existing .venv"
    .venv/bin/reflex run > "$LOG_FILE" 2>&1 &
else
    echo "Using uv run (will create new venv)"
    uv run reflex run > "$LOG_FILE" 2>&1 &
fi

REFLEX_PID=$!

# Save PID
echo $REFLEX_PID > "$PID_FILE"

echo "Reflex started with PID: $REFLEX_PID"
echo "Waiting 30 seconds for compilation..."

# Wait 30 seconds for compilation
sleep 30

# Kill Reflex
echo ""
echo "Stopping Reflex..."
kill $REFLEX_PID 2>/dev/null || true
sleep 2
kill -9 $REFLEX_PID 2>/dev/null || true

# Clean up PID file
rm -f "$PID_FILE"

echo ""
echo "======================================"
echo "📋 Log Analysis:"
echo "======================================"
echo ""

# Check for errors
if grep -i "error" "$LOG_FILE" | grep -v "0 errors" | grep -v "No errors"; then
    echo "❌ ERRORS FOUND:"
    echo ""
    grep -i "error" "$LOG_FILE" | grep -v "0 errors" | grep -v "No errors" | head -20
    echo ""
    echo "Full log saved to: $LOG_FILE"
    exit 1
fi

if grep -i "traceback" "$LOG_FILE"; then
    echo "❌ PYTHON TRACEBACK FOUND:"
    echo ""
    grep -A 10 -i "traceback" "$LOG_FILE" | head -30
    echo ""
    echo "Full log saved to: $LOG_FILE"
    exit 1
fi

if grep -i "failed" "$LOG_FILE" | grep -v "0 failed"; then
    echo "❌ FAILURES FOUND:"
    echo ""
    grep -i "failed" "$LOG_FILE" | grep -v "0 failed" | head -20
    echo ""
    echo "Full log saved to: $LOG_FILE"
    exit 1
fi

if grep -i "App running at" "$LOG_FILE"; then
    echo "✅ SUCCESS! Reflex app compiled and started successfully"
    echo ""
    echo "Key indicators found:"
    grep -i "App running at\|compiled\|success" "$LOG_FILE" | head -10
    echo ""
    echo "Full log saved to: $LOG_FILE"
    exit 0
fi

if grep -i "compiled successfully" "$LOG_FILE"; then
    echo "✅ SUCCESS! Reflex app compiled successfully"
    echo ""
    echo "Compilation output:"
    grep -i "compiled" "$LOG_FILE" | head -10
    echo ""
    echo "Full log saved to: $LOG_FILE"
    exit 0
fi

echo "⚠️  INCONCLUSIVE - App may have compiled but no clear success indicator found"
echo ""
echo "Last 20 lines of log:"
tail -20 "$LOG_FILE"
echo ""
echo "Full log saved to: $LOG_FILE"
exit 2
