#!/usr/bin/env bash
# Prueft die Punkte 3, 4 und 6 der offenen Liste in einem Lauf.
#  4: Hintergrundbreite der Schiffskampfkarten
#  3: Inventar-Reproduktion ohne Kameraantrieb
#  6: Status der alten Meldungen 16 und 20
#
# Hinweis: Die Umgebungsvariable muss direkt vor dem Befehl stehen. Ein vorgeschaltetes
# env "$@" hat in frueheren Laeufen dazu gefuehrt, dass das Binary sofort und ohne Ausgabe
# endet (rc=0, keine Bilder).
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/release/linux" || exit 1

probe() {
	local label="$1" room="$2"
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 15 "$BIN" --config=scummvm.ini --path=game --boot-param="$room" comi > /dev/null 2>&1
	local rc=$?
	local geo
	geo=$(grep -o 'hdgeom: scale=[0-9]* camX=[0-9-]* camY=[0-9-]* bg=[0-9x]* room=[0-9x]*' hd_state.log 2>/dev/null | tail -1)
	echo "$label Raum $room: rc=$rc Frames=$(ls -1 /tmp/hd_scan/*.ppm 2>/dev/null | wc -l)"
	[ -n "$geo" ] && echo "      $geo"
	ls -1 /tmp/hd_scan/*_raum${room}_*.ppm 2>/dev/null | tail -1
}

echo "=== Punkt 4: Breite der Schiffskampfkarten ==="
for R in 40 41 42 43; do probe "Karte" "$R"; done

echo
echo "=== Punkt 3: Inventar ohne Kameraantrieb, mit Bildaufnahme ==="
for R in 33 44 60; do probe "ohne " "$R"; done

echo
echo "=== Punkt 6: alte Meldungen 16 und 20 ==="
for R in 16 20; do probe "alt  " "$R"; done
echo "PRUEFUNG_DURCH"
