#!/usr/bin/env bash
# Packt auslieferbare Staende: Engine, Startdatei, Konfiguration, Dokumentation.
#
#   bash scripts/package_release.sh [ausgabeordner]
#
# Ergebnis: comi-hd-<datum>-linux.tar.gz und comi-hd-<datum>-windows.zip
# Spieldaten (copyright) und HD-Assets sind NICHT enthalten. Die HD-Assets liegen als
# hd_assets_part1..3.zip daneben, die Spieldaten bringt jeder aus der eigenen Kopie mit.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUS="${1:-$ROOT/dist}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BASE="comi-hd-$STAMP"

mkdir -p "$AUS"

install_txt() {
cat <<'TEXT'
COMI HD - Installation

1. Dieses Paket in einen Ordner entpacken, zum Beispiel COMI-HD
2. Die eigenen Spieldateien (COMI.LA0, COMI.LA1, COMI.LA2) in einen Unterordner "game"
   legen.
3. HD-Assets: hd_assets_part1.zip bis hd_assets_part3.zip hier entpacken, sodass ein
   Ordner "hd" entsteht. Reihenfolge ist beliebig.
4. Starten: linux ./start_comi_hd.sh   windows start_comi_hd.bat

Eigene HD-Upscales: Bilder nach hd/ legen (Aufbau siehe docs/MODDING.md) und vorher
pruefen mit: python3 scripts/validate_hd_mod.py --dir hd

Die Spieldaten sind aus rechtlichen Gruenden nicht enthalten.
TEXT
}

gemeinsam() {
    dir="$1"
    mkdir -p "$dir/scripts" "$dir/docs"
    cp -f "$ROOT/scripts/validate_hd_mod.py" "$dir/scripts/"
    cp -f "$ROOT/scripts/check_texture_packs.py" "$dir/scripts/"
    cp -f "$ROOT/docs/MODDING.md" "$dir/docs/"
    cp -f "$ROOT/docs/ASSETS.md" "$dir/docs/"
    cp -f "$ROOT/docs/VERIFY.md" "$dir/docs/"
    install_txt > "$dir/INSTALL.txt"
}

# --- Linux
L="$AUS/$BASE-linux"
mkdir -p "$L"
cp -f "$ROOT/release/linux/scummvm" "$L/"
cp -f "$ROOT/release/linux/scummvm_video.ini" "$L/"
cp -f "$ROOT/release/linux/start_comi_hd.sh" "$L/"
cp -f "$ROOT/scripts/install.sh" "$L/scripts/" 2>/dev/null || { mkdir -p "$L/scripts"; cp -f "$ROOT/scripts/install.sh" "$L/scripts/"; }
gemeinsam "$L"
( cd "$L" && sha256sum scummvm scummvm_video.ini start_comi_hd.sh > SHA256SUMS )
tar -C "$AUS" -czf "$AUS/$BASE-linux.tar.gz" "$BASE-linux"
echo "$AUS/$BASE-linux.tar.gz ($(du -h "$AUS/$BASE-linux.tar.gz" | cut -f1))"

# --- Windows
W="$AUS/$BASE-windows"
mkdir -p "$W"
if [ -f "$ROOT/release/windows/scummvm.exe" ]; then
    cp -f "$ROOT/release/windows/scummvm.exe" "$W/"
    [ -f "$ROOT/release/windows/SDL2.dll" ] && cp -f "$ROOT/release/windows/SDL2.dll" "$W/"
    [ -f "$ROOT/release/windows/start_comi_hd.bat" ] && cp -f "$ROOT/release/windows/start_comi_hd.bat" "$W/"
    [ -f "$ROOT/release/windows/scummvm.ini" ] && cp -f "$ROOT/release/windows/scummvm.ini" "$W/"
    gemeinsam "$W"
    ( cd "$W" && sha256sum scummvm.exe > SHA256SUMS )
    python3 "$ROOT/scripts/make_zip.py" "$W" "$AUS/$BASE-windows.zip"
else
    echo "kein Windows-Binary, Windows-Paket uebersprungen"
fi
