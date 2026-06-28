#!/usr/bin/env bash
set -e

# Detect OS and set venv paths
OS="$(uname -s)"
case "$OS" in
  Linux*|Darwin*)
    VENV_PYTHON=".venv/bin/python"
    VENV_PIP=".venv/bin/pip"
    PY_VERSIONED_PREFIX="python"
    PY_FALLBACK="python3"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    VENV_PYTHON=".venv/Scripts/python"
    VENV_PIP=".venv/Scripts/pip"
    PY_VERSIONED_PREFIX="python"
    PY_FALLBACK="python"
    ;;
  *)
    echo "Warning: unrecognized OS '$OS', assuming Unix-like paths."
    VENV_PYTHON=".venv/bin/python"
    VENV_PIP=".venv/bin/pip"
    PY_VERSIONED_PREFIX="python"
    PY_FALLBACK="python3"
    ;;
esac

# Resolve Python command from .python-version if present
PY_CMD="$PY_FALLBACK"
if [ -f ".python-version" ]; then
  PY_VER="$(tr -d '[:space:]' < .python-version)"
  PY_MINOR="$(echo "$PY_VER" | cut -d. -f1,2)"   # e.g. 3.11
  if command -v "${PY_VERSIONED_PREFIX}${PY_MINOR}" >/dev/null 2>&1; then
    PY_CMD="${PY_VERSIONED_PREFIX}${PY_MINOR}"
  elif command -v "$PY_FALLBACK" >/dev/null 2>&1; then
    ACTUAL="$("$PY_FALLBACK" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])')"
    if [ "$ACTUAL" != "$PY_VER" ]; then
      echo "Warning: .python-version requires $PY_VER but found $ACTUAL."
    fi
    PY_CMD="$PY_FALLBACK"
  else
    echo "Error: Python $PY_VER required but no matching interpreter found." >&2
    exit 1
  fi
fi

# Create venv if it doesn't exist
if [ ! -d ".venv" ]; then
  echo "Creating virtual environment (Python $("$PY_CMD" --version 2>&1 | awk '{print $2}'))..."
  "$PY_CMD" -m venv .venv
fi

echo "Upgrading pip..."
"$VENV_PYTHON" -m pip install --upgrade pip

echo "Installing dependencies..."
"$VENV_PIP" install -r requirements.txt

echo ""
echo "Done. Activate with:"
case "$OS" in
  Linux*|Darwin*)        echo "  source .venv/bin/activate" ;;
  MINGW*|MSYS*|CYGWIN*) echo "  .venv\\Scripts\\activate" ;;
  *)                     echo "  source .venv/bin/activate" ;;
esac
