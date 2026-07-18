#!/bin/bash
# Playback a recorded gameplay session
# Usage: ./playback_gameplay.sh <recording_basename>
#   e.g. ./playback_gameplay.sh record_20240718_123456
#   or:  ./playback_gameplay.sh /full/path/to/recording.pbp

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
DUMPS_DIR="$REPO_DIR/dumps"
BUILD_DIR="$REPO_DIR/scummvm/fork/build-linux"
SCUMMVM="$BUILD_DIR/scummvm"
GAME_PATH="/opt/data/local/comi-hd-final"

if [ -z "$1" ]; then
  echo "Usage: $0 <recording_basename_or_path>"
  echo "Examples:"
  echo "  $0 record_20240718_123456    (from dumps/ directory)"
  echo "  $0 /path/to/file.pbp         (full path)"
  echo ""
  echo "Available recordings:"
  ls -1 "$DUMPS_DIR"/*.pbp 2>/dev/null || echo "  (none in $DUMPS_DIR)"
  ls -1 /opt/data/home/.local/share/scummvm/saves/*.pbp 2>/dev/null | head -3
  exit 1
fi

# Determine the recording file
if [[ "$1" == *.pbp && -f "$1" ]]; then
  # Full path provided
  RECORD_FILE="$(basename "$1")"
  SAVE_PATH="$(dirname "$1")"
elif [[ "$1" == *.pbp ]]; then
  RECORD_FILE="$1"
  SAVE_PATH="$DUMPS_DIR"
else
  RECORD_FILE="${1}.pbp"
  SAVE_PATH="$DUMPS_DIR"
fi

echo "=== Playing back $SAVE_PATH/$RECORD_FILE ==="

# Kill any existing game process
pkill -f scummvm 2>/dev/null || true
sleep 1

# Run playback with event recorder
cd "$BUILD_DIR"
"$SCUMMVM" \
  --path="$GAME_PATH" \
  --savepath="$SAVE_PATH" \
  --fullscreen \
  --record-mode=playback \
  --record-file-name="$RECORD_FILE" \
  comi 2>&1

echo "=== Playback complete ==="
