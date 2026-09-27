#!/usr/bin/env bash
# Punkt 6: laedt die Raeume der alten Meldungen 16 und 20 und legt je ein Bild ab.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
OUT=/tmp/hd_old
cd "$REPO/release/linux" || exit 1
rm -rf "$OUT"; mkdir -p "$OUT"

for R in 16 20; do
	for attempt in 1 2; do
		rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
		HD_AUTO_SHOTS=1 timeout 15 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
		RC=$?
		# Der Sprung landet nicht immer im gewuenschten Raum, deshalb wird geprueft,
		# in welchem Raum die Bilder wirklich entstanden sind.
		FOUND=$(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | wc -l)
		echo "Versuch $attempt Raum $R: rc=$RC Bilder fuer diesen Raum=$FOUND"
		if [ "$FOUND" -gt 0 ]; then
			cp -f "$(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm | tail -1)" "$OUT/raum${R}.ppm"
			break
		fi
	done
done
ls -la "$OUT"
echo "PRUEFUNG_DURCH"
