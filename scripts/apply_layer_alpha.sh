#!/usr/bin/env bash
# Setzt das Alpha der neu skalierten Objektebenen aus der jeweiligen Objekttextur.
# Die Ebene liegt als Vollbild vor; sichtbar ist nur der Objektbereich. Seine Form kommt
# deshalb aus der Objekttextur, nicht aus der Leinwandmaske.
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=/opt/hermes/.venv/bin/python
ZIP=/opt/data/dist/comi-original-assets.zip

for pair in "release/linux/hd" "release/linux/game/hd" "release/windows/hd" "scummvm/fork/hd"; do
  echo "=== $pair/objects_layers"
  "$PY" "$ROOT/scripts/fix_mask_alpha.py" \
        --hd "$ROOT/$pair/objects_layers" \
        --src-zip "$ZIP" --prefix objects_layers --layer \
        --object-hd "$ROOT/$pair/objects" --apply 2>&1 | tail -2
done
echo "=== Integritaet ==="
for pair in "release/linux/hd" "release/linux/game/hd" "release/windows/hd" "scummvm/fork/hd"; do
  "$PY" "$ROOT/scripts/check_texture_integrity.py" "$ROOT/$pair/objects_layers" 2>&1 | tail -1
done
