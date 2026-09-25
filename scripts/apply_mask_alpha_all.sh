#!/usr/bin/env bash
# Wendet den maskenbasierten Alpha-Schritt (fix_mask_alpha.py) auf alle Kopien an.
# Regel im Skript: nur wo die Quelle eine Magentamaske AM BILDRAND hat, wird
# angefasst. Logo und Raumobjekte fallen dadurch heraus.
set -u
BASE=/opt/data/local/comi-hd-repo
PY=/opt/hermes/.venv/bin/python
S="$BASE/scripts/fix_mask_alpha.py"
SRCZIP=/opt/data/dist/comi-original-assets.zip
ORIGCUR=/opt/data/backups/comi-hd-cursor-icons-20260924-154157
TS=$(date +%Y%m%d-%H%M%S)
LOG=/tmp/mask_alpha_$TS.log
: > "$LOG"
RESTORE_FROM="${1:-}"     # optional: Sicherungsordner, aus dem vorher der Originalzustand kommt

OBJ_DIRS=(
  release/linux/hd/objects release/linux/game/hd/objects release/windows/hd/objects scummvm/fork/hd/objects
)
LAY_DIRS=(
  release/linux/hd/objects_layers release/linux/game/hd/objects_layers release/windows/hd/objects_layers scummvm/fork/hd/objects_layers
)

# Originale der beiden Cursordateien zurueckholen (die Sicherung von 19:20 enthielt sie schon bearbeitet)
for d in "${OBJ_DIRS[@]}"; do
  cp -a "$ORIGCUR/0003_system-cursor-icon_0000.png" "$BASE/$d/"
  cp -a "$ORIGCUR/0003_system-cursor-icon_0001.png" "$BASE/$d/"
done
echo "Cursordateien aus Original-Sicherung zurueckgeholt" >> "$LOG"

if [ -n "$RESTORE_FROM" ]; then
  for d in "${OBJ_DIRS[@]}" "${LAY_DIRS[@]}"; do
    src="$RESTORE_FROM/${d//\//_}"
    if [ -d "$src" ]; then
      cp -a "$src/." "$BASE/$d/"
      echo "zurueckgespielt vor dem Lauf: $d <- $src" >> "$LOG"
    fi
  done
fi

for d in "${OBJ_DIRS[@]}"; do
  echo "=== objects $d" >> "$LOG"
  "$PY" "$S" --hd "$BASE/$d" --src-zip "$SRCZIP" --prefix objects --apply \
        --backup "/opt/data/backups/comi-hd-mask-$TS/${d//\//_}" >> "$LOG" 2>&1
done
for d in "${LAY_DIRS[@]}"; do
  echo "=== layers $d" >> "$LOG"
  # Objektebenen: Maske 39 aussen, Alpha innen exakt aus der zugehoerigen Objekttextur
  od="${d/objects_layers/objects}"
  "$PY" "$S" --hd "$BASE/$d" --src-zip "$SRCZIP" --prefix objects_layers --layer \
        --object-hd "$BASE/$od" --apply \
        --backup "/opt/data/backups/comi-hd-mask-$TS/${d//\//_}" >> "$LOG" 2>&1
  echo "rc=$?" >> "$LOG"
done
echo "DONE $TS" >> "$LOG"
