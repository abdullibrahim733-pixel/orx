#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [[ ! -d .venv ]]; then
  echo "No .venv found. Run ./scripts/setup.sh first."
  exit 1
fi

source .venv/bin/activate

echo "Orx Benchmark Mode — FPS output every second. Close window to end."
python -m orx --bench
