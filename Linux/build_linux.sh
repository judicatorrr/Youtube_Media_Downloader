#!/bin/bash
set -e
cd "$(dirname "$0")/../Files"

python_ok() {
  local exe="$1"
  command -v "$exe" >/dev/null 2>&1 || return 1
  "$exe" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1
}

PYTHON_EXE=""
for candidate in "${PYTHON:-}" python3.14 python3.13 python3.12 python3.11 python3; do
  [ -n "$candidate" ] || continue
  if python_ok "$candidate"; then
    PYTHON_EXE="$(command -v "$candidate")"
    break
  fi
done

if [ -z "$PYTHON_EXE" ]; then
  echo "Python 3.11+ is required to build the app."
  echo "Run start_linux.sh first to prepare the runtime."
  exit 1
fi

if [ -x ".venv/bin/python" ] && ! python_ok ".venv/bin/python"; then
  rm -rf .venv
fi

if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_EXE" -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python build_app.py

echo
echo "Build is in the Files/dist folder."
