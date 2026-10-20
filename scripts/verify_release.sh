#!/usr/bin/env bash
# Pruef-Tor fuer einen Release-Stand. Ein Aufruf, klare Rueckmeldung, Rueckgabewert 0 nur
# wenn alles stimmt.
#
#   bash scripts/verify_release.sh
#
# Geprueft wird:
#   1. Engine-Binary vorhanden und startfaehig
#   2. HD-Assets gegen die Pruefsummenliste (docs/asset-manifest.txt)
#   3. Texture-Packs enthalten jede Asset-Datei genau einmal
#   4. Raumvergleich: kein Raum ueber 10 Prozent starker Abweichung, Mittel unter 1 Prozent
#      (Grundlage: harness/final_sweep.py, Ergebnis in reports/final_save/gleicher_frame.csv)
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
PY="$ROOT/venv/bin/python3"
[ -x "$PY" ] || PY=python3
FEHLER=0

sag() { printf '%-46s %s\n' "$1" "$2"; }
ok()  { sag "$1" "ok"; }
bad() { sag "$1" "FEHLER"; FEHLER=$((FEHLER + 1)); }

echo "== 1. Engine"
BIN="$ROOT/release/linux/scummvm"
if [ -x "$BIN" ]; then
    VERSION="$("$BIN" --version 2>/dev/null | head -1)"
    ok "release/linux/scummvm (${VERSION:-Version unbekannt})"
else
    bad "release/linux/scummvm fehlt"
fi

echo "== 1b. Windows-Binary"
WIN="$ROOT/release/windows/scummvm.exe"
if [ -f "$WIN" ]; then
    QUELLE="$(git -C "$ROOT" log -1 --format=%ct -- scummvm/fork/engines/scumm 2>/dev/null || echo 0)"
    BIN_ZEIT="$(stat -c %Y "$WIN" 2>/dev/null || echo 0)"
    if [ "$BIN_ZEIT" -ge "$QUELLE" ]; then
        ok "release/windows/scummvm.exe juenger als die Quellen"
    else
        bad "release/windows/scummvm.exe aelter als die Quellen (siehe docs/BUILD_WINDOWS.md)"
    fi
else
    bad "release/windows/scummvm.exe fehlt (siehe docs/BUILD_WINDOWS.md)"
fi

echo "== 2. HD-Assets"
if "$PY" scripts/asset_manifest.py --check > /tmp/hd_manifest_check.log 2>&1; then
    ok "Pruefsummen ($(grep -c . docs/asset-manifest.txt) Zeilen)"
else
    bad "Pruefsummen weichen ab (siehe /tmp/hd_manifest_check.log)"
    tail -5 /tmp/hd_manifest_check.log
fi

echo "== 3. Texture-Packs"
if "$PY" scripts/check_texture_packs.py > /tmp/hd_pack_check.log 2>&1; then
    ok "$(head -2 /tmp/hd_pack_check.log | tail -1)"
else
    bad "Packs unvollstaendig oder doppelt (siehe /tmp/hd_pack_check.log)"
    tail -5 /tmp/hd_pack_check.log
fi

echo "== 4. Raumvergleich"
# Erwartete Raeume aus den Soll-Aufnahmen; ein Messergebnis muss sie alle abdecken.
ERWARTET="/opt/data/projects/comi-hd/work/rooms_expected.txt"
mkdir -p "$(dirname "$ERWARTET")"
find /opt/data/projects/comi-hd/reports/sd -maxdepth 1 -type d -name "[0-9]*" -printf "%f\n" | sort -n > "$ERWARTET"
# Ausnahmen abziehen: Raeume, die der Pruefstand nicht anspringen kann (docs/rooms-excluded.txt).
AUSNAHMEN="$ROOT/docs/rooms-excluded.txt"
if [ -f "$AUSNAHMEN" ]; then
    AUSGENOMMEN="$(grep -E '^[0-9]+' "$AUSNAHMEN" | cut -d' ' -f1 | sort -n)"
    for r in $AUSGENOMMEN; do
        grep -vx "$r" "$ERWARTET" > "$ERWARTET.tmp" && mv "$ERWARTET.tmp" "$ERWARTET"
    done
    echo "   ausgenommen: $(echo $AUSGENOMMEN | tr '\n' ' ')"
fi
CSV="$(ls -t /opt/data/projects/comi-hd/reports/final_save*/gleicher_frame.csv 2>/dev/null | head -1)"
if [ -s "$CSV" ]; then
    # Ein Messergebnis, das aelter ist als die Engine, sagt nichts ueber diesen Stand.
    if [ "$BIN" -nt "$CSV" ]; then
        bad "Messergebnis aelter als die Engine ($(basename "$(dirname "$CSV")")); neu messen mit harness/final_sweep.py"
        CSV=""
    fi
fi
if [ -s "$CSV" ]; then
    "$PY" - "$CSV" "$ERWARTET" <<'PY'
import csv, sys

csv_pfad, erwartet_pfad = sys.argv[1], sys.argv[2]
rows = list(csv.DictReader(open(csv_pfad), delimiter=";"))
gemessen = {r["raum"] for r in rows}
werte = [float(r["ueber40_prozent"]) for r in rows if r.get("ueber40_prozent")]

# Vollstaendigkeit: ein Teil der Raeume als "innerhalb der Schwellen" durchzuwinken ist
# kein Nachweis. Fehlende Raeume zaehlen als offener Punkt.
erwartet = {z.strip() for z in open(erwartet_pfad) if z.strip()}
fehlt = sorted(erwartet - gemessen)

if not werte:
    print("keine Werte")
    sys.exit(2)
schlecht = sorted(r["raum"] for r in rows if float(r["ueber40_prozent"]) > 10)
mittel = sum(werte) / len(werte)
print("Raeume %d von %d, Mittel %.2f%%, ueber 10%%: %d %s" %
      (len(gemessen), len(erwartet), mittel, len(schlecht), schlecht[:8]))
if fehlt:
    print("fehlende Raeume: %d %s" % (len(fehlt), fehlt[:12]))
sys.exit(0 if (not schlecht and not fehlt and mittel < 1.0) else 1)
PY
    if [ $? -eq 0 ]; then ok "Raumvergleich innerhalb der Schwellen"; else bad "Raumvergleich ueber Schwelle"; fi
else
    bad "kein Messergebnis (keine gleicher_frame.csv gefunden)"
fi

echo
if [ "$FEHLER" -eq 0 ]; then
    echo "GESAMT: bestanden"
    exit 0
fi
echo "GESAMT: $FEHLER Punkt(e) offen"
exit 1
