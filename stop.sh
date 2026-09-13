#!/usr/bin/env bash
# Stops both DHRUVA servers started by start.sh.

if pkill -f "uvicorn dhruva.app" 2>/dev/null; then
  echo "[backend]  stopped"
else
  echo "[backend]  was not running"
fi

if pkill -f "vite" 2>/dev/null; then
  echo "[frontend] stopped"
else
  echo "[frontend] was not running"
fi
