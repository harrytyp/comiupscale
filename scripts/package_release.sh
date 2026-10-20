#!/usr/bin/env bash
# Packt einen auslieferbaren Stand: Engine, Startskript, Konfiguration, Dokumentation.
#
#   bash scripts/package_release.sh [ausgabeordner]
#
# Spieldaten (copyright) und HD-Assets sind NICHT enthalten. Die HD-Assets liegen als
# hd_assets_part1..3.zip daneben, die Spieldaten bringt jeder aus der eigenen Kopie mit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUS="${1:-$ROOT/dist}"
STAMP="$(date +%Y%m%d-%H%M%S)"
NAME="comi-hd-$STAMP"
TMP="$AUS/$NAME"

mkdir -p "$AUS" "$TMP/scripts" "$TMP/docs"

cp -f "$ROOT/release/linux/scummvm" "$TMP/"
cp -f "$ROOT/release/linux/scummvm_video.ini" "$TMP/"
cp -f "$ROOT/release/linux/start_comi_hd.sh" "$TMP/"
cp -f "$ROOT/scripts/install.sh" "$TMP/scripts/"
cp -f "$ROOT/scripts/validate_hd_mod.py" "$TMP/scripts/"
cp -f "$ROOT/scripts/check_texture_packs.py" "$TMP/scripts/"
cp -f "$ROOT/docs/MODDING.md" "$TMP/docs/"
cp -f "$ROOT/docs/ASSETS.md" "$TMP/docs/"

cat > "$TMP/INSTALL.txt" <<'TEXT'
COMI HD - Installation

1. Dieses Paket in einen Ordner entpacken, zum Beispiel ~/COMI-HD
2. Die eigenen Spieldateien (COMI.LA0, COMI.LA1, COMI.LA2) in denselben Ordner legen,
   in einen Unterordner "game".
3. HD-Assets: die Dateien hd_assets_part1.zip bis hd_assets_part3.zip in diesem Ordner
   entpacken, sodass ein Ordner "hd" entsteht. Reihenfolge ist beliebig.
4. Starten: ./start_comi_hd.sh

Eigene HD-Upscales: Bilder nach hd/ legen (Aufbau siehe docs/MODDING.md) und vorher
pruefen mit: python3 scripts/validate_hd_mod.py --dir hd

Die Spieldaten sind aus rechtlichen Gruenden nicht enthalten.
TEXT

( cd "$TMP" && sha256sum scummvm scummvm_video.ini start_comi_hd.sh > SHA256SUMS )

tar -C "$AUS" -czf "$AUS/$NAME.tar.gz" "$NAME"
echo "$AUS/$NAME.tar.gz ($(du -h "$AUS/$NAME.tar.gz" | cut -f1))"
