#!/usr/bin/env bash
set -e

OS="$(uname -s)"
case "$OS" in
  Linux*|Darwin*)        : ;;
  MINGW*|MSYS*|CYGWIN*)  : ;;
  *)
    echo "Warning: unrecognized OS '$OS', proceeding with Unix-like commands."
    ;;
esac

echo "Cleaning Python bytecode & caches..."
find . -type f -name "*.pyc" -delete
find . -type f -name "*.pyo" -delete
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

echo "Cleaning tool caches..."
rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov

echo "Cleaning egg / dist artifacts..."
find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
rm -rf dist build

echo "Cleaning virtual environment..."
rm -rf .venv

echo "Cleaning local SQLite databases..."
find . -type f \( -name "*.db" -o -name "*.sqlite" -o -name "*.sqlite3" \) -delete

echo ""
echo "Done. To recreate the environment, run:"
case "$OS" in
  MINGW*|MSYS*|CYGWIN*) echo "  bash scripts/setup.sh" ;;
  *)                     echo "  bash scripts/setup.sh" ;;
esac
