#!/usr/bin/env bash
# Baut den Fork und prueft danach die vier hohen Raeume mit und ohne Kameraantrieb.
# A = nur Antrieb, B = nur Bildaufnahme, C = beides, D = nichts.
set -u
REPO=/opt/data/local/comi-hd-repo
BIN=$REPO/scummvm/fork/scummvm
cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_clip.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_clip.log)"
grep -m5 "error:" /tmp/build_clip.log
[ -x "$BIN" ] || { echo "kein Binary"; exit 1; }

cd "$REPO/release/linux" || exit 1
run() {
	local label="$1" room="$2"; shift 2
	rm -f /tmp/hd_scan/*.ppm hd_state.log 2>/dev/null
	env "$@" timeout 25 "$BIN" --config=scummvm.ini --path=game --boot-param="$room" comi > /tmp/probe_out.log 2>&1
	local rc=$?
	local n
	n=$(ls -1 /tmp/hd_scan/*.ppm 2>/dev/null | wc -l)
	# 124 = Timeout ohne Absturz, 139 = Segfault
	echo "$label Raum $room: rc=$rc Frames=$n"
}

for R in 77 79 82; do
	run "nur Antrieb     " "$R" HD_SCROLL_TEST=1
	run "beides          " "$R" HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1
done
run "nur Antrieb     " 40 HD_SCROLL_TEST=1
run "beides          " 40 HD_SCROLL_TEST=1 HD_AUTO_SHOTS=1
echo "PRUEFUNG_DURCH"
