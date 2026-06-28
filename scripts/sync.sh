#!/usr/bin/env bash
set -e

MODE="${1:-dev}"

OS="$(uname -s)"
case "$OS" in
  Linux*|Darwin*)
    VENV_BIN=".venv/bin"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    VENV_BIN=".venv/Scripts"
    ;;
  *)
    echo "Warning: unrecognized OS '$OS', assuming Unix-like paths."
    VENV_BIN=".venv/bin"
    ;;
esac

if [ ! -f "$VENV_BIN/python" ] && [ ! -f "$VENV_BIN/python.exe" ]; then
  echo "Error: virtual environment not found. Run scripts/setup.sh first." >&2
  exit 1
fi

export PATH="$(pwd)/$VENV_BIN:$PATH"

_require_env_file() {
  if [ ! -f "$1" ]; then
    echo "Error: $1 not found. Copy $1.example and fill in values." >&2
    exit 1
  fi
}

case "$MODE" in
  dev)
    _require_env_file ".env.dev"
    echo "Running force-sync [dev]..."
    ENVIRONMENT=dev python -m databases.sync
    ;;

  dev_tunnel)
    _require_env_file ".env.dev_tunnel"
    echo "Running force-sync [dev-tunnel]..."
    ENVIRONMENT=dev_tunnel python -m databases.sync
    ;;

  prod)
    _require_env_file ".env.prod"
    echo "Running force-sync [prod]..."
    ENVIRONMENT=prod python -m databases.sync
    ;;

  *)
    echo "Usage: bash scripts/sync.sh [dev|dev_tunnel|prod]" >&2
    exit 1
    ;;
esac
