#!/bin/bash
# Build and register the claude-resume:// URL handler.
#   ./install.sh            → installs to ~/Applications/ClaudeResumeCopy.app
#   ./install.sh uninstall  → removes it and unregisters the scheme
set -euo pipefail

APP="${CLAUDE_RESUME_APP:-$HOME/Applications/ClaudeResumeCopy.app}"
SRC="$(cd "$(dirname "$0")" && pwd)/ClaudeResumeCopy.applescript"
LSREGISTER=/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister

if [ "${1:-}" = "uninstall" ]; then
    [ -d "$APP" ] && "$LSREGISTER" -u "$APP" 2>/dev/null || true
    rm -rf "$APP"
    echo "removed $APP"
    exit 0
fi

mkdir -p "$(dirname "$APP")"
rm -rf "$APP"
osacompile -o "$APP" "$SRC"

PLIST="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes array' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0 dict' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0:CFBundleURLName string "Claude Resume"' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0:CFBundleURLSchemes array' "$PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleURLTypes:0:CFBundleURLSchemes:0 string claude-resume' "$PLIST"
# No Dock icon or menu bar: it fires and quits.
/usr/libexec/PlistBuddy -c 'Add :LSUIElement bool true' "$PLIST"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier com.skproductions.claude-resume-copy' "$PLIST" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c 'Add :CFBundleIdentifier string com.skproductions.claude-resume-copy' "$PLIST"

"$LSREGISTER" -f "$APP"
echo "installed $APP"
echo "handler for: claude-resume://<session-id>"
