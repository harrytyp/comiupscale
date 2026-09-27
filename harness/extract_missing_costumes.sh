#!/usr/bin/env bash
# Schliesst die Luecke bei den Kostuemtexturen der Schiffskampfkarten.
# Raum 40 hat 202 Dateien, die Raeume 41, 42 und 43 haben keine einzige, weshalb dort
# ein Teil der Schiffe aus der 8-Bit-Ebene kommt und Segel und Schatten nicht zusammenpassen.
#
# Schritt 1: Kostueme aus den Spieldaten extrahieren
# Schritt 2: nur die fehlenden Raumnummern uebernehmen
set -u
REPO=/opt/data/local/comi-hd-repo
PY=$REPO/.venv-upscale/bin/python
GAME=$REPO/release/linux/game/COMI.LA0
RAW=/tmp/comi_costumes_raw
HD=$REPO/release/linux/hd/costumes

echo "=== Spieldaten und Extraktor ==="
ls -la "$GAME" | awk '{print $5, $9}'
ls -la "$REPO/scripts/extract_costumes_fixed.py" | awk '{print $5, $9}'

echo "=== Schritt 1: extrahieren ==="
rm -rf "$RAW"; mkdir -p "$RAW"
"$PY" "$REPO/scripts/extract_costumes_fixed.py" "$GAME" "$RAW" 2>&1 | tail -8
echo "extract=$?"
echo "Dateien im Rohauszug: $(ls "$RAW" 2>/dev/null | wc -l)"
echo "Hinweis: der Extraktor legt seine Ausgabe moeglicherweise in Unterordnern ab."
find "$RAW" -name "*.png" 2>/dev/null | wc -l

echo "=== Schritt 2: welche Raumnummern fehlen im Paket? ==="
for R in 0040 0041 0042 0043; do
	SD=$(find "$RAW" -name "LFLF_${R}_*.png" 2>/dev/null | wc -l)
	HDN=$(ls "$HD" 2>/dev/null | grep -c "^LFLF_${R}_")
	echo "  Raum $R: im Rohauszug $SD, im HD-Paket $HDN"
done
echo "LUECKE_GEMESSEN"
