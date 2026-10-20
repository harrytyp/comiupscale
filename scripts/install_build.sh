#!/usr/bin/env bash
# Uebernimmt die gebauten Engines in die Release-Ordner.
#
#   release/linux/scummvm        <- scummvm/fork/scummvm
#   release/windows/scummvm.exe  <- build/out/scummvm.exe   (falls vorhanden)
#
# Die vorherige Fassung bleibt als .prev-<datum> liegen, damit ein Rueckfall ohne Neubau
# moeglich ist. Danach zeigt --version den neuen Zeitstempel.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAMP="$(date +%Y%m%d-%H%M%S)"
FEHLER=0

tausch() {
    lokal="$1"; ziel="$2"
    if [ ! -f "$lokal" ]; then
        echo "fehlt, uebersprungen: $lokal"
        return 1
    fi
    [ -f "$ziel" ] && cp -p "$ziel" "$ziel.prev-$STAMP"
    cp -p "$lokal" "$ziel"
    echo "$ziel <- $(basename "$lokal") ($(stat -c%s "$ziel") Bytes, $(date -r "$ziel" +%Y-%m-%d\ %H:%M))"
}

tausch "$ROOT/scummvm/fork/scummvm" "$ROOT/release/linux/scummvm" || FEHLER=1
tausch "$ROOT/build/out/scummvm.exe" "$ROOT/release/windows/scummvm.exe" || FEHLER=1

"$ROOT/release/linux/scummvm" --version | head -1
if [ -f "$ROOT/release/windows/scummvm.exe" ]; then
    file -b "$ROOT/release/windows/scummvm.exe" | cut -c1-70
fi
exit "$FEHLER"
