#!/usr/bin/env bash
# Nimmt die Schiffskampfräume auf und legt je Raum vier Bilder in ein Raster.
# Ohne rm: die Bilder werden ueber den Raumnamen im Dateinamen getrennt.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/release/linux" || exit 1

mkdir -p /tmp/pruef
for R in 40 41 42 43 25; do
	HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 18 "$BIN" --config=scummvm_video.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	rc=$?
	n=$(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | wc -l)
	echo "--- Raum $R: rc=$rc Frames=$n ---"
	echo "  Inventarobjekt zuletzt: $(grep -oE '(CULL|RENDER) obj=114[^\"]*' hd_state.log 2>/dev/null | tail -1)"
	echo "  Anzahl Klicks: $(grep -c 'INVCLICK' hd_state.log 2>/dev/null)"
	ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | awk 'NR%7==1' | head -4 | while read -r f; do
		cp "$f" "/tmp/pruef/r${R}_$(basename "$f")"
	done
done
ls -1 /tmp/pruef/ | wc -l
echo PRUEFUNG_DURCH
