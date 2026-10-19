#!/usr/bin/env bash
# webfetch — shell wrapper for webfetch.py.
#
# Locates webfetch.py next to this file and runs it with `uv run --script`,
# which resolves the PEP 723 dependencies declared in webfetch.py.
# Usage: webfetch.sh [flags] <URL>   (see webfetch.py --help)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! command -v uv >/dev/null 2>&1; then
  echo "webfetch.sh: 'uv' not found on PATH; install uv first." >&2
  exit 1
fi

exec uv run --script "$SCRIPT_DIR/webfetch.py" "$@"
