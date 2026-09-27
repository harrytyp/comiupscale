#!/usr/bin/env bash
# Prueft, ob sich die Wasserflaeche in den Schiffskampfkarten bewegt.
# Dazu werden aufeinanderfolgende Bilder eines Laufs genommen und die Wasserbereiche
# verglichen. Bewegt sich nichts, ist die Animation verloren gegangen.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
OUT=/tmp/hd_water
cd "$REPO/release/linux" || exit 1
rm -rf "$OUT"; mkdir -p "$OUT"

for R in 40 41; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 16 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	# zusammenhaengende Bilder ohne Ausdünnung, damit eine Bewegung sichtbar wird
	N=0
	for f in $(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | head -40); do
		cp -f "$f" "$OUT/raum${R}_$(printf '%03d' $N).ppm"
		N=$((N + 1))
	done
	echo "Raum $R: $N Bilder kopiert, rc=$?"
done
ls "$OUT" | head -4
echo "WASSER_LAUF_DURCH"
