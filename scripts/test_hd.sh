#!/usr/bin/env bash
# Automated HD Rendering Test Suite for COMI Upscaled
#
# Tests HD asset loading and rendering without manual gameplay.
# Launches the fork, captures trace output, triggers dump at key scenes.
#
# Usage:
#   bash scripts/test_hd.sh
#   bash scripts/test_hd.sh --analyze-only   # skip launch, just analyze dumps
#

set -e

cd "$(dirname "$0")/.."
PROJECT_DIR="$(pwd)"
LOG_DIR="$PROJECT_DIR/logs"
FORK_DIR="$PROJECT_DIR/scummvm/fork"
DUMP_DIR="$PROJECT_DIR/logs"
SCUMMVM_INI="C:/Users/$(whoami)/AppData/Roaming/ScummVM/scummvm.ini"

mkdir -p "$LOG_DIR"

echo "=== COMI Upscaled HD Test Suite ==="
echo "Project: $PROJECT_DIR"
echo "Logs:    $LOG_DIR"

# ── Step 1: Validate paths ──
echo ""
echo "[1/5] Validating project paths..."
python scripts/check_setup.py --debug 2>&1 | grep -E "^  ." | head -20
echo ""

# ── Step 2: Enable debug config ──
echo "[2/5] Enabling debug config (hd_trace, hd_dump_frame)..."
python3 -c "
import pathlib
p = pathlib.Path('$SCUMMVM_INI')
data = p.read_text()
# Add trace + dump if not present
if 'hd_trace' not in data:
    data = data.replace('[comi]', '[comi]\nhd_trace=true')
if 'hd_dump_frame' not in data:
    data = data.replace('[comi]', '[comi]\nhd_dump_frame=1')
p.write_text(data)
print('  Config updated')
"

# ── Step 3: Launch game and capture output ──
echo "[3/5] Launching game with auto-start..."
echo "  (waiting up to 30 seconds for dump files...)"
export PATH="/mingw64/bin:/usr/bin:$PATH"

# Start the game in background
"$FORK_DIR/scummvm.exe" \
  --path="$PROJECT_DIR/game" \
  --logfile="$LOG_DIR/scummvm-test.log" \
  --config="$SCUMMVM_INI" &
SCUMMVM_PID=$!

# Wait for dump files to appear (up to 30 seconds)
WAIT_MAX=30
WAITED=0
DUMP_FOUND=0
while [ $WAITED -lt $WAIT_MAX ]; do
  DUMPS=$(ls "$DUMP_DIR"/hd_dump_*.raw 2>/dev/null | wc -l)
  if [ "$DUMPS" -gt 0 ]; then
    echo "  Dump files found after ${WAITED}s ($DUMPS files)"
    DUMP_FOUND=1
    break
  fi
  sleep 2
  WAITED=$((WAITED + 2))
done

# Kill the game
kill $SCUMMVM_PID 2>/dev/null || true
wait $SCUMMVM_PID 2>/dev/null || true

if [ "$DUMP_FOUND" -eq 0 ]; then
  echo "  ⚠ No dump files appeared — game may not have started or HD mode is off"
fi
echo ""

# ── Step 4: Check trace output ──
echo "[4/5] Analyzing HD trace output..."
if [ -f "$LOG_DIR/scummvm-test.log" ]; then
  echo ""
  echo "  --- HD Asset Access Summary ---"
  grep "hd_trace:" "$LOG_DIR/scummvm-test.log" | sort | uniq -c | sort -rn | head -20
  echo ""
  echo "  --- HD Errors ---"
  grep -i "error\|fail\|miss" "$LOG_DIR/scummvm-test.log" | grep -i "hd\|trace" | head -10
  echo ""
  echo "  --- HD Events ---"
  grep "HD:" "$LOG_DIR/scummvm-test.log" | head -15
  echo ""
else
  echo "  ⚠ No log file found"
fi

# ── Step 5: Analyze dump files ──
echo "[5/5] Analyzing dump files..."
python scripts/check_hd_dumps.py "$DUMP_DIR"
echo ""

echo "=== Test complete ==="
echo "Log:  $LOG_DIR/scummvm-test.log"
echo "Dumps: $LOG_DIR/hd_dump_*.raw"
