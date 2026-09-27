#!/usr/bin/env bash
# Baut den Fork und prueft, ob der Rechtsklick vor dem Schwenk das Inventar schliesst.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_invclose.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_invclose.log)"
grep -m5 "error:" /tmp/build_invclose.log

cd "$REPO/release/linux" || exit 1
for R in 40 41 25 60; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1 timeout 16 "$BIN" --config=scummvm_video.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	echo "--- Raum $R: rc=$? ---"
	echo "  invActive: $(grep -oE 'invActive=[0-9]' hd_state.log 2>/dev/null | sort -u | tr '\n' ' ')"
	echo "  Inventar:  $(grep -oE '(CULL|RENDER) obj=114[^\"]*' hd_state.log 2>/dev/null | sort -u | head -1)"
	echo "  Bilder:    $(ls -1 /tmp/hd_scan/*_raum${R}_*.ppm 2>/dev/null | wc -l)"
done
echo "INVENTAR_SCHLIESSEN_DURCH"
