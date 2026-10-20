#!/usr/bin/env bash
# Richtet eine lauffaehige Installation ein.
#
#   bash scripts/install.sh --ziel ~/COMI-HD --spiel /pfad/zu/den/COMI-Dateien
#
# Kopiert Engine, Startskript und HD-Assets. Die Spieldaten werden NICHT mitgeliefert, sie
# kommen aus der eigenen Kopie des Spiels (COMI.LA0, COMI.LA1, COMI.LA2 im selben Ordner).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ZIEL=""
SPIEL=""
OHNE_HD=0

while [ $# -gt 0 ]; do
    case "$1" in
        --ziel)    ZIEL="$2"; shift 2 ;;
        --spiel)   SPIEL="$2"; shift 2 ;;
        --ohne-hd) OHNE_HD=1; shift ;;
        *) echo "unbekannt: $1"; exit 2 ;;
    esac
done

[ -n "$ZIEL" ] || { echo "Bitte --ziel angeben."; exit 2; }
[ -n "$SPIEL" ] || { echo "Bitte --spiel angeben (Ordner mit COMI.LA0)."; exit 2; }
[ -f "$SPIEL/COMI.LA0" ] || { echo "In $SPIEL fehlt COMI.LA0."; exit 2; }

mkdir -p "$ZIEL/game" "$ZIEL/hd"
echo "== Spieldaten"
for f in COMI.LA0 COMI.LA1 COMI.LA2 comi.la0 comi.la1 comi.la2; do
    [ -f "$SPIEL/$f" ] && cp -f "$SPIEL/$f" "$ZIEL/game/" && echo "  $f"
done

echo "== Engine"
cp -f "$ROOT/release/linux/scummvm" "$ZIEL/"
cp -f "$ROOT/release/linux/scummvm_video.ini" "$ZIEL/"
cp -f "$ROOT/release/linux/start_comi_hd.sh" "$ZIEL/"
chmod +x "$ZIEL/scummvm" "$ZIEL/start_comi_hd.sh"

if [ "$OHNE_HD" -eq 0 ]; then
    echo "== HD-Assets"
    if [ -d "$ROOT/release/linux/hd" ]; then
        cp -a "$ROOT/release/linux/hd/." "$ZIEL/hd/"
        echo "  aus release/linux/hd kopiert ($(find "$ZIEL/hd" -type f | wc -l) Dateien)"
    else
        echo "  release/linux/hd fehlt; Packs muessen von Hand entpackt werden:" >&2
        echo "    unzip hd_assets_part1.zip -d \"$ZIEL\"" >&2
    fi
fi

echo "== Pruefung"
"$ZIEL/scummvm" --version | head -1
[ -f "$ZIEL/game/COMI.LA0" ] && echo "  Spieldaten vollstaendig"
[ -d "$ZIEL/hd/backgrounds" ] && echo "  HD-Hintergruende: $(ls "$ZIEL/hd/backgrounds" | wc -l)"

cat <<HINWEIS

Fertig. Starten mit:
    cd "$ZIEL" && ./start_comi_hd.sh

Eigene HD-Upscales: Bilder nach "$ZIEL/hd" legen und vorher pruefen mit
    python3 "$ROOT/scripts/validate_hd_mod.py" --dir "$ZIEL/hd"
HINWEIS
