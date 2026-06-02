#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v python &>/dev/null; then
  echo "python not found on PATH"
  exit 1
fi

PY_VER="$(python -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
echo "Using python ${PY_VER}"

if [[ ! -d .venv ]]; then
  # `--upgrade-deps` installs/updates pip+setuptools in the venv when supported.
  python -m venv --upgrade-deps .venv || python -m venv .venv
fi

source .venv/bin/activate

if ! python -m pip -V &>/dev/null; then
  cat <<'EOF'
pip is not available in this virtualenv.

On Arch Linux, install pip for your Python and re-run:
  sudo pacman -S --needed python-pip

If you manage Python via mise/pyenv, ensure that build includes ensurepip,
or install pip into the interpreter, then re-run this script.
EOF
  exit 1
fi

python -m pip install -U pip
python -m pip install -e ".[dev]"

cat <<'EOF'

Setup complete.

Next:
  source .venv/bin/activate
  python -m orx

Arch notes:
  You likely want SDL2 installed via pacman (for best integration):
    sudo pacman -S --needed sdl2 sdl2_image sdl2_mixer sdl2_ttf

EOF

