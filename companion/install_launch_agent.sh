#!/bin/sh

set -eu

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script only runs on macOS." >&2
    exit 1
fi

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
PYTHON_BIN=${PYTHON:-python3}
if [ -x "$PYTHON_BIN" ]; then
    PYTHON_BIN=$(cd "$(dirname "$PYTHON_BIN")" && pwd)/$(basename "$PYTHON_BIN")
else
    PYTHON_BIN=$(command -v "$PYTHON_BIN")
fi
STATE_DIR="${HOME}/.cc-usage-display"
PLIST_DIR="${HOME}/Library/LaunchAgents"
PLIST_PATH="${PLIST_DIR}/com.ccusage.display.plist"
LOG_PATH="${STATE_DIR}/companion.log"

mkdir -p "$STATE_DIR" "$PLIST_DIR"

"$PYTHON_BIN" - "$PLIST_PATH" "$SCRIPT_DIR" "$PYTHON_BIN" "$LOG_PATH" <<'PY'
import plistlib
import sys

plist_path, script_dir, python_bin, log_path = sys.argv[1:]
plist = {
    "Label": "com.ccusage.display",
    "ProgramArguments": [
        python_bin,
        "-m",
        "cc_usage_display",
        "--log-file",
        log_path,
    ],
    "WorkingDirectory": script_dir,
    "EnvironmentVariables": {"PYTHONPATH": script_dir},
    "RunAtLoad": True,
    # The Python process owns the rotating companion.log file. Keep launchd's
    # inherited streams separate so it does not write to that file directly.
    "StandardOutPath": "/dev/null",
    "StandardErrorPath": "/dev/null",
}
with open(plist_path, "wb") as handle:
    plistlib.dump(plist, handle, sort_keys=False)
PY

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"

echo "LaunchAgent installed: $PLIST_PATH"
echo "Companion log: $LOG_PATH"
