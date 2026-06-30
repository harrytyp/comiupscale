#!/bin/bash
# COMI-Upscaled — Start Script (Linux)
# 
# 1. Edit GAME_PATH below to point to your COMI game folder
# 2. Make this script executable: chmod +x start_comi_hd.sh
# 3. Run: ./start_comi_hd.sh

SCUMMVM_DIR="$(cd "$(dirname "$0")" && pwd)"
GAME_PATH="/pfad/zu/deinem/COMI-Ordner"  # ← Bitte anpassen!
HD_PATH="$SCUMMVM_DIR/hd"

# Für Systeme ohne dedizierte GPU (Docker, VM, Headless):
# Exportiere diese Zeilen bei Bedarf:
# export LIBGL_ALWAYS_SOFTWARE=1
# export GALLIUM_DRIVER=llvmpipe

exec "$SCUMMVM_DIR/scummvm" \
    --config="$SCUMMVM_DIR/scummvm.ini" \
    --path="$GAME_PATH" \
    --renderer=opengl \
    comi
