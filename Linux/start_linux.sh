#!/bin/bash
set -e
cd "$(dirname "$0")/../Files"

python_ok() {
  local exe="$1"
  command -v "$exe" >/dev/null 2>&1 || return 1
  "$exe" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)' >/dev/null 2>&1
}

find_python() {
  for candidate in "${PYTHON:-}" python3.14 python3.13 python3.12 python3.11 python3; do
    [ -n "$candidate" ] || continue
    if python_ok "$candidate"; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

PYTHON_EXE="$(find_python || true)"

if [ -z "$PYTHON_EXE" ]; then
  echo "Python 3.11+ not found. Trying to install it automatically..."

  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-pip ca-certificates
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y python3 python3-pip ca-certificates
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm python python-pip ca-certificates
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper --non-interactive install python3 python3-pip ca-certificates
  else
    echo "No supported package manager was found (apt/dnf/pacman/zypper)."
    exit 1
  fi

  PYTHON_EXE="$(find_python || true)"
fi

if [ -z "$PYTHON_EXE" ]; then
  echo "Python was installed, but version 3.11+ is still unavailable."
  exit 1
fi

# yt-dlp Auto mode on Linux intentionally uses the system CA store.
# Ensure a CA bundle exists, especially on minimal distributions/containers.
if [ ! -s /etc/ssl/certs/ca-certificates.crt ] && \
   [ ! -s /etc/pki/tls/certs/ca-bundle.crt ] && \
   [ ! -s /etc/ssl/ca-bundle.pem ]; then
  echo "System CA certificates are missing. Installing ca-certificates..."
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y ca-certificates
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y ca-certificates
  elif command -v pacman >/dev/null 2>&1; then
    sudo pacman -S --needed --noconfirm ca-certificates
  elif command -v zypper >/dev/null 2>&1; then
    sudo zypper --non-interactive install ca-certificates
  fi
fi

echo "Python: $PYTHON_EXE"

if [ -x ".venv/bin/python" ] && ! python_ok ".venv/bin/python"; then
  echo "Old Python detected in .venv. Recreating environment..."
  rm -rf .venv
fi

if [ ! -x ".venv/bin/python" ]; then
  "$PYTHON_EXE" -m venv .venv
fi

VENV_PY=".venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt

echo "Checking yt-dlp / FFmpeg / FFprobe / Deno..."
"$VENV_PY" bootstrap_dependencies.py

exec "$VENV_PY" main.py
