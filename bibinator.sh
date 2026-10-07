#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

if command -v python3 &>/dev/null; then
    SYS_PYTHON=python3
elif command -v python &>/dev/null; then
    SYS_PYTHON=python
else
    echo "Error: Python is not installed."
    exit 1
fi

echo "Using $($SYS_PYTHON --version)"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $SYS_PYTHON -m venv "$VENV_DIR"
fi

PYTHON="$VENV_DIR/bin/python"

echo "Installing dependencies..."
$PYTHON -m pip install -q mysql-connector-python streamlit pandas numpy plotly

cd "$SCRIPT_DIR/src/app"
echo ""
$PYTHON main.py
