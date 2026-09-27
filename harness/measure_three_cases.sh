#!/usr/bin/env bash
# Messung zu den drei gemeldeten Faellen.
#  Inventar: ist der Cursor (Objekt 105) wirklich sichtbar, und wo steht er?
#  Banjo:    welche Objekte zeichnet der Motor in Raum 25 und an welcher Position?
#  Schiffe:  Cursor und Inventarobjekt in den Schiffskampfkarten
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/release/linux" || exit 1

for R in 25 40 41 60; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 14 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "===== Raum $R: rc=$? ====="
	echo "  Cursor 105:"
	grep -oE "obj=105[^\"]*visible=[0-9]+[^\"]*" hd_state.log 2>/dev/null | sort -u | head -3
	grep -oE "obj=105.*state=[0-9]+.*pos=\([0-9-]+,[0-9-]+\)" hd_state.log 2>/dev/null | sort -u | head -3
	echo "  Inventarobjekt 114:"
	grep -oE "obj=114[^\"]*state=[0-9]+" hd_state.log 2>/dev/null | sort -u | head -3
	echo "  invActive-Werte: $(grep -oE 'invActive=[0-9]' hd_state.log 2>/dev/null | sort -u | tr '\n' ' ')"
	echo "  CULL-Zeilen fuer 114:"
	grep -oE "CULL obj=114[^\"]*" hd_state.log 2>/dev/null | sort -u | head -2
	echo "  Objekte mit Position (Raum 25: Banjo):"
	grep -oE "ROOM OBJ: oi=[0-9]+ obj=[0-9]+ fl=[0-9]+ state=[0-9]+ pos=\([0-9-]+,[0-9-]+\) sz=\([0-9]+x[0-9]+\)" hd_state.log 2>/dev/null | head -12
done
echo "MESSUNG_DURCH"
