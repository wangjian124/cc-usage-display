#!/bin/sh

set -eu

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON_BIN=${PYTHON:-python3}

if [ -n "${PYTHONPATH:-}" ]; then
    export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"
else
    export PYTHONPATH="$SCRIPT_DIR"
fi

exec "$PYTHON_BIN" -m cc_usage_display "$@"
