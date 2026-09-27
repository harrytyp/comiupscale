#!/usr/bin/env bash
# Klaert, ob das Inventar nur wegen des Raumsprungs offen ist.
# Vergleich: Start ohne boot-param (normales Spiel) gegen Start mit Sprung in Raum 40.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/release/linux" || exit 1

lauf() {
	local label="$1"; shift
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 20 "$BIN" --config=scummvm.ini --path=game "$@" comi > /dev/null 2>&1
	echo "--- $label: rc=$? ---"
	echo "  invActive: $(grep -oE 'invActive=[0-9]' hd_state.log 2>/dev/null | sort -u | tr '\n' ' ')"
	echo "  Inventarobjekt: $(grep -oE 'CULL obj=114[^\"]*|RENDER obj=114[^\"]*' hd_state.log 2>/dev/null | sort -u | head -1)"
	echo "  Cursor: $(grep -oE 'obj=105 fl=4 visible=[0-9]+' hd_state.log 2>/dev/null | sort -u | head -1)"
	echo "  Raum: $(grep -oE 'room=[0-9]+x[0-9]+' hd_state.log 2>/dev/null | tail -1)"
}

lauf "Normales Spiel, kein Sprung"
lauf "Mit Sprung in Raum 40" --boot-param=40
echo "VERGLEICH_DURCH"
