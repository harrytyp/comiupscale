#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# COMI Upscaled — Quick Setup Script
# ============================================================
# This script downloads the pre-built ScummVM HD binary and HD
# background assets, places them alongside your game files, and
# gets you playing in minutes.
#
# Usage:
#   ./setup.sh --game /path/to/COMI
#
# Flags:
#   --game PATH     Path to your COMI game directory (COMI.LA0/1/2)
#   --release VER   GitHub release tag to use (default: latest)
#   --no-videos     Skip downloading upscaled videos from archive.org
#   --help          Show this message
# ============================================================

GH_REPO="harrytyp/comiupscale"
GAME_DIR=""
RELEASE_TAG="latest"
NO_VIDEOS=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --game)     GAME_DIR="$2"; shift 2 ;;
        --release)  RELEASE_TAG="$2"; shift 2 ;;
        --no-videos) NO_VIDEOS=true; shift ;;
        --help)     grep "^#" "$0" | head -30 | cut -c3-; exit 0 ;;
        *)          echo "Unknown: $1"; exit 1 ;;
    esac
done

if [ -z "$GAME_DIR" ]; then
    echo "ERROR: --game is required. Usage: ./setup.sh --game /path/to/COMI"
    exit 1
fi

# Resolve paths
GAME_DIR="$(realpath "$GAME_DIR")"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/game"

echo "=== COMI Upscaled Setup ==="
echo "Game files:  $GAME_DIR"
echo "Output dir:  $OUTPUT_DIR"
echo "Release:     $RELEASE_TAG"
echo ""

# --- Step 1: Verify game files ---
echo "[1/5] Verifying game files..."
LA0=$(find "$GAME_DIR" -maxdepth 1 -iname "COMI.LA0" -print -quit)
LA1=$(find "$GAME_DIR" -maxdepth 1 -iname "COMI.LA1" -print -quit)
LA2=$(find "$GAME_DIR" -maxdepth 1 -iname "COMI.LA2" -print -quit)
if [ -z "$LA0" ] || [ -z "$LA1" ] || [ -z "$LA2" ]; then
    echo "ERROR: COMI.LA0, COMI.LA1, COMI.LA2 not found in $GAME_DIR"
    echo "Make sure these files are in the specified directory."
    exit 1
fi
echo "  OK — found COMI.LA0/1/2"

# --- Step 2: Download ScummVM HD binary ---
echo "[2/5] Downloading ScummVM HD binary..."
mkdir -p "$OUTPUT_DIR"

if [ "$RELEASE_TAG" = "latest" ]; then
    API_URL="https://api.github.com/repos/$GH_REPO/releases/latest"
else
    API_URL="https://api.github.com/repos/$GH_REPO/releases/tags/$RELEASE_TAG"
fi

# Find the scummvm-hd asset URL
ASSET_URL=$(curl -sL "$API_URL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if asset['name'].startswith('scummvm-hd'):
        print(asset['browser_download_url'])
        break
")

if [ -z "$ASSET_URL" ]; then
    echo "WARNING: Could not find scummvm-hd binary in release. Skipping."
    echo "  You'll need to build it yourself (see docs/BUILD.md)."
else
    echo "  Downloading from $ASSET_URL"
    curl -L -o "$OUTPUT_DIR/scummvm-hd.exe" "$ASSET_URL"
    chmod +x "$OUTPUT_DIR/scummvm-hd.exe"
    echo "  OK — scummvm-hd.exe ($(du -h "$OUTPUT_DIR/scummvm-hd.exe" | cut -f1))"
fi

# --- Step 3: Copy game files ---
echo "[3/5] Copying game files..."
cp "$LA0" "$OUTPUT_DIR/COMI.LA0"
cp "$LA1" "$OUTPUT_DIR/COMI.LA1"
cp "$LA2" "$OUTPUT_DIR/COMI.LA2"
echo "  OK — game files copied"

# --- Step 4: Download HD backgrounds ---
echo "[4/5] Downloading HD backgrounds..."
if [ "$RELEASE_TAG" = "latest" ]; then
    BG_URL="$API_URL"
else
    BG_URL="https://api.github.com/repos/$GH_REPO/releases/tags/$RELEASE_TAG"
fi

BG_ZIP_URL=$(curl -sL "$BG_URL" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for asset in data.get('assets', []):
    if asset['name'].startswith('hd-backgrounds'):
        print(asset['browser_download_url'])
        break
")

if [ -z "$BG_ZIP_URL" ]; then
    echo "WARNING: Could not find hd-backgrounds.zip in release. Skipping."
    echo "  You'll need to run the upscale pipeline (see scripts/full_pipeline.sh)."
else
    echo "  Downloading from $BG_ZIP_URL"
    curl -L -o /tmp/hd-backgrounds.zip "$BG_ZIP_URL"
    mkdir -p "$OUTPUT_DIR/hd"
    unzip -o -q /tmp/hd-backgrounds.zip -d "$OUTPUT_DIR/hd/"
    rm -f /tmp/hd-backgrounds.zip
    COUNT=$(ls "$OUTPUT_DIR/hd/"*.png 2>/dev/null | wc -l)
    echo "  OK — $COUNT HD backgrounds extracted to hd/"
fi

# --- Step 5: Download upscaled videos (optional) ---
VIDEO_DIR="$OUTPUT_DIR/hd/videos"
if [ "$NO_VIDEOS" = false ]; then
    echo "[5/5] Downloading upscaled videos from archive.org..."
    echo "  Source: https://archive.org/details/COMI_4k"
    echo "  Downloads may be large (several GB)."
    echo "  Run with --no-videos to skip this step."
    echo ""
    echo "  Downloading manifest..."
    
    # Try to download from archive.org
    IA_BASE="https://archive.org/download/COMI_4k"
    IA_FILES=$(curl -sL "$IA_BASE/" | python3 -c "
import sys, re, html
content = sys.stdin.read()
# Find file links
for m in re.finditer(r'href=\"([^\"]+\.(avi|mp4|mkv))\">', content):
    fname = html.unescape(m.group(1))
    print(fname)
" 2>/dev/null || echo "")
    
    if [ -n "$IA_FILES" ]; then
        mkdir -p "$VIDEO_DIR"
        echo "$IA_FILES" | while read -r fname; do
            echo "  Downloading $fname..."
            curl -L -o "$VIDEO_DIR/$fname" "$IA_BASE/$fname"
        done
        echo "  OK — videos downloaded to hd/videos/"
    else
        echo "  SKIP — couldn't fetch video list from archive.org."
        echo "  Download manually from: https://archive.org/details/COMI_4k"
    fi
else
    echo "[5/5] Skipping videos (--no-videos)"
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "To play:"
echo "  cd $OUTPUT_DIR"
echo "  ./scummvm-hd.exe --path=. scumm:comi"
echo ""
echo "If the binary wasn't downloaded (no GitHub release yet),"
echo "build from source: cd scummvm-fork && ./configure ... (see docs/BUILD.md)"
