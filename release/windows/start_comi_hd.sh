#!/bin/bash
# COMI-Upscaled — Start Script (Linux)
# Automatically records gameplay to comi_recording.pbp

SCUMMVM_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME_PATH="${SCUMMVM_DIR}/game"

"${SCUMMVM_DIR}/scummvm" \
    --config="${SCUMMVM_DIR}/scummvm.ini" \
    --path="${GAME_PATH}" \
    --renderer=opengl \
    --record-mode=record \
    --record-file-name="${SCUMMVM_DIR}/comi_recording.pbp" \
    comi
