#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Error: install Python 3.9+ on the Linux host.' >&2
  exit 2
fi
exec python3 "$SCRIPT_DIR/launcher.py" "$@"
