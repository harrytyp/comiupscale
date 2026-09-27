#!/usr/bin/env bash
# Baut den Fork und erzeugt danach das Scrolling-Video neu.
set -u
REPO=/opt/data/local/comi-hd-repo
OUT=${1:-/opt/data/projects/comi-hd/reports/scroll-alle-raeume.mp4}
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_video.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_video.log)"
grep -m3 "error:" /tmp/build_video.log
bash "$REPO/harness/make_scroll_montage.sh" "$OUT"
