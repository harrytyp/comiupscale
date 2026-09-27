#!/usr/bin/env bash
# Baut den Fork und misst die Figurenskalierung in Raum 20, wo alles zu gross erscheint.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_scale.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_scale.log)"
grep -m4 "error:" /tmp/build_scale.log

cd "$REPO/release/linux" || exit 1
for R in 20 14; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 20 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "--- Raum $R: rc=$? ---"
	echo "hdgeom: $(grep -o 'hdgeom:.*' hd_state.log 2>/dev/null | tail -1)"
	echo "Figuren (Skala, Groesse der Textur, Groesse des Blits):"
	grep -o "costume HIT:.*" hd_state.log 2>/dev/null | sort -u | head -10
	echo "Objektmeldungen mit Groesse:"
	grep -o "INV-BLAST[^ ]*.*\|LOAD obj=[0-9]*.*sz=([0-9]*x[0-9]*).*" hd_state.log 2>/dev/null | head -6
done
echo "SKALEN_PRUEFUNG_DURCH"
