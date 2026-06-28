#!/usr/bin/env bash
set -e

OS="$(uname -s)"
case "$OS" in
  Linux*|Darwin*)
    VENV_PIP=".venv/bin/pip"
    VENV_PYTHON=".venv/bin/python"
    ;;
  MINGW*|MSYS*|CYGWIN*)
    VENV_PIP=".venv/Scripts/pip"
    VENV_PYTHON=".venv/Scripts/python"
    ;;
  *)
    echo "Warning: unrecognized OS '$OS', assuming Unix-like paths."
    VENV_PIP=".venv/bin/pip"
    VENV_PYTHON=".venv/bin/python"
    ;;
esac

if [ ! -f "$VENV_PIP" ]; then
  echo "Error: virtual environment not found. Run scripts/setup.sh first." >&2
  exit 1
fi

echo "Freezing dependencies to requirements.txt..."
"$VENV_PIP" freeze > requirements.txt

PKG_COUNT="$("$VENV_PYTHON" -c "print(sum(1 for l in open('requirements.txt') if l.strip()))")"
echo "Done. $PKG_COUNT packages written to requirements.txt"
