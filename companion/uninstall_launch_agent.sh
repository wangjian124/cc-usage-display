#!/bin/sh

set -eu

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script only runs on macOS." >&2
    exit 1
fi

PLIST_PATH="${HOME}/Library/LaunchAgents/com.ccusage.display.plist"

if [ -f "$PLIST_PATH" ]; then
    if ! launchctl bootout "gui/$(id -u)" "$PLIST_PATH" 2>/dev/null; then
        if launchctl print "gui/$(id -u)/com.ccusage.display" >/dev/null 2>&1; then
            echo "Could not unload the running LaunchAgent: $PLIST_PATH" >&2
            exit 1
        fi
    fi
    rm -f "$PLIST_PATH"
    echo "LaunchAgent removed: $PLIST_PATH"
else
    echo "LaunchAgent is not installed: $PLIST_PATH"
fi
