#!/usr/bin/env bash
# Legt den Spielstand an, den der Aufnahmelauf zum Laden der Raeume braucht.
#
# Der Raum wird im Aufnahmelauf ueber einen geladenen Spielstand und startScene angesprungen,
# damit Raumskript und Oberflaechensperre (SO_USERPUT_OFF) so laufen wie im Spiel. Der
# Startparameter --boot-param springt dagegen mitten hinein, ohne dass das Skript je laeuft.
#
# Ergebnis: $HOME/.local/share/scummvm/saves/comi.s01
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO/release/linux" || exit 1
HD_SAVE_SLOT=1 timeout 15 "$REPO/scummvm/fork/scummvm" \
    --config=scummvm_video.ini --path=game comi > /tmp/hd_make_save.log 2>&1
grep -m1 'HD_SAVE_SLOT' /tmp/hd_make_save.log
ls -la "$HOME/.local/share/scummvm/saves/" 2>/dev/null | tail -3
