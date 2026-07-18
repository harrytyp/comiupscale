#!/bin/bash
# Record gameplay with the event recorder
# Usage: ./record_gameplay.sh [output_name]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
DUMPS_DIR="$REPO_DIR/dumps"
BUILD_DIR="$REPO_DIR/scummvm/fork/build-linux"
SCUMMVM="$BUILD_DIR/scummvm"
GAME_PATH="/opt/data/local/comi-hd-final"

mkdir -p "$DUMPS_DIR"

# Determine output file (event recorder only uses the filename, savepath sets the dir)
OUTPUT="${1:-record_$(date +%Y%m%d_%H%M%S)}"

echo "=== Recording gameplay to $DUMPS_DIR/${OUTPUT}.pbp ==="

# Kill any existing game process
pkill -f scummvm 2>/dev/null || true
sleep 1

# Run with event recorder
# --savepath controls where the .pbp file is stored
cd "$BUILD_DIR"
timeout 30 "$SCUMMVM" \
  --path="$GAME_PATH" \
  --savepath="$DUMPS_DIR" \
  --fullscreen \
  --record-mode=record \
  --record-file-name="${OUTPUT}.pbp" \
  comi 2>&1

echo "=== Recording saved ==="
ls -la "$DUMPS_DIR/${OUTPUT}.pbp" 2>/dev/null || echo "(recording may be empty if game exited too quickly)"
