#!/usr/bin/env bash
# Normalisiert die Objektebenen: Originalstand zurueckspielen und den maskenbasierten
# Schritt einmal deterministisch anwenden, damit alle vier Texturkopien identisch sind.
set -u
BASE=/opt/data/local/comi-hd-repo
PY=/opt/hermes/.venv/bin/python
S="$BASE/scripts/fix_mask_alpha.py"
SRCZIP=/opt/data/dist/comi-original-assets.zip
PRISTINE=/opt/data/backups/comi-hd-mask-20260924-202846
TS=$(date +%Y%m%d-%H%M%S)
LOG=/tmp/layer_normalize_$TS.log
: > "$LOG"

DIRS=(release/linux/hd release/linux/game/hd release/windows/hd scummvm/fork/hd)
for d in "${DIRS[@]}"; do
  src="$PRISTINE/${d//\//_}_objects_layers"
  if [ -d "$src" ]; then
    cp -a "$src/." "$BASE/$d/objects_layers/"
    echo "zurueckgespielt: $d/objects_layers" >> "$LOG"
  else
    echo "Sicherung fehlt: $src" >> "$LOG"
  fi
done
for d in "${DIRS[@]}"; do
  echo "=== $d" >> "$LOG"
  "$PY" "$S" --hd "$BASE/$d/objects_layers" --src-zip "$SRCZIP" --prefix objects_layers --layer \
        --object-hd "$BASE/$d/objects" --apply >> "$LOG" 2>&1
  echo "rc=$?" >> "$LOG"
done
echo "DONE $TS" >> "$LOG"
