#!/usr/bin/env bash
# Orx: Ascension of the Prime Cy-Orx Launcher

# Navigate to the script's directory
cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment (.venv) not found."
    echo "Please run './scripts/setup.sh' first."
    exit 1
fi

PYTHON="./.venv/bin/python"

# Prefer the installed package, but fall back to the local src tree when the
# editable install has not been performed in this virtualenv yet.
if ! "$PYTHON" -c "import orx" >/dev/null 2>&1; then
    if [ -d "src/orx" ]; then
        export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)/src"
    else
        echo "Error: Could not import 'orx' and no local src tree was found."
        echo "Please run './scripts/setup.sh' first."
        exit 1
    fi
fi

# Run the game using the virtual environment's python.
# Forward all arguments to the game (e.g., --windowed, --debug)
"$PYTHON" -m orx "$@"
