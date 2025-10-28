#!/bin/bash

# Script to test if Reflex app starts correctly
# Runs the app, waits 10 seconds, stops it, and checks logs

set -e

LOG_FILE="reflex_startup_test.log"
PID_FILE="reflex_app.pid"

echo "================================================"
echo "Testing Reflex App Startup"
echo "================================================"
echo ""

# Clean up any existing log and pid files
rm -f "$LOG_FILE" "$PID_FILE"

echo "Starting Reflex app..."
echo "Logging output to: $LOG_FILE"
echo ""

# Start Reflex in background and capture PID
uv run reflex run >"$LOG_FILE" 2>&1 &
APP_PID=$!
echo $APP_PID >"$PID_FILE"

echo "Reflex app started with PID: $APP_PID"
echo "Monitoring log file until startup completes..."
echo ""

# Monitor log file and stop when it stops growing
MAX_WAIT=30      # Maximum wait time in seconds
STABLE_TIME=3    # Seconds of no change to consider stable
CHECK_INTERVAL=1 # Check every 1 second

prev_size=0
stable_count=0
elapsed=0

while [ $elapsed -lt $MAX_WAIT ]; do
  # Check if log file exists
  if [ -f "$LOG_FILE" ]; then
    current_size=$(wc -c <"$LOG_FILE" 2>/dev/null || echo 0)

    # Check if size changed
    if [ "$current_size" -eq "$prev_size" ]; then
      stable_count=$((stable_count + 1))
      echo -ne "  Log stable for ${stable_count}s (no new output)...\r"

      # If stable for required time, break
      if [ $stable_count -ge $STABLE_TIME ]; then
        echo ""
        echo "✓ Log output stabilized - app appears to be running"
        break
      fi
    else
      # Size changed, reset stable counter
      stable_count=0
      echo -ne "  Waiting for log to stabilize... (${elapsed}s elapsed)\r"
    fi

    prev_size=$current_size
  fi

  sleep $CHECK_INTERVAL
  elapsed=$((elapsed + CHECK_INTERVAL))
done

if [ $elapsed -ge $MAX_WAIT ]; then
  echo ""
  echo "⚠️  Reached maximum wait time of ${MAX_WAIT}s"
fi

echo ""

# Stop the app
echo "Stopping Reflex app (PID: $APP_PID)..."
kill $APP_PID 2>/dev/null || true

# Give it a moment to shut down gracefully
sleep 2

# Force kill if still running
if ps -p $APP_PID >/dev/null 2>&1; then
  echo "Force killing app..."
  kill -9 $APP_PID 2>/dev/null || true
fi

# Clean up PID file
rm -f "$PID_FILE"

echo "App stopped."
echo ""
echo "================================================"
echo "Analyzing Log Output"
echo "================================================"
echo ""

# Check if log file exists and has content
if [ ! -f "$LOG_FILE" ]; then
  echo "❌ ERROR: Log file not created!"
  exit 1
fi

if [ ! -s "$LOG_FILE" ]; then
  echo "❌ ERROR: Log file is empty!"
  exit 1
fi

echo "📋 Last 30 lines of log output:"
echo "================================================"
tail -n 30 "$LOG_FILE"
echo "================================================"
echo ""

# Check for success indicators
SUCCESS=true

echo "🔍 Checking for success indicators..."
echo ""

# Check 1: Look for "App running at" or similar success message
if grep -q "App running at" "$LOG_FILE"; then
  echo "✅ Found 'App running at' - Server started successfully"
elif grep -q "Compiled successfully" "$LOG_FILE"; then
  echo "✅ Found 'Compiled successfully' - App compiled"
elif grep -q "Starting frontend" "$LOG_FILE"; then
  echo "✅ Found 'Starting frontend' - Frontend started"
else
  echo "⚠️  Warning: Could not find clear success message"
  SUCCESS=false
fi

# Check 2: Look for critical errors
echo ""
if grep -qi "error" "$LOG_FILE" | head -5; then
  echo "⚠️  Found errors in log (showing first 5):"
  grep -i "error" "$LOG_FILE" | head -5
  echo ""
fi

if grep -qi "traceback" "$LOG_FILE"; then
  echo "⚠️  Found Python traceback in log"
  SUCCESS=false
fi

if grep -qi "failed" "$LOG_FILE"; then
  echo "⚠️  Found 'failed' in log"
  SUCCESS=false
fi

# Check 3: Look for port binding
echo ""
if grep -q "localhost:3000" "$LOG_FILE" || grep -q "127.0.0.1:3000" "$LOG_FILE" || grep -q ":3000" "$LOG_FILE"; then
  echo "✅ Found port 3000 binding - Server listening on expected port"
elif grep -q "localhost:8000" "$LOG_FILE" || grep -q ":8000" "$LOG_FILE"; then
  echo "✅ Found port 8000 binding - Backend server running"
fi

# Check 4: Look for compilation success
echo ""
if grep -q "Compiling:" "$LOG_FILE"; then
  echo "✅ Found compilation activity"
fi

echo ""
echo "================================================"
echo "Test Summary"
echo "================================================"

if [ "$SUCCESS" = true ]; then
  echo "✅ SUCCESS: Reflex app appears to have started correctly!"
  echo ""
  echo "The app initialized within 10 seconds and key success"
  echo "indicators were found in the logs."
  exit 0
else
  echo "❌ ISSUES DETECTED: There may be problems with app startup"
  echo ""
  echo "Please review the log file for details:"
  echo "  cat $LOG_FILE"
  echo ""
  echo "Or check for specific errors:"
  echo "  grep -i error $LOG_FILE"
  exit 1
fi
