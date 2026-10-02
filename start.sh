#!/usr/bin/env bash
# Start the 1 BIR portal and open it whenever Windows starts.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PORT="${PORT:-8000}"
URL="http://127.0.0.1:${PORT}/"

win_path() {
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$1"
  elif command -v wslpath >/dev/null 2>&1; then
    wslpath -w "$1"
  else
    printf '%s\n' "$1"
  fi
}

if [ -z "${APPDATA:-}" ] && command -v cmd.exe >/dev/null 2>&1; then
  APPDATA="$(cmd.exe /c 'echo %APPDATA%' | tr -d '\r')"
fi

if [ -n "${APPDATA:-}" ]; then
  STARTUP="${APPDATA}/Microsoft/Windows/Start Menu/Programs/Startup"
  mkdir -p "$STARTUP"
  LAUNCHER="${STARTUP}/1-BIR-start.cmd"
  WIN_ROOT="$(win_path "$ROOT")"
  cat > "$LAUNCHER" <<EOF
@echo off
cd /d "${WIN_ROOT}"
start "1 BIR Portal" cmd /k python manage.py runserver 127.0.0.1:${PORT}
timeout /t 3 /nobreak >nul
start ${URL}
EOF
  echo "1 BIR will open automatically when Windows starts."
  echo "To stop that, delete:"
  echo "  ${LAUNCHER}"
fi

if command -v cmd.exe >/dev/null 2>&1; then
  cmd.exe /c start "${URL}" >/dev/null 2>&1 || true
fi

exec python manage.py runserver "127.0.0.1:${PORT}"
