#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "Orx deploy (dev helper)"
echo "- repo: $(pwd)"

if [[ ! -d .venv ]]; then
  echo "No .venv found. Run ./scripts/setup.sh first."
  exit 1
fi

source .venv/bin/activate
python -m pip install -e .

echo "Done. Run: python -m orx"

