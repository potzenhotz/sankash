#!/bin/bash
# Test if Reflex app starts correctly

set -e

LOG_FILE="reflex_startup_test.log"

echo "================================================"
echo "Testing Reflex App Startup"
echo "================================================"
echo ""

# Start Reflex in background with output to log file
echo "Starting Reflex app..."
if [ -d ".venv" ]; then
  script -q "$LOG_FILE" .venv/bin/reflex run &
else
  script -q "$LOG_FILE" uv run reflex run &
fi

APP_PID=$!
echo "Reflex app started with PID: $APP_PID"
echo ""

# Wait for app to start (check for listening port)
echo "Waiting for app to start..."
MAX_WAIT=30
elapsed=0

while [ $elapsed -lt $MAX_WAIT ]; do
  # Check if any port 3000-3010 is listening (Reflex picks first available)
  if lsof -i :3000-3010 -sTCP:LISTEN 2>/dev/null | grep -q LISTEN; then
    echo "✅ App is listening on a port!"
    PORT=$(lsof -i :3000-3010 -sTCP:LISTEN 2>/dev/null | grep LISTEN | head -1 | awk '{print $9}' | cut -d':' -f2)
    echo "   Port detected: $PORT"
    break
  fi
  sleep 1
  elapsed=$((elapsed + 1))
  echo -ne "  Waiting... ${elapsed}s\r"
done

echo ""

if [ $elapsed -ge $MAX_WAIT ]; then
  echo "❌ FAILED: App did not start within ${MAX_WAIT}s"
  kill $APP_PID 2>/dev/null || true
  exit 1
fi

# Wait a bit for log file to be written
sleep 5

# Display warnings and deprecations from log
echo ""
echo "================================================"
echo "Checking for Warnings"
echo "================================================"
echo ""

if [ -f "$LOG_FILE" ]; then
  # Extract warnings and deprecations
  WARNINGS=$(grep -E "(Warning:|DeprecationWarning:)" "$LOG_FILE" 2>/dev/null || true)

  if [ -z "$WARNINGS" ]; then
    echo "✅ No warnings found!"
  else
    echo "⚠️  Found the following warnings:"
    echo ""
    echo "$WARNINGS"
  fi
else
  echo "⚠️  Log file not found - cannot check for warnings"
fi

echo ""
echo "Stopping Reflex app (PID: $APP_PID)..."
kill $APP_PID 2>/dev/null || true
sleep 2
kill -9 $APP_PID 2>/dev/null || true

echo "App stopped."
echo ""
echo "================================================"
echo "✅ SUCCESS: Reflex app started successfully!"
echo "================================================"
echo ""
echo "The app started and was listening on port $PORT"
exit 0
