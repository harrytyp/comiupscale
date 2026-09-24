#!/usr/bin/env bash
# Stellt ALLE HD-Objekt- und Layer-Ordner auf den Originalzustand zurueck.
# Hintergrund: die farbbasierte Magenta-Regel hat bei Logo und Raumobjekten
# echtes Violett entfernt. Originale liegen in den Sicherungen, es wird nichts
# geloescht, nur ueberschrieben.
set -u
BASE=/opt/data/local/comi-hd-repo
P1=/opt/data/backups/comi-hd-magenta-20260924-192054
P2=/opt/data/backups/comi-hd-magenta-20260924-fixall2
LOG=/tmp/restore_pristine.log
: > "$LOG"

restore() {
  local rel="$1" src="$2"
  if [ ! -d "$src" ]; then echo "FEHLT $src" >> "$LOG"; return; fi
  cp -a "$src/." "$BASE/$rel/"
  echo "zurueckgespielt: $rel <- $src" >> "$LOG"
}

restore "release/linux/hd/objects"             "$P1/release_linux_hd_objects"
restore "release/linux/game/hd/objects"        "$P1/release_linux_game_hd_objects"
restore "release/windows/hd/objects"           "$P1/release_windows_hd_objects"
restore "scummvm/fork/hd/objects"              "$P1/scummvm_fork_hd_objects"
restore "release/linux/hd/objects_layers"      "$P1/release_linux_hd_objects_layers"
restore "release/linux/game/hd/objects_layers" "$P1/release_linux_game_hd_objects_layers"
restore "release/windows/hd/objects_layers"    "$P2/release_windows_hd_objects_layers"
restore "scummvm/fork/hd/objects_layers"       "$P2/scummvm_fork_hd_objects_layers"

echo "DONE" >> "$LOG"
