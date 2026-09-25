#!/usr/bin/env bash
# ============================================================================
# Holt den Upscaler, den die Pipeline vorschreibt: RealESRGAN-NCNN-Vulkan.
#
# Warum ueberhaupt ein Skript: die Tool-Binaries sind in .gitignore ausgenommen
# (tools/realesrgan-ncnn-vulkan/, tools/nutcracker-Windows_X64/), weil es keine Quellen sind.
# Ohne diesen Schritt kann ein frischer Klon die Stufe "upscale" nicht ausfuehren, und genau
# das ist die Luecke zwischen "auf GitHub dokumentiert" und "laeuft reproduzierbar".
#
# Aufruf:  bash scripts/fetch_upscaler.sh [--windows|--linux]
#
# Ergebnis:
#   tools/realesrgan-ncnn-vulkan-v0.2.0-windows/   (Windows, wie in config/upscale/*.sh erwartet)
#   tools/realesrgan-ncnn-vulkan/                  (Linux)
# jeweils mit models/realesrgan-x4plus-anime.*
#
# Nach dem Lauf wird der SHA256 des Archivs in scripts/upscaler_checksum.txt festgehalten, damit
# weitere Aufrufe gegen denselben Stand pruefen koennen.
# ============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="0.2.0"
PLATFORM="${1:---windows}"

case "$PLATFORM" in
  --windows)
    ARCHIVE="realesrgan-ncnn-vulkan-${VERSION}-windows.zip"
    TARGET="$ROOT/tools/realesrgan-ncnn-vulkan-v${VERSION}-windows"
    ;;
  --linux)
    ARCHIVE="realesrgan-ncnn-vulkan-${VERSION}-ubuntu.zip"
    TARGET="$ROOT/tools/realesrgan-ncnn-vulkan"
    ;;
  *)
    echo "Unbekannte Option: $PLATFORM (erlaubt: --windows, --linux)"; exit 2 ;;
esac

URL="https://github.com/xinntao/Real-ESRGAN/releases/download/v${VERSION}/${ARCHIVE}"
SUMS="$ROOT/scripts/upscaler_checksum.txt"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Lade $ARCHIVE (RealESRGAN v$VERSION)..."
if command -v curl >/dev/null; then
  curl -fL --retry 3 -o "$TMP/$ARCHIVE" "$URL"
else
  wget -q -O "$TMP/$ARCHIVE" "$URL"
fi

SHA="$(sha256sum "$TMP/$ARCHIVE" | cut -d' ' -f1)"
echo "SHA256: $SHA"

if [ -f "$SUMS" ]; then
  EXPECTED="$(grep -F "$ARCHIVE" "$SUMS" | awk '{print $1}' | head -1 || true)"
  if [ -n "$EXPECTED" ] && [ "$EXPECTED" != "$SHA" ]; then
    echo "ABBRUCH: Pruefsumme weicht ab."
    echo "  erwartet: $EXPECTED"
    echo "  erhalten: $SHA"
    exit 1
  fi
else
  echo "$SHA  $ARCHIVE" > "$SUMS"
  echo "Pruefsumme in scripts/upscaler_checksum.txt festgehalten (erster Abgleich)."
fi

mkdir -p "$TARGET"
if command -v unzip >/dev/null; then
  unzip -q -o "$TMP/$ARCHIVE" -d "$TARGET"
else
  python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$TMP/$ARCHIVE" "$TARGET"
fi

echo
echo "Modelle:"
ls -1 "$TARGET/models" 2>/dev/null | sed 's/^/  /' | head -12
echo
echo "Fertig: $TARGET"
echo "Die Pipeline sucht genau hier:"
echo "  config/upscale/upscale_objects.sh   -> tools/realesrgan-ncnn-vulkan-v0.2.0-windows/realesrgan-ncnn-vulkan.exe"
echo "  config/upscale/batch_upscale.sh     -> dieselbe Ablage"
echo "Modell laut Pipeline: realesrgan-x4plus-anime"
