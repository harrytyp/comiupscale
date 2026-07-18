#!/usr/bin/env bash
# scripts/hd_screenshot.sh — capture current Xvfb frame as PNG
# Uses ImageMagick 'import' if available, falls back to ffmpeg

OUTPUT="/opt/data/local/comi-hd-repo/dumps/latest_screenshot.png"

if command -v import &>/dev/null; then
    DISPLAY=:99 import -window root "$OUTPUT"
else
    DISPLAY=:99 ffmpeg -f x11grab -video_size 2560x1920 -i :99 -vframes 1 "$OUTPUT"
fi
