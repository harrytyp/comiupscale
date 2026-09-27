#!/usr/bin/env bash
# Baut den Fork und prueft die Wirkung der neuen Vordergrundreferenz.
# Verglichen wird der Zustand vor und nach der Aenderung an denselben Raumbildern.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_fg.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_fg.log)"
grep -m5 "error:" /tmp/build_fg.log

cd "$REPO/release/linux" || exit 1
OUT=/tmp/hd_fg
rm -rf "$OUT"; mkdir -p "$OUT"
for R in 25 40 41 43 67; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_AUTO_SHOTS=1 HD_SCROLL_TEST=1 timeout 18 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	RC=$?
	N=0
	for f in /tmp/hd_scan/*_raum${R}_*.ppm; do
		[ -f "$f" ] || continue
		N=$((N + 1))
		[ $((N % 4)) -eq 0 ] || continue
		cp -f "$f" "$OUT/raum${R}_$(basename "$f")"
	done
	GEO=$(grep -o 'bg=[0-9x]*' hd_state.log 2>/dev/null | tail -1)
	echo "Raum $R: rc=$RC Bilder=$N $GEO"
done
echo "PRUEFUNG_DURCH"
