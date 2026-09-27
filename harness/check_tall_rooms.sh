#!/usr/bin/env bash
# Baut den Fork und prueft die hohen Raeume auf Absturz und Kamerawerte,
# danach der Pixelvergleich gegen einen Referenzstand.
#
# Aufruf: harness/check_tall_rooms.sh [referenzstand]
# Der Referenzstand ist ein Verzeichnis wie /tmp/hd_bench/issue25.
set -u
REPO=$(cd "$(dirname "$0")/.." && pwd)
BIN=$REPO/scummvm/fork/scummvm
REF=${1:-}

cd "$REPO/scummvm/fork" || exit 1
LIBRARY_PATH=$REPO/build/x11link:/opt/data/tmp/devlibs make -j"$(nproc)" scummvm > /tmp/build_check.log 2>&1
echo "Buildfehler: $(grep -c 'error:' /tmp/build_check.log)"

cd "$REPO/release/linux" || exit 1
for R in 77 79 82 40 41 43; do
	rm -f /tmp/hd_scan/*.ppm hd_state.log
	HD_AUTO_SHOTS=1 timeout 20 "$BIN" --config=scummvm.ini --path=game --boot-param="$R" comi > /dev/null 2>&1
	RC=$?
	echo "Raum $R: rc=$RC (124 ist der normale Timeout) Frames=$(ls -1 /tmp/hd_scan/*.ppm 2>/dev/null | wc -l) $(grep -o 'hdgeom:.*' hd_state.log 2>/dev/null | tail -1)"
done

if [ -n "$REF" ]; then
	bash "$REPO/harness/benchmark_hd.sh" /tmp/hd_bench/check > /tmp/bench_check.log 2>&1
	bash "$REPO/harness/benchmark_hd.sh" --compare "$REF" /tmp/hd_bench/check >> /tmp/bench_check.log 2>&1
	tail -8 /tmp/bench_check.log
fi
echo "PRUEFUNG_DURCH"
