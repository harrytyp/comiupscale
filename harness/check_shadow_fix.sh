#!/usr/bin/env bash
# Baut den Fork und prueft den Schatten-Fix an Raumbildern mit Figuren.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_shadow.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_shadow.log)"
grep -m4 "error:" /tmp/build_shadow.log

cd "$REPO/release/linux" || exit 1
OUT=/tmp/hd_shadow
rm -rf "$OUT"; mkdir -p "$OUT"
for R in 14 44 60 67; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 timeout 15 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	RC=$?
	N=0
	for f in /tmp/hd_scan/*_raum${R}_*.ppm; do
		[ -f "$f" ] || continue
		N=$((N + 1))
		[ $((N % 5)) -eq 0 ] || continue
		cp -f "$f" "$OUT/raum${R}_$(basename "$f")"
	done
	echo "Raum $R: rc=$RC Bilder=$N"
done
echo "SCHATTEN_PRUEFUNG_DURCH"
