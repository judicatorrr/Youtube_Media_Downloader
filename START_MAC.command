#!/bin/bash
set -e
cd "$(dirname "$0")"

MIN_MINOR=11
PYTHON_VERSION="3.12.10"

python_ok() {
  local exe="$1"
  [ -x "$exe" ] || command -v "$exe" >/dev/null 2>&1 || return 1
  "$exe" -c "import sys; raise SystemExit(0 if sys.version_info >= (3,$MIN_MINOR) else 1)" >/dev/null 2>&1
}

find_python() {
  for candidate in \
    "${PYTHON:-}" \
    python3.14 python3.13 python3.12 python3.11 python3 \
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
  echo "Python 3.11+ not found. Installing Python automatically..."

  if command -v brew >/dev/null 2>&1; then
    brew install python@3.12
  else
    PKG="/tmp/python-${PYTHON_VERSION}-macos11.pkg"
    URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-macos11.pkg"
    echo "Downloading $URL"
    curl -L "$URL" -o "$PKG"
    echo "macOS may ask for your administrator password."
    sudo installer -pkg "$PKG" -target /
    rm -f "$PKG"
  fi

  PYTHON_EXE="$(find_python || true)"
fi

if [ -z "$PYTHON_EXE" ]; then
  echo "Python 3.11+ could not be installed/found."
  exit 1
fi

echo "Python: $PYTHON_EXE"

if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_EXE" -m venv .venv
fi

VENV_PY=".venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt

echo "Checking yt-dlp / FFmpeg / FFprobe / Deno..."
"$VENV_PY" bootstrap_dependencies.py

exec "$VENV_PY" main.py
