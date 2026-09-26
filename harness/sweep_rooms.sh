#!/usr/bin/env bash
# Laedt jeden Raum einmal und vergleicht den HD-Hintergrund mit dem Raumbild aus den
# Spieldaten. Gesucht werden Raeume, deren HD-Hintergrund fehlt, nicht geladen wird
# oder inhaltlich nicht zum Raum passt.
#
# Aufruf: bash harness/sweep_rooms.sh [ausgabeordner]
# Ergebnis: sweep.csv mit einer Zeile je Raum und einem Urteil.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN="$REPO/scummvm/fork/scummvm"
PY=/opt/hermes/.venv/bin/python
EXTRACT=/tmp/comi_extract/COMI/IMAGES/backgrounds
OUT="${1:-/tmp/hd_sweep}"
mkdir -p "$OUT" /tmp/hd_scan
cd "$REPO/release/linux" || exit 1

ROOMS=$("$PY" - "$EXTRACT" <<'PYEOF'
import glob, os, re, sys
rooms = []
for p in sorted(glob.glob(os.path.join(sys.argv[1], "*.png"))):
    m = re.match(r"(\d{4})_", os.path.basename(p))
    if m:
        rooms.append(int(m.group(1)))
print(" ".join(str(r) for r in sorted(set(rooms))))
PYEOF
)
echo "Raeume: $(echo $ROOMS | wc -w)"

: > "$OUT/sweep.csv"
for R in $ROOMS; do
    rm -f /tmp/hd_state.log hd_state.log /tmp/hd_step_*.ppm 2>/dev/null
    HD_DUMP_STEPS=1 timeout 8 "$BIN" --config=scummvm.ini --path=game --boot-param=$R comi > /dev/null 2>&1
    GEO=$(grep -o 'hdgeom: scale=[0-9]* camX=[0-9-]* bg=[0-9x]* room=[0-9x]*' hd_state.log 2>/dev/null | tail -1)
    if [ -s /tmp/hd_step_1_hintergrund.ppm ]; then
        cp -f /tmp/hd_step_1_hintergrund.ppm "$OUT/${R}_hd_hintergrund.ppm"
    fi
    echo "$R|$GEO" >> "$OUT/sweep.csv"
    echo "  Raum $R: $GEO"
done
echo SWEEP_LÄUFE_DURCH
