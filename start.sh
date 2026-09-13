#!/usr/bin/env bash
# Starts both DHRUVA servers (backend on :8000, frontend on :5173) and opens
# the app in your browser. Safe to run more than once — it detects a server
# that's already up and leaves it alone rather than starting a duplicate.
#
# Usage:
#   ./start.sh          # start both servers
#   ./stop.sh           # stop both servers (companion script)

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend"
BACKEND_LOG="/tmp/dhruva-backend.log"
FRONTEND_LOG="/tmp/dhruva-frontend.log"

is_up() {
  # $1 = URL. 200 means up; anything else (including curl failing = 000) means down.
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$1" 2>/dev/null)" = "200" ]
}

echo "== DHRUVA startup =="
echo

# --------------------------------------------------------------- backend ----
if is_up "http://localhost:8000/health"; then
  echo "[backend]  already running on :8000 — leaving it alone"
else
  echo "[backend]  starting..."
  cd "$BACKEND_DIR" || { echo "backend/ not found at $BACKEND_DIR"; exit 1; }

  if [ ! -d .venv ]; then
    echo "[backend]  no .venv found — setting up (first run only, ~1 min)"
    uv venv --python 3.12
    # shellcheck disable=SC1091
    source .venv/bin/activate
    uv pip install -e ".[data,geo,graph,dev]"
  else
    # shellcheck disable=SC1091
    source .venv/bin/activate
  fi

  nohup uvicorn dhruva.app:app --port 8000 > "$BACKEND_LOG" 2>&1 &
  disown
  cd "$REPO_ROOT" || exit 1
fi

# -------------------------------------------------------------- frontend ----
if is_up "http://localhost:5173"; then
  echo "[frontend] already running on :5173 — leaving it alone"
else
  echo "[frontend] starting..."
  cd "$FRONTEND_DIR" || { echo "frontend/ not found at $FRONTEND_DIR"; exit 1; }

  if [ ! -d node_modules ]; then
    echo "[frontend] no node_modules found — installing (first run only)"
    npm install
  fi

  nohup npm run dev -- --port 5173 > "$FRONTEND_LOG" 2>&1 &
  disown
  cd "$REPO_ROOT" || exit 1
fi

# ------------------------------------------------------- wait for both up ----
echo
echo -n "Waiting for both servers to come up"
for _ in $(seq 1 30); do
  if is_up "http://localhost:8000/health" && is_up "http://localhost:5173"; then
    echo
    echo
    echo "Both servers are up:"
    echo "  Backend:   http://localhost:8000/health"
    echo "  Frontend:  http://localhost:5173"
    echo
    echo "Logs (if something looks wrong):"
    echo "  Backend:   $BACKEND_LOG"
    echo "  Frontend:  $FRONTEND_LOG"
    echo
    echo "Opening the app..."
    open "http://localhost:5173" 2>/dev/null || true
    exit 0
  fi
  echo -n "."
  sleep 1
done

echo
echo
echo "Servers did not come up within 30s. Check the logs:"
echo "  tail -50 $BACKEND_LOG"
echo "  tail -50 $FRONTEND_LOG"
exit 1
