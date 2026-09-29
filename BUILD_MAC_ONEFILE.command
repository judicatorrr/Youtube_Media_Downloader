#!/bin/bash
set -e
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

if [ ! -d ".venv" ]; then
  "$PYTHON" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python build_app.py --onefile

echo
echo "ONEFILE build is in the dist folder."
