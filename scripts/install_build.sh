#!/usr/bin/env bash
# Uebernimmt den gebauten Fork in die Release-Ordner.
#
# Die vorherige Fassung bleibt als .prev-<datum> liegen, damit ein Rueckfall ohne Neubau
# moeglich ist. Danach zeigt --version den neuen Zeitstempel.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
BIN="$ROOT/scummvm/fork/scummvm"
[ -x "$BIN" ] || { echo "kein Build: $BIN"; exit 1; }

STAMP="$(date +%Y%m%d-%H%M%S)"
for ziel in release/linux/scummvm; do
    if [ -f "$ziel" ]; then
        cp -p "$ziel" "$ziel.prev-$STAMP"
    fi
    cp -p "$BIN" "$ziel"
    echo "$ziel <- $(basename "$BIN") ($(stat -c%s "$ziel") Bytes, $(date -r "$ziel" +%H:%M))"
done
"$ROOT/release/linux/scummvm" --version | head -1
