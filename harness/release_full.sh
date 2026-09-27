#!/usr/bin/env bash
# Baut Linux und Windows, uebernimmt die Binaries und laedt alles auf ein neues Tag.
set -u
REPO=/opt/data/local/comi-hd-repo
TAG=${1:-v0.0.71}
cd "$REPO" || exit 1

echo "=== Linux uebernehmen ==="
cp -f "$REPO/scummvm/fork/scummvm" "$REPO/release/linux/scummvm"
ls -la "$REPO/release/linux/scummvm" | awk '{print $5, $9}'

echo "=== Windows bauen ==="
bash build/build-all.sh windows > /tmp/win_build2.log 2>&1
echo "build=$?"
STRIP=$(ls build/install/llvm-mingw/bin/*-strip 2>/dev/null | head -1)
cp -f build/out/scummvm.exe release/windows/scummvm.exe
[ -n "$STRIP" ] && "$STRIP" release/windows/scummvm.exe && echo "gestrippt"
ls -la release/windows/scummvm.exe | awk '{print $5, $9}'

echo "=== Bundle ==="
bash scripts/build_win_bundle.sh /opt/data/dist/scummvm-win-bundle.zip 2>&1 | grep -E "Bundle|Groesse|SHA256"

echo "=== Tag $TAG ==="
gh release view "$TAG" > /dev/null 2>&1 || \
  gh release create "$TAG" --title "$TAG - shadows fixed" \
  --notes "The shadow under a character is now drawn by the 8-bit layer instead of being taken from the HD costume texture. It was a fixed brown value from a capture and only matched one background, which is why it looked brown elsewhere. Now it is a darker sand on sand and a darker wood on wood. Also adds a scale and blit size readout for actor costumes and the check scripts for the open points." 2>&1 | tail -2

echo "=== Hochladen ==="
gh release upload "$TAG" release/linux/scummvm release/windows/scummvm.exe \
  /opt/data/dist/scummvm-win-bundle.zip /opt/data/dist/hd_assets_part1.zip --clobber 2>&1 | tail -3

echo "=== Gegenprobe ==="
gh release view "$TAG" --json assets -q '.assets[] | "\(.name)  \(.size)"'
echo "RELEASE_FERTIG"
