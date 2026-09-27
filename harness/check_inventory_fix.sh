#!/usr/bin/env bash
# Baut den Fork und prueft, ob die neue Inventarerkennung greift.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
OUT=/tmp/hd_invfix
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_inv.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_inv.log)"
grep -m4 "error:" /tmp/build_inv.log

cd "$REPO/release/linux" || exit 1
rm -rf "$OUT"; mkdir -p "$OUT"
for R in 40 41 25 60; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 14 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	RC=$?
	echo "--- Raum $R: rc=$RC ---"
	echo "  invActive: $(grep -oE 'invActive=[0-9]' hd_state.log 2>/dev/null | sort -u | tr '\n' ' ')"
	echo "  CULL 114:  $(grep -oE 'CULL obj=114[^\"]*' hd_state.log 2>/dev/null | sort -u | head -1)"
	echo "  RENDER 114: $(grep -oE 'RENDER obj=114[^\"]*' hd_state.log 2>/dev/null | sort -u | head -1)"
	N=0
	for f in $(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | head -30); do
		N=$((N + 1))
		[ $((N % 12)) -eq 0 ] || continue
		cp -f "$f" "$OUT/raum${R}_$(printf '%02d' $N).ppm"
	done
	echo "  Bilder: $(ls -1 $OUT/raum${R}_*.ppm 2>/dev/null | wc -l)"
done
echo "INVENTAR_PRUEFUNG_DURCH"
