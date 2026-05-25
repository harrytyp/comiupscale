#!/usr/bin/env bash
# Batch upscale objects and object layers with RealESRGAN
# Usage: bash hd_config/upscale_objects.sh
#
# Input:  CMI UPSCALED/extracted/COMI/IMAGES/objects/  (600 PNGs)
#         CMI UPSCALED/extracted/COMI/IMAGES/objects_layers/  (234 PNGs)
# Output: CMI UPSCALED/upscaled/objects/
#         CMI UPSCALED/upscaled/objects_layers/

set -e

REALESRGAN="/z/Projekte/COMI-Upscaled/tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe"
MODEL="realesrgan-x4plus-anime"
MODELS_DIR="/z/Projekte/COMI-Upscaled/tools/realesrgan-ncnn-vulkan-v0.2.0-windows/models"
BASE="/z/Projekte/COMI-Upscaled/CMI UPSCALED"

upscale_dir() {
    local SRC="$1"
    local DST="$2"
    local NAME="$3"

    mkdir -p "$DST"
    total=$(ls "$SRC"/*.png 2>/dev/null | wc -l)
    count=0

    echo "=== $NAME: $total files → $DST ==="
    for src in "$SRC"/*.png; do
        name=$(basename "$src")
        out="$DST/$name"
        count=$((count + 1))

        if [ -f "$out" ]; then
            echo "[$count/$total] SKIP $name (exists)"
            continue
        fi

        echo "[$count/$total] Upscaling $name..."
        "$REALESRGAN" -i "$src" -o "$out" -m "$MODELS_DIR" -n "$MODEL"
    done
    echo "✓ $NAME done ($count/$total)"
    echo ""
}

# Objects
upscale_dir "$BASE/extracted/COMI/IMAGES/objects" \
            "$BASE/upscaled/objects" \
            "Objects"

# Object layers
upscale_dir "$BASE/extracted/COMI/IMAGES/objects_layers" \
            "$BASE/upscaled/objects_layers" \
            "Object layers"

echo "=== All done! ==="
echo "Next step: copy upscaled PNGs to ScummVM/monkey3/hd/objects/ and hd/objects_layers/"
