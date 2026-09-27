#!/usr/bin/env bash
# Laesst den Motor den tatsaechlich geladenen Hintergrund ablegen, damit sichtbar wird,
# welche Datei fuer Raum 25 verwendet wird, und prueft den Inventarstatus in denselben
# Raeumen ohne Kameraantrieb.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
OUT=/tmp/hd_bgcheck
cd "$REPO/release/linux" || exit 1
rm -rf "$OUT"; mkdir -p "$OUT"

for R in 25 40 41; do
	rm -f /tmp/hd_scan/*.ppm /tmp/hd_bg_dump* hd_state.log 2>/dev/null
	HD_DUMP_BG=1 HD_AUTO_SHOTS=1 timeout 16 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "--- Raum $R: rc=$? ---"
	echo "  geladener Hintergrund: $(grep -o 'bg=[0-9]*x[0-9]*' hd_state.log 2>/dev/null | tail -1)"
	echo "  Datei die der Motor nennt:"
	grep -oE "(bg|background|hd_bg)[^ ]*\.png" hd_state.log 2>/dev/null | sort -u | head -3
	ls -la /tmp/hd_bg_dump* 2>/dev/null | head -3
	if [ -f /tmp/hd_bg_dump.ppm ]; then
		cp -f /tmp/hd_bg_dump.ppm "$OUT/raum${R}_hintergrund.ppm"
	fi
	echo "  Inventarzustand:"
	grep -o "obj=114[^,]*state=[0-9]*\|invActive=[0-9]*" hd_state.log 2>/dev/null | tail -2
done
echo "HINTERGRUND_PRUEFUNG_DURCH"
