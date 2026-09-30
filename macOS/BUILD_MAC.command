#!/bin/bash
set -e
cd "$(dirname "$0")/../Files"

MIN_MINOR=11

python_ok() {
  local exe="$1"
  [ -n "$exe" ] || return 1
  command -v "$exe" >/dev/null 2>&1 || [ -x "$exe" ] || return 1
  "$exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,$MIN_MINOR) else 1)" >/dev/null 2>&1
}

find_python() {
  for candidate in \
    "${PYTHON:-}" \
    python3.14 python3.13 python3.12 python3.11 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3 \
    /Library/Frameworks/Python.framework/Versions/3.12/bin/python3
  do
    [ -n "$candidate" ] || continue
    if python_ok "$candidate"; then
      command -v "$candidate" 2>/dev/null || printf '%s\n' "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_EXE="$(find_python || true)"

if [ -z "$PYTHON_EXE" ]; then
  echo "Python 3.11+ is required to build the app."
  echo "Run START_MAC.command once: it can install Python 3.12 automatically."
  exit 1
fi

echo "Build Python: $("$PYTHON_EXE" --version)"

if [ -x ".venv/bin/python" ] && ! python_ok ".venv/bin/python"; then
  echo "Old build .venv detected. Recreating it..."
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
