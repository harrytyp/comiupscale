#!/usr/bin/env bash
# ============================================================================
# COMI Upscaled — Full Pipeline: Extract → Upscale → Build → Play
# ============================================================================
# This script automates the ENTIRE process from game files to playable HD:
#   1. Extract original backgrounds from COMI.LA0/1/2 
#   2. AI-upscale them 4× with RealESRGAN
#   3. Build the ScummVM HD fork from source
#   4. Place everything for instant play
#
# For the QUICK setup (download pre-built binary + pre-upscaled backgrounds),
# use ./setup.sh instead.
#
# Usage:
#   bash scripts/full_pipeline.sh --game /path/to/COMI
#
# Flags:
#   --game PATH     Path to your COMI game directory (COMI.LA0/1/2)
#   --skip-extract  Skip extraction (use existing PNGs)
#   --skip-upscale  Skip AI upscaling (use existing HD PNGs)
#   --skip-build    Skip ScummVM build
#   --model MODEL   RealESRGAN model name (default: realesrgan-x4plus-anime)
#   --help          Show this message
#
# Requires:
#   - Python 3 with numpy, pillow
#   - tools/nutcracker/ (included in repo)
#   - RealESRGAN-NCNN-Vulkan (for --skip-upscale, set ESRGAN env var)
#   - Linux build environment (for --skip-build, see build/BUILD.md)
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
GAME_DIR=""
SKIP_EXTRACT=false
SKIP_UPSCALE=false
SKIP_BUILD=false
ESRGAN_MODEL="realesrgan-x4plus-anime"

# Use Python NUTcracker module from repo
NUTCRACKER_PYTHON="PYTHONPATH=$PROJECT_ROOT/tools python3"
ESRGAN="${ESRGAN:-$PROJECT_ROOT/tools/realesrgan-ncnn-vulkan/realesrgan-ncnn-vulkan}"
ESRGAN_MODELS=""

SCRATCH="$PROJECT_ROOT/.pipeline"
ORIGINAL_DIR="$SCRATCH/original"
UPSCALED_DIR="$SCRATCH/upscaled"
HD_DIR="$PROJECT_ROOT/game/hd"

# --- Parse args ---
while [[ $# -gt 0 ]]; do
    case "$1" in
        --game)          GAME_DIR="$2"; shift 2 ;;
        --skip-extract)  SKIP_EXTRACT=true; shift ;;
        --skip-upscale)  SKIP_UPSCALE=true; shift ;;
        --skip-build)    SKIP_BUILD=true; shift ;;
        --model)         ESRGAN_MODEL="$2"; shift 2 ;;
        --help)          grep "^#" "$0" | head -10 | cut -c3-; exit 0 ;;
        *)               echo "Unknown: $1"; exit 1 ;;
    esac
done

if [ -z "$GAME_DIR" ]; then
    echo "ERROR: --game is required"
    exit 1
fi

GAME_DIR="$(realpath "$GAME_DIR")"

echo "=== COMI Upscaled — Full Pipeline ==="
echo "Game:      $GAME_DIR"
echo "Scratch:   $SCRATCH"
echo "Output:    $HD_DIR"
echo ""

# --- Step 1: Extract original backgrounds ---
if [ "$SKIP_EXTRACT" = false ]; then
    echo "[1/4] Extracting original backgrounds from game files..."
    mkdir -p "$ORIGINAL_DIR"
    
    if ! python3 -c "import nutcracker" 2>/dev/null; then
        echo "ERROR: NUTcracker module not found. Set PYTHONPATH=tools first:"
        echo "  export PYTHONPATH=$PROJECT_ROOT/tools"
        exit 1
    fi
    
    # Copy game files to scratch for extraction
    cp "$GAME_DIR"/*.LA0 "$GAME_DIR"/*.LA1 "$GAME_DIR"/*.LA2 "$SCRATCH/" 2>/dev/null || true
    
    # Room list with backgrounds
    # Rooms 1-93, skipping rooms without background images
    cd "$SCRATCH"
    for room in 1 2 4 5 6 9 10 11 12 13 14 15 16 17 18 19 20 \
                21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 \
                40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 \
                60 61 62 63 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79 \
                80 81 82 83 84 85 86 87 88 89 90 91 92 93; do
        rm -rf "room$room" 2>/dev/null
        "$NUTCRACKER" sputm room decode "COMI.LA0" "$room" 2>/dev/null || true
        # Look for background PNG
        bg=$(find "room$room" -maxdepth 1 -name "*.png" 2>/dev/null | head -1)
        if [ -n "$bg" ]; then
            cp "$bg" "$ORIGINAL_DIR/bg_$(printf '%04d' $room).png"
            echo "  Room $room: extracted"
        fi
    done
    COUNT=$(ls "$ORIGINAL_DIR"/*.png 2>/dev/null | wc -l)
    echo "  ✓ $COUNT backgrounds extracted to $ORIGINAL_DIR"
else
    echo "[1/4] Skipping extraction"
    COUNT=$(ls "$ORIGINAL_DIR"/*.png 2>/dev/null | wc -l)
    echo "  Using $COUNT existing backgrounds from $ORIGINAL_DIR"
fi

# --- Step 2: AI-upscale backgrounds ---
if [ "$SKIP_UPSCALE" = false ]; then
    echo "[2/4] AI-upscaling backgrounds 4× with RealESRGAN..."
    mkdir -p "$UPSCALED_DIR"
    
    if [ ! -f "$ESRGAN" ] && [ -z "$(command -v realesrgan-ncnn-vulkan 2>/dev/null || true)" ]; then
        echo "WARNING: RealESRGAN not found at $ESRGAN or in PATH"
        echo "  Install RealESRGAN-NCNN-Vulkan and set ESRGAN env var,"
        echo "  or run scripts/upscale_esrgan.py directly:"
        echo "    PYTHONPATH=$PROJECT_ROOT/tools python3 scripts/upscale_esrgan.py --input ..."
        echo "  Skipping upscale."
        SKIP_UPSCALE=true
    fi
    
    # Process each original PNG
    TOTAL=$(ls "$ORIGINAL_DIR"/*.png 2>/dev/null | wc -l)
    COUNT=0
    for src in "$ORIGINAL_DIR"/*.png; do
        fname=$(basename "$src")
        dst="$UPSCALED_DIR/$fname"
        if [ -f "$dst" ]; then
            echo "  [$((++COUNT))/$TOTAL] $fname — already upscaled, skipping"
            continue
        fi
        echo "  [$((++COUNT))/$TOTAL] Upscaling $fname..."
        "$ESRGAN" -i "$src" -o "$dst" -m "$ESRGAN_MODELS" -n "$ESRGAN_MODEL" 2>/dev/null
    done
    echo "  ✓ $TOTAL backgrounds upscaled"
else
    echo "[2/4] Skipping upscaling"
fi

# --- Step 3: Place HD backgrounds ---
echo "[3/4] Placing HD backgrounds in game directory..."
mkdir -p "$HD_DIR"
COUNT=0
for src in "$UPSCALED_DIR"/*.png; do
    fname=$(basename "$src")
    cp "$src" "$HD_DIR/$fname"
    ((COUNT++))
done
echo "  ✓ $COUNT HD backgrounds placed in $HD_DIR"

# --- Step 4: Build ScummVM fork (optional) ---
if [ "$SKIP_BUILD" = false ]; then
    echo "[4/4] Building ScummVM HD fork..."
    echo "  See build/BUILD.md for detailed instructions"
    
    cd "$PROJECT_ROOT"
    bash build/build-all.sh linux 2>&1
    
    if [ -f build/out/scummvm ]; then
        cp build/out/scummvm "$PROJECT_ROOT/game/scummvm"
        chmod +x "$PROJECT_ROOT/game/scummvm"
        echo "  ✓ Linux binary deployed to game/scummvm"
    fi
    if [ -f build/out/scummvm.exe ]; then
        cp build/out/scummvm.exe "$PROJECT_ROOT/game/scummvm.exe"
        echo "  ✓ Windows binary deployed to game/scummvm.exe"
    fi
else
    echo "[4/4] Skipping build"
fi

echo ""
echo "=== All done! ==="
echo "  Run: cd $PROJECT_ROOT/game"
echo "  ./scummvm --config=scummvm.ini --path=game --renderer=opengl comi"
echo "  (or double-click start_comi_hd.bat on Windows)"
echo ""
echo "For quick download of pre-upscaled assets instead, use:"
echo "  ./setup.sh --game $GAME_DIR"
