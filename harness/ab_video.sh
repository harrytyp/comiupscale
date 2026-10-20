#!/usr/bin/env bash
# Videoaufnahme je Raum: Original | HD-Komposition | Abweichung, waehrend die Kamera faehrt.
# Rot im dritten Bild heisst: dort steckt kein HD-Asset, es wird das hochskalierte Original gezeigt.
#
# Aufruf: bash harness/ab_video.sh "<raumliste>" [ausgabeordner]
set -u
REPO=/opt/data/local/comi-hd-repo
BIN="$REPO/scummvm/fork/scummvm"
PY="$REPO/venv/bin/python3"
OUT="${2:-/opt/data/projects/comi-hd/reports/ab/videos}"
ROOMS="${1:?Raumliste fehlt}"
mkdir -p "$OUT" || exit 1
cd "$REPO/release/linux" || exit 1

CFG=scummvm_video.ini
[ -f "$CFG" ] || grep -v '^jev_cmd_fifo=' scummvm.ini > "$CFG"

for R in $ROOMS; do
    rm -rf /tmp/hd_scan /tmp/hd_refscan
    mkdir -p /tmp/hd_scan /tmp/hd_refscan
    HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 20 "$BIN" \
        --config="$CFG" --path=game --boot-param=$R comi > /dev/null 2>&1
    FRAMES=/tmp/ab_video_frames/$R
    rm -rf "$FRAMES"
    mkdir -p "$FRAMES"
    "$PY" "$REPO/harness/ab_scroll.py" /tmp/hd_refscan /tmp/hd_scan "$OUT/scroll.csv" "$FRAMES" 1280
    COUNT=$(ls -1 "$FRAMES"/f*.png 2>/dev/null | wc -l)
    if [ "$COUNT" -lt 3 ]; then
        echo "  Raum $R: nur $COUNT Bilder, kein Video"
        continue
    fi
    ffmpeg -y -framerate 12 -i "$FRAMES/f%05d.png" -c:v libx264 -pix_fmt yuv420p \
        -crf 23 -movflags +faststart "$OUT/raum${R}.mp4" > /dev/null 2>&1
    echo "  Raum $R: Video aus $COUNT Bildern, $(du -h "$OUT/raum${R}.mp4" | cut -f1)"
done
echo AB_VIDEOS_DURCH
