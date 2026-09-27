#!/usr/bin/env bash
# Baut die Windows-Binary per Cross-Compile, uebernimmt sie ins Release,
# baut das Bundle und laedt beides auf das Tag v0.0.70 nach.
set -u
REPO=/opt/data/local/comi-hd-repo
cd "$REPO" || exit 1

echo "=== Cross-Compile Windows ==="
bash build/build-all.sh windows > /tmp/win_build.log 2>&1
echo "build=$?"
tail -5 /tmp/win_build.log
ls -la build/out/scummvm.exe 2>/dev/null || { echo "keine exe entstanden"; exit 1; }

echo "=== Strippen und ins Release uebernehmen ==="
STRIP=$(ls build/install/llvm-mingw/bin/*-strip 2>/dev/null | head -1)
if [ -n "$STRIP" ]; then
	cp -f build/out/scummvm.exe release/windows/scummvm.exe
	"$STRIP" release/windows/scummvm.exe && echo "gestrippt mit $STRIP"
else
	cp -f build/out/scummvm.exe release/windows/scummvm.exe
	echo "kein strip gefunden, ungestrippt uebernommen"
fi
ls -la release/windows/scummvm.exe | awk '{print $5, $9}'

echo "=== Gegenprobe: enthaelt die Exe den Fix? ==="
grep -c "hdRefreshCleanBackground" release/windows/scummvm.exe 2>/dev/null || echo "Symbol nicht gefunden (gestrippt, dann ueber Groesse und Datum pruefen)"

echo "=== Bundle bauen ==="
bash scripts/build_win_bundle.sh /opt/data/dist/scummvm-win-bundle.zip 2>&1 | tail -12

echo "=== Auf v0.0.70 nachladen ==="
gh release upload v0.0.70 release/windows/scummvm.exe /opt/data/dist/scummvm-win-bundle.zip --clobber 2>&1 | tail -3
gh release view v0.0.70 --json assets -q '.assets[] | "\(.name)  \(.size)"'
echo "WINDOWS_FERTIG"
