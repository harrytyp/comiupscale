#!/usr/bin/env bash
# Prueft, ob die Aufnahmekonfiguration ohne Harness-FIFO das Inventar geschlossen laesst.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/release/linux" || exit 1

lauf() {
	local label="$1" cfg="$2"
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 16 "$BIN" --config="$cfg" --path=game --boot-param=40 comi > /dev/null 2>&1
	echo "--- $label ($cfg): rc=$? ---"
	echo "  invActive: $(grep -oE 'invActive=[0-9]' hd_state.log 2>/dev/null | sort -u | tr '\n' ' ')"
	echo "  Inventarobjekt: $(grep -oE '(CULL|RENDER) obj=114[^\"]*' hd_state.log 2>/dev/null | sort -u | head -1)"
	echo "  Cursor: $(grep -oE 'obj=105 fl=4 visible=[0-9]+' hd_state.log 2>/dev/null | sort -u | head -1)"
}

lauf "Alte Konfiguration mit FIFO" "scummvm.ini"
lauf "Aufnahmekonfiguration ohne FIFO" "scummvm_video.ini"
echo "VERGLEICH_DURCH"
