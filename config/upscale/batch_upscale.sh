#!/usr/bin/env bash
# Batch upscale all 40 COMI backgrounds with RealESRGAN
# Place upscaled output in the HD directory for the ScummVM fork
#
# Usage: bash config/upscale/batch_upscale.sh

set -e

REALESRGAN="tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe"
MODEL="realesrgan-x4plus-anime"
MODELS_DIR="tools/realesrgan-ncnn-vulkan-v0.2.0-windows/models"

BG_SRC="assets/extracted/COMI/IMAGES/backgrounds"
HD_OUT="assets/upscaled/backgrounds"

mkdir -p "$HD_OUT"

echo "=== Batch upscaling $BG_SRC/*.png → $HD_OUT/ ==="
echo "Model: $MODEL"
echo ""

total=$(ls "$BG_SRC"/*.png 2>/dev/null | wc -l)
count=0

for bg in "$BG_SRC"/*.png; do
    name=$(basename "$bg")
    out="$HD_OUT/$name"
    count=$((count + 1))
    
    # Skip if already exists
    if [ -f "$out" ]; then
        echo "[$count/$total] SKIP $name (exists)"
        continue
    fi
    
    echo "[$count/$total] Upscaling $name..."
    "$REALESRGAN" -i "$bg" -o "$out" -m "$MODELS_DIR" -n "$MODEL"
    echo "  → $(du -h "$out" | cut -f1)"
done

echo ""
echo "Done! $count/$total backgrounds processed."
echo "Output: $HD_OUT/"
