#!/usr/bin/env bash
# scripts/cleanup_dumps.sh — keep only the 3 latest frame-number dump sets
# Dump files: hd_dump_<frame>_*.raw / hd_dump_<frame>_*.txt
# Uses find + xargs to avoid 'Argument list too long'

DUMP_DIR="/opt/data/local/comi-hd-repo/dumps"

# Bail if dump dir doesn't exist
[ -d "$DUMP_DIR" ] || { echo "ERROR: $DUMP_DIR not found" >&2; exit 1; }

# Extract unique frame numbers from dump filenames, sort numerically
# Filenames look like: hd_dump_<frame>_*.raw or hd_dump_<frame>_*.txt
FRAMES=$(find "$DUMP_DIR" -maxdepth 1 -type f -name 'hd_dump_*' \
    | sed -n 's/.*hd_dump_\([0-9]\+\).*/\1/p' \
    | sort -un)

# Count total unique frames
[ -z "$FRAMES" ] && COUNT=0 || COUNT=$(echo "$FRAMES" | wc -l)

if [ "$COUNT" -le 3 ]; then
    echo "Only $COUNT frame set(s) found, nothing to clean up."
    exit 0
fi

# Keep the 3 highest frame numbers
KEEP=$(echo "$FRAMES" | tail -n 3)

# Delete all files belonging to non-kept frames
N_DELETE=$((COUNT - 3))
echo "$FRAMES" | head -n "$N_DELETE" | while read -r frame; do
    [ -n "$frame" ] && find "$DUMP_DIR" -maxdepth 1 -type f -name "hd_dump_${frame}_*" -delete
done

echo "Cleaned up: removed dump files for $N_DELETE frame set(s), kept the 3 newest."
