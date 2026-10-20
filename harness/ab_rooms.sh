#!/usr/bin/env bash
# Faehrt Raeume headless und legt je Raum das Original (8-Bit) neben die HD-Komposition.
# Die Bilder entstehen im selben Bild, deshalb gibt es keine Zustandsdrift zwischen den Laeufen.
#
# Aufruf: bash harness/ab_rooms.sh "<raumliste>" [ausgabeordner] [antrieb]
#   raumliste   z.B. "9 40 41 77" oder "$(seq 1 90)"
#   ausgabe     Standard /tmp/hd_ab
#   antrieb     beliebiger Wert schaltet HD_SCROLL_TEST zu, damit die Kamera faehrt
# Ergebnis: <ausgabe>/<raum>_ab.png (nebeneinander), _diff.png (Abweichung),
#           ab.csv mit einer Zeile je Raum.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN="$REPO/scummvm/fork/scummvm"
PY="$REPO/venv/bin/python3"
OUT="${2:-/tmp/hd_ab}"
DRIVE="${3:-}"
ROOMS="${1:?Raumliste fehlt}"
mkdir -p "$OUT" || exit 1
cd "$REPO/release/linux" || exit 1

for R in $ROOMS; do
    rm -f /tmp/hd_ref.ppm /tmp/hd_step_*.ppm
    if [ -n "$DRIVE" ]; then
        HD_DUMP_STEPS=1 HD_DUMP_REF=1 HD_SCROLL_TEST=1 timeout 8 \
            "$BIN" --config=scummvm.ini --path=game --boot-param=$R comi > /dev/null 2>&1
    else
        HD_DUMP_STEPS=1 HD_DUMP_REF=1 timeout 8 \
            "$BIN" --config=scummvm.ini --path=game --boot-param=$R comi > /dev/null 2>&1
    fi
    RC=$?
    if [ ! -s /tmp/hd_ref.ppm ] || [ ! -s /tmp/hd_step_4_kostueme.ppm ]; then
        echo "raum $R: keine Bilder (rc=$RC)"
        continue
    fi
    cp -f /tmp/hd_ref.ppm "$OUT/${R}_ref.ppm"
    cp -f /tmp/hd_step_4_kostueme.ppm "$OUT/${R}_hd.ppm"
    "$PY" "$REPO/harness/ab_compare.py" "$OUT/${R}_ref.ppm" "$OUT/${R}_hd.ppm" "$OUT" "$R"
    grep -o 'hdgeom: .*' hd_state.log 2>/dev/null | tail -1 | sed 's/^/  /'
    echo "raum $R fertig (rc=$RC)"
done
echo AB_LÄUFE_DURCH
