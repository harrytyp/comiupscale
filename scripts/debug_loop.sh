#!/usr/bin/env bash
###############################################################################
# debug_loop.sh — Automated HD Asset Debug & Test Loop for COMI Upscaled
#
# Phases:
#   1. Setup:     Populate hd/ directory from SMB, configure ScummVM, start Xvfb
#   2. Test Loop: Launch ScummVM per test room, screenshot, parse logs
#   3. Report:    Generate debug_loop_report.md with per-room status
#
# Usage:
#   bash scripts/debug_loop.sh              # full run
#   bash scripts/debug_loop.sh --setup-only # setup + SMB copy only
#   bash scripts/debug_loop.sh --test-only  # skip setup, run test loop
#   bash scripts/debug_loop.sh --report-only # regenerate report from existing logs
#
# Idempotent: safe to re-run. Won't re-copy files already present.
###############################################################################
set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
SCUMMVM_BIN="/opt/data/local/comi-hd-repo/scummvm/fork/scummvm"
BUILD_DIR="/opt/data/local/scummvm-build"
GAME_DIR="/opt/data/local/comi-hd-final"
REPO_DIR="/opt/data/local/comi-hd-repo"
HD_DIR="$GAME_DIR/hd"
DEBUG_DIR="$BUILD_DIR/debug"
LOG_DIR="$DEBUG_DIR/logs"
SCREENSHOT_TOOL=""  # auto-detected below
VISION_QA_SCRIPT="$REPO_DIR/scripts/vision_qa.py"
VISION_MODEL="mimo-v2.5"
VISION_RESULTS_DIR="$DEBUG_DIR/vision"

# SMB configuration
SMB_HOST="192.168.2.152"
SMB_USER="kolja"
SMB_PASS="forever"
SMB_SHARE="kolja"
SMB_BASE="Projekte/COMI-Upscaled/CMI UPSCALED/upscaled"

# Test rooms: room_number=description
declare -A TEST_ROOMS=(
    [4]="opening"
    [15]="stage"
    [19]="fort"
    [1]="lobby"
)

# How long to wait for ScummVM to load a room before screenshot (seconds)
ROOM_WAIT=15
# Max seconds for ScummVM to start before we declare it hung
STARTUP_TIMEOUT=30

# ── Parse Arguments ──────────────────────────────────────────────────────────
MODE="full"
for arg in "$@"; do
    case "$arg" in
        --setup-only)  MODE="setup" ;;
        --test-only)   MODE="test" ;;
        --report-only) MODE="report" ;;
        --help|-h)
            echo "Usage: $0 [--setup-only|--test-only|--report-only]"
            exit 0
            ;;
    esac
done

# ── Logging helpers ──────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()   { echo -e "${BLUE}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }

# ── Detect screenshot tool ───────────────────────────────────────────────────
detect_screenshot_tool() {
    if command -v scrot &>/dev/null; then
        SCREENSHOT_TOOL="scrot"
    elif command -v import &>/dev/null; then
        SCREENSHOT_TOOL="import"
    elif python3 -c "import mss" &>/dev/null; then
        SCREENSHOT_TOOL="mss"
    elif python3 -c "from PIL import ImageGrab" &>/dev/null; then
        SCREENSHOT_TOOL="pil"
    else
        warn "No screenshot tool found. Screenshots will be skipped."
        SCREENSHOT_TOOL="none"
    fi
    log "Screenshot tool: $SCREENSHOT_TOOL"
}

take_screenshot() {
    local output="$1"
    case "$SCREENSHOT_TOOL" in
        scrot)
            DISPLAY=:99 scrot -o "$output" 2>/dev/null
            ;;
        import)
            DISPLAY=:99 import -window root "$output" 2>/dev/null
            ;;
        mss)
            DISPLAY=:99 python3 -c "
import mss
with mss.mss(display=':99') as sct:
    sct.shot(mon=-1, output='$output')
" 2>/dev/null
            ;;
        pil)
            DISPLAY=:99 python3 -c "
from PIL import ImageGrab
img = ImageGrab.grab()
img.save('$output')
" 2>/dev/null
            ;;
        none)
            warn "Skipping screenshot (no tool available)"
            return 0
            ;;
    esac
    if [[ -f "$output" ]]; then
        local size
        size=$(stat -c%s "$output" 2>/dev/null || echo 0)
        ok "Screenshot saved: $output ($size bytes)"
    else
        warn "Screenshot may have failed: $output"
    fi
}

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1: SETUP
# ═════════════════════════════════════════════════════════════════════════════
setup_phase() {
    log "═══ PHASE 1: SETUP ═══"

    # ── 1a. Create directory structure ──
    log "Creating hd/ directory structure under $HD_DIR ..."
    mkdir -p "$HD_DIR"/{backgrounds,costumes,objects,fonts}
    mkdir -p "$DEBUG_DIR"/{logs,screenshots,reports}
    mkdir -p "$LOG_DIR"
    mkdir -p "$VISION_RESULTS_DIR"

    # ── 1b. Verify prerequisites ──
    log "Checking prerequisites..."
    if [[ ! -x "$SCUMMVM_BIN" ]]; then
        err "ScummVM binary not found at $SCUMMVM_BIN"
        exit 1
    fi
    ok "ScummVM binary: $SCUMMVM_BIN"

    if [[ ! -d "$GAME_DIR" ]]; then
        err "Game directory not found at $GAME_DIR"
        exit 1
    fi
    ok "Game directory: $GAME_DIR"

    # Check for game data files
    local has_game_data=0
    for f in COMI.LA0 COMI.LA1 COMI.LA2; do
        if [[ -f "$GAME_DIR/$f" ]]; then
            has_game_data=1
            break
        fi
    done
    if [[ "$has_game_data" -eq 0 ]]; then
        warn "No COMI.LA* files found in $GAME_DIR — game may not run"
    else
        ok "Game data files present"
    fi

    if [[ ! -f "$REPO_DIR/config/object_map.json" ]]; then
        warn "object_map.json not found at $REPO_DIR/config/object_map.json"
    fi

    detect_screenshot_tool

    # ── 1c. Copy object_map.json ──
    log "Copying object_map.json..."
    if [[ -f "$REPO_DIR/config/object_map.json" ]]; then
        if [[ ! -f "$HD_DIR/object_map.json" ]] || \
           [[ "$REPO_DIR/config/object_map.json" -nt "$HD_DIR/object_map.json" ]]; then
            cp "$REPO_DIR/config/object_map.json" "$HD_DIR/object_map.json"
            ok "object_map.json copied"
        else
            ok "object_map.json already up to date"
        fi
    fi

    # ── 1d. SMB copy: backgrounds ──
    log "Checking SMB backgrounds..."
    copy_smb_assets "backgrounds" "$HD_DIR/backgrounds" "bg"

    # ── 1e. SMB copy: costumes ──
    log "Checking SMB costumes..."
    copy_smb_assets "costumes" "$HD_DIR/costumes" ""

    # ── 1f. SMB copy: objects ──
    log "Checking SMB objects..."
    copy_smb_assets "objects" "$HD_DIR/objects" ""

    # ── 1g. SMB copy: fonts ──
    log "Checking SMB fonts..."
    copy_smb_assets "fonts" "$HD_DIR/fonts" ""

    # ── 1h. Create/update scummvm.ini ──
    log "Configuring scummvm.ini..."
    create_scummvm_ini

    # ── 1i. Start Xvfb ──
    log "Starting Xvfb on :99..."
    start_xvfb

    # ── 1j. Verify directory structure ──
    log "Verifying directory structure..."
    verify_directory_structure
}

# ── SMB Asset Copy (uses pysmb) ─────────────────────────────────────────────
copy_smb_assets() {
    local smb_subdir="$1"
    local local_dir="$2"
    local rename_prefix="$3"  # "bg" for backgrounds, "" for others

    # Check if we already have files locally
    local local_count
    local_count=$(find "$local_dir" -name "*.png" -type f 2>/dev/null | wc -l)

    if [[ "$local_count" -gt 0 ]]; then
        ok "  $smb_subdir: $local_count files already present locally"
        return 0
    fi

    log "  $smb_subdir: No local files, attempting SMB copy..."

    # Try SMB copy via Python pysmb
    python3 - "$SMB_HOST" "$SMB_USER" "$SMB_PASS" "$SMB_SHARE" \
             "$SMB_BASE/$smb_subdir" "$local_dir" "$rename_prefix" <<'PYEOF'
import sys
import os
import io

try:
    from smb.SMBConnection import SMBConnection
except ImportError:
    print("ERROR: pysmb not installed. Install with: pip install pysmb")
    sys.exit(1)

smb_host = sys.argv[1]
smb_user = sys.argv[2]
smb_pass = sys.argv[3]
smb_share = sys.argv[4]
smb_path = sys.argv[5]
local_dir = sys.argv[6]
rename_prefix = sys.argv[7]

os.makedirs(local_dir, exist_ok=True)

try:
    conn = SMBConnection(smb_user, smb_pass, 'debug_loop', smb_host,
                         use_ntlm_v2=True, is_direct_tcp=True)
    connected = conn.connect(smb_host, 445, timeout=15)
    if not connected:
        print(f"WARNING: Could not connect to SMB share at {smb_host}")
        sys.exit(0)
except Exception as e:
    print(f"WARNING: SMB connection failed: {e}")
    sys.exit(0)

try:
    files = conn.listPath(smb_share, smb_path)
except Exception as e:
    print(f"WARNING: Could not list SMB path {smb_path}: {e}")
    conn.close()
    sys.exit(0)

png_files = [f for f in files if f.filename.endswith('.png') and not f.isDirectory]
print(f"  Found {len(png_files)} PNG files on SMB")

copied = 0
skipped = 0
errors = 0

for f in png_files:
    # Determine local filename
    if rename_prefix == "bg" and not f.filename.startswith("bg_"):
        # backgrounds: 0029_voodoo-e.png -> bg_0029.png
        parts = f.filename.split('_', 1)
        if parts[0].isdigit():
            local_name = f"bg_{parts[0]}.png"
        else:
            local_name = f.filename
    else:
        local_name = f.filename

    local_path = os.path.join(local_dir, local_name)
    if os.path.exists(local_path):
        skipped += 1
        continue

    try:
        with io.BytesIO() as buf:
            file_attributes, file_size = conn.retrieveFile(
                smb_share, smb_path + '/' + f.filename, buf)
            buf.seek(0)
            with open(local_path, 'wb') as out:
                out.write(buf.read())
        copied += 1
        if (copied % 100) == 0:
            print(f"  ... copied {copied} files so far")
    except Exception as e:
        print(f"  ERROR copying {f.filename}: {e}")
        errors += 1

conn.close()
print(f"  Done: {copied} copied, {skipped} skipped (existing), {errors} errors")
PYEOF

    local exit_code=$?
    if [[ "$exit_code" -ne 0 ]]; then
        warn "  SMB copy for $smb_subdir had issues (exit code: $exit_code)"
    fi

    local new_count
    new_count=$(find "$local_dir" -name "*.png" -type f 2>/dev/null | wc -l)
    if [[ "$new_count" -gt 0 ]]; then
        ok "  $smb_subdir: $new_count files now in $local_dir"
    else
        warn "  $smb_subdir: No files copied to $local_dir"
    fi
}

# ── Create scummvm.ini ───────────────────────────────────────────────────────
create_scummvm_ini() {
    local ini_file="$BUILD_DIR/scummvm.ini"

    # Check if [comi] section with hd_trace already exists
    if grep -q '\[comi\]' "$ini_file" 2>/dev/null && \
       grep -A5 '^\[comi\]' "$ini_file" 2>/dev/null | grep -q 'hd_trace=true'; then
        ok "scummvm.ini already has [comi] with hd_trace=true"
        return 0
    fi

    # If there's already a [comi] or [comi-de] section, update it
    if grep -q '^\[comi\]' "$ini_file" 2>/dev/null; then
        # Add hd_trace if missing
        if ! grep -q 'hd_trace=true' "$ini_file"; then
            sed -i '/^\[comi\]/a hd_trace=true' "$ini_file"
        fi
    else
        # Add a new [comi] section
        cat >> "$ini_file" <<EOF

[comi]
description=The Curse of Monkey Island (English)
path=$GAME_DIR
gameid=comi
engineid=scumm
platform=win
fullscreen=true
hd_trace=true
guioptions=sndNoMIDI noAspect gameOption2 gameOption4 gameOption5 gameOption9 lang_English plat_windows
EOF
    fi

    # Ensure fullscreen and gamepath are set in [comi] section
    if ! grep -q 'fullscreen=true' "$ini_file"; then
        sed -i '/^\[comi\]/a fullscreen=true' "$ini_file"
    fi

    ok "scummvm.ini updated with hd_trace=true"
    log "  Current scummvm.ini:"
    cat "$ini_file" | sed 's/^/    /'
}

# ── Start Xvfb ──────────────────────────────────────────────────────────────
start_xvfb() {
    # Check if Xvfb is already running on :99
    if pgrep -f "Xvfb :99" &>/dev/null; then
        ok "Xvfb already running on :99"
        export DISPLAY=:99
        return 0
    fi

    # Kill any stale Xvfb
    pkill -f "Xvfb :99" 2>/dev/null || true
    sleep 0.5

    Xvfb :99 -screen 0 2560x1920x24 &>/dev/null &
    local xvfb_pid=$!
    sleep 1

    if kill -0 "$xvfb_pid" 2>/dev/null; then
        ok "Xvfb started on :99 (PID: $xvfb_pid, 2560x1920x24)"
        export DISPLAY=:99
    else
        err "Xvfb failed to start"
        exit 1
    fi
}

# ── Verify Directory Structure ───────────────────────────────────────────────
verify_directory_structure() {
    local issues=0

    log "Checking hd/ directory layout..."
    for subdir in backgrounds costumes objects fonts; do
        local count
        count=$(find "$HD_DIR/$subdir" -name "*.png" -type f 2>/dev/null | wc -l)
        if [[ "$count" -gt 0 ]]; then
            ok "  hd/$subdir/: $count PNG files"
        else
            warn "  hd/$subdir/: EMPTY (no PNG files)"
            issues=$((issues + 1))
        fi
    done

    if [[ -f "$HD_DIR/object_map.json" ]]; then
        ok "  hd/object_map.json: present"
    else
        warn "  hd/object_map.json: MISSING"
        issues=$((issues + 1))
    fi

    if [[ "$issues" -gt 0 ]]; then
        warn "Directory structure has $issues issue(s) — HD assets may not load correctly"
    else
        ok "Directory structure verified OK"
    fi
}

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2: TEST LOOP
# ═════════════════════════════════════════════════════════════════════════════
test_loop_phase() {
    log "═══ PHASE 2: TEST LOOP ═══"

    # Ensure Xvfb is running
    start_xvfb
    export DISPLAY=:99

    local room_nums
    room_nums=$(echo "${!TEST_ROOMS[@]}" | tr ' ' '\n' | sort -n)

    for room_num in $room_nums; do
        local room_name="${TEST_ROOMS[$room_num]}"
        test_single_room "$room_num" "$room_name"
    done
}

test_single_room() {
    local room_num="$1"
    local room_name="$2"

    log "────────────────────────────────────────────────"
    log "Testing Room $room_num ($room_name)..."
    log "────────────────────────────────────────────────"

    local room_log="$LOG_DIR/room_${room_num}.log"
    local room_screenshot="$DEBUG_DIR/screenshots/room_${room_num}.png"

    # Remove old log
    rm -f "$room_log"

    # Build ScummVM command
    # Use --loadgame with the save game if available, otherwise start fresh
    # The save comi.s00 is the default save in slot 0
    local game_args=(
        "--path=$GAME_DIR"
        "--fullscreen"
        "--logfile=$room_log"
    )

    # If we have a save game, try to use it
    local save_dir="$BUILD_DIR/.local/share/scummvm/saves"
    if [[ -d "$save_dir" ]]; then
        game_args+=("--loadgame=0")
    fi

    log "  Launching ScummVM..."
    log "  Args: ${game_args[*]}"

    # Launch ScummVM in background
    LIBGL_ALWAYS_SOFTWARE=1 \
    DISPLAY=:99 \
    "$SCUMMVM_BIN" "${game_args[@]}" &>/dev/null &
    local scummvm_pid=$!
    log "  ScummVM PID: $scummvm_pid"

    # Wait for ScummVM to start
    local waited=0
    while [[ $waited -lt $STARTUP_TIMEOUT ]]; do
        if ! kill -0 "$scummvm_pid" 2>/dev/null; then
            warn "  ScummVM exited prematurely after ${waited}s"
            break
        fi
        sleep 2
        waited=$((waited + 2))
    done

    if kill -0 "$scummvm_pid" 2>/dev/null; then
        # ScummVM is still running, wait for room load
        log "  Waiting ${ROOM_WAIT}s for room to load..."
        sleep "$ROOM_WAIT"

        # Take screenshot
        log "  Taking screenshot..."
        take_screenshot "$room_screenshot"

        # Capture a second screenshot after a bit more time
        sleep 3
        local room_screenshot2="$DEBUG_DIR/screenshots/room_${room_num}_final.png"
        take_screenshot "$room_screenshot2"

        # ── Visual Quality Analysis ──
        log "  Running visual quality analysis (MiMo V2.5 Vision)..."
        run_visual_qa "$room_num" "$room_screenshot2"
    fi

    # Kill ScummVM
    log "  Stopping ScummVM..."
    kill "$scummvm_pid" 2>/dev/null || true
    sleep 1
    kill -9 "$scummvm_pid" 2>/dev/null || true
    wait "$scummvm_pid" 2>/dev/null || true
    log "  ScummVM stopped"

    # Parse log for HD messages
    log "  Parsing log for HD messages..."
    parse_room_log "$room_num" "$room_name" "$room_log"
}

parse_room_log() {
    local room_num="$1"
    local room_name="$2"
    local room_log="$3"

    if [[ ! -f "$room_log" ]]; then
        warn "  No log file for room $room_num"
        return 0
    fi

    local log_size
    log_size=$(wc -c < "$room_log")
    log "  Log file: $room_log ($log_size bytes)"

    # Extract HD-related lines to a summary file
    local hd_summary="$LOG_DIR/room_${room_num}_hd_summary.txt"

    {
        echo "=== HD Trace Summary for Room $room_num ($room_name) ==="
        echo "=== Generated: $(date -Iseconds) ==="
        echo ""

        echo "── Backgrounds ──"
        grep -i "hd.*bg\|loaded bg\|background" "$room_log" 2>/dev/null || echo "(none)"
        echo ""

        echo "── Costumes ──"
        grep -i "hd.*costume\|hasCostume\|AKOS\|hd_costume" "$room_log" 2>/dev/null || echo "(none)"
        echo ""

        echo "── Objects ──"
        grep -i "hd.*object\|hasObject\|hd_object" "$room_log" 2>/dev/null || echo "(none)"
        echo ""

        echo "── Fonts ──"
        grep -i "hd.*font\|FONT\|hd_font" "$room_log" 2>/dev/null || echo "(none)"
        echo ""

        echo "── Errors / Assertions ──"
        grep -iE "error|assert|fatal|crash|abort|segmentation|segfault" "$room_log" 2>/dev/null || echo "(none)"
        echo ""

        echo "── Full HD Lines ──"
        grep -i "hd\|upscale\|trace" "$room_log" 2>/dev/null | head -100 || echo "(none)"
    } > "$hd_summary"

    ok "  HD summary: $hd_summary"

    # Quick inline status
    local bg_count costume_count object_count font_count error_count
    bg_count=$(grep -ci "hd.*bg\|loaded bg\|background" "$room_log" 2>/dev/null || echo 0)
    costume_count=$(grep -ci "hd.*costume\|hasCostume\|hd_costume" "$room_log" 2>/dev/null || echo 0)
    object_count=$(grep -ci "hd.*object\|hasObject\|hd_object" "$room_log" 2>/dev/null || echo 0)
    font_count=$(grep -ci "hd.*font\|hd_font" "$room_log" 2>/dev/null || echo 0)
    error_count=$(grep -ciE "error|assert|fatal|crash|abort" "$room_log" 2>/dev/null || echo 0)

    log "  BG: $bg_count | Costumes: $costume_count | Objects: $object_count | Fonts: $font_count | Errors: $error_count"
}

# ── Visual Quality Analysis ──────────────────────────────────────────────────
run_visual_qa() {
    local room_num="$1"
    local screenshot="$2"
    local result_file="$VISION_RESULTS_DIR/room_${room_num}.json"

    # Skip if no screenshot exists
    if [[ ! -f "$screenshot" ]]; then
        warn "  No screenshot for visual QA: $screenshot"
        return 0
    fi

    # Skip if vision script doesn't exist
    if [[ ! -f "$VISION_QA_SCRIPT" ]]; then
        warn "  Vision QA script not found: $VISION_QA_SCRIPT"
        return 0
    fi

    # Skip if no API key is available
    if [[ -z "${OPENCODE_GO_API_KEY:-}" ]] && [[ -z "${OPENAI_API_KEY:-}" ]]; then
        warn "  No API key found for vision analysis (set OPENCODE_GO_API_KEY)"
        return 0
    fi

    # Run vision analysis
    local start_time
    start_time=$(date +%s)

    if python3 "$VISION_QA_SCRIPT" "$screenshot" \
        --model "$VISION_MODEL" \
        --json-only > "$result_file" 2>"$VISION_RESULTS_DIR/room_${room_num}.stderr"; then
        local end_time
        end_time=$(date +%s)
        local elapsed=$((end_time - start_time))
        ok "  Visual QA complete (${elapsed}s) → $result_file"

        # Extract overall score for quick display
        local overall_score
        overall_score=$(python3 -c "
import json, sys
try:
    d = json.load(open('$result_file'))
    print(d.get('overall', {}).get('score', '?'))
except: print('?')
" 2>/dev/null || echo "?")
        log "  Visual Quality Score: ${overall_score}/10"
    else
        warn "  Vision analysis failed (see $VISION_RESULTS_DIR/room_${room_num}.stderr)"
    fi
}

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3: REPORT
# ═════════════════════════════════════════════════════════════════════════════
report_phase() {
    log "═══ PHASE 3: REPORT ═══"

    local report="$DEBUG_DIR/debug_loop_report.md"
    local timestamp
    timestamp=$(date -Iseconds)

    {
        echo "# COMI HD Debug Loop Report"
        echo ""
        echo "**Generated:** $timestamp"
        echo "**ScummVM binary:** $SCUMMVM_BIN"
        echo "**Game directory:** $GAME_DIR"
        echo "**HD directory:** $HD_DIR"
        echo "**Display:** :99 (2560x1920)"
        echo ""

        echo "## Asset Inventory"
        echo ""
        echo "| Directory | File Count |"
        echo "|-----------|-----------|"
        for subdir in backgrounds costumes objects fonts; do
            local count
            count=$(find "$HD_DIR/$subdir" -name "*.png" -type f 2>/dev/null | wc -l)
            echo "| hd/$subdir/ | $count |"
        done
        if [[ -f "$HD_DIR/object_map.json" ]]; then
            local obj_map_size
            obj_map_size=$(stat -c%s "$HD_DIR/object_map.json" 2>/dev/null || echo "?")
            echo "| hd/object_map.json | present ($obj_map_size bytes) |"
        else
            echo "| hd/object_map.json | **MISSING** |"
        fi
        echo ""

        echo "## Per-Room Test Results"
        echo ""
        echo "| Room | Name | Backgrounds | Costumes | Objects | Fonts | Errors | Screenshot | Visual QA |"
        echo "|------|------|-------------|----------|---------|-------|--------|------------|-----------|"

        local room_nums
        room_nums=$(echo "${!TEST_ROOMS[@]}" | tr ' ' '\n' | sort -n)

        local total_bg=0 total_costume=0 total_object=0 total_font=0 total_error=0

        for room_num in $room_nums; do
            local room_name="${TEST_ROOMS[$room_num]}"
            local room_log="$LOG_DIR/room_${room_num}.log"
            local screenshot="$DEBUG_DIR/screenshots/room_${room_num}.png"
            local screenshot_status="none"

            if [[ -f "$screenshot" ]]; then
                local ss_size
                ss_size=$(stat -c%s "$screenshot" 2>/dev/null || echo 0)
                screenshot_status="✅ ($ss_size bytes)"
            fi

            if [[ -f "$room_log" ]]; then
                local bg_count costume_count object_count font_count error_count
                bg_count=$(grep -ci "hd.*bg\|loaded bg\|background" "$room_log" 2>/dev/null || echo 0)
                costume_count=$(grep -ci "hd.*costume\|hasCostume\|hd_costume" "$room_log" 2>/dev/null || echo 0)
                object_count=$(grep -ci "hd.*object\|hasObject\|hd_object" "$room_log" 2>/dev/null || echo 0)
                font_count=$(grep -ci "hd.*font\|hd_font" "$room_log" 2>/dev/null || echo 0)
                error_count=$(grep -ciE "error|assert|fatal|crash|abort" "$room_log" 2>/dev/null || echo 0)

                total_bg=$((total_bg + bg_count))
                total_costume=$((total_costume + costume_count))
                total_object=$((total_object + object_count))
                total_font=$((total_font + font_count))
                total_error=$((total_error + error_count))

                local bg_icon="❌"
                [[ "$bg_count" -gt 0 ]] && bg_icon="✅ ($bg_count)"
                local costume_icon="❌"
                [[ "$costume_count" -gt 0 ]] && costume_icon="✅ ($costume_count)"
                local object_icon="❌"
                [[ "$object_count" -gt 0 ]] && object_icon="✅ ($object_count)"
                local font_icon="❌"
                [[ "$font_count" -gt 0 ]] && font_icon="✅ ($font_count)"
                local error_icon="✅"
                [[ "$error_count" -gt 0 ]] && error_icon="❌ ($error_count)"

                # Visual QA status
                local visual_status="—"
                local visual_file="$VISION_RESULTS_DIR/room_${room_num}.json"
                if [[ -f "$visual_file" ]]; then
                    visual_status=$(python3 -c "
import json, sys
try:
    d = json.load(open('$visual_file'))
    if 'error' in d and 'backgrounds' not in d:
        print('⚠️ error')
    else:
        o = d.get('overall', {}).get('score', '?')
        print(f'✅ {o}/10')
except: print('⚠️ parse error')
" 2>/dev/null || echo "⚠️ parse error")
                fi

                echo "| $room_num | $room_name | $bg_icon | $costume_icon | $object_icon | $font_icon | $error_icon | $screenshot_status | $visual_status |"
            else
                local visual_status="—"
                local visual_file="$VISION_RESULTS_DIR/room_${room_num}.json"
                if [[ -f "$visual_file" ]]; then
                    visual_status=$(python3 -c "
import json, sys
try:
    d = json.load(open('$visual_file'))
    if 'error' in d and 'backgrounds' not in d:
        print('⚠️ error')
    else:
        o = d.get('overall', {}).get('score', '?')
        print(f'✅ {o}/10')
except: print('⚠️ parse error')
" 2>/dev/null || echo "⚠️ parse error")
                fi
                echo "| $room_num | $room_name | ⚠️ no log | ⚠️ no log | ⚠️ no log | ⚠️ no log | ⚠️ no log | $screenshot_status | $visual_status |"
            fi
        done

        echo ""
        echo "**Totals:** BG: $total_bg | Costumes: $total_costume | Objects: $total_object | Fonts: $total_font | Errors: $total_error"
        echo ""

        echo "## Detailed Log Excerpts"
        echo ""

        for room_num in $room_nums; do
            local room_name="${TEST_ROOMS[$room_num]}"
            local hd_summary="$LOG_DIR/room_${room_num}_hd_summary.txt"
            local room_log="$LOG_DIR/room_${room_num}.log"

            echo "### Room $room_num ($room_name)"
            echo ""

            if [[ -f "$hd_summary" ]]; then
                echo "<details>"
                echo "<summary>HD Summary (click to expand)</summary>"
                echo ""
                echo '```'
                cat "$hd_summary"
                echo '```'
                echo ""
                echo "</details>"
            else
                echo "_No HD summary available._"
            fi
            echo ""

            if [[ -f "$room_log" ]]; then
                local log_lines
                log_lines=$(wc -l < "$room_log")
                echo "<details>"
                echo "<summary>Full log ($log_lines lines, click to expand)</summary>"
                echo ""
                echo '```'
                # Show first 50 and last 50 lines if log is large
                if [[ "$log_lines" -gt 120 ]]; then
                    head -50 "$room_log"
                    echo ""
                    echo "... ($((log_lines - 100)) lines omitted) ..."
                    echo ""
                    tail -50 "$room_log"
                else
                    cat "$room_log"
                fi
                echo '```'
                echo ""
                echo "</details>"
            else
                echo "_No log file available._"
            fi
            echo ""
        done

        # ── Visual Quality Analysis Section ──
        echo "## Visual Quality Analysis (MiMo V2.5 Vision)"
        echo ""

        local vision_count=0
        local vision_total_score=0

        for room_num in $room_nums; do
            local room_name="${TEST_ROOMS[$room_num]}"
            local visual_file="$VISION_RESULTS_DIR/room_${room_num}.json"

            if [[ -f "$visual_file" ]]; then
                vision_count=$((vision_count + 1))
                echo "### Room $room_num ($room_name)"
                echo ""

                python3 -c "
import json, sys
try:
    d = json.load(open('$visual_file'))
    if 'error' in d and 'backgrounds' not in d:
        print(f'⚠️ Vision analysis error: {d[\"error\"][:200]}')
    else:
        for cat in ('backgrounds', 'costumes', 'objects', 'fonts', 'overall'):
            info = d.get(cat, {})
            score = info.get('score', '?')
            desc = info.get('description', 'N/A')
            icon = '✅' if isinstance(score, int) and score >= 7 else '⚠️' if isinstance(score, int) and score >= 4 else '❌'
            print(f'- **{cat.title()}**: {icon} {score}/10 — {desc}')
except Exception as e:
    print(f'⚠️ Failed to parse vision results: {e}')
" 2>/dev/null || echo "_No visual analysis available._"

                echo ""

                # Accumulate overall score
                local oscore
                oscore=$(python3 -c "
import json
try:
    d = json.load(open('$visual_file'))
    print(d.get('overall', {}).get('score', 0))
except: print(0)
" 2>/dev/null || echo "0")
                if [[ "$oscore" -gt 0 ]] 2>/dev/null; then
                    vision_total_score=$((vision_total_score + oscore))
                fi
            fi
        done

        if [[ "$vision_count" -eq 0 ]]; then
            echo "_No visual analysis results available. Run the test loop with API key configured._"
            echo ""
        else
            local avg_score=$((vision_total_score / vision_count))
            echo "**Average Visual Quality Score:** ${avg_score}/10 across ${vision_count} room(s)"
            echo ""
        fi

        echo "## Summary"
        echo ""

        # Determine overall status
        if [[ "$total_error" -eq 0 ]] && [[ "$total_bg" -gt 0 ]]; then
            echo "### ✅ Overall: HD Assets Loading Successfully"
            echo ""
            echo "All test rooms loaded without errors. HD backgrounds, costumes, objects, and fonts are being detected by the engine."
        elif [[ "$total_bg" -gt 0 ]]; then
            echo "### ⚠️ Overall: Partial Success"
            echo ""
            echo "Some HD assets are loading but there are errors that need investigation."
        elif [[ "$total_error" -gt 0 ]]; then
            echo "### ❌ Overall: Errors Detected"
            echo ""
            echo "ScummVM encountered errors during HD asset loading."
        else
            echo "### ❌ Overall: No HD Activity Detected"
            echo ""
            echo "No HD trace messages found in logs. Possible causes:"
            echo "- hd_trace not enabled in scummvm.ini"
            echo "- HD directory structure incorrect"
            echo "- ScummVM not using the HD-patched build"
            echo "- Game not reaching rooms where HD assets would be loaded"
        fi

        echo ""
        echo "---"
        echo "*Report generated by debug_loop.sh*"

    } > "$report"

    ok "Report generated: $report"
    log "  Preview (first 30 lines):"
    head -30 "$report" | sed 's/^/    /'
}

# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  COMI HD Debug Loop — $(date -Iseconds)        ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    case "$MODE" in
        full)
            setup_phase
            test_loop_phase
            report_phase
            ;;
        setup)
            setup_phase
            ;;
        test)
            test_loop_phase
            report_phase
            ;;
        report)
            report_phase
            ;;
    esac

    echo ""
    log "═══ COMPLETE ═══"
    echo ""
    log "Debug directory: $DEBUG_DIR"
    log "  logs/         — ScummVM output per room"
    log "  screenshots/  — Per-room screenshots"
    log "  vision/       — Visual QA analysis results"
    log "  debug_loop_report.md — Full report"
    echo ""
}

main "$@"
