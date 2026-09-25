#!/usr/bin/env bash
# Uebernimmt die neu skalierten Objekttexturen in alle vier HD-Kopien und baut die Pakete.
#
# Aufruf: bash scripts/apply_reupscale.sh [--upload]
#
# Ohne --upload werden nur kopiert und Pakete gebaut. Mit --upload werden die Pakete anschliessend
# in das Release hd_assets_v1.0.5 geladen (ueberschreiben) und die Pruefsummen verglichen.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/.pipeline/reupscale/out"
PY=/opt/hermes/.venv/bin/python
ZIP_OUT=/opt/data/dist
DO_UPLOAD="${1:-}"

COUNT=$(ls -1 "$SRC"/*.png 2>/dev/null | wc -l)
echo "Neu skalierte Objekttexturen: $COUNT"
[ "$COUNT" -lt 300 ] && { echo "Zu wenige Ergebnisse, Abbruch."; exit 1; }

for dest in "$ROOT/release/linux/hd/objects" "$ROOT/release/linux/game/hd/objects" \
            "$ROOT/release/windows/hd/objects" "$ROOT/scummvm/fork/hd/objects"; do
  [ -d "$dest" ] || { echo "Zielordner fehlt: $dest"; exit 1; }
  # Nur Dateien ersetzen, die es in der Installation schon gibt. Das Roharchiv enthaelt mehr
  # Objekte als das Spiel ausliefert (1365 gegen 600), und neue Dateien ungefragt dazuzulegen
  # waere eine Aenderung ueber den Auftrag hinaus.
  n=0
  for f in "$SRC"/*.png; do
    [ -e "$f" ] || continue
    b=$(basename "$f")
    [ -e "$dest/$b" ] || continue
    cp -f "$f" "$dest/$b"
    n=$((n + 1))
  done
  echo "  $n Dateien uebernommen nach $dest"
done

echo "=== Pakete bauen ==="
"$PY" "$ROOT/scripts/build_texture_pack.py" --dir "$ROOT/release/linux/hd" \
      --out "$ZIP_OUT/hd_textures_v1.0.5_objects_layers.zip" 2>&1 | tail -2
"$PY" "$ROOT/scripts/build_texture_pack.py" --dir "$ROOT/release/linux/hd" \
      --out "$ZIP_OUT/hd_assets_part1.zip" --folders backgrounds objects objects_layers fonts 2>&1 | tail -2

stat -c '%n %s' "$ZIP_OUT/hd_textures_v1.0.5_objects_layers.zip" "$ZIP_OUT/hd_assets_part1.zip"

if [ "$DO_UPLOAD" = "--upload" ]; then
  echo "=== Hochladen ==="
  cd "$ROOT"
  gh release upload hd_assets_v1.0.5 "$ZIP_OUT/hd_textures_v1.0.5_objects_layers.zip" \
     "$ZIP_OUT/hd_assets_part1.zip" --clobber
  echo "=== Gegenprobe ==="
  gh release view hd_assets_v1.0.5 --json assets --jq '.assets[] | "\(.name) \(.size) \(.state) \(.digest)"'
  echo "--- lokal ---"
  sha256sum "$ZIP_OUT/hd_textures_v1.0.5_objects_layers.zip" "$ZIP_OUT/hd_assets_part1.zip"
fi
