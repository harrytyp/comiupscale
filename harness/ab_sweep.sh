#!/usr/bin/env bash
# Faehrt alle Raeume headless und vergleicht Original und HD-Komposition.
# Phase A: jeder Raum einmal stehen, Bild gegen Bild (fehlende HD-Assets, Struktur).
# Phase B: scrollende Raeume mit Kamerafahrt (Versatz und Drift ueber die Fahrt).
#
# Aufruf: bash harness/ab_sweep.sh [raumliste] [ausgabeordner]
# Ergebnis: <ausgabe>/statisch.csv, <ausgabe>/scroll.csv, Bilder je Raum.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN="$REPO/scummvm/fork/scummvm"
PY="$REPO/venv/bin/python3"
OUT="${2:-/opt/data/projects/comi-hd/reports/ab}"
EXTRACT=/tmp/comi_extract/COMI/IMAGES/backgrounds
SCROLL="14 15 22 25 33 40 41 42 43 44 45 46 47 48 49 50 51 53 55 60 61 70 75 77 79 82 86"

if [ -n "${1:-}" ]; then
    ROOMS="$1"
elif [ -d "$EXTRACT" ]; then
    ROOMS=$(ls "$EXTRACT" | sed -n 's/^\([0-9]\{4\}\)_.*/\1/p' | sort -u | sed 's/^0*//' | sort -n | tr '\n' ' ')
else
    ROOMS=$(seq 1 95 | tr '\n' ' ')
fi

mkdir -p "$OUT" || exit 1
: > "$OUT/statisch.csv"
: > "$OUT/scroll.csv"
cd "$REPO/release/linux" || exit 1

# Aufnahmekonfiguration ohne Harness-FIFO (wie make_scroll_montage.sh).
CFG=scummvm_video.ini
if [ ! -f "$CFG" ]; then
    grep -v '^jev_cmd_fifo=' scummvm.ini > "$CFG"
fi

echo "Raeume: $(echo $ROOMS | wc -w)"

echo "=== Phase A: stehende Bilder ==="
for R in $ROOMS; do
    rm -f /tmp/hd_ref.ppm /tmp/hd_step_*.ppm hd_state.log
    HD_DUMP_STEPS=1 HD_DUMP_REF=1 timeout 8 "$BIN" \
        --config="$CFG" --path=game --boot-param=$R comi > /dev/null 2>&1
    RC=$?
    if [ ! -s /tmp/hd_ref.ppm ] || [ ! -s /tmp/hd_step_4_kostueme.ppm ]; then
        echo "$R;keine_bilder;rc=$RC" >> "$OUT/statisch.csv"
        echo "  Raum $R: keine Bilder (rc=$RC)"
        continue
    fi
    cp -f /tmp/hd_ref.ppm "$OUT/${R}_ref.ppm"
    cp -f /tmp/hd_step_4_kostueme.ppm "$OUT/${R}_hd.ppm"
    cp -f hd_state.log "$OUT/${R}_state.log" 2>/dev/null
    "$PY" "$REPO/harness/ab_compare.py" "$OUT/${R}_ref.ppm" "$OUT/${R}_hd.ppm" "$OUT" "$R" \
        | tr '\n' ' ' | sed "s/^/  /"
    echo
done

echo "=== Phase B: Kamerafahrt ==="
for R in $SCROLL; do
    rm -rf /tmp/hd_scan /tmp/hd_refscan
    mkdir -p /tmp/hd_scan /tmp/hd_refscan
    HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 20 "$BIN" \
        --config="$CFG" --path=game --boot-param=$R comi > /dev/null 2>&1
    "$PY" "$REPO/harness/ab_scroll.py" /tmp/hd_refscan /tmp/hd_scan "$OUT/scroll.csv"
done
echo AB_SWEEP_DURCH
