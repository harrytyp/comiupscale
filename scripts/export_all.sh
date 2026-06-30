#!/usr/bin/env bash
# ============================================================================
# COMI Upscaled — Full Asset Export Script
# ============================================================================
# Extracts ALL visual assets from "The Curse of Monkey Island" (SCUMM V8):
#   - Backgrounds, Objects, Object Layers (via sputm room decode)
#   - Cutscene frames from 15 SAN files (via smush decode)
#   - Font glyph grids from 5 NUT files (via smush decode --nut)
#   - Costume/character sprites from 457 AKOS entries (via Python decoder)
#
# Usage:
#   cd <project-root>   # e.g. D:\COMI-Upscaled or wherever you cloned
#   bash scripts/export_all.sh
#
# Requires:
#   - NUTcracker binary: nutcracker-Windows_X64/nutcracker.exe
#   - NUTcracker Python source: nutcracker/src/
#   - Python 3.11+ with numpy, pillow, typer (pip install -r requirements.txt)
#   - Game files under game/ (COMI.LA0/1/2)
# ============================================================================

set -euo pipefail

# ---- Configuration ---------------------------------------------------------
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GAME_DIR="$PROJECT_ROOT/comi-hd-final"
RESOURCE_DIR="$GAME_DIR/RESOURCE"
NUTCRACKER="$PROJECT_ROOT/tools/nutcracker-Windows_X64/nutcracker.exe"
NUTCRACKER_SRC="$PROJECT_ROOT/../nutcracker_src"
OUTPUT_BASE="$PROJECT_ROOT/assets/extracted/COMI"
PYTHON=""
VERBOSE=false

# ---- Helper functions ------------------------------------------------------
info()  { echo -e "\033[36m[INFO]\033[0m $*"; }
ok()    { echo -e "\033[32m[ OK ]\033[0m $*"; }
warn()  { echo -e "\033[33m[WARN]\033[0m $*"; }
fail()  { echo -e "\033[31m[FAIL]\033[0m $*"; exit 1; }
count() { find "$1" -maxdepth 1 -name "*.png" 2>/dev/null | wc -l; }

# ---- Prerequisite checks ---------------------------------------------------
check_prereqs() {
  info "Checking prerequisites..."

  # Project root
  cd "$PROJECT_ROOT"

  # NUTcracker binary
  if [ ! -f "$NUTCRACKER" ]; then
    fail "NUTcracker binary not found at $NUTCRACKER"
  fi
  ok "NUTcracker binary found"

  # NUTcracker Python source
  if [ ! -d "$NUTCRACKER_SRC" ]; then
    fail "NUTcracker Python source not found at $NUTCRACKER_SRC"
  fi
  ok "NUTcracker Python source found"

  # Python with numpy - try system Python paths first (Hermes venv has no pip)
  PYTHON=""
  for try_py in \
    "$(command -v python3 2>/dev/null)" \
    "$(command -v python 2>/dev/null)" \
    "/c/Users/$USER/AppData/Local/Programs/Python/Python313/python.exe" \
    "/c/Users/$USER/AppData/Local/Programs/Python/Python312/python.exe"; do
    if [ -n "$try_py" ] && [ -x "$try_py" ] && "$try_py" -c "import numpy; import PIL" 2>/dev/null; then
      PYTHON="$try_py"
      break
    fi
  done
  if [ -z "$PYTHON" ]; then
    fail "Python with numpy/pillow not found. Run: pip install -r requirements.txt"
  fi
  ok "Python with numpy/pillow found: $($PYTHON --version)"

  # Game files
  if [ ! -f "$GAME_DIR/COMI.LA0" ]; then
    fail "Game file COMI.LA0 not found at $GAME_DIR"
  fi
  if [ ! -d "$RESOURCE_DIR" ]; then
    fail "RESOURCE directory not found at $RESOURCE_DIR"
  fi
  ok "Game files found"

  # Count SAN files
  san_count=$(ls "$RESOURCE_DIR"/*.SAN 2>/dev/null | wc -l)
  info "Found $san_count SAN cutscene files"
}

# ---- Step 1: Backgrounds, Objects, Object Layers ---------------------------
step1_backgrounds_objects() {
  echo ""
  info "=== Step 1: Backgrounds, Objects & Object Layers ==="

  cd "$PROJECT_ROOT"
  "$NUTCRACKER" sputm room decode "$GAME_DIR/COMI.LA0"

  bg_count=$(count "$OUTPUT_BASE/IMAGES/backgrounds")
  obj_count=$(count "$OUTPUT_BASE/IMAGES/objects")
  lay_count=$(count "$OUTPUT_BASE/IMAGES/objects_layers")

  ok "Backgrounds: $bg_count PNGs"
  ok "Objects: $obj_count PNGs"
  ok "Object layers: $lay_count PNGs"
}

# ---- Step 2: Cutscene SAN Files --------------------------------------------
step2_cutscenes() {
  echo ""
  info "=== Step 2: Cutscene Frames (15 SAN files) ==="

  cd "$PROJECT_ROOT"

  OUTDIR="$OUTPUT_BASE/cutscenes"
  mkdir -p "$OUTDIR"

  for san in "$RESOURCE_DIR"/*.SAN; do
    name=$(basename "$san")
    printf "  Decoding %-25s ... " "$name"
    "$NUTCRACKER" smush decode "$san" -t "$OUTDIR" 2>/dev/null
    frame_count=$(count "$OUTDIR/${name%.SAN}.SAN" 2>/dev/null || count "$OUTDIR/$name" 2>/dev/null || echo "?")
    echo "$frame_count frames"
  done

  # Clean up leftover stub SAN files that some decoder versions leave behind
  find "$OUTDIR" -name '*.SAN' -type f -delete 2>/dev/null || true

  total_frames=$(find "$OUTDIR" -name "*.png" 2>/dev/null | wc -l)
  ok "Total cutscene frames: $total_frames"
}

# ---- Step 3: Fonts ----------------------------------------------------------
step3_fonts() {
  echo ""
  info "=== Step 3: Fonts (5 NUT files) ==="

  cd "$PROJECT_ROOT"

  OUTDIR="$OUTPUT_BASE/fonts"
  mkdir -p "$OUTDIR"

  for nut in "$RESOURCE_DIR"/FONT[0-4].NUT; do
    name=$(basename "$nut")
    printf "  Decoding %-25s ... " "$name"
    "$NUTCRACKER" smush decode "$nut" --nut -t "$OUTDIR" 2>/dev/null
    if [ -f "$OUTDIR/${nut%.NUT}.NUT/chars.png" ]; then
      echo "chars.png"
    else
      echo "done"
    fi
  done

  font_count=$(find "$OUTDIR" -name "chars.png" 2>/dev/null | wc -l)
  ok "Fonts decoded: $font_count"
}

# ---- Step 4: Costumes/Sprites (AKOS) ---------------------------------------
step4_costumes() {
  echo ""
  info "=== Step 4: Costumes & Sprites (AKOS entries) ==="

  cd "$PROJECT_ROOT"

  # Run the AKOS decoder (writes to AKOS_out/COMI/ by default)
  PYTHONPATH="$NUTCRACKER_SRC" \
    $PYTHON -m nutcracker.sputm.costume.akos \
    "$GAME_DIR/COMI.LA0" 2>/dev/null

  # Move frames to the costumes directory
  OUTDIR="$OUTPUT_BASE/costumes"
  mkdir -p "$OUTDIR"

  if [ -d "AKOS_out/COMI" ]; then
    mv AKOS_out/COMI/*.png "$OUTDIR/" 2>/dev/null || true
    rm -rf AKOS_out
  fi

  # Clean up any nested COMI dir from previous runs
  if [ -d "$OUTDIR/COMI" ]; then
    mv "$OUTDIR/COMI"/*.png "$OUTDIR/" 2>/dev/null || true
    rmdir "$OUTDIR/COMI" 2>/dev/null || true
  fi

  costume_count=$(find "$OUTDIR" -name "*.png" 2>/dev/null | wc -l)
  ok "Costume frames: $costume_count"
}

# ---- Summary ---------------------------------------------------------------
print_summary() {
  echo ""
  echo "=============================================="
  echo "  Export Complete"
  echo "=============================================="
  echo ""

  bg=$(count "$OUTPUT_BASE/IMAGES/backgrounds" 2>/dev/null || echo 0)
  ob=$(count "$OUTPUT_BASE/IMAGES/objects" 2>/dev/null || echo 0)
  ol=$(count "$OUTPUT_BASE/IMAGES/objects_layers" 2>/dev/null || echo 0)
  cs=$(find "$OUTPUT_BASE/cutscenes" -name "*.png" 2>/dev/null | wc -l || echo 0)
  fn=$(find "$OUTPUT_BASE/fonts" -name "chars.png" 2>/dev/null | wc -l || echo 0)
  co=$(find "$OUTPUT_BASE/costumes" -name "*.png" 2>/dev/null | wc -l || echo 0)
  total=$((bg + ob + ol + cs + fn + co))

  printf "  %-35s %5d PNGs\n" "Backgrounds" "$bg"
  printf "  %-35s %5d PNGs\n" "Objects" "$ob"
  printf "  %-35s %5d PNGs\n" "Object layers" "$ol"
  printf "  %-35s %5d PNGs\n" "Cutscene frames" "$cs"
  printf "  %-35s %5d PNGs\n" "Font grids" "$fn"
  printf "  %-35s %5d PNGs\n" "Costume/sprites" "$co"
  echo "  --------------------------------------------"
  printf "  %-35s %5d PNGs\n" "TOTAL" "$total"
  echo ""
  ok "All assets in: $OUTPUT_BASE"
}

# ---- Main ------------------------------------------------------------------
main() {
  echo ""
  echo "  ╔══════════════════════════════════════════╗"
  echo "  ║    COMI Upscaled — Full Asset Export     ║"
  echo "  ╚══════════════════════════════════════════╝"
  echo ""

  check_prereqs
  step1_backgrounds_objects
  step2_cutscenes
  step3_fonts
  step4_costumes
  print_summary
}

main
