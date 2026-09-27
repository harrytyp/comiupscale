#!/usr/bin/env bash
# Diagnose fuer die beiden verbliebenen Probleme.
#  #30: oeffnet sich das Inventar von selbst? Der Motor hat eine Debug-Zaehlung der
#       Vordergrundpixel im Inventarbereich und meldet das Inventarobjekt 114.
#  #20: Objekte in Raum 20 erscheinen zu gross. Der Motor protokolliert Position und
#       Groesse jedes geladenen HD-Objekts, damit laesst sich das nachrechnen.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
OUT=/tmp/hd_diag
cd "$REPO/release/linux" || exit 1
rm -rf "$OUT"; mkdir -p "$OUT"

run_room() {
	local room="$1" drive="$2"
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	if [ -n "$drive" ]; then
		HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 20 "$BIN" --config=scummvm.ini --path=game --boot-param="$room" comi > /dev/null 2>&1
	else
		HD_AUTO_SHOTS=1 timeout 20 "$BIN" --config=scummvm.ini --path=game --boot-param="$room" comi > /dev/null 2>&1
	fi
	cp -f hd_state.log "$OUT/state_${room}${drive:+_drive}.log" 2>/dev/null
	echo "--- Raum $room ${drive:+(mit Antrieb)} ---"
	grep -o 'step2 invArea: [^)]*)' "$OUT/state_${room}${drive:+_drive}.log" 2>/dev/null | tail -3
	echo "  Inventarobjekt-Meldungen: $(grep -c 'obj=114' "$OUT/state_${room}${drive:+_drive}.log" 2>/dev/null)"
	echo "  hdgeom: $(grep -o 'hdgeom: [^ ]* scale=[0-9]* camX=[0-9-]* camY=[0-9-]* bg=[0-9x]* room=[0-9x]*' "$OUT/state_${room}${drive:+_drive}.log" 2>/dev/null | tail -1)"
}

echo "=========== #30 Inventar ==========="
for R in 33 44 60; do run_room "$R" ""; run_room "$R" drive; done

echo
echo "=========== #20 Objektgroessen Raum 20 ==========="
grep -E "LOAD obj=|hdPos=" "$OUT/state_20_drive.log" 2>/dev/null | head -8
grep -oE "obj=[0-9]+ .*sz=\([0-9]+x[0-9]+\) surf=\([0-9]+x[0-9]+\)" "$OUT/state_20_drive.log" 2>/dev/null | head -8
echo
echo "Rohe Objektzeilen aus dem Protokoll:"
grep -E "step25_loaded|obj=" "$OUT/state_20_drive.log" 2>/dev/null | tail -12
echo "DIAGNOSE_DURCH"
