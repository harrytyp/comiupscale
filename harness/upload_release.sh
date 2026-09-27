#!/usr/bin/env bash
# Laedt das neu gebaute Assetpaket und die neuen Binaries hoch.
# Neues Tag statt Ueberschreiben, damit die alte Fassung erhalten bleibt.
set -u
REPO=/opt/data/local/comi-hd-repo
DIST=/opt/data/dist
cd "$REPO" || exit 1

echo "=== Paket ==="
stat -c '%s %n' "$DIST/hd_assets_part1.zip"
sha256sum "$DIST/hd_assets_part1.zip"

echo "=== Tag hd_assets_v1.0.6 anlegen ==="
gh release view hd_assets_v1.0.6 > /dev/null 2>&1 || \
  gh release create hd_assets_v1.0.6 --title "HD Assets v1.0.6 (ship combat maps widened)" \
  --notes "Ship combat backgrounds (rooms 40 to 43) are now 4992 pixels wide, exactly four times the room width of 1248. The source art was 4800, four times 1200, so the engine clamped the camera at the right edge and showed a section from slightly further left. Nothing else changed." 2>&1 | tail -2

echo "=== Hochladen ==="
gh release upload hd_assets_v1.0.6 "$DIST/hd_assets_part1.zip" "$DIST/hd_textures_v1.0.5_objects_layers.zip" --clobber 2>&1 | tail -3
echo "upload=$?"

echo "=== Gegenprobe: was haengt am Tag ==="
gh release view hd_assets_v1.0.6 --json assets -q '.assets[] | "\(.name)  \(.size)  \(.url)"'

echo "=== Tag v0.0.70 mit den Binaries ==="
gh release view v0.0.70 > /dev/null 2>&1 || \
  gh release create v0.0.70 --title "v0.0.70 - foreground reference fix and no crashes" \
  --notes "The foreground reference now includes the room objects, which removes the rectangle around the boat, the broken banjo, the flickering water and the duplicated sprites. Also clips the HD object blit, which fixes the crash in room 77. Verified over all 93 rooms with the camera drive: no crashes." 2>&1 | tail -2
gh release upload v0.0.70 "$REPO/release/linux/scummvm" --clobber 2>&1 | tail -2
gh release upload v0.0.70 "$DIST/hd_assets_part1.zip" --clobber 2>&1 | tail -2
gh release view v0.0.70 --json assets -q '.assets[] | "\(.name)  \(.size)"'
echo "HOCHLADEN_FERTIG"
