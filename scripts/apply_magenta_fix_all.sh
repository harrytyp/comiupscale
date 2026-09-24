#!/usr/bin/env bash
# Wendet den Magenta-Fix (add_object_alpha_v7.py) auf alle HD-Objekt- und Layer-Ordner an.
# Idempotent: bereits bereinigte Dateien melden sich als "sauber".
# Aufruf: bash apply_magenta_fix_all.sh <zeitstempel>
set -u
BASE=/opt/data/local/comi-hd-repo
S="$BASE/scripts/add_object_alpha_v7.py"
PY="${JEV_PY:-/opt/hermes/.venv/bin/python}"   # muss numpy + PIL haben
TS="${1:-$(date +%Y%m%d-%H%M%S)}"
BKROOT="/opt/data/backups/comi-hd-magenta-$TS"
LOG="/tmp/magenta_fix_$TS.log"
: > "$LOG"
DIRS=(
  release/linux/hd/objects
  release/linux/game/hd/objects
  release/windows/hd/objects
  scummvm/fork/hd/objects
  release/linux/hd/objects_layers
  release/linux/game/hd/objects_layers
  release/windows/hd/objects_layers
  scummvm/fork/hd/objects_layers
)
for d in "${DIRS[@]}"; do
  echo "=== $d" >> "$LOG"
  if [ ! -d "$BASE/$d" ]; then
    echo "ordner fehlt" >> "$LOG"
    continue
  fi
  bk="$BKROOT/${d//\//_}"
  "$PY" "$S" "$BASE/$d" --apply --backup "$bk" >> "$LOG" 2>&1
  echo "rc=$?" >> "$LOG"
  echo "fertig $d" >&2
done
echo "DONE $TS" >> "$LOG"
echo "$TS"
