#!/usr/bin/env bash
# ============================================================================
# COMI Upscaled — Upscale Costumes + Fonts with RealESRGAN + Alpha Fixup
# ============================================================================
# Upscales all remaining assets (costumes + fonts) using the same RealESRGAN
# pipeline, then deploys to the ScummVM HD directory and runs alpha fixup.
#
# Usage:
#   bash config/upscale/upscale_remaining.sh
#
# Flags:
#   --skip-upscale   Skip AI upscaling (just deploy existing + alpha fixup)
#   --skip-alpha     Skip alpha fixup (just upscale + deploy)
#   --costumes-only  Only upscale costumes, skip fonts
#   --fonts-only     Only upscale fonts, skip costumes
#   --gpu ID         GPU device ID for RealESRGAN (default: auto)
#   --help           Show this message
#
# Requirements:
#   - RealESRGAN-NCNN-Vulkan (AMD GPU compatible via Vulkan)
#   - Python 3 with Pillow, numpy
#
# NOTE: The costume source dir has 25K+ files on a NAS, so shell glob/ls
# on the entire directory is VERY slow. This script uses Python for the
# actual file iteration to avoid the bottleneck entirely.
# ============================================================================

set -euo pipefail

# ---- Configuration ---------------------------------------------------------
PROJECT_ROOT=""
BASE="$PROJECT_ROOT/assets"

REALESRGAN="$PROJECT_ROOT/tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe"
MODEL="realesrgan-x4plus-anime"
MODELS_DIR="$PROJECT_ROOT/tools/realesrgan-ncnn-vulkan-v0.2.0-windows/models"

EXTRACTED_COSTUMES="$BASE/extracted/COMI/costumes"
EXTRACTED_FONTS="$BASE/extracted/COMI/fonts"
UPSCALED_COSTUMES="$BASE/upscaled/costumes"
UPSCALED_FONTS="$BASE/upscaled/fonts"
HD_DIR="$PROJECT_ROOT/game/hd"
HD_COSTUMES="$HD_DIR/costumes"
HD_FONTS="$HD_DIR/fonts"

PYTHON="/c/Users/kolja/AppData/Local/Programs/Python/Python312/python.exe"

GPU_ID="auto"
SKIP_UPSCALE=false
SKIP_ALPHA=false
COSTUMES_ONLY=false
FONTS_ONLY=false

# ---- Parse args -----------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --skip-upscale)   SKIP_UPSCALE=true; shift ;;
        --skip-alpha)     SKIP_ALPHA=true; shift ;;
        --costumes-only)  COSTUMES_ONLY=true; shift ;;
        --fonts-only)     FONTS_ONLY=true; shift ;;
        --gpu)            GPU_ID="$2"; shift 2 ;;
        --help)           grep "^#" "$0" | grep -v "^#!" | head -30 | cut -c3-; exit 0 ;;
        *)                echo "Unknown: $1"; exit 1 ;;
    esac
done

# ---- Helper functions ------------------------------------------------------
info()  { echo -e "\033[36m[INFO]\033[0m $*"; }
ok()    { echo -e "\033[32m[ OK ]\033[0m $*"; }
warn()  { echo -e "\033[33m[WARN]\033[0m $*"; }
fail()  { echo -e "\033[31m[FAIL]\033[0m $*"; exit 1; }

# ---- Check prerequisites ---------------------------------------------------
check_prereqs() {
    if [ ! -f "$REALESRGAN" ]; then
        fail "RealESRGAN not found at $REALESRGAN"
    fi
    if [ ! -d "$EXTRACTED_COSTUMES" ]; then
        fail "Costume source directory not found: $EXTRACTED_COSTUMES"
    fi
    if [ ! -d "$EXTRACTED_FONTS" ]; then
        fail "Fonts source directory not found: $EXTRACTED_FONTS"
    fi
    $PYTHON -c "from PIL import Image; import numpy" 2>/dev/null || \
        fail "Python with Pillow & numpy not found at $PYTHON"
    ok "Prerequisites satisfied"
}

# ---- Step 1: Upscale costumes (via dedicated Python script) -----------------
upscale_costumes() {
    if [ "$SKIP_UPSCALE" = true ]; then
        info "Skipping costume upscale (--skip-upscale)"
        return
    fi

    mkdir -p "$UPSCALED_COSTUMES"
    info "Upscaling costume PNGs with RealESRGAN ($MODEL)..."

    $PYTHON "$PROJECT_ROOT/scripts/upscale_costumes.py" \
        --gpu "$GPU_ID" \
        --src "$EXTRACTED_COSTUMES" \
        --dst "$UPSCALED_COSTUMES" \
        --esrgan "$REALESRGAN" \
        --models "$MODELS_DIR" \
        --model-name "$MODEL" \
        --skip-existing

    ok "Costume upscale done"
}

# ---- Step 2: Upscale fonts -------------------------------------------------
upscale_fonts() {
    if [ "$SKIP_UPSCALE" = true ]; then
        info "Skipping font upscale (--skip-upscale)"
        return
    fi

    mkdir -p "$UPSCALED_FONTS"

    info "Upscaling font chars.png files..."

    for fontdir in "$EXTRACTED_FONTS"/*/; do
        # Only iterate the 5 font dirs — safe to glob
        [ -d "$fontdir" ] || continue
        fontname=$(basename "$fontdir")
        src="$fontdir/chars.png"
        dst="$UPSCALED_FONTS/${fontname}_chars.png"

        if [ ! -f "$src" ]; then
            warn "No chars.png in $fontdir, skipping"
            continue
        fi

        if [ -f "$dst" ]; then
            echo "  $fontname/chars.png → already exists, skipping"
            continue
        fi

        echo "  Upscaling $fontname/chars.png (896×896 → 3584×3584)..."
        "$REALESRGAN" -i "$src" -o "$dst" -m "$MODELS_DIR" -n "$MODEL" -g "$GPU_ID"
    done

    FONT_DONE=$(find "$UPSCALED_FONTS" -maxdepth 1 -name "*.png" 2>/dev/null | wc -l)
    ok "Fonts: $FONT_DONE upscaled"
}

# ---- Step 3: Deploy to HD directory ----------------------------------------
deploy_hd() {
    info "Deploying upscaled assets to HD directory..."

    if [ "$FONTS_ONLY" = false ]; then
        mkdir -p "$HD_COSTUMES"
        $PYTHON "$PROJECT_ROOT/scripts/deploy_hd.py" \
            --src "$UPSCALED_COSTUMES" \
            --dst "$HD_COSTUMES"
    fi

    if [ "$COSTUMES_ONLY" = false ]; then
        mkdir -p "$HD_FONTS"
        FONT_COUNT=0
        for src in "$UPSCALED_FONTS"/*.png; do
            [ -f "$src" ] || continue
            fname=$(basename "$src")
            if [ ! -f "$HD_FONTS/$fname" ]; then
                cp "$src" "$HD_FONTS/$fname"
                FONT_COUNT=$((FONT_COUNT + 1))
            fi
        done
        HD_FONT=$(find "$HD_FONTS" -maxdepth 1 -name "*.png" 2>/dev/null | wc -l)
        ok "Fonts deployed: $HD_FONT files → $HD_FONTS/"
    fi
}

# ---- Step 4: Alpha fixup on HD assets ------------------------------------
run_alpha_fixup() {
    if [ "$SKIP_ALPHA" = true ]; then
        info "Skipping alpha fixup (--skip-alpha)"
        return
    fi

    info "Running alpha transparency fixup on HD objects & costumes..."

    $PYTHON "$PROJECT_ROOT/scripts/add_object_alpha_v4.py"
    ok "Object alpha fixup complete"

    $PYTHON "$PROJECT_ROOT/scripts/add_costume_alpha.py"
    ok "Costume alpha fixup complete"
}

# ---- Summary (no glob on 25K dirs) -----------------------------------------
print_summary() {
    # Only count small dirs with ls; skip counting costumes (slow on NAS)
    BG_COUNT=$(ls "$HD_DIR"/bg_*.png 2>/dev/null | wc -l)
    OBJ_COUNT=$(ls "$HD_DIR/objects/"*.png 2>/dev/null | wc -l)
    LYR_COUNT=$(ls "$HD_DIR/objects_layers/"*.png 2>/dev/null | wc -l)
    VID_COUNT=$(ls "$HD_DIR/videos/"*.mp4 2>/dev/null | wc -l)
    FONT_COUNT=$(ls "$HD_FONTS"/*_chars.png 2>/dev/null | wc -l)

    echo "  Backgrounds:    $BG_COUNT"
    echo "  Objects:        $OBJ_COUNT"
    echo "  Object layers:  $LYR_COUNT"
    echo "  Cutscene vids:  $VID_COUNT"
    echo "  Fonts:          $FONT_COUNT"

    if [ -d "$HD_COSTUMES" ]; then
        # Quick count via Python (much faster than bash glob on NAS)
        COST_COUNT=$($PYTHON -c "
import os; c=0
with os.scandir('game/hd/costumes') as it:
    for e in it:
        if e.name.endswith('.png') and e.is_file(): c+=1
print(c)
")
        echo "  Costumes:       $COST_COUNT"
    fi
}

# ---- Main ------------------------------------------------------------------
echo ""
echo "=== COMI Upscaled — Remaining Assets Pipeline ==="
echo "Model:      $MODEL"
echo "GPU:        $GPU_ID"
echo "Output:     $HD_DIR/"
echo ""

check_prereqs

if [ "$COSTUMES_ONLY" = false ] && [ "$FONTS_ONLY" = false ]; then
    upscale_costumes
    upscale_fonts
elif [ "$COSTUMES_ONLY" = true ]; then
    upscale_costumes
elif [ "$FONTS_ONLY" = true ]; then
    upscale_fonts
fi

deploy_hd
run_alpha_fixup

echo ""
echo "=== All done! ==="
print_summary
echo ""
echo "Next step after this: generate hd_manifest.json"
echo "  python scripts/hd_manifest_gen.py --hd-dir assets/upscaled"
