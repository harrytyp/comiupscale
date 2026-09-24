#!/usr/bin/env bash
# Stellt die HD-Ordner aus den Original-Sicherungen wieder her und wendet die
# verschaerfte v7-Regel erneut an (ohne neue Sicherung, die Originale gibt es schon).
set -u
BASE=/opt/data/local/comi-hd-repo
PY=/opt/hermes/.venv/bin/python
S="$BASE/scripts/add_object_alpha_v7.py"
PRISTINE_192054=/opt/data/backups/comi-hd-magenta-20260924-192054
PRISTINE_FIXALL2=/opt/data/backups/comi-hd-magenta-20260924-fixall2
LOG=/tmp/magenta_fix_v7tight.log
: > "$LOG"

restore_and_apply() {
  local rel="$1" src="$2"
  local dst="$BASE/$rel"
  if [ ! -d "$src" ]; then echo "Sicherung fehlt: $src" >> "$LOG"; return; fi
  cp -a "$src/." "$dst/"
  echo "=== $rel  (zurueckgespielt aus $(basename $(dirname $src))/$(basename $src))" >> "$LOG"
  "$PY" "$S" "$dst" --apply >> "$LOG" 2>&1
  echo "rc=$?" >> "$LOG"
}

restore_and_apply "release/linux/hd/objects"                 "$PRISTINE_192054/release_linux_hd_objects"
restore_and_apply "release/linux/game/hd/objects"            "$PRISTINE_192054/release_linux_game_hd_objects"
restore_and_apply "release/windows/hd/objects"               "$PRISTINE_192054/release_windows_hd_objects"
restore_and_apply "scummvm/fork/hd/objects"                  "$PRISTINE_192054/scummvm_fork_hd_objects"
restore_and_apply "release/linux/hd/objects_layers"          "$PRISTINE_192054/release_linux_hd_objects_layers"
restore_and_apply "release/linux/game/hd/objects_layers"     "$PRISTINE_192054/release_linux_game_hd_objects_layers"
restore_and_apply "release/windows/hd/objects_layers"        "$PRISTINE_FIXALL2/release_windows_hd_objects_layers"
restore_and_apply "scummvm/fork/hd/objects_layers"           "$PRISTINE_FIXALL2/scummvm_fork_hd_objects_layers"

echo "DONE" >> "$LOG"
