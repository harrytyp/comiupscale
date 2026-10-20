#!/usr/bin/env bash
# Laesst die unveraenderte ScummVM ueber dieselben Raeume laufen und legt je Raum Bilder ab.
# Diese Bilder sind die Soll-Vorlage fuer den Vergleich mit der HD-Fassung.
#
# Aufruf: bash harness/sd_sweep.sh "<raumliste>" [ausgabebasis]
set -u
SD_BIN=/opt/data/local/scummvm-sd/scummvm
GAME=/opt/data/local/comi-hd-repo/release/linux/game
OUT="${2:-/opt/data/projects/comi-hd/reports/sd}"
ROOMS="${1:?Raumliste fehlt}"
FORKSWEEP=/opt/data/projects/comi-hd/reports/ab
mkdir -p "$OUT" || exit 1

for R in $ROOMS; do
    D="$OUT/$R"
    mkdir -p "$D"
    rm -f "$D"/*.png 2>/dev/null
    SD_DUMP_DIR="$D" timeout 8 "$SD_BIN" --path="$GAME" --boot-param=$R comi > /dev/null 2>&1
    RC=$?
    COUNT=$(ls -1 "$D"/*.png 2>/dev/null | wc -l)
    if [ "$COUNT" -lt 1 ]; then
        echo "  Raum $R: keine SD-Bilder (rc=$RC)"
        continue
    fi
    if [ -s "$FORKSWEEP/${R}_hd.ppm" ]; then
        /opt/data/local/comi-hd-repo/venv/bin/python3 \
            /opt/data/local/comi-hd-repo/harness/sd_pair.py "$FORKSWEEP/${R}_hd.ppm" "$D" "$OUT" "$R" 2
    else
        echo "  Raum $R: $COUNT SD-Bilder, aber kein HD-Bild vorhanden"
    fi
done
echo SD_SWEEP_DURCH
