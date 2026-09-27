#!/usr/bin/env bash
# Nimmt die drei gemeldeten Faelle auf, ohne Kameraantrieb, damit das Bild dem
# normalen Spiel entspricht:
#   Raum 25  Banjo liegt als Overlay ueber einem Raum, in dem es nicht vorkommt
#   Raum 40  Inventar offen, zwei Schiffe mit unterschiedlichem Schatten und Segeln
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
OUT=/tmp/hd_report
cd "$REPO/release/linux" || exit 1
rm -rf "$OUT"; mkdir -p "$OUT"

for R in 25 40 41; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 18 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "--- Raum $R: rc=$? ---"
	echo "  hdgeom: $(grep -o 'hdgeom:.*' hd_state.log 2>/dev/null | tail -1)"
	echo "  Inventarstatus: $(grep -o 'obj=114 [^ ]* [^ ]* [^ ]* [^ ]* state=[0-9]*' hd_state.log 2>/dev/null | tail -1)"
	echo "  Inventar aktiv: $(grep -o 'invActive=[0-9]*' hd_state.log 2>/dev/null | tail -1)"
	# je Raum drei Bilder aus dem Lauf
	N=0
	for f in $(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | head -30); do
		N=$((N + 1))
		[ $((N % 10)) -eq 0 ] || continue
		cp -f "$f" "$OUT/raum${R}_$(printf '%02d' $N).ppm"
	done
	echo "  Bilder: $(ls -1 $OUT/raum${R}_*.ppm 2>/dev/null | wc -l)"
done
ls -la "$OUT" | head -12
echo "AUFNAHME_DURCH"
